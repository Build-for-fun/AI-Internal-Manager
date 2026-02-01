"""
RBAC Guards - Enforcement points for access control.

Provides decorators and utilities for enforcing RBAC at various system points:
- API endpoints
- Agent responses
- Knowledge graph queries
- Memory access
- MCP tool calls
"""

from functools import wraps
from typing import Any, Callable, TypeVar

import structlog

from src.rbac.models import (
    Role,
    AccessLevel,
    ResourceType,
    UserContext,
    AccessDecision,
)
from src.rbac.engine import policy_engine

logger = structlog.get_logger()

F = TypeVar("F", bound=Callable[..., Any])


class RBACGuard:
    """
    Central RBAC guard for enforcing access control.

    Provides methods for:
    - Checking access before operations
    - Filtering responses based on permissions
    - Scoping queries based on role
    - Auditing access decisions
    """

    def __init__(self):
        self.engine = policy_engine
        self._audit_handlers: list[Callable[[AccessDecision, UserContext], None]] = []

    def register_audit_handler(
        self, handler: Callable[[AccessDecision, UserContext], None]
    ) -> None:
        """Register a handler to be called for audit logging."""
        self._audit_handlers.append(handler)

    def _audit(self, decision: AccessDecision, context: UserContext) -> None:
        """Log access decision for audit purposes."""
        logger.info(
            "RBAC access decision",
            allowed=decision.allowed,
            user_id=context.user_id,
            role=context.role.name,
            resource=decision.resource.value if decision.resource else None,
            reason=decision.reason,
            policy_id=decision.policy_id,
        )

        for handler in self._audit_handlers:
            try:
                handler(decision, context)
            except Exception as e:
                logger.error("Audit handler failed", error=str(e))

    def check_access(
        self,
        context: UserContext,
        resource: ResourceType,
        required_level: AccessLevel = AccessLevel.READ,
        resource_attrs: dict[str, Any] | None = None,
    ) -> AccessDecision:
        """
        Check if access is allowed and return decision with scope filters.

        This is the primary method for access control checks.
        """
        decision = self.engine.evaluate(
            context=context,
            resource=resource,
            required_level=required_level,
            resource_attrs=resource_attrs,
        )

        self._audit(decision, context)
        return decision

    def require_access(
        self,
        context: UserContext,
        resource: ResourceType,
        required_level: AccessLevel = AccessLevel.READ,
        resource_attrs: dict[str, Any] | None = None,
    ) -> AccessDecision:
        """
        Check access and raise exception if denied.

        Use this when access denial should abort the operation.
        """
        decision = self.check_access(
            context=context,
            resource=resource,
            required_level=required_level,
            resource_attrs=resource_attrs,
        )

        if not decision.allowed:
            raise PermissionError(
                f"Access denied: {decision.reason}"
            )

        return decision

    def filter_chat_response(
        self,
        context: UserContext,
        response: str,
        sources: list[dict[str, Any]] | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Filter chat response based on user's access level.

        Removes or redacts information the user shouldn't see.
        """
        filtered_sources = []

        if sources:
            for source in sources:
                # Check if user can access each source
                source_resource = self._map_source_to_resource(source)
                source_attrs = {
                    "team_id": source.get("team_id"),
                    "department_id": source.get("department_id"),
                    "owner_id": source.get("owner_id"),
                }

                decision = self.check_access(
                    context=context,
                    resource=source_resource,
                    resource_attrs=source_attrs,
                )

                if decision.allowed:
                    filtered_sources.append(source)
                else:
                    # Add redacted placeholder
                    filtered_sources.append(
                        {
                            "title": "[Restricted]",
                            "type": source.get("type"),
                            "access_denied": True,
                        }
                    )

        # Filter sensitive patterns from response based on role
        filtered_response = self._filter_response_content(context, response)

        return filtered_response, filtered_sources

    def _filter_response_content(self, context: UserContext, response: str) -> str:
        """Filter sensitive content from response based on role."""
        if context.role.value >= Role.LEADERSHIP.value:
            # Leadership and above see everything
            return response

        # Define sensitive patterns to redact for lower roles
        sensitive_patterns = [
            (r"salary[:\s]+\$[\d,]+", "[SALARY REDACTED]"),
            (r"compensation[:\s]+\$[\d,]+", "[COMPENSATION REDACTED]"),
            (r"revenue[:\s]+\$[\d,]+[BMK]?", "[REVENUE REDACTED]"),
            (r"budget[:\s]+\$[\d,]+[BMK]?", "[BUDGET REDACTED]"),
        ]

        import re

        filtered = response
        for pattern, replacement in sensitive_patterns:
            if context.role.value < Role.MANAGER.value:
                filtered = re.sub(pattern, replacement, filtered, flags=re.IGNORECASE)

        return filtered

    def _map_source_to_resource(self, source: dict[str, Any]) -> ResourceType:
        """Map a source type to a resource type for access checking."""
        source_type = source.get("type", "").lower()

        mapping = {
            "document": ResourceType.KNOWLEDGE_TEAM,
            "team_doc": ResourceType.KNOWLEDGE_TEAM,
            "department_doc": ResourceType.KNOWLEDGE_DEPARTMENT,
            "company_doc": ResourceType.KNOWLEDGE_GLOBAL,
            "personal": ResourceType.KNOWLEDGE_PERSONAL,
            "jira": ResourceType.MCP_JIRA,
            "github": ResourceType.MCP_GITHUB,
            "slack": ResourceType.MCP_SLACK,
        }

        return mapping.get(source_type, ResourceType.KNOWLEDGE_TEAM)

    def get_knowledge_scope(self, context: UserContext) -> dict[str, Any]:
        """
        Get the knowledge graph traversal scope for a user.

        Returns filters to apply to knowledge queries.
        """
        scope = {
            "allowed_nodes": [],
            "max_depth": 10,
            "filters": {},
        }

        if context.role == Role.CEO:
            # CEO can access everything
            scope["allowed_nodes"] = ["*"]

        elif context.role == Role.LEADERSHIP:
            # Leadership can access their department and below
            scope["allowed_nodes"] = [
                f"department:{context.department_id}",
                f"team:{context.team_id}",
            ]
            scope["filters"]["department_id"] = context.department_id

        elif context.role == Role.MANAGER:
            # Managers can access their team
            scope["allowed_nodes"] = [f"team:{context.team_id}"]
            scope["filters"]["team_id"] = context.team_id

        elif context.role == Role.IC:
            # ICs can access their team with some restrictions
            scope["allowed_nodes"] = [f"team:{context.team_id}"]
            scope["filters"]["team_id"] = context.team_id
            scope["max_depth"] = 5

        elif context.role == Role.NEW_EMPLOYEE:
            # New employees have limited access
            scope["allowed_nodes"] = [f"team:{context.team_id}"]
            scope["filters"]["team_id"] = context.team_id
            scope["filters"]["onboarding_visible"] = True
            scope["max_depth"] = 2

        return scope

    def get_mcp_tool_permissions(
        self, context: UserContext
    ) -> dict[str, dict[str, Any]]:
        """
        Get MCP tool permissions for a user.

        Returns a dict of tool -> permission config.
        """
        permissions = {}

        # Check Jira access
        jira_decision = self.check_access(
            context, ResourceType.MCP_JIRA, AccessLevel.READ
        )
        permissions["jira"] = {
            "allowed": jira_decision.allowed,
            "scope": jira_decision.scope_filters,
            "level": "read" if jira_decision.allowed else "none",
        }

        # Check GitHub access
        github_decision = self.check_access(
            context, ResourceType.MCP_GITHUB, AccessLevel.READ
        )
        permissions["github"] = {
            "allowed": github_decision.allowed,
            "scope": github_decision.scope_filters,
            "level": "read" if github_decision.allowed else "none",
        }

        # Check Slack access
        slack_decision = self.check_access(
            context, ResourceType.MCP_SLACK, AccessLevel.READ
        )
        permissions["slack"] = {
            "allowed": slack_decision.allowed,
            "scope": slack_decision.scope_filters,
            "level": "read" if slack_decision.allowed else "none",
        }

        return permissions

    def get_dashboard_config(self, context: UserContext) -> dict[str, Any]:
        """
        Get dashboard configuration based on user's role.

        Returns which dashboard components the user can see.
        """
        config = {
            "widgets": [],
            "data_scope": {},
            "refresh_interval": 60,
        }

        if context.role == Role.CEO:
            config["widgets"] = [
                "company_overview",
                "all_teams_health",
                "cross_team_analytics",
                "company_okrs",
                "executive_summary",
                "bottleneck_analysis",
                "ownership_map",
            ]
            config["data_scope"] = {"level": "company"}

        elif context.role == Role.LEADERSHIP:
            config["widgets"] = [
                "department_overview",
                "team_health",
                "department_analytics",
                "department_okrs",
                "team_bottlenecks",
                "ownership_map",
            ]
            config["data_scope"] = {
                "level": "department",
                "department_id": context.department_id,
            }

        elif context.role == Role.MANAGER:
            config["widgets"] = [
                "team_overview",
                "sprint_velocity",
                "team_workload",
                "team_analytics",
                "member_status",
                "ownership_lookup",
            ]
            config["data_scope"] = {
                "level": "team",
                "team_id": context.team_id,
            }

        elif context.role == Role.IC:
            config["widgets"] = [
                "personal_tasks",
                "team_activity",
                "my_analytics",
                "team_knowledge",
            ]
            config["data_scope"] = {
                "level": "personal",
                "team_id": context.team_id,
                "user_id": context.user_id,
            }

        elif context.role == Role.NEW_EMPLOYEE:
            config["widgets"] = [
                "onboarding_progress",
                "next_steps",
                "team_introduction",
                "help_resources",
            ]
            config["data_scope"] = {
                "level": "onboarding",
                "user_id": context.user_id,
            }
            config["refresh_interval"] = 300  # Less frequent for new employees

        return config

    def can_view_employee_data(
        self, context: UserContext, target_user_id: str, target_team_id: str
    ) -> bool:
        """Check if user can view another employee's data."""
        # Can always view own data
        if context.user_id == target_user_id:
            return True

        # CEO can view anyone
        if context.role == Role.CEO:
            return True

        # Manager can view their direct reports
        if context.role == Role.MANAGER and context.is_manager_of(target_user_id):
            return True

        # Same team members can see limited data
        if context.same_team(target_team_id):
            return True

        # Leadership can view within their department
        if context.role == Role.LEADERSHIP:
            # Would need to check if target is in same department
            # For now, allow if they have the permission
            decision = self.check_access(
                context,
                ResourceType.TEAM_MEMBERS,
                resource_attrs={"team_id": target_team_id},
            )
            return decision.allowed

        return False


def require_permission(
    resource: ResourceType, level: AccessLevel = AccessLevel.READ
) -> Callable[[F], F]:
    """
    Decorator to require a specific permission for a function.

    The decorated function must have a `context: UserContext` parameter.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            context = kwargs.get("context")
            if not context:
                # Try to find context in args
                for arg in args:
                    if isinstance(arg, UserContext):
                        context = arg
                        break

            if not context:
                raise ValueError("UserContext required for permission check")

            rbac_guard.require_access(context, resource, level)
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            context = kwargs.get("context")
            if not context:
                for arg in args:
                    if isinstance(arg, UserContext):
                        context = arg
                        break

            if not context:
                raise ValueError("UserContext required for permission check")

            rbac_guard.require_access(context, resource, level)
            return func(*args, **kwargs)

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


# Global RBAC guard instance
rbac_guard = RBACGuard()
