"""RBAC models and data structures."""

from enum import Enum, IntEnum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class Role(IntEnum):
    """
    Organizational roles ordered by hierarchy level.
    Higher value = higher privilege level.
    """

    NEW_EMPLOYEE = 1  # Onboarding-only access
    IC = 2  # Individual Contributor - team-level access
    MANAGER = 3  # Team lead - team management access
    LEADERSHIP = 4  # Director/VP - department-level access
    CEO = 5  # Executive - company-wide access

    @classmethod
    def from_string(cls, role_str: str) -> "Role":
        """Convert string to Role enum."""
        mapping = {
            "new_employee": cls.NEW_EMPLOYEE,
            "intern": cls.NEW_EMPLOYEE,
            "ic": cls.IC,
            "individual_contributor": cls.IC,
            "engineer": cls.IC,
            "employee": cls.IC,
            "manager": cls.MANAGER,
            "team_lead": cls.MANAGER,
            "lead": cls.MANAGER,
            "leadership": cls.LEADERSHIP,
            "director": cls.LEADERSHIP,
            "vp": cls.LEADERSHIP,
            "vice_president": cls.LEADERSHIP,
            "ceo": cls.CEO,
            "cto": cls.CEO,
            "cfo": cls.CEO,
            "executive": cls.CEO,
        }
        return mapping.get(role_str.lower(), cls.IC)

    def can_access_role(self, target_role: "Role") -> bool:
        """Check if this role can access data of target role level."""
        return self.value >= target_role.value


class AccessLevel(str, Enum):
    """Access level for resources."""

    NONE = "none"  # No access
    READ = "read"  # Read-only access
    WRITE = "write"  # Read and write access
    ADMIN = "admin"  # Full administrative access


class ResourceType(str, Enum):
    """Types of resources that can be accessed."""

    # Chat & Conversations
    CHAT = "chat"
    CHAT_HISTORY = "chat_history"

    # Knowledge Graph
    KNOWLEDGE_GLOBAL = "knowledge_global"
    KNOWLEDGE_DEPARTMENT = "knowledge_department"
    KNOWLEDGE_TEAM = "knowledge_team"
    KNOWLEDGE_PERSONAL = "knowledge_personal"

    # Memory
    MEMORY_ORG = "memory_org"
    MEMORY_TEAM = "memory_team"
    MEMORY_USER = "memory_user"

    # Analytics & Dashboards
    DASHBOARD_COMPANY = "dashboard_company"
    DASHBOARD_DEPARTMENT = "dashboard_department"
    DASHBOARD_TEAM = "dashboard_team"
    DASHBOARD_PERSONAL = "dashboard_personal"

    # MCP Tools
    MCP_JIRA = "mcp_jira"
    MCP_GITHUB = "mcp_github"
    MCP_SLACK = "mcp_slack"

    # Team Management
    TEAM_MEMBERS = "team_members"
    TEAM_WORKLOAD = "team_workload"
    TEAM_ANALYTICS = "team_analytics"

    # Onboarding
    ONBOARDING_FLOWS = "onboarding_flows"
    ONBOARDING_PROGRESS = "onboarding_progress"

    # Ownership & Recommendations
    OWNERSHIP_LOOKUP = "ownership_lookup"
    EXPERTISE_SEARCH = "expertise_search"


@dataclass
class Permission:
    """A single permission definition."""

    resource: ResourceType
    access_level: AccessLevel
    scope: str | None = None  # Optional scope restriction (team_id, dept_id, etc.)

    def allows(self, required_level: AccessLevel) -> bool:
        """Check if this permission allows the required access level."""
        level_hierarchy = {
            AccessLevel.NONE: 0,
            AccessLevel.READ: 1,
            AccessLevel.WRITE: 2,
            AccessLevel.ADMIN: 3,
        }
        return level_hierarchy[self.access_level] >= level_hierarchy[required_level]


