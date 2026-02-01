"""
User context builder for RBAC.

Constructs UserContext objects from various sources:
- JWT tokens
- Database records
- Request metadata
"""

from typing import Any

import structlog

from src.rbac.models import Role, UserContext

logger = structlog.get_logger()


class ContextBuilder:
    """
    Builds UserContext from various sources.

    Can fetch additional context from database, org chart, etc.
    """

    def __init__(self):
        self._org_chart_cache: dict[str, dict] = {}

    async def from_jwt(
        self,
        token_payload: dict[str, Any],
        session_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UserContext:
        """
        Build UserContext from JWT token payload.

        Expected token fields:
        - sub: user_id
        - role: role string
        - team_id: team identifier
        - department_id: department identifier
        - org_id: organization identifier
        """
        user_id = token_payload.get("sub")
        if not user_id:
            raise ValueError("Token missing 'sub' (user_id)")

        # Parse role from token
        role_str = token_payload.get("role", "ic")
        role = Role.from_string(role_str)

        # Get additional user data if available
        user_data = await self._fetch_user_data(user_id)

        context = UserContext(
            user_id=user_id,
            role=role,
            team_id=token_payload.get("team_id", user_data.get("team_id", "")),
            department_id=token_payload.get(
                "department_id", user_data.get("department_id", "")
            ),
            organization_id=token_payload.get(
                "org_id", user_data.get("organization_id", "default")
            ),
            email=token_payload.get("email", user_data.get("email")),
            name=token_payload.get("name", user_data.get("name")),
            manager_id=user_data.get("manager_id"),
            direct_reports=user_data.get("direct_reports", []),
            project_ids=user_data.get("project_ids", []),
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return context

    async def from_user_id(
        self,
        user_id: str,
        session_id: str | None = None,
        ip_address: str | None = None,
    ) -> UserContext:
        """Build UserContext by looking up user from database."""
        user_data = await self._fetch_user_data(user_id)

        if not user_data:
            raise ValueError(f"User not found: {user_id}")

        role = Role.from_string(user_data.get("role", "ic"))

        return UserContext(
            user_id=user_id,
            role=role,
            team_id=user_data.get("team_id", ""),
            department_id=user_data.get("department_id", ""),
            organization_id=user_data.get("organization_id", "default"),
            email=user_data.get("email"),
            name=user_data.get("name"),
            manager_id=user_data.get("manager_id"),
            direct_reports=user_data.get("direct_reports", []),
            project_ids=user_data.get("project_ids", []),
            session_id=session_id,
            ip_address=ip_address,
        )

    async def _fetch_user_data(self, user_id: str) -> dict[str, Any]:
        """
        Fetch user data from database.

        In production, this would query the users table and org chart.
        """
        # TODO: Implement actual database lookup
        # For now, return empty dict - caller should have data from JWT

        # Check cache first
        if user_id in self._org_chart_cache:
            return self._org_chart_cache[user_id]

        # Would query:
        # - users table for basic info
        # - team_members table for team membership
        # - org_chart for manager/reports
        # - project_members for project access

        return {}

    async def enrich_with_org_chart(self, context: UserContext) -> UserContext:
        """
        Enrich context with org chart data.

        Fetches manager_id and direct_reports from org chart.
        """
        org_data = await self._fetch_org_chart_data(context.user_id)

        if org_data:
            context.manager_id = org_data.get("manager_id", context.manager_id)
            context.direct_reports = org_data.get(
                "direct_reports", context.direct_reports
            )

        return context

    async def _fetch_org_chart_data(self, user_id: str) -> dict[str, Any]:
        """Fetch org chart data for a user."""
        # TODO: Implement org chart lookup
        # This would typically come from:
        # - HR system integration
        # - Neo4j REPORTS_TO relationships
        # - Dedicated org chart service

        return {}

    def build_anonymous_context(
        self,
        session_id: str | None = None,
        ip_address: str | None = None,
    ) -> UserContext:
        """Build a minimal context for unauthenticated users."""
        return UserContext(
            user_id="anonymous",
            role=Role.NEW_EMPLOYEE,  # Most restrictive role
            team_id="",
            department_id="",
            organization_id="",
            session_id=session_id,
            ip_address=ip_address,
        )


# Convenience function for getting user context from request
async def get_user_context(
    token_payload: dict[str, Any] | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> UserContext:
    """
    Get user context from available information.

    Priority:
    1. JWT token payload
    2. User ID lookup
    3. Anonymous context
    """
    builder = ContextBuilder()

    if token_payload:
        return await builder.from_jwt(
            token_payload,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    if user_id:
        return await builder.from_user_id(
            user_id,
            session_id=session_id,
            ip_address=ip_address,
        )

    return builder.build_anonymous_context(
        session_id=session_id,
        ip_address=ip_address,
    )
