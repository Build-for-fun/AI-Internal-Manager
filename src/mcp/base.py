"""Base classes for MCP connectors."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

import structlog

logger = structlog.get_logger()


@dataclass
class MCPToolParameter:
    """Parameter definition for an MCP tool."""

    name: str
    type: str  # "string", "integer", "boolean", "array", "object"
    description: str
    required: bool = True
    default: Any = None
    enum: list[Any] | None = None


@dataclass
class MCPTool:
    """Definition of an MCP tool that can be called by agents."""

    name: str
    description: str
    parameters: list[MCPToolParameter]
    handler: Callable[..., Coroutine[Any, Any, Any]]
    connector_name: str = ""
    category: str = ""

    def to_openai_function(self) -> dict[str, Any]:
        """Convert to OpenAI function calling format."""
        properties = {}
        required = []

        for param in self.parameters:
            prop: dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default

            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def to_anthropic_tool(self) -> dict[str, Any]:
        """Convert to Anthropic tool format."""
        properties = {}
        required = []

        for param in self.parameters:
            prop: dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum

            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    async def execute(self, **kwargs: Any) -> Any:
        """Execute the tool with given parameters."""
        try:
            result = await self.handler(**kwargs)
            logger.info(
                "Tool executed",
                tool=self.name,
                connector=self.connector_name,
            )
            return result
        except Exception as e:
            logger.error(
                "Tool execution failed",
                tool=self.name,
                connector=self.connector_name,
                error=str(e),
            )
            raise


class BaseMCPConnector(ABC):
    """Base class for MCP connectors.

    Each connector provides:
    - Connection to an external service (Jira, GitHub, Slack)
    - A set of tools that agents can use
    - Data normalization to fit the knowledge graph schema
    """

    def __init__(self, name: str):
        self.name = name
        self._tools: dict[str, MCPTool] = {}
        self._connected = False

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the external service."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the external service."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the connection is healthy."""
        pass

    @property
    def is_connected(self) -> bool:
        """Check if connector is connected."""
        return self._connected

    def register_tool(self, tool: MCPTool) -> None:
        """Register a tool with this connector."""
        tool.connector_name = self.name
        self._tools[tool.name] = tool
        logger.debug("Registered tool", tool=tool.name, connector=self.name)

    def get_tools(self) -> list[MCPTool]:
        """Get all tools provided by this connector."""
        return list(self._tools.values())

    def get_tool(self, name: str) -> MCPTool | None:
        """Get a specific tool by name."""
        return self._tools.get(name)

    async def execute_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Execute a tool by name."""
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found in connector {self.name}")
        return await tool.execute(**kwargs)

    def _create_tool(
        self,
        name: str,
        description: str,
        parameters: list[MCPToolParameter],
        handler: Callable[..., Coroutine[Any, Any, Any]],
        category: str = "",
    ) -> MCPTool:
        """Helper to create and register a tool."""
        tool = MCPTool(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            connector_name=self.name,
            category=category,
        )
        self.register_tool(tool)
        return tool
