"""Evaluator agent for running LLM evaluations via Keywords AI.

This agent integrates with Keywords AI's evaluation features to assess
LLM outputs against configurable evaluators. It supports:
- Running single evaluations on LLM outputs
- Batch evaluations across multiple outputs
- Custom evaluators configured in Keywords AI dashboard
- Ideal output comparison for accuracy assessment
"""

from typing import Any

import structlog
from openai import AsyncOpenAI

from src.agents.base import BaseAgent
from src.agents.evaluator.schemas import (
    DEFAULT_EVALUATOR_ID,
    BatchEvaluationRequest,
    BatchEvaluationResponse,
    EvalInputs,
    EvalParams,
    EvaluationRequest,
    EvaluationResponse,
    EvaluationResult,
    EvaluationStatus,
    EvaluatorConfig,
)
from src.config import settings

logger = structlog.get_logger()


class EvaluatorAgent(BaseAgent):
    """Agent for running LLM evaluations via Keywords AI.

    This agent provides evaluation capabilities using Keywords AI's
    evaluation infrastructure. Evaluators are configured in the
    Keywords AI dashboard and referenced by their slug in code.

    Usage:
        # Single evaluation
        result = await evaluator_agent.evaluate(
            completion_message={"role": "assistant", "content": "Hello!"},
            prompt_messages=[{"role": "user", "content": "Say hello"}],
            evaluator_slugs=["tone-checker", "grammar-validator"]
        )

        # With ideal output for comparison
        result = await evaluator_agent.evaluate(
            completion_message={"role": "assistant", "content": "The answer is 42"},
            prompt_messages=[{"role": "user", "content": "What is 6 * 7?"}],
            evaluator_slugs=["factual-correctness"],
            ideal_output="The answer is 42"
        )
    """

    def __init__(self):
        super().__init__(
            name="evaluator",
            description="Evaluates LLM outputs using Keywords AI evaluation infrastructure",
        )

        # Initialize Keywords AI client for evaluations
        # Evaluations always go through Keywords AI regardless of llm_provider setting
        self.eval_client = AsyncOpenAI(
            api_key=settings.keywords_ai_api_key.get_secret_value(),
            base_url=settings.keywords_ai_base_url,
        )
        self.eval_model = settings.keywords_ai_default_model

    async def process(
        self,
        query: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Process a query for evaluation assistance.

        This method handles natural language requests about evaluations,
        helping users understand evaluation results or configure evaluators.

        Args:
            query: The user's query about evaluations
            context: Context including evaluation data, user info, etc.

        Returns:
            Response with evaluation insights or guidance
        """
        memory_context = context.get("memory_context", {})
        evaluation_history = context.get("evaluation_history", [])

        system = """You are an LLM evaluation assistant. You help users:
- Understand their evaluation results and what they mean
- Suggest appropriate evaluators for their use cases
- Explain how to improve LLM outputs based on evaluation feedback
- Configure evaluation parameters for optimal results

Be concise and actionable in your responses."""

        messages = [
            {"role": "user", "content": query}
        ]

        if evaluation_history:
            context_str = self._format_evaluation_history(evaluation_history)
            messages[0]["content"] = f"Recent evaluation results:\n{context_str}\n\nUser query: {query}"

        result = await self._call_llm(
            messages=messages,
            system=system,
        )

        return {
            "response": result["content"],
            "sources": [],
            "metadata": {
                "agent": self.name,
                "usage": result.get("usage", {}),
            },
        }

    async def evaluate(
        self,
        completion_message: dict[str, Any],
        prompt_messages: list[dict[str, Any]] | None = None,
        evaluator_slugs: list[str] | None = None,
        ideal_output: str | None = None,
        eval_inputs: dict[str, Any] | None = None,
        model: str | None = None,
        customer_identifier: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EvaluationResponse:
        """Evaluate an LLM output using Keywords AI evaluators.

        This method uses the Keywords AI Logging API to evaluate
        an existing LLM completion against specified evaluators.

        Args:
            completion_message: The LLM completion to evaluate
                Example: {"role": "assistant", "content": "Hello!"}
            prompt_messages: Optional prompt messages that generated the completion
            evaluator_slugs: List of evaluator slugs to run (configured in Keywords AI)
            ideal_output: Optional expected output for comparison evaluators
            eval_inputs: Additional custom inputs for evaluators
            model: Model identifier (for logging purposes)
            customer_identifier: Optional customer ID for tracking
            metadata: Additional metadata to attach

        Returns:
            EvaluationResponse with results from all evaluators
        """
        # Use default evaluator if none specified
        if not evaluator_slugs:
            evaluator_slugs = [DEFAULT_EVALUATOR_ID]

        # Build evaluation request
        request = self._build_evaluation_request(
            completion_message=completion_message,
            prompt_messages=prompt_messages or [],
            evaluator_slugs=evaluator_slugs,
            ideal_output=ideal_output,
            eval_inputs=eval_inputs,
            model=model,
            customer_identifier=customer_identifier,
            metadata=metadata,
        )

        try:
            # Execute evaluation via Keywords AI Logging API
            response = await self._execute_logging_api_evaluation(request)
            return response
        except Exception as e:
            logger.error("Evaluation failed", error=str(e))
            return EvaluationResponse(
                status=EvaluationStatus.FAILED,
                results=[EvaluationResult(
                    evaluator_slug="all",
                    error=str(e),
                )],
                model=request.model,
                total_evaluators=len(evaluator_slugs),
                error_count=len(evaluator_slugs),
            )

    async def evaluate_with_generation(
        self,
        messages: list[dict[str, Any]],
        evaluator_slugs: list[str],
        ideal_output: str | None = None,
        eval_inputs: dict[str, Any] | None = None,
        model: str | None = None,
        customer_identifier: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[str, EvaluationResponse]:
        """Generate an LLM response and evaluate it in a single call.

        This method uses the Keywords AI LLM gateway to both generate
        a response AND evaluate it, reducing latency and API calls.

        Args:
            messages: Messages to send to the LLM
            evaluator_slugs: List of evaluator slugs to run
            ideal_output: Optional expected output for comparison
            eval_inputs: Additional custom inputs for evaluators
            model: Model to use for generation
            customer_identifier: Optional customer ID
            metadata: Additional metadata

        Returns:
            Tuple of (generated_response, evaluation_response)
        """
        use_model = model or self.eval_model

        # Build eval params
        eval_params = self._build_eval_params(
            evaluator_slugs=evaluator_slugs,
            ideal_output=ideal_output,
            eval_inputs=eval_inputs,
        )

        # Build request body with eval_params
        extra_body: dict[str, Any] = {
            "eval_params": eval_params.model_dump(exclude_none=True),
        }

        if customer_identifier:
            extra_body["customer_identifier"] = customer_identifier

        if metadata:
            extra_body["metadata"] = metadata

        # Add caching if enabled
        if settings.keywords_ai_cache_enabled:
            extra_body["cache_enabled"] = True
            extra_body["cache_ttl"] = settings.keywords_ai_cache_ttl

        try:
            response = await self.eval_client.chat.completions.create(
                model=use_model,
                messages=messages,
                extra_body=extra_body,
            )

            generated_content = response.choices[0].message.content or ""

            # Evaluations run asynchronously on Keywords AI side
            # Results will be available in the Keywords AI dashboard Logs
            eval_response = EvaluationResponse(
                status=EvaluationStatus.PENDING,
                results=[
                    EvaluationResult(
                        evaluator_slug=slug,
                        reasoning="Evaluation submitted - check Keywords AI dashboard for results",
                    )
                    for slug in evaluator_slugs
                ],
                model=use_model,
                total_evaluators=len(evaluator_slugs),
                metadata={
                    "note": "Evaluations run asynchronously. View results in Keywords AI Logs.",
                    "response_id": getattr(response, "id", None),
                },
            )

            logger.info(
                "LLM generation with evaluation submitted",
                model=use_model,
                evaluators=evaluator_slugs,
            )

            return generated_content, eval_response

        except Exception as e:
            logger.error("Generation with evaluation failed", error=str(e))
            raise

    async def batch_evaluate(
        self,
        evaluations: list[dict[str, Any]],
    ) -> BatchEvaluationResponse:
        """Run batch evaluations on multiple outputs.

        Args:
            evaluations: List of evaluation configs, each containing:
                - completion_message: The completion to evaluate
                - prompt_messages: Optional prompt messages
                - evaluator_slugs: Evaluators to run
                - ideal_output: Optional expected output
                - eval_inputs: Optional additional inputs

        Returns:
            BatchEvaluationResponse with all results
        """
        results: list[EvaluationResponse] = []
        failed = 0

        for eval_config in evaluations:
            try:
                result = await self.evaluate(
                    completion_message=eval_config["completion_message"],
                    prompt_messages=eval_config.get("prompt_messages", []),
                    evaluator_slugs=eval_config.get("evaluator_slugs", []),
                    ideal_output=eval_config.get("ideal_output"),
                    eval_inputs=eval_config.get("eval_inputs"),
                    model=eval_config.get("model"),
                    customer_identifier=eval_config.get("customer_identifier"),
                    metadata=eval_config.get("metadata"),
                )
                results.append(result)
                if result.status == EvaluationStatus.FAILED:
                    failed += 1
            except Exception as e:
                logger.error("Batch evaluation item failed", error=str(e))
                failed += 1
                results.append(EvaluationResponse(
                    status=EvaluationStatus.FAILED,
                    results=[EvaluationResult(evaluator_slug="", error=str(e))],
                    model=eval_config.get("model", self.eval_model),
                    total_evaluators=len(eval_config.get("evaluator_slugs", [])),
                    error_count=len(eval_config.get("evaluator_slugs", [])),
                ))

        return BatchEvaluationResponse(
            total=len(evaluations),
            completed=len(evaluations) - failed,
            failed=failed,
            results=results,
        )

    def _build_evaluation_request(
        self,
        completion_message: dict[str, Any],
        prompt_messages: list[dict[str, Any]],
        evaluator_slugs: list[str],
        ideal_output: str | None = None,
        eval_inputs: dict[str, Any] | None = None,
        model: str | None = None,
        customer_identifier: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EvaluationRequest:
        """Build an evaluation request object."""
        eval_params = self._build_eval_params(
            evaluator_slugs=evaluator_slugs,
            ideal_output=ideal_output,
            eval_inputs=eval_inputs,
        )

        return EvaluationRequest(
            model=model or self.eval_model,
            prompt_messages=prompt_messages,
            completion_message=completion_message,
            eval_params=eval_params,
            customer_identifier=customer_identifier,
            metadata=metadata or {},
        )

    def _build_eval_params(
        self,
        evaluator_slugs: list[str],
        ideal_output: str | None = None,
        eval_inputs: dict[str, Any] | None = None,
    ) -> EvalParams:
        """Build evaluation parameters."""
        evaluators = [
            EvaluatorConfig(evaluator_id=slug)
            for slug in evaluator_slugs
        ]

        inputs = None
        if ideal_output or eval_inputs:
            inputs = EvalInputs(
                ideal_output=ideal_output,
                custom_inputs=eval_inputs or {},
            )

        return EvalParams(
            evaluators=evaluators,
            eval_inputs=inputs,
        )

    async def _execute_logging_api_evaluation(
        self,
        request: EvaluationRequest,
    ) -> EvaluationResponse:
        """Execute evaluation via Keywords AI Logging API.

        The Logging API allows evaluating existing completions
        without making a new LLM call.
        """
        import httpx

        logging_url = f"{settings.keywords_ai_base_url}request-logs/create/"

        # Build request payload matching Keywords AI Logging API format
        payload = {
            "model": request.model,
            "prompt_messages": request.prompt_messages,
            "completion_message": request.completion_message,
            "eval_params": request.eval_params.model_dump(exclude_none=True),
        }

        if request.customer_identifier:
            payload["customer_identifier"] = request.customer_identifier

        if request.metadata:
            payload["metadata"] = request.metadata

        headers = {
            "Authorization": f"Bearer {settings.keywords_ai_api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                logging_url,
                json=payload,
                headers=headers,
                timeout=30.0,
            )

            if response.status_code not in (200, 201):
                error_msg = f"Logging API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return EvaluationResponse(
                    status=EvaluationStatus.FAILED,
                    results=[EvaluationResult(
                        evaluator_slug="all",
                        error=error_msg,
                    )],
                    model=request.model,
                    total_evaluators=len(request.eval_params.evaluators),
                    error_count=len(request.eval_params.evaluators),
                )

            # Evaluations are processed asynchronously by Keywords AI
            # Results are available in the Keywords AI dashboard
            return EvaluationResponse(
                status=EvaluationStatus.PENDING,
                results=[
                    EvaluationResult(
                        evaluator_slug=e.evaluator_id,
                        reasoning="Evaluation submitted - check Keywords AI dashboard for results",
                    )
                    for e in request.eval_params.evaluators
                ],
                model=request.model,
                total_evaluators=len(request.eval_params.evaluators),
                metadata={
                    "note": "Evaluations run asynchronously. View results in Keywords AI Logs.",
                },
            )

    def _format_evaluation_history(
        self,
        history: list[dict[str, Any]],
    ) -> str:
        """Format evaluation history for context."""
        if not history:
            return "No recent evaluations."

        lines = []
        for i, eval_result in enumerate(history[-5:], 1):  # Last 5 evaluations
            status = eval_result.get("status", "unknown")
            evaluators = eval_result.get("evaluators", [])
            lines.append(f"{i}. Status: {status}, Evaluators: {', '.join(evaluators)}")

        return "\n".join(lines)


# Singleton instance
evaluator_agent = EvaluatorAgent()
