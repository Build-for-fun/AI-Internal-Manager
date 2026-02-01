"""Base agent class for all specialized agents."""

from abc import ABC, abstractmethod
from typing import Any

import structlog
from anthropic import AsyncAnthropic

from src.config import settings
from src.mcp.base import MCPTool

logger = structlog.get_logger()


class BaseAgent(ABC):
    """Base class for all agents in the system.

    Each agent specializes in a specific domain:
    - OrchestratorAgent: Routes queries to appropriate agents
    - KnowledgeAgent: Retrieves and synthesizes knowledge
    - OnboardingAgent: Guides new employee onboarding
    - TeamAnalysisAgent: Analyzes team health and metrics
    """

    def __init__(
        self,
        name: str,
        description: str,
        model: str | None = None,
    ):
        self.name = name
        self.description = description
        self.model = model or settings.anthropic_default_model
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key.get_secret_value())
        self._tools: list[MCPTool] = []

    def set_tools(self, tools: list[MCPTool]) -> None:
        """Set the tools available to this agent."""
        self._tools = tools

    def get_tools_for_llm(self) -> list[dict[str, Any]]:
        """Get tools in Anthropic format."""
        return [tool.to_anthropic_tool() for tool in self._tools]

    @abstractmethod
    async def process(
        self,
        query: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Process a query and return a response.

        Args:
            query: The user's query
            context: Context including conversation history, user info, etc.

        Returns:
            A dictionary containing:
            - response: The agent's response text
            - sources: Any sources used (for RAG)
            - metadata: Additional metadata
        """
        pass

    async def _call_llm(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Call the LLM with the given messages.

        Returns the full response including tool calls if any.
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens or settings.anthropic_max_tokens,
            "messages": messages,
        }

        if system:
            kwargs["system"] = system

        if tools:
            kwargs["tools"] = tools

        response = await self.client.messages.create(**kwargs)

        return {
            "content": self._extract_text_content(response.content),
            "tool_calls": self._extract_tool_calls(response.content),
            "stop_reason": response.stop_reason,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        }

    def _extract_text_content(self, content: list) -> str:
        """Extract text content from response."""
        text_parts = []
        for block in content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
        return "\n".join(text_parts)

    def _extract_tool_calls(self, content: list) -> list[dict[str, Any]]:
        """Extract tool calls from response."""
        tool_calls = []
        for block in content:
            if hasattr(block, "type") and block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
        return tool_calls

    async def _execute_tool(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        """Execute a tool by name."""
        for tool in self._tools:
            if tool.name == tool_name:
                return await tool.execute(**tool_input)
        raise ValueError(f"Tool {tool_name} not found")

    async def _run_with_tools(
        self,
        messages: list[dict[str, Any]],
        system: str,
        max_iterations: int = 5,
    ) -> dict[str, Any]:
        """Run the agent with tool use until completion.

        Handles the tool use loop automatically.
        """
        tools = self.get_tools_for_llm() if self._tools else None
        current_messages = messages.copy()
        all_tool_calls = []
        all_tool_results = []

        for _ in range(max_iterations):
            response = await self._call_llm(
                messages=current_messages,
                system=system,
                tools=tools,
            )

            tool_calls = response.get("tool_calls", [])

            if not tool_calls:
                # No tool calls, we're done
                return {
                    "response": response["content"],
                    "tool_calls": all_tool_calls,
                    "tool_results": all_tool_results,
                    "usage": response["usage"],
                }

            # Execute tool calls
            tool_results = []
            for tool_call in tool_calls:
                all_tool_calls.append(tool_call)
                try:
                    result = await self._execute_tool(
                        tool_call["name"],
                        tool_call["input"],
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call["id"],
                        "content": str(result),
                    })
                    all_tool_results.append({
                        "tool": tool_call["name"],
                        "result": result,
                    })
                except Exception as e:
                    logger.error(
                        "Tool execution failed",
                        tool=tool_call["name"],
                        error=str(e),
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call["id"],
                        "content": f"Error: {str(e)}",
                        "is_error": True,
                    })

            # Add assistant message with tool use
            current_messages.append({
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": tc["id"], "name": tc["name"], "input": tc["input"]}
                    for tc in tool_calls
                ],
            })

            # Add tool results
            current_messages.append({
                "role": "user",
                "content": tool_results,
            })

        # Max iterations reached
        logger.warning("Max tool iterations reached", agent=self.name)
        return {
            "response": "I've reached the maximum number of steps. Here's what I found so far...",
            "tool_calls": all_tool_calls,
            "tool_results": all_tool_results,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }
