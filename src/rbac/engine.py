"""
RBAC Policy Engine - Cedar-style policy evaluation.

Manages policy definitions and evaluates access requests against them.
"""

from typing import Any
from collections import defaultdict

import structlog

from src.rbac.models import (
    Role,
    AccessLevel,
    ResourceType,
    UserContext,
    AccessPolicy,
    AccessDecision,
)

logger = structlog.get_logger()


class PolicyEngine:
    """
    Central policy engine for RBAC decisions.

    Implements a Cedar-style policy evaluation system with:
    - Hierarchical role inheritance
    - Condition-based policies
    - Scope filtering for partial access
    """

    def __init__(self):
        self._policies: dict[str, AccessPolicy] = {}
        self._role_policies: dict[Role, list[AccessPolicy]] = defaultdict(list)
        self._resource_policies: dict[ResourceType, list[AccessPolicy]] = defaultdict(
            list
        )

        # Initialize default policies
        self._initialize_default_policies()

    def _initialize_default_policies(self) -> None:
        """Initialize the default RBAC policies for the system."""

        # ============================================================
        # CEO POLICIES - Full company-wide access
        # ============================================================
        self.register_policy(
            AccessPolicy(
                policy_id="ceo-global-knowledge",
                role=Role.CEO,
                resource=ResourceType.KNOWLEDGE_GLOBAL,
                access_level=AccessLevel.ADMIN,
                description="CEO has full access to all knowledge",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="ceo-company-dashboard",
                role=Role.CEO,
                resource=ResourceType.DASHBOARD_COMPANY,
                access_level=AccessLevel.ADMIN,
                description="CEO can view and configure company dashboards",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="ceo-all-analytics",
                role=Role.CEO,
                resource=ResourceType.TEAM_ANALYTICS,
                access_level=AccessLevel.READ,
                description="CEO can view all team analytics",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="ceo-org-memory",
                role=Role.CEO,
                resource=ResourceType.MEMORY_ORG,
                access_level=AccessLevel.ADMIN,
                description="CEO has full access to organizational memory",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="ceo-ownership-lookup",
                role=Role.CEO,
                resource=ResourceType.OWNERSHIP_LOOKUP,
                access_level=AccessLevel.READ,
                description="CEO can look up ownership across company",
            )
        )

        # ============================================================
        # LEADERSHIP POLICIES - Department-level access
        # ============================================================
        self.register_policy(
            AccessPolicy(
                policy_id="leadership-dept-knowledge",
                role=Role.LEADERSHIP,
                resource=ResourceType.KNOWLEDGE_DEPARTMENT,
                access_level=AccessLevel.WRITE,
                conditions={"same_department": True},
                description="Leadership has write access to department knowledge",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="leadership-dept-dashboard",
                role=Role.LEADERSHIP,
                resource=ResourceType.DASHBOARD_DEPARTMENT,
                access_level=AccessLevel.ADMIN,
                conditions={"same_department": True},
                description="Leadership can manage department dashboards",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="leadership-team-analytics",
                role=Role.LEADERSHIP,
                resource=ResourceType.TEAM_ANALYTICS,
                access_level=AccessLevel.READ,
                conditions={"same_department": True},
                description="Leadership can view team analytics in their department",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="leadership-team-memory",
                role=Role.LEADERSHIP,
                resource=ResourceType.MEMORY_TEAM,
                access_level=AccessLevel.READ,
                conditions={"same_department": True},
                description="Leadership can read team memory in their department",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="leadership-ownership-dept",
                role=Role.LEADERSHIP,
                resource=ResourceType.OWNERSHIP_LOOKUP,
                access_level=AccessLevel.READ,
                conditions={"same_department": True},
                description="Leadership can look up ownership in their department",
            )
        )

        # ============================================================
        # MANAGER POLICIES - Team-level access
        # ============================================================
        self.register_policy(
            AccessPolicy(
                policy_id="manager-team-knowledge",
                role=Role.MANAGER,
                resource=ResourceType.KNOWLEDGE_TEAM,
                access_level=AccessLevel.WRITE,
                conditions={"same_team": True},
                description="Managers have write access to team knowledge",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="manager-team-dashboard",
                role=Role.MANAGER,
                resource=ResourceType.DASHBOARD_TEAM,
                access_level=AccessLevel.ADMIN,
                conditions={"same_team": True},
                description="Managers can manage team dashboards",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="manager-team-members",
                role=Role.MANAGER,
                resource=ResourceType.TEAM_MEMBERS,
                access_level=AccessLevel.READ,
                conditions={"same_team": True},
                description="Managers can view team member information",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="manager-team-workload",
                role=Role.MANAGER,
                resource=ResourceType.TEAM_WORKLOAD,
                access_level=AccessLevel.READ,
                conditions={"same_team": True},
                description="Managers can view team workload",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="manager-team-analytics",
                role=Role.MANAGER,
                resource=ResourceType.TEAM_ANALYTICS,
                access_level=AccessLevel.READ,
                conditions={"same_team": True},
                description="Managers can view their team's analytics",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="manager-team-memory",
                role=Role.MANAGER,
                resource=ResourceType.MEMORY_TEAM,
                access_level=AccessLevel.WRITE,
                conditions={"same_team": True},
                description="Managers can read/write team memory",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="manager-ownership-team",
                role=Role.MANAGER,
                resource=ResourceType.OWNERSHIP_LOOKUP,
                access_level=AccessLevel.READ,
                conditions={"same_team": True},
                description="Managers can look up ownership in their team",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="manager-mcp-jira",
                role=Role.MANAGER,
                resource=ResourceType.MCP_JIRA,
                access_level=AccessLevel.READ,
                conditions={"same_team": True},
                description="Managers can access Jira for their team",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="manager-mcp-github",
                role=Role.MANAGER,
                resource=ResourceType.MCP_GITHUB,
                access_level=AccessLevel.READ,
                conditions={"same_team": True},
                description="Managers can access GitHub for their team",
            )
        )

        # ============================================================
        # IC (INDIVIDUAL CONTRIBUTOR) POLICIES - Team-scoped access
        # ============================================================
        self.register_policy(
            AccessPolicy(
                policy_id="ic-team-knowledge-read",
                role=Role.IC,
                resource=ResourceType.KNOWLEDGE_TEAM,
                access_level=AccessLevel.READ,
                conditions={"same_team": True},
                description="ICs can read team knowledge",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="ic-personal-knowledge",
                role=Role.IC,
                resource=ResourceType.KNOWLEDGE_PERSONAL,
                access_level=AccessLevel.WRITE,
                conditions={"is_owner": True},
                description="ICs have full access to their personal knowledge",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="ic-personal-dashboard",
                role=Role.IC,
                resource=ResourceType.DASHBOARD_PERSONAL,
                access_level=AccessLevel.WRITE,
                conditions={"is_owner": True},
                description="ICs can manage their personal dashboard",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="ic-user-memory",
                role=Role.IC,
                resource=ResourceType.MEMORY_USER,
                access_level=AccessLevel.WRITE,
                conditions={"is_owner": True},
                description="ICs have full access to their personal memory",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="ic-chat",
                role=Role.IC,
                resource=ResourceType.CHAT,
                access_level=AccessLevel.WRITE,
                description="ICs can use chat",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="ic-ownership-team",
                role=Role.IC,
                resource=ResourceType.OWNERSHIP_LOOKUP,
                access_level=AccessLevel.READ,
                conditions={"same_team": True},
                description="ICs can look up ownership in their team",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="ic-mcp-jira-own",
                role=Role.IC,
                resource=ResourceType.MCP_JIRA,
                access_level=AccessLevel.READ,
                conditions={"is_owner": True},
                description="ICs can access their own Jira tickets",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="ic-mcp-github-own",
                role=Role.IC,
                resource=ResourceType.MCP_GITHUB,
                access_level=AccessLevel.READ,
                conditions={"is_owner": True},
                description="ICs can access their own GitHub activity",
            )
        )

        # ============================================================
        # NEW EMPLOYEE POLICIES - Onboarding-focused access
        # ============================================================
        self.register_policy(
            AccessPolicy(
                policy_id="new-onboarding-flows",
                role=Role.NEW_EMPLOYEE,
                resource=ResourceType.ONBOARDING_FLOWS,
                access_level=AccessLevel.READ,
                description="New employees can access onboarding flows",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="new-onboarding-progress",
                role=Role.NEW_EMPLOYEE,
                resource=ResourceType.ONBOARDING_PROGRESS,
                access_level=AccessLevel.WRITE,
                conditions={"is_owner": True},
                description="New employees can update their onboarding progress",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="new-team-knowledge-limited",
                role=Role.NEW_EMPLOYEE,
                resource=ResourceType.KNOWLEDGE_TEAM,
                access_level=AccessLevel.READ,
                conditions={"same_team": True, "max_hierarchy_depth": 2},
                description="New employees have limited team knowledge access",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="new-chat",
                role=Role.NEW_EMPLOYEE,
                resource=ResourceType.CHAT,
                access_level=AccessLevel.WRITE,
                description="New employees can use chat for onboarding help",
            )
        )
        self.register_policy(
            AccessPolicy(
                policy_id="new-ownership-team-limited",
                role=Role.NEW_EMPLOYEE,
                resource=ResourceType.OWNERSHIP_LOOKUP,
                access_level=AccessLevel.READ,
                conditions={"same_team": True},
                description="New employees can find contacts in their team",
            )
        )

        # ============================================================
        # COMMON POLICIES - Apply to multiple roles
        # ============================================================
        for role in [Role.IC, Role.MANAGER, Role.LEADERSHIP, Role.CEO]:
            self.register_policy(
                AccessPolicy(
                    policy_id=f"{role.name.lower()}-chat",
                    role=role,
                    resource=ResourceType.CHAT,
                    access_level=AccessLevel.WRITE,
                    description=f"{role.name} can use chat",
                )
            )
            self.register_policy(
                AccessPolicy(
                    policy_id=f"{role.name.lower()}-chat-history-own",
                    role=role,
                    resource=ResourceType.CHAT_HISTORY,
                    access_level=AccessLevel.READ,
                    conditions={"is_owner": True},
                    description=f"{role.name} can view their own chat history",
                )
            )

        logger.info(
            "RBAC policies initialized",
            policy_count=len(self._policies),
        )

    def register_policy(self, policy: AccessPolicy) -> None:
        """Register a new policy."""
        self._policies[policy.policy_id] = policy
        self._role_policies[policy.role].append(policy)
        self._resource_policies[policy.resource].append(policy)

    def unregister_policy(self, policy_id: str) -> bool:
        """Remove a policy by ID."""
        if policy_id not in self._policies:
            return False

        policy = self._policies.pop(policy_id)
        self._role_policies[policy.role].remove(policy)
        self._resource_policies[policy.resource].remove(policy)
        return True

    def evaluate(
        self,
        context: UserContext,
        resource: ResourceType,
        required_level: AccessLevel,
        resource_attrs: dict[str, Any] | None = None,
    ) -> AccessDecision:
        """
        Evaluate access request against policies.

        Args:
            context: User context for the request
            resource: Resource being accessed
            required_level: Required access level
            resource_attrs: Additional resource attributes for condition evaluation

        Returns:
            AccessDecision with allow/deny and scope filters
        """
        resource_attrs = resource_attrs or {}

        # Add context-derived attributes
        resource_attrs.setdefault("owner_id", context.user_id)

        # Get applicable policies (check role and higher roles for inheritance)
        applicable_policies = self._get_applicable_policies(context, resource)

        if not applicable_policies:
            return AccessDecision.deny(
                f"No policies found for role {context.role.name} on resource {resource.value}",
                resource=resource,
            )

        # Sort by priority (highest first)
        applicable_policies.sort(key=lambda p: p.priority, reverse=True)

        # Evaluate each policy
        for policy in applicable_policies:
            if policy.evaluate(context, resource_attrs):
                if policy.access_level == AccessLevel.NONE:
                    return AccessDecision.deny(
                        f"Access denied by policy {policy.policy_id}",
                        resource=resource,
                    )

                if policy.allows(required_level):
                    # Build scope filters based on conditions
                    scope_filters = self._build_scope_filters(
                        context, policy, resource_attrs
                    )

                    decision = AccessDecision.allow(
                        policy_id=policy.policy_id,
                        resource=resource,
                        access_level=policy.access_level,
                        scope_filters=scope_filters,
                    )
                    decision.context_snapshot = context.to_dict()

                    logger.debug(
                        "Access granted",
                        user_id=context.user_id,
                        role=context.role.name,
                        resource=resource.value,
                        policy_id=policy.policy_id,
                    )

                    return decision

        return AccessDecision.deny(
            f"No policy grants {required_level.value} access to {resource.value}",
            resource=resource,
        )

    def _get_applicable_policies(
        self, context: UserContext, resource: ResourceType
    ) -> list[AccessPolicy]:
        """Get all policies applicable to the context and resource."""
        policies = []

        # Get policies for the user's role
        for policy in self._resource_policies.get(resource, []):
            if policy.role == context.role and policy.enabled:
                policies.append(policy)

        # For higher roles, check if they have inherited access
        # (e.g., CEO inherits all lower role permissions)
        if context.role.value >= Role.LEADERSHIP.value:
            for policy in self._resource_policies.get(resource, []):
                if (
                    policy.role.value < context.role.value
                    and policy.enabled
                    and policy not in policies
                ):
                    # Create an inherited policy with the user's actual role
                    inherited = AccessPolicy(
                        policy_id=f"{policy.policy_id}-inherited",
                        role=context.role,
                        resource=policy.resource,
                        access_level=policy.access_level,
                        conditions={},  # Remove scope conditions for inheritance
                        description=f"Inherited from {policy.policy_id}",
                        priority=policy.priority - 1,  # Lower priority than direct policies
                    )
                    policies.append(inherited)

        return policies

    def _build_scope_filters(
        self,
        context: UserContext,
        policy: AccessPolicy,
        resource_attrs: dict[str, Any],
    ) -> dict[str, Any]:
        """Build scope filters based on policy conditions."""
        filters = {}

        if policy.conditions.get("same_team"):
            filters["team_id"] = context.team_id

        if policy.conditions.get("same_department"):
            filters["department_id"] = context.department_id

        if policy.conditions.get("is_owner"):
            filters["owner_id"] = context.user_id

        if policy.conditions.get("project_member"):
            filters["project_ids"] = context.project_ids

        if "max_hierarchy_depth" in policy.conditions:
            filters["max_depth"] = policy.conditions["max_hierarchy_depth"]

        return filters

    def get_permissions_for_role(self, role: Role) -> list[dict[str, Any]]:
        """Get all permissions for a role (for UI display)."""
        permissions = []
        for policy in self._role_policies.get(role, []):
            if policy.enabled:
                permissions.append(
                    {
                        "resource": policy.resource.value,
                        "access_level": policy.access_level.value,
                        "conditions": policy.conditions,
                        "description": policy.description,
                    }
                )
        return permissions

    def check_quick(
        self,
        context: UserContext,
        resource: ResourceType,
        required_level: AccessLevel = AccessLevel.READ,
    ) -> bool:
        """Quick check for access (returns bool only)."""
        decision = self.evaluate(context, resource, required_level)
        return decision.allowed


# Global policy engine instance
policy_engine = PolicyEngine()
