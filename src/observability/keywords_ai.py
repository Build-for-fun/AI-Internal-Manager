"""Keywords AI logging helpers."""

from __future__ import annotations

import json

import httpx
import structlog

from src.config import settings

logger = structlog.get_logger()


def _build_request_log_url() -> str:
    base_url = settings.keywords_ai_base_url.rstrip("/")
    return f"{base_url}/request-logs/create/"


async def log_keywords_ai_chat(
    *,
    messages: list[dict[str, str]],
    output: dict[str, str],
    customer_identifier: str,
    model: str,
) -> None:
    """Send a chat log entry to Keywords AI.

    This is best-effort and should never raise errors to the caller.
    """
    api_key = settings.keywords_ai_api_key.get_secret_value()
    if not api_key:
        return

    payload = {
        "model": model,
        "log_type": "chat",
        "input": json.dumps(messages),
        "output": json.dumps(output),
        "customer_identifier": customer_identifier,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                _build_request_log_url(),
                headers=headers,
                json=payload,
            )
            if response.status_code >= 300:
                logger.warning(
                    "Keywords AI log request failed",
                    status_code=response.status_code,
                    response_text=response.text[:500],
                )
    except Exception as exc:
        logger.warning("Keywords AI log request error", error=str(exc))