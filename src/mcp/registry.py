"""MCP Connector Registry."""

from typing import Any

import structlog

from src.mcp.base import BaseMCPConnector, MCPTool

logger = structlog.get_logger()


class MCPRegistry:
    """Registry for MCP connectors.

    Manages all registered connectors and provides unified access to tools.
    """

    def __init__(self):
        self._connectors: dict[str, BaseMCPConnector] = {}

    def register(self, connector: BaseMCPConnector) -> None:
        """Register a connector."""
        self._connectors[connector.name] = connector
        logger.info("Registered MCP connector", connector=connector.name)

    def unregister(self, name: str) -> None:
        """Unregister a connector."""
        if name in self._connectors:
            del self._connectors[name]
            logger.info("Unregistered MCP connector", connector=name)

    def get_connector(self, name: str) -> BaseMCPConnector | None:
        """Get a connector by name."""
        return self._connectors.get(name)

    def get_all_connectors(self) -> list[BaseMCPConnector]:
        """Get all registered connectors."""
        return list(self._connectors.values())

    def get_connected_connectors(self) -> list[BaseMCPConnector]:
        """Get all connected connectors."""
        return [c for c in self._connectors.values() if c.is_connected]

    async def connect_all(self) -> dict[str, bool]:
        """Connect all registered connectors.

        Returns a dict of connector name to connection status.
        """
        results = {}
        for name, connector in self._connectors.items():
            try:
                await connector.connect()
                results[name] = True
                logger.info("Connected MCP connector", connector=name)
            except Exception as e:
                results[name] = False
                logger.error("Failed to connect MCP connector", connector=name, error=str(e))
        return results

    async def disconnect_all(self) -> None:
        """Disconnect all connectors."""
        for name, connector in self._connectors.items():
            try:
                await connector.disconnect()
                logger.info("Disconnected MCP connector", connector=name)
            except Exception as e:
                logger.error("Failed to disconnect MCP connector", connector=name, error=str(e))

    async def health_check_all(self) -> dict[str, bool]:
        """Check health of all connectors."""
        results = {}
        for name, connector in self._connectors.items():
            try:
                results[name] = await connector.health_check()
            except Exception:
                results[name] = False
        return results

    def get_all_tools(self) -> list[MCPTool]:
        """Get all tools from all connected connectors."""
        tools = []
        for connector in self.get_connected_connectors():
            tools.extend(connector.get_tools())
        return tools

    def get_tools_by_category(self, category: str) -> list[MCPTool]:
        """Get tools by category."""
        return [t for t in self.get_all_tools() if t.category == category]

    def get_tool(self, tool_name: str) -> MCPTool | None:
        """Get a tool by name from any connector."""
        for connector in self._connectors.values():
            tool = connector.get_tool(tool_name)
            if tool:
                return tool
        return None

    async def execute_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Execute a tool by name."""
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found in any connector")
        return await tool.execute(**kwargs)

    def get_tools_for_agent(self, agent_type: str) -> list[MCPTool]:
        """Get relevant tools for a specific agent type.

        Different agents may need different subsets of tools.
        """
        all_tools = self.get_all_tools()

        # Define tool categories relevant to each agent
        agent_tool_categories = {
            "knowledge": ["jira_read", "github_read", "slack_read", "search"],
            "onboarding": ["jira_read", "github_read", "knowledge"],
            "team_analysis": ["jira_analytics", "github_analytics", "slack_analytics"],
            "orchestrator": [],  # Orchestrator doesn't use tools directly
        }

        relevant_categories = agent_tool_categories.get(agent_type, [])
        if not relevant_categories:
            return all_tools

        return [t for t in all_tools if t.category in relevant_categories]


# Singleton instance
mcp_registry = MCPRegistry()
