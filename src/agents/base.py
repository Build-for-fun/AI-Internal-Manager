"""Base agent class for all specialized agents."""

from abc import ABC, abstractmethod
from typing import Any

import structlog
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

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
        self.llm_provider = settings.llm_provider
        self._tools: list[MCPTool] = []

        if self.llm_provider == "keywords_ai":
            self.model = model or settings.keywords_ai_default_model
            self.client = AsyncOpenAI(
                api_key=settings.keywords_ai_api_key.get_secret_value(),
                base_url=settings.keywords_ai_base_url,
            )
        else:
            self.model = model or settings.anthropic_default_model
            self.client = AsyncAnthropic(api_key=settings.anthropic_api_key.get_secret_value())

    def set_tools(self, tools: list[MCPTool]) -> None:
        """Set the tools available to this agent."""
        self._tools = tools

    def get_tools_for_llm(self) -> list[dict[str, Any]]:
        """Get tools in provider-specific format."""
        if self.llm_provider == "keywords_ai":
            return [tool.to_openai_function() for tool in self._tools]
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
        if self.llm_provider == "keywords_ai":
            return await self._call_openai(messages, system, tools, max_tokens)

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

    async def _call_openai(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Call the OpenAI-compatible LLM."""
        openai_messages = messages.copy()
        if system:
            # Check if system message already exists at the start
            if not (openai_messages and openai_messages[0]["role"] == "system"):
                openai_messages.insert(0, {"role": "system", "content": system})

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,  # OpenAI might default differently, but passing None is usually fine if model has default
            "messages": openai_messages,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await self.client.chat.completions.create(**kwargs)
        message = response.choices[0].message

        # Safe JSON load
        import json
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "input": args,
                })

        return {
            "content": message.content or "",
            "tool_calls": tool_calls,
            "stop_reason": response.choices[0].finish_reason,
            "usage": {
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0,
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
            if self.llm_provider == "keywords_ai":
                import json
                
                # OpenAI format
                assistant_msg = {
                    "role": "assistant",
                    "content": response.get("content"),
                }
                
                if tool_calls:
                    assistant_msg["tool_calls"] = []
                    for tc in tool_calls:
                        assistant_msg["tool_calls"].append({
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["input"]),
                            }
                        })
                
                current_messages.append(assistant_msg)

                # Add tool results
                for tr in tool_results:
                    current_messages.append({
                        "role": "tool",
                        "tool_call_id": tr["tool_use_id"],
                        "content": tr["content"],
                    })

            else:
                # Anthropic format
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