@dataclass
class UserContext:
    """
    Complete context for a user making a request.
    This is the primary input for all access control decisions.
    """

    user_id: str
    role: Role
    team_id: str
    department_id: str
    organization_id: str

    # Additional context
    email: str | None = None
    name: str | None = None
    manager_id: str | None = None
    direct_reports: list[str] = field(default_factory=list)
    project_ids: list[str] = field(default_factory=list)

    # Session metadata
    session_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)

    def is_manager_of(self, user_id: str) -> bool:
        """Check if this user is the manager of another user."""
        return user_id in self.direct_reports

    def same_team(self, team_id: str) -> bool:
        """Check if this user is on the specified team."""
        return self.team_id == team_id

    def same_department(self, department_id: str) -> bool:
        """Check if this user is in the specified department."""
        return self.department_id == department_id

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "user_id": self.user_id,
            "role": self.role.name,
            "team_id": self.team_id,
            "department_id": self.department_id,
            "organization_id": self.organization_id,
            "email": self.email,
            "name": self.name,
            "manager_id": self.manager_id,
            "direct_reports": self.direct_reports,
            "project_ids": self.project_ids,
        }


@dataclass
class AccessPolicy:
    """
    Defines access policy for a role to resources.
    Cedar-style policy definition.
    """

    policy_id: str
    role: Role
    resource: ResourceType
    access_level: AccessLevel
    conditions: dict[str, Any] = field(default_factory=dict)

    # Policy metadata
    description: str = ""
    priority: int = 0  # Higher priority policies override lower ones
    enabled: bool = True

    def allows(self, required_level: AccessLevel) -> bool:
        """Check if this policy's access level allows the required access level."""
        level_hierarchy = {
            AccessLevel.NONE: 0,
            AccessLevel.READ: 1,
            AccessLevel.WRITE: 2,
            AccessLevel.ADMIN: 3,
        }
        return level_hierarchy[self.access_level] >= level_hierarchy[required_level]

    def evaluate(self, context: UserContext, resource_attrs: dict[str, Any]) -> bool:
        """
        Evaluate if this policy permits access given context and resource attributes.

        Returns True if access is permitted, False otherwise.
        """
        if not self.enabled:
            return False

        # Check role matches
        if context.role != self.role:
            return False

        # Evaluate conditions
        return self._evaluate_conditions(context, resource_attrs)

    def _evaluate_conditions(
        self, context: UserContext, resource_attrs: dict[str, Any]
    ) -> bool:
        """Evaluate policy conditions."""
        for condition_type, condition_value in self.conditions.items():
            if condition_type == "same_team":
                if condition_value and not context.same_team(
                    resource_attrs.get("team_id", "")
                ):
                    return False

            elif condition_type == "same_department":
                if condition_value and not context.same_department(
                    resource_attrs.get("department_id", "")
                ):
                    return False

            elif condition_type == "is_owner":
                if condition_value and context.user_id != resource_attrs.get(
                    "owner_id"
                ):
                    return False

            elif condition_type == "is_manager_of_owner":
                if condition_value and not context.is_manager_of(
                    resource_attrs.get("owner_id", "")
                ):
                    return False

            elif condition_type == "project_member":
                if condition_value:
                    project_id = resource_attrs.get("project_id")
                    if project_id and project_id not in context.project_ids:
                        return False

            elif condition_type == "max_hierarchy_depth":
                depth = resource_attrs.get("hierarchy_depth", 0)
                if depth > condition_value:
                    return False

        return True


@dataclass
class AccessDecision:
    """Result of an access control decision."""

    allowed: bool
    reason: str
    policy_id: str | None = None
    resource: ResourceType | None = None
    access_level: AccessLevel | None = None

    # For filtering/scoping
    scope_filters: dict[str, Any] = field(default_factory=dict)

    # Audit metadata
    decision_time: datetime = field(default_factory=datetime.utcnow)
    context_snapshot: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def deny(cls, reason: str, resource: ResourceType | None = None) -> "AccessDecision":
        """Create a deny decision."""
        return cls(allowed=False, reason=reason, resource=resource)

    @classmethod
    def allow(
        cls,
        policy_id: str,
        resource: ResourceType,
        access_level: AccessLevel,
        scope_filters: dict[str, Any] | None = None,
    ) -> "AccessDecision":
        """Create an allow decision."""
        return cls(
            allowed=True,
            reason="Access granted by policy",
            policy_id=policy_id,
            resource=resource,
            access_level=access_level,
            scope_filters=scope_filters or {},
        )
