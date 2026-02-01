"""Evaluator API endpoints for running LLM evaluations via Keywords AI."""

from typing import Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.evaluator.agent import evaluator_agent
from src.agents.evaluator.schemas import (
    DEFAULT_EVALUATOR_ID,
    BatchEvaluationResponse,
    EvaluationResponse,
    EvaluationStatus,
)
from src.models.database import get_db
from src.models.user import User

logger = structlog.get_logger()

router = APIRouter()


# Request/Response models for API
class EvaluateRequest(BaseModel):
    """Request to evaluate an LLM output."""

    completion_message: dict[str, Any] = Field(
        ...,
        description="The completion message from the LLM to evaluate",
        examples=[{"role": "assistant", "content": "Hello, how can I help you?"}],
    )
    prompt_messages: list[dict[str, Any]] = Field(
        default_factory=list,
        description="The prompt messages that generated the completion",
        examples=[[{"role": "user", "content": "Say hello"}]],
    )
    evaluator_slugs: list[str] | None = Field(
        None,
        description="List of evaluator slugs to run. Defaults to the configured evaluator.",
        examples=[["05887584fc104d27af141c07d704415c"]],
    )
    ideal_output: str | None = Field(
        None,
        description="Expected/ideal output for comparison evaluators",
    )
    eval_inputs: dict[str, Any] | None = Field(
        None,
        description="Additional custom inputs for evaluators",
    )
    model: str | None = Field(
        None,
        description="Model identifier for logging purposes",
    )
    customer_identifier: str | None = Field(
        None,
        description="Optional customer ID for tracking",
    )
    metadata: dict[str, Any] | None = Field(
        None,
        description="Additional metadata to attach to the evaluation",
    )


class GenerateAndEvaluateRequest(BaseModel):
    """Request to generate an LLM response and evaluate it."""

    messages: list[dict[str, Any]] = Field(
        ...,
        description="Messages to send to the LLM",
        examples=[[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is 2+2?"},
        ]],
    )
    evaluator_slugs: list[str] | None = Field(
        None,
        description="List of evaluator slugs to run. Defaults to the configured evaluator.",
    )
    ideal_output: str | None = Field(
        None,
        description="Expected output for comparison",
    )
    eval_inputs: dict[str, Any] | None = Field(
        None,
        description="Additional inputs for evaluators",
    )
    model: str | None = Field(
        None,
        description="Model to use for generation",
    )
    customer_identifier: str | None = Field(
        None,
        description="Optional customer ID",
    )
    metadata: dict[str, Any] | None = Field(
        None,
        description="Additional metadata",
    )


class GenerateAndEvaluateResponse(BaseModel):
    """Response from generate and evaluate endpoint."""

    generated_content: str
    evaluation: EvaluationResponse


class BatchEvaluateRequest(BaseModel):
    """Request to evaluate multiple outputs."""

    evaluations: list[EvaluateRequest] = Field(
        ...,
        description="List of evaluation requests",
    )


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


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_output(
    request: EvaluateRequest,
    user: User = Depends(get_current_user),
) -> EvaluationResponse:
    """Evaluate an existing LLM output using Keywords AI evaluators.

    This endpoint uses the Keywords AI Logging API to evaluate
    a completion against specified evaluators. Evaluators must be
    configured in the Keywords AI dashboard first.

    **Example usage:**
    ```python
    response = requests.post("/api/v1/evaluator/evaluate", json={
        "completion_message": {"role": "assistant", "content": "Hello!"},
        "prompt_messages": [{"role": "user", "content": "Greet me"}],
        "evaluator_slugs": ["tone-checker", "helpfulness"]
    })
    ```

    Note: Evaluations run asynchronously on Keywords AI. Results
    are available in the Keywords AI dashboard Logs.
    """
    try:
        result = await evaluator_agent.evaluate(
            completion_message=request.completion_message,
            prompt_messages=request.prompt_messages,
            evaluator_slugs=request.evaluator_slugs,
            ideal_output=request.ideal_output,
            eval_inputs=request.eval_inputs,
            model=request.model,
            customer_identifier=request.customer_identifier or user.id,
            metadata=request.metadata,
        )

        logger.info(
            "Evaluation submitted",
            user_id=user.id,
            evaluator_slugs=request.evaluator_slugs,
            status=result.status,
        )

        return result

    except Exception as e:
        logger.error("Evaluation failed", error=str(e), user_id=user.id)
        raise HTTPException(
            status_code=500,
            detail=f"Evaluation failed: {str(e)}",
        ) from e


