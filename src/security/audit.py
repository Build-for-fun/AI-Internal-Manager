"""
Audit logging for security and compliance.

Provides comprehensive logging of:
- Access decisions (allow/deny)
- Data access patterns
- Ownership lookups
- Sensitive operations
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

import structlog

from src.rbac.models import UserContext, AccessDecision

logger = structlog.get_logger()


class AuditEventType(str, Enum):
    """Types of auditable events."""

    # Access control
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"

    # Data operations
    DATA_READ = "data_read"
    DATA_WRITE = "data_write"
    DATA_DELETE = "data_delete"

    # Knowledge graph
    KNOWLEDGE_QUERY = "knowledge_query"
    KNOWLEDGE_UPDATE = "knowledge_update"

    # Chat
    CHAT_MESSAGE = "chat_message"
    CHAT_RESPONSE = "chat_response"
    CHAT_FILTERED = "chat_filtered"

    # Ownership
    OWNERSHIP_LOOKUP = "ownership_lookup"
    EXPERTISE_SEARCH = "expertise_search"
    RECOMMENDATION_MADE = "recommendation_made"

    # MCP Tools
    MCP_TOOL_CALL = "mcp_tool_call"
    MCP_TOOL_BLOCKED = "mcp_tool_blocked"

    # Authentication
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"

    # Administrative
    POLICY_CHANGE = "policy_change"
    ROLE_CHANGE = "role_change"


@dataclass
class AuditEvent:
    """A single audit event."""

    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: AuditEventType = AuditEventType.DATA_READ
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Actor information
    user_id: str | None = None
    user_role: str | None = None
    team_id: str | None = None
    department_id: str | None = None

    # Action details
    resource_type: str | None = None
    resource_id: str | None = None
    action: str | None = None
    result: str | None = None  # "success", "denied", "error"

    # Request context
    session_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    # Policy information (for access events)
    policy_id: str | None = None
    access_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "user_role": self.user_role,
            "team_id": self.team_id,
            "department_id": self.department_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "result": self.result,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "metadata": self.metadata,
            "policy_id": self.policy_id,
            "access_reason": self.access_reason,
        }


class AuditLogger:
    """
    Centralized audit logger for security events.

    Supports:
    - Structured logging
    - Database persistence
    - Real-time alerting for sensitive events
    """

    def __init__(self):
        self._handlers: list[callable] = []
        self._alert_handlers: list[callable] = []
        self._sensitive_events = {
            AuditEventType.ACCESS_DENIED,
            AuditEventType.LOGIN_FAILED,
            AuditEventType.POLICY_CHANGE,
            AuditEventType.ROLE_CHANGE,
            AuditEventType.MCP_TOOL_BLOCKED,
        }

    def add_handler(self, handler: callable) -> None:
        """Add a handler for audit events (e.g., database writer)."""
        self._handlers.append(handler)

    def add_alert_handler(self, handler: callable) -> None:
        """Add a handler for security alerts."""
        self._alert_handlers.append(handler)

    async def log(self, event: AuditEvent) -> None:
        """Log an audit event."""
        # Structured logging
        logger.info(
            "Audit event",
            event_type=event.event_type.value,
            user_id=event.user_id,
            resource=event.resource_type,
            result=event.result,
            **event.metadata,
        )

        # Dispatch to handlers
        for handler in self._handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error("Audit handler failed", error=str(e))

        # Check for sensitive events
        if event.event_type in self._sensitive_events:
            await self._trigger_alert(event)

    async def _trigger_alert(self, event: AuditEvent) -> None:
        """Trigger security alert for sensitive events."""
        for handler in self._alert_handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error("Alert handler failed", error=str(e))

    def log_access_decision(
        self, decision: AccessDecision, context: UserContext
    ) -> None:
        """Log an access control decision."""
        event = AuditEvent(
            event_type=(
                AuditEventType.ACCESS_GRANTED
                if decision.allowed
                else AuditEventType.ACCESS_DENIED
            ),
            user_id=context.user_id,
            user_role=context.role.name,
            team_id=context.team_id,
            department_id=context.department_id,
            resource_type=decision.resource.value if decision.resource else None,
            result="success" if decision.allowed else "denied",
            policy_id=decision.policy_id,
            access_reason=decision.reason,
            session_id=context.session_id,
            ip_address=context.ip_address,
            metadata={"scope_filters": decision.scope_filters},
        )

        # Use sync logging for decorator compatibility
        logger.info(
            "Access decision",
            allowed=decision.allowed,
            user_id=context.user_id,
            role=context.role.name,
            resource=decision.resource.value if decision.resource else None,
            policy=decision.policy_id,
        )

    def log_ownership_lookup(
        self,
        context: UserContext,
        query: str,
        results: list[dict[str, Any]],
        scope: dict[str, Any],
    ) -> None:
        """Log an ownership/expertise lookup."""
        event = AuditEvent(
            event_type=AuditEventType.OWNERSHIP_LOOKUP,
            user_id=context.user_id,
            user_role=context.role.name,
            team_id=context.team_id,
            department_id=context.department_id,
            action="ownership_lookup",
            result="success",
            metadata={
                "query": query,
                "result_count": len(results),
                "scope": scope,
            },
        )

        logger.info(
            "Ownership lookup",
            user_id=context.user_id,
            query=query[:100],  # Truncate for logging
            result_count=len(results),
        )

    def log_chat_interaction(
        self,
        context: UserContext,
        query: str,
        response: str,
        agent: str,
        sources_count: int,
        filtered: bool = False,
    ) -> None:
        """Log a chat interaction."""
        event = AuditEvent(
            event_type=AuditEventType.CHAT_FILTERED if filtered else AuditEventType.CHAT_RESPONSE,
            user_id=context.user_id,
            user_role=context.role.name,
            team_id=context.team_id,
            action="chat_response",
            result="success",
            metadata={
                "agent": agent,
                "query_length": len(query),
                "response_length": len(response),
                "sources_count": sources_count,
                "filtered": filtered,
            },
        )

        logger.info(
            "Chat interaction",
            user_id=context.user_id,
            agent=agent,
            filtered=filtered,
        )

    def log_mcp_tool_call(
        self,
        context: UserContext,
        tool_name: str,
        allowed: bool,
        scope: dict[str, Any] | None = None,
    ) -> None:
        """Log an MCP tool call."""
        event = AuditEvent(
            event_type=(
                AuditEventType.MCP_TOOL_CALL
                if allowed
                else AuditEventType.MCP_TOOL_BLOCKED
            ),
            user_id=context.user_id,
            user_role=context.role.name,
            team_id=context.team_id,
            resource_type=f"mcp_{tool_name}",
            action="tool_call",
            result="success" if allowed else "blocked",
            metadata={"tool": tool_name, "scope": scope or {}},
        )

        logger.info(
            "MCP tool call",
            user_id=context.user_id,
            tool=tool_name,
            allowed=allowed,
        )


# Global audit logger instance
audit_logger = AuditLogger()
