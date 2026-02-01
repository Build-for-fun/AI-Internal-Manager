"""
Agent Guard - RBAC enforcement for LLM agents.

Ensures all agent responses are filtered through role + team context.
"""

from typing import Any

import structlog

from src.rbac.models import UserContext, ResourceType, AccessLevel
from src.rbac.guards import rbac_guard
from src.security.audit import audit_logger

logger = structlog.get_logger()


class AgentGuard:
    """
    Guards agent interactions with RBAC enforcement.

    Key responsibilities:
    1. Filter context provided to agents based on user permissions
    2. Scope tool calls to permitted data
    3. Filter agent responses before returning to user
    4. Audit all agent interactions
    """

    def __init__(self):
        self.guard = rbac_guard

    def build_agent_context(
        self,
        context: UserContext,
        query: str,
    ) -> dict[str, Any]:
        """
        Build context dict to pass to agents with RBAC constraints.

        The agent receives this context and must operate within its bounds.
        """
        # Get user's permissions and scopes
        knowledge_scope = self.guard.get_knowledge_scope(context)
        mcp_permissions = self.guard.get_mcp_tool_permissions(context)
        dashboard_config = self.guard.get_dashboard_config(context)

        return {
            # User identity (limited info)
            "user_id": context.user_id,
            "user_role": context.role.name,
            "user_team": context.team_id,
            "user_department": context.department_id,
            # Access constraints
            "knowledge_scope": knowledge_scope,
            "mcp_permissions": mcp_permissions,
            "dashboard_widgets": dashboard_config["widgets"],
            "data_scope": dashboard_config["data_scope"],
            # Query context
            "query": query,
            # Flags
            "is_new_employee": context.role.name == "NEW_EMPLOYEE",
            "can_see_cross_team": context.role.value >= 4,  # Leadership+
            "can_see_sensitive": context.role.value >= 4,
        }

    def get_system_prompt_additions(self, context: UserContext) -> str:
        """
        Get RBAC-aware additions to the system prompt.

        These instructions tell the agent what it can and cannot access.
        """
        role_name = context.role.name
        constraints = []

        # Role-specific constraints
        if role_name == "NEW_EMPLOYEE":
            constraints.extend(
                [
                    "The user is a new employee in onboarding.",
                    "Only provide information relevant to their team and onboarding process.",
                    "Do not reveal sensitive business metrics or cross-team data.",
                    "Focus on helping them learn and get started.",
                    "Recommend they contact their manager for access to restricted information.",
                ]
            )
        elif role_name == "IC":
            constraints.extend(
                [
                    "The user is an individual contributor.",
                    f"They have access to their team ({context.team_id}) data only.",
                    "Do not reveal information about other teams unless it's publicly shared.",
                    "For cross-team questions, suggest they contact the relevant team.",
                ]
            )
        elif role_name == "MANAGER":
            constraints.extend(
                [
                    "The user is a team manager.",
                    f"They have access to their team ({context.team_id}) data.",
                    "They can see team member workloads and analytics.",
                    "Do not reveal other teams' private data or sensitive HR information.",
                ]
            )
        elif role_name == "LEADERSHIP":
            constraints.extend(
                [
                    "The user is in leadership.",
                    f"They have access to department-level ({context.department_id}) data.",
                    "They can see cross-team analytics within their department.",
                    "Exercise discretion with highly sensitive information.",
                ]
            )
        elif role_name == "CEO":
            constraints.extend(
                [
                    "The user has executive access.",
                    "They can access company-wide data and analytics.",
                    "Provide comprehensive information while maintaining professionalism.",
                ]
            )

        # Build prompt addition
        prompt = "\n## Access Control Constraints\n"
        prompt += "You MUST follow these constraints based on the user's role:\n"
        for constraint in constraints:
            prompt += f"- {constraint}\n"

        prompt += "\nIf asked for information outside these constraints, politely explain "
        prompt += "that the user doesn't have access and suggest who they could contact.\n"

        return prompt

    def filter_retrieved_context(
        self,
        context: UserContext,
        retrieved_docs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Filter retrieved documents based on user permissions.

        Called before documents are passed to the LLM for response generation.
        """
        filtered = []
        knowledge_scope = self.guard.get_knowledge_scope(context)

        for doc in retrieved_docs:
            # Check if document is within user's scope
            doc_team = doc.get("team_id")
            doc_dept = doc.get("department_id")
            doc_depth = doc.get("hierarchy_depth", 0)

            # Apply scope filters
            if knowledge_scope.get("filters"):
                filters = knowledge_scope["filters"]

                if "team_id" in filters and doc_team and doc_team != filters["team_id"]:
                    continue

                if (
                    "department_id" in filters
                    and doc_dept
                    and doc_dept != filters["department_id"]
                ):
                    continue

                if (
                    "onboarding_visible" in filters
                    and not doc.get("onboarding_visible", False)
                ):
                    continue

            # Check depth constraint
            max_depth = knowledge_scope.get("max_depth", 10)
            if doc_depth > max_depth:
                continue

            filtered.append(doc)

        logger.debug(
            "Context filtered",
            original_count=len(retrieved_docs),
            filtered_count=len(filtered),
            user_id=context.user_id,
        )

        return filtered

    def filter_agent_response(
        self,
        context: UserContext,
        response: str,
        sources: list[dict[str, Any]] | None = None,
        agent_name: str = "unknown",
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Filter agent response before returning to user.

        Ensures no sensitive information leaks through.
        """
        # Use the main guard's filtering
        filtered_response, filtered_sources = self.guard.filter_chat_response(
            context=context,
            response=response,
            sources=sources,
        )

        # Check if filtering occurred
        response_filtered = filtered_response != response
        sources_filtered = sources and filtered_sources != sources

        # Audit the interaction
        audit_logger.log_chat_interaction(
            context=context,
            query="[agent response]",
            response=filtered_response[:500],  # Truncate for logging
            agent=agent_name,
            sources_count=len(filtered_sources) if filtered_sources else 0,
            filtered=response_filtered or sources_filtered,
        )

        return filtered_response, filtered_sources

    def check_tool_permission(
        self,
        context: UserContext,
        tool_name: str,
        tool_params: dict[str, Any] | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Check if user can use a specific tool and get scope constraints.

        Returns (allowed, scope_filters).
        """
        # Map tool names to resource types
        tool_resource_map = {
            "jira_search": ResourceType.MCP_JIRA,
            "jira_get_issue": ResourceType.MCP_JIRA,
            "jira_get_sprint": ResourceType.MCP_JIRA,
            "github_search": ResourceType.MCP_GITHUB,
            "github_get_pr": ResourceType.MCP_GITHUB,
            "github_get_commits": ResourceType.MCP_GITHUB,
            "slack_search": ResourceType.MCP_SLACK,
            "slack_get_channel": ResourceType.MCP_SLACK,
            "knowledge_search": ResourceType.KNOWLEDGE_TEAM,
            "team_analytics": ResourceType.TEAM_ANALYTICS,
            "ownership_lookup": ResourceType.OWNERSHIP_LOOKUP,
        }

        resource = tool_resource_map.get(tool_name)
        if not resource:
            logger.warning("Unknown tool", tool=tool_name)
            return False, {}

        decision = self.guard.check_access(
            context=context,
            resource=resource,
            required_level=AccessLevel.READ,
            resource_attrs=tool_params or {},
        )

        # Audit the tool call
        audit_logger.log_mcp_tool_call(
            context=context,
            tool_name=tool_name,
            allowed=decision.allowed,
            scope=decision.scope_filters if decision.allowed else None,
        )

        return decision.allowed, decision.scope_filters

    def apply_tool_scope(
        self,
        tool_params: dict[str, Any],
        scope_filters: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Apply scope filters to tool parameters.

        Ensures tool calls are constrained to permitted data.
        """
        scoped_params = tool_params.copy()

        # Apply filters
        if "team_id" in scope_filters:
            scoped_params["team_id"] = scope_filters["team_id"]
            scoped_params["team_filter"] = scope_filters["team_id"]

        if "department_id" in scope_filters:
            scoped_params["department_id"] = scope_filters["department_id"]

        if "owner_id" in scope_filters:
            scoped_params["owner_id"] = scope_filters["owner_id"]
            scoped_params["assignee"] = scope_filters["owner_id"]

        if "project_ids" in scope_filters:
            scoped_params["project_ids"] = scope_filters["project_ids"]

        if "max_depth" in scope_filters:
            scoped_params["max_depth"] = scope_filters["max_depth"]

        return scoped_params


# Global agent guard instance
agent_guard = AgentGuard()


# Convenience functions for agents
def get_agent_context(context: UserContext, query: str) -> dict[str, Any]:
    """Get RBAC-aware context for an agent."""
    return agent_guard.build_agent_context(context, query)


def get_rbac_system_prompt(context: UserContext) -> str:
    """Get RBAC additions for system prompt."""
    return agent_guard.get_system_prompt_additions(context)


def filter_for_user(
    context: UserContext,
    response: str,
    sources: list[dict] | None = None,
    agent: str = "unknown",
) -> tuple[str, list[dict]]:
    """Filter agent response for user."""
    return agent_guard.filter_agent_response(context, response, sources, agent)