@router.post("/generate-and-evaluate", response_model=GenerateAndEvaluateResponse)
async def generate_and_evaluate(
    request: GenerateAndEvaluateRequest,
    user: User = Depends(get_current_user),
) -> GenerateAndEvaluateResponse:
    """Generate an LLM response and evaluate it in a single call.

    This endpoint uses the Keywords AI LLM gateway to both generate
    a response AND submit it for evaluation, reducing latency.

    **Example usage:**
    ```python
    response = requests.post("/api/v1/evaluator/generate-and-evaluate", json={
        "messages": [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "What is 2+2?"}
        ],
        "evaluator_slugs": ["factual-correctness"],
        "ideal_output": "4"
    })
    ```
    """
    try:
        generated_content, evaluation = await evaluator_agent.evaluate_with_generation(
            messages=request.messages,
            evaluator_slugs=request.evaluator_slugs,
            ideal_output=request.ideal_output,
            eval_inputs=request.eval_inputs,
            model=request.model,
            customer_identifier=request.customer_identifier or user.id,
            metadata=request.metadata,
        )

        logger.info(
            "Generate and evaluate completed",
            user_id=user.id,
            evaluator_slugs=request.evaluator_slugs,
        )

        return GenerateAndEvaluateResponse(
            generated_content=generated_content,
            evaluation=evaluation,
        )

    except Exception as e:
        logger.error("Generate and evaluate failed", error=str(e), user_id=user.id)
        raise HTTPException(
            status_code=500,
            detail=f"Generate and evaluate failed: {str(e)}",
        ) from e


@router.post("/batch-evaluate", response_model=BatchEvaluationResponse)
async def batch_evaluate(
    request: BatchEvaluateRequest,
    user: User = Depends(get_current_user),
) -> BatchEvaluationResponse:
    """Evaluate multiple LLM outputs in batch.

    This endpoint processes multiple evaluation requests sequentially.
    Use for bulk evaluation of test datasets or historical outputs.

    **Example usage:**
    ```python
    response = requests.post("/api/v1/evaluator/batch-evaluate", json={
        "evaluations": [
            {
                "completion_message": {"role": "assistant", "content": "Hi!"},
                "evaluator_slugs": ["tone-checker"]
            },
            {
                "completion_message": {"role": "assistant", "content": "Hello!"},
                "evaluator_slugs": ["tone-checker"]
            }
        ]
    })
    ```
    """
    try:
        evaluations = [
            {
                "completion_message": e.completion_message,
                "prompt_messages": e.prompt_messages,
                "evaluator_slugs": e.evaluator_slugs,
                "ideal_output": e.ideal_output,
                "eval_inputs": e.eval_inputs,
                "model": e.model,
                "customer_identifier": e.customer_identifier or user.id,
                "metadata": e.metadata,
            }
            for e in request.evaluations
        ]

        result = await evaluator_agent.batch_evaluate(evaluations)

        logger.info(
            "Batch evaluation completed",
            user_id=user.id,
            total=result.total,
            completed=result.completed,
            failed=result.failed,
        )

        return result

    except Exception as e:
        logger.error("Batch evaluation failed", error=str(e), user_id=user.id)
        raise HTTPException(
            status_code=500,
            detail=f"Batch evaluation failed: {str(e)}",
        ) from e


@router.get("/health")
async def evaluator_health() -> dict[str, Any]:
    """Check evaluator service health.

    Returns status of the evaluator agent and its connection
    to Keywords AI.
    """
    try:
        # Simple check that agent is initialized
        return {
            "status": "healthy",
            "agent_name": evaluator_agent.name,
            "model": evaluator_agent.eval_model,
            "provider": "keywords_ai",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }
