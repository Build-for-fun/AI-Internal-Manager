"""RBAC API endpoints for frontend configuration."""

from uuid import uuid4

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import get_db
from src.models.user import User
from src.rbac.engine import policy_engine
from src.rbac.guards import rbac_guard
from src.rbac.models import Role, UserContext
from src.config import settings

router = APIRouter()


async def get_current_user(
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current user (dev placeholder)."""
    stmt = select(User).limit(1)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=str(uuid4()),
            email="dev@example.com",
            hashed_password="dev",
            full_name="Development User",
            role="Software Engineer",
            department="Engineering",
            team="Platform",
        )
        db.add(user)
        await db.commit()

    return user


@router.get("/bootstrap")
async def get_rbac_bootstrap(
    user: User = Depends(get_current_user),
    demo_role: str | None = Header(default=None, alias="X-Demo-Role"),
) -> dict:
    """Return RBAC configuration for the current user."""
    role = Role.from_string(user.role or "ic")
    if demo_role and settings.environment != "production":
        role = Role.from_string(demo_role)

    context = UserContext(
        user_id=user.id,
        role=role,
        team_id=user.team or "",
        department_id=user.department or "",
        organization_id="default",
        email=user.email,
        name=user.full_name,
    )

    return {
        "user": {
            "id": user.id,
            "name": user.full_name,
            "email": user.email,
            "role": role.name,
            "team_id": user.team,
            "department_id": user.department,
            "organization_id": "default",
        },
        "dashboard": rbac_guard.get_dashboard_config(context),
        "mcp_permissions": rbac_guard.get_mcp_tool_permissions(context),
        "knowledge_scope": rbac_guard.get_knowledge_scope(context),
        "permissions": policy_engine.get_permissions_for_role(role),
    }
