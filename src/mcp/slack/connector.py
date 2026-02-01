"""Slack MCP Connector implementation."""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

import httpx
import structlog

from src.config import settings
from src.mcp.base import BaseMCPConnector, MCPToolParameter
from src.mcp.slack.schemas import (
    SlackChannel,
    SlackChannelActivity,
    SlackCommunicationGraph,
    SlackDecisionTrail,
    SlackMessage,
    SlackTopicCluster,
    SlackUser,
)

logger = structlog.get_logger()


class SlackConnector(BaseMCPConnector):
    """MCP Connector for Slack.

    Provides tools for:
    - Message search
    - Channel activity analysis
    - Topic clustering
    - Decision extraction
    - Communication graph analysis
    """

    def __init__(self):
        super().__init__("slack")
        self._client: httpx.AsyncClient | None = None
        self._register_tools()

    def _register_tools(self) -> None:
        """Register all Slack tools."""

        # Search Messages
        self._create_tool(
            name="slack_search_messages",
            description="Search for messages in Slack",
            parameters=[
                MCPToolParameter(
                    name="query",
                    type="string",
                    description="Search query",
                ),
                MCPToolParameter(
                    name="channel",
                    type="string",
                    description="Channel ID to search in (optional)",
                    required=False,
                ),
                MCPToolParameter(
                    name="limit",
                    type="integer",
                    description="Maximum results",
                    required=False,
                    default=20,
                ),
            ],
            handler=self.search_messages,
            category="slack_read",
        )

        # Get Channel Activity
        self._create_tool(
            name="slack_get_channel_activity",
            description="Get activity metrics for a channel",
            parameters=[
                MCPToolParameter(
                    name="channel_id",
                    type="string",
                    description="Channel ID",
                ),
                MCPToolParameter(
                    name="days",
                    type="integer",
                    description="Number of days to analyze",
                    required=False,
                    default=7,
                ),
            ],
            handler=self.get_channel_activity,
            category="slack_analytics",
        )

        # Get Topic Clusters
        self._create_tool(
            name="slack_get_topic_clusters",
            description="Get topic clusters from channel conversations",
            parameters=[
                MCPToolParameter(
                    name="channel_id",
                    type="string",
                    description="Channel ID",
                ),
                MCPToolParameter(
                    name="days",
                    type="integer",
                    description="Number of days to analyze",
                    required=False,
                    default=7,
                ),
            ],
            handler=self.get_topic_clusters,
            category="slack_analytics",
        )

        # Extract Decisions
        self._create_tool(
            name="slack_extract_decisions",
            description="Extract decisions from channel conversations",
            parameters=[
                MCPToolParameter(
                    name="channel_id",
                    type="string",
                    description="Channel ID",
                ),
                MCPToolParameter(
                    name="days",
                    type="integer",
                    description="Number of days to analyze",
                    required=False,
                    default=14,
                ),
            ],
            handler=self.extract_decisions,
            category="slack_analytics",
        )

        # Get Communication Graph
        self._create_tool(
            name="slack_get_communication_graph",
            description="Get communication patterns between team members",
            parameters=[
                MCPToolParameter(
                    name="channel_ids",
                    type="array",
                    description="List of channel IDs to analyze",
                ),
                MCPToolParameter(
                    name="days",
                    type="integer",
                    description="Number of days to analyze",
                    required=False,
                    default=30,
                ),
            ],
            handler=self.get_communication_graph,
            category="slack_analytics",
        )

    async def connect(self) -> None:
        """Connect to Slack API."""
        token = settings.slack_bot_token.get_secret_value()
        if not token:
            logger.warning("Slack bot token not configured")
            return

        self._client = httpx.AsyncClient(
            base_url="https://slack.com/api",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        self._connected = True
        logger.info("Slack connector connected")

    async def disconnect(self) -> None:
        """Disconnect from Slack API."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False

    async def health_check(self) -> bool:
        """Check Slack API health."""
        if not self._client:
            return False
        try:
            response = await self._client.get("/auth.test")
            data = response.json()
            return data.get("ok", False)
        except Exception:
            return False

    async def search_messages(
        self,
        query: str,
        channel: str | None = None,
        limit: int = 20,
    ) -> list[SlackMessage]:
        """Search for messages in Slack."""
        search_query = query
        if channel:
            search_query = f"in:{channel} {query}"

        response = await self._client.get(
            "/search.messages",
            params={"query": search_query, "count": limit},
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("ok"):
            logger.error("Slack search failed", error=data.get("error"))
            return []

        messages = []
        for match in data.get("messages", {}).get("matches", []):
            messages.append(self._parse_message(match))

        return messages

    async def get_channel_activity(
        self,
        channel_id: str,
        days: int = 7,
    ) -> SlackChannelActivity:
        """Get activity metrics for a channel."""
        # Get channel info
        channel_response = await self._client.get(
            "/conversations.info",
            params={"channel": channel_id},
        )
        channel_data = channel_response.json()
        channel = self._parse_channel(channel_data.get("channel", {}))

        # Get recent messages
        oldest = (datetime.utcnow() - timedelta(days=days)).timestamp()
        history_response = await self._client.get(
            "/conversations.history",
            params={"channel": channel_id, "oldest": oldest, "limit": 1000},
        )
        history_data = history_response.json()
        messages = history_data.get("messages", [])

        # Calculate metrics
        user_counts: dict[str, int] = defaultdict(int)
        hour_counts: dict[int, int] = defaultdict(int)
        thread_count = 0
        response_times = []

        for msg in messages:
            user_id = msg.get("user", "unknown")
            user_counts[user_id] += 1

            ts = float(msg.get("ts", 0))
            hour = datetime.fromtimestamp(ts).hour
            hour_counts[hour] += 1

            if msg.get("thread_ts") and msg.get("thread_ts") != msg.get("ts"):
                thread_count += 1
                # Calculate response time (simplified)
                parent_ts = float(msg.get("thread_ts", 0))
                response_time = (ts - parent_ts) / 60  # minutes
                if response_time > 0 and response_time < 1440:  # Within 24 hours
                    response_times.append(response_time)

        # Get peak hours
        peak_hours = sorted(hour_counts.keys(), key=lambda h: hour_counts[h], reverse=True)[:3]

        # Get top contributors
        top_user_ids = sorted(user_counts.keys(), key=lambda u: user_counts[u], reverse=True)[:5]
        top_contributors = []
        for user_id in top_user_ids:
            user_info = await self._get_user(user_id)
            if user_info:
                top_contributors.append(user_info)

        return SlackChannelActivity(
            channel=channel,
            message_count=len(messages),
            thread_count=thread_count,
            active_users=len(user_counts),
            avg_response_time_minutes=sum(response_times) / len(response_times) if response_times else 0,
            peak_hours=peak_hours,
            top_contributors=top_contributors,
        )

    async def get_topic_clusters(
        self,
        channel_id: str,
        days: int = 7,
    ) -> list[SlackTopicCluster]:
        """Get topic clusters from channel conversations.

        This is a simplified implementation. In production, you would use
        an LLM or clustering algorithm to identify topics.
        """
        oldest = (datetime.utcnow() - timedelta(days=days)).timestamp()

        response = await self._client.get(
            "/conversations.history",
            params={"channel": channel_id, "oldest": oldest, "limit": 500},
        )
        data = response.json()
        messages = data.get("messages", [])

        # Group messages by thread
        threads: dict[str, list[dict]] = defaultdict(list)
        for msg in messages:
            thread_ts = msg.get("thread_ts", msg.get("ts"))
            threads[thread_ts].append(msg)

        # Create clusters from threads with 3+ messages
        clusters = []
        for thread_ts, thread_msgs in threads.items():
            if len(thread_msgs) >= 3:
                # Get first message as topic indicator
                first_msg = min(thread_msgs, key=lambda m: float(m.get("ts", 0)))
                text = first_msg.get("text", "")[:100]

                # Get participants
                participants = []
                user_ids = set(m.get("user") for m in thread_msgs if m.get("user"))
                for user_id in list(user_ids)[:5]:
                    user = await self._get_user(user_id)
                    if user:
                        participants.append(user)

                # Extract keywords (simplified)
                words = text.lower().split()
                keywords = [w for w in words if len(w) > 4][:5]

                clusters.append(SlackTopicCluster(
                    topic=text[:50] + "..." if len(text) > 50 else text,
                    summary=text,
                    message_count=len(thread_msgs),
                    participants=participants,
                    key_messages=[self._parse_message(first_msg)],
                    start_time=datetime.fromtimestamp(float(first_msg.get("ts", 0))),
                    end_time=datetime.fromtimestamp(
                        float(max(thread_msgs, key=lambda m: float(m.get("ts", 0))).get("ts", 0))
                    ),
                    channels=[channel_id],
                    keywords=keywords,
                ))

        # Sort by message count
        clusters.sort(key=lambda c: c.message_count, reverse=True)
        return clusters[:10]

    async def extract_decisions(
        self,
        channel_id: str,
        days: int = 14,
    ) -> list[SlackDecisionTrail]:
        """Extract decisions from channel conversations.

        Looks for decision indicators like "decided", "agreed", "will do", etc.
        In production, use an LLM for better extraction.
        """
        decision_keywords = [
            "decided", "agreed", "will do", "let's go with",
            "decision:", "final:", "approved", "moving forward with",
        ]

        oldest = (datetime.utcnow() - timedelta(days=days)).timestamp()

        response = await self._client.get(
            "/conversations.history",
            params={"channel": channel_id, "oldest": oldest, "limit": 500},
        )
        data = response.json()
        messages = data.get("messages", [])

        decisions = []
        for msg in messages:
            text = msg.get("text", "").lower()
            if any(keyword in text for keyword in decision_keywords):
                user = await self._get_user(msg.get("user"))

                decisions.append(SlackDecisionTrail(
                    decision=msg.get("text", "")[:200],
                    context="Extracted from Slack conversation",
                    participants=[user] if user else [],
                    decision_maker=user,
                    channel=channel_id,
                    thread_ts=msg.get("thread_ts"),
                    made_at=datetime.fromtimestamp(float(msg.get("ts", 0))),
                    supporting_messages=[self._parse_message(msg)],
                ))

        return decisions[:20]

    async def get_communication_graph(
        self,
        channel_ids: list[str],
        days: int = 30,
    ) -> SlackCommunicationGraph:
        """Build communication graph between team members."""
        oldest = (datetime.utcnow() - timedelta(days=days)).timestamp()

        # Collect all interactions
        interactions: dict[tuple[str, str], dict] = defaultdict(lambda: {
            "message_count": 0,
            "reaction_count": 0,
            "thread_replies": 0,
            "channels": set(),
        })
        users: dict[str, SlackUser] = {}

        for channel_id in channel_ids:
            response = await self._client.get(
                "/conversations.history",
                params={"channel": channel_id, "oldest": oldest, "limit": 500},
            )
            data = response.json()
            messages = data.get("messages", [])

            # Track thread participants for reply connections
            threads: dict[str, list[str]] = defaultdict(list)

            for msg in messages:
                user_id = msg.get("user")
                if not user_id:
                    continue

                # Track user
                if user_id not in users:
                    user = await self._get_user(user_id)
                    if user:
                        users[user_id] = user

                # Track thread replies
                thread_ts = msg.get("thread_ts")
                if thread_ts:
                    threads[thread_ts].append(user_id)

                # Track reactions
                for reaction in msg.get("reactions", []):
                    for reactor_id in reaction.get("users", []):
                        if reactor_id != user_id:
                            key = tuple(sorted([user_id, reactor_id]))
                            interactions[key]["reaction_count"] += 1
                            interactions[key]["channels"].add(channel_id)

            # Process thread interactions
            for thread_ts, participants in threads.items():
                unique_participants = list(set(participants))
                for i, p1 in enumerate(unique_participants):
                    for p2 in unique_participants[i + 1:]:
                        key = tuple(sorted([p1, p2]))
                        interactions[key]["thread_replies"] += 1
                        interactions[key]["channels"].add(channel_id)

        # Build edges
        from src.mcp.slack.schemas import SlackCommunicationEdge
        edges = []
        for (user1_id, user2_id), data in interactions.items():
            if user1_id in users and user2_id in users:
                edges.append(SlackCommunicationEdge(
                    from_user=users[user1_id],
                    to_user=users[user2_id],
                    message_count=data["message_count"],
                    reaction_count=data["reaction_count"],
                    thread_replies=data["thread_replies"],
                    channels_in_common=list(data["channels"]),
                ))

        return SlackCommunicationGraph(
            nodes=list(users.values()),
            edges=edges,
            clusters=[],  # Would need community detection algorithm
        )

    async def _get_user(self, user_id: str) -> SlackUser | None:
        """Get user info by ID."""
        try:
            response = await self._client.get(
                "/users.info",
                params={"user": user_id},
            )
            data = response.json()
            if data.get("ok"):
                return self._parse_user(data.get("user", {}))
        except Exception:
            pass
        return None

    def _parse_message(self, data: dict[str, Any]) -> SlackMessage:
        """Parse message data."""
        ts = data.get("ts", "0")
        return SlackMessage(
            ts=ts,
            channel_id=data.get("channel", {}).get("id", "") if isinstance(data.get("channel"), dict) else data.get("channel", ""),
            user=self._parse_user(data.get("user")) if isinstance(data.get("user"), dict) else None,
            text=data.get("text", ""),
            thread_ts=data.get("thread_ts"),
            reply_count=data.get("reply_count", 0),
            reply_users_count=data.get("reply_users_count", 0),
            reactions=data.get("reactions", []),
            attachments=data.get("attachments", []),
            blocks=data.get("blocks", []),
            created_at=datetime.fromtimestamp(float(ts)),
            edited_at=datetime.fromtimestamp(float(data["edited"]["ts"]))
            if data.get("edited") else None,
        )

    def _parse_user(self, data: dict[str, Any] | str | None) -> SlackUser | None:
        """Parse user data."""
        if not data:
            return None
        if isinstance(data, str):
            return SlackUser(id=data, name=data)
        return SlackUser(
            id=data.get("id", ""),
            name=data.get("name", ""),
            real_name=data.get("real_name"),
            email=data.get("profile", {}).get("email"),
            avatar_url=data.get("profile", {}).get("image_48"),
            is_bot=data.get("is_bot", False),
        )

    def _parse_channel(self, data: dict[str, Any]) -> SlackChannel:
        """Parse channel data."""
        return SlackChannel(
            id=data.get("id", ""),
            name=data.get("name", ""),
            is_private=data.get("is_private", False),
            is_archived=data.get("is_archived", False),
            topic=data.get("topic", {}).get("value"),
            purpose=data.get("purpose", {}).get("value"),
            member_count=data.get("num_members", 0),
            created=datetime.fromtimestamp(data["created"]) if data.get("created") else None,
        )


# Singleton instance
slack_connector = SlackConnector()
