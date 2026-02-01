"""
RBAC Middleware - FastAPI middleware for access control.

Integrates RBAC with the API layer:
- Extracts user context from JWT
- Enforces access before request processing
- Filters responses based on permissions
"""

from typing import Callable, Any
from functools import wraps

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

import structlog

from src.config import settings
from src.rbac.models import UserContext, ResourceType, AccessLevel
from src.rbac.guards import rbac_guard
from src.security.context import get_user_context
from src.security.audit import audit_logger, AuditEvent, AuditEventType

logger = structlog.get_logger()

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> UserContext:
    """
    Extract and validate user context from request.

    This is the main dependency for protected endpoints.
    """
    if not credentials:
        # Return anonymous context for unauthenticated requests
        return await get_user_context(
            session_id=request.headers.get("X-Session-ID"),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        )

    try:
        # Decode JWT token
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        # Build user context
        context = await get_user_context(
            token_payload=payload,
            session_id=request.headers.get("X-Session-ID"),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        )

        return context

    except JWTError as e:
        logger.warning("JWT validation failed", error=str(e))
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token",
        )


def require_role(min_role: str):
    """
    Decorator to require a minimum role for an endpoint.

    Usage:
        @app.get("/admin")
        @require_role("manager")
        async def admin_endpoint(context: UserContext = Depends(get_current_user)):
            ...
    """
    from src.rbac.models import Role

    min_role_enum = Role.from_string(min_role)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find context in kwargs or args
            context = kwargs.get("context")
            if not context:
                for arg in args:
                    if isinstance(arg, UserContext):
                        context = arg
                        break

            if not context:
                raise HTTPException(status_code=401, detail="Authentication required")

            if context.role.value < min_role_enum.value:
                logger.warning(
                    "Role check failed",
                    user_id=context.user_id,
                    user_role=context.role.name,
                    required_role=min_role,
                )
                raise HTTPException(
                    status_code=403,
                    detail=f"Requires {min_role} role or higher",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_resource_access(
    resource: ResourceType,
    level: AccessLevel = AccessLevel.READ,
    get_resource_attrs: Callable[[Request], dict[str, Any]] | None = None,
):
    """
    Decorator to require access to a specific resource.

    Usage:
        @app.get("/team/{team_id}/analytics")
        @require_resource_access(
            ResourceType.TEAM_ANALYTICS,
            AccessLevel.READ,
            get_resource_attrs=lambda r: {"team_id": r.path_params["team_id"]}
        )
        async def get_analytics(
            team_id: str,
            context: UserContext = Depends(get_current_user)
        ):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, request: Request = None, **kwargs):
            context = kwargs.get("context")
            if not context:
                for arg in args:
                    if isinstance(arg, UserContext):
                        context = arg
                        break

            if not context:
                raise HTTPException(status_code=401, detail="Authentication required")

            # Get resource attributes from request
            resource_attrs = {}
            if get_resource_attrs and request:
                resource_attrs = get_resource_attrs(request)

            # Check access
            decision = rbac_guard.check_access(
                context=context,
                resource=resource,
                required_level=level,
                resource_attrs=resource_attrs,
            )

            if not decision.allowed:
                logger.warning(
                    "Resource access denied",
                    user_id=context.user_id,
                    resource=resource.value,
                    reason=decision.reason,
                )
                raise HTTPException(
                    status_code=403,
                    detail=decision.reason,
                )

            # Add scope filters to kwargs for use in endpoint
            kwargs["rbac_scope"] = decision.scope_filters

            return await func(*args, request=request, **kwargs)

        return wrapper

    return decorator


class RBACMiddleware:
    """
    FastAPI middleware for RBAC.

    Provides request-level access control and logging.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Create request object for inspection
        request = Request(scope, receive)

        # Log request for audit
        logger.debug(
            "Request received",
            path=request.url.path,
            method=request.method,
        )

        await self.app(scope, receive, send)


def filter_response_for_user(
    data: dict[str, Any],
    context: UserContext,
    sensitive_fields: list[str] | None = None,
) -> dict[str, Any]:
    """
    Filter response data based on user's role.

    Removes or redacts sensitive fields for lower-privilege users.
    """
    from src.rbac.models import Role

    sensitive_fields = sensitive_fields or [
        "salary",
        "compensation",
        "ssn",
        "social_security",
        "bank_account",
        "personal_email",
        "home_address",
        "phone_number",
    ]

    def filter_dict(d: dict, depth: int = 0) -> dict:
        if depth > 10:  # Prevent infinite recursion
            return d

        filtered = {}
        for key, value in d.items():
            # Check if field is sensitive
            key_lower = key.lower()
            is_sensitive = any(sf in key_lower for sf in sensitive_fields)

            if is_sensitive:
                # Only leadership+ can see sensitive fields
                if context.role.value >= Role.LEADERSHIP.value:
                    filtered[key] = value
                else:
                    filtered[key] = "[REDACTED]"
            elif isinstance(value, dict):
                filtered[key] = filter_dict(value, depth + 1)
            elif isinstance(value, list):
                filtered[key] = [
                    filter_dict(item, depth + 1) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                filtered[key] = value

        return filtered

    return filter_dict(data)


def get_user_dashboard_config(context: UserContext) -> dict[str, Any]:
    """Get dashboard configuration for the current user."""
    return rbac_guard.get_dashboard_config(context)


def get_user_mcp_permissions(context: UserContext) -> dict[str, dict[str, Any]]:
    """Get MCP tool permissions for the current user."""
    return rbac_guard.get_mcp_tool_permissions(context)


def get_user_knowledge_scope(context: UserContext) -> dict[str, Any]:
    """Get knowledge graph scope for the current user."""
    return rbac_guard.get_knowledge_scope(context)
