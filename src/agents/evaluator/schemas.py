"""Schemas for the evaluator agent."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EvaluatorConfig(BaseModel):
    """Configuration for a single evaluator."""

    evaluator_slug: str = Field(..., description="The slug of the evaluator to run")


class EvalInputs(BaseModel):
    """Evaluation inputs including ideal output."""

    ideal_output: str | None = Field(None, description="Expected/ideal output for comparison")
    custom_inputs: dict[str, Any] = Field(default_factory=dict, description="Additional custom inputs")


class EvalParams(BaseModel):
    """Parameters for running evaluations."""

    evaluators: list[EvaluatorConfig] = Field(
        default_factory=list,
        description="List of evaluators to run"
    )
    eval_inputs: EvalInputs | None = Field(None, description="Inputs for evaluation")


class EvaluationRequest(BaseModel):
    """Request to evaluate an LLM output."""

    model: str = Field(default="gpt-4o", description="Model to use for evaluation")
    prompt_messages: list[dict[str, Any]] = Field(
        default_factory=list,
        description="The prompt messages that were sent to the LLM"
    )
    completion_message: dict[str, Any] = Field(
        ...,
        description="The completion message from the LLM to evaluate"
    )
    eval_params: EvalParams = Field(..., description="Evaluation parameters")
    customer_identifier: str | None = Field(None, description="Optional customer ID for tracking")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class EvaluationStatus(str, Enum):
    """Status of an evaluation."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EvaluationResult(BaseModel):
    """Result of a single evaluation."""

    evaluator_slug: str
    score: float | None = None
    passed: bool | None = None
    reasoning: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationResponse(BaseModel):
    """Response from an evaluation run."""

    status: EvaluationStatus
    results: list[EvaluationResult] = Field(default_factory=list)
    model: str
    total_evaluators: int
    passed_count: int = 0
    failed_count: int = 0
    error_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class BatchEvaluationRequest(BaseModel):
    """Request to evaluate multiple outputs."""

    evaluations: list[EvaluationRequest] = Field(
        ...,
        description="List of evaluation requests to process"
    )


class BatchEvaluationResponse(BaseModel):
    """Response from a batch evaluation run."""

    total: int
    completed: int
    failed: int
    results: list[EvaluationResponse] = Field(default_factory=list)
