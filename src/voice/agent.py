"""Voice Onboarding Agent with Textbook Knowledge and Team Metrics Integration.

This agent:
- Handles voice-based queries from new employees
- Retrieves relevant knowledge from the textbook hierarchy
- Accesses team metrics (velocity, sprint data) from Neo4j
- Provides spoken responses using ElevenLabs TTS
- Integrates with Zoom for meeting-based onboarding
"""

import asyncio
import base64
import re
from datetime import datetime
from typing import Any, AsyncGenerator
from uuid import uuid4

import structlog

from src.agents.base import BaseAgent
from src.agents.knowledge.retrieval import hybrid_retriever
from src.config import settings
from src.knowledge.textbook.hierarchy import HierarchyManager
from src.memory.manager import memory_manager
from src.mcp.internal.connector import internal_analytics_connector
from src.voice.elevenlabs_client import elevenlabs_client

logger = structlog.get_logger()

# Patterns that indicate team metrics queries
TEAM_METRICS_PATTERNS = [
    r'\b(team|sprint)\s*(velocity|metrics|performance|health)\b',
    r'\b(velocity|burndown|sprint)\b.*\b(team|backend|frontend|platform|ml)\b',
    r'\b(backend|frontend|platform|ml|engineering)\s*team\b.*\b(doing|performance|metrics|velocity|sprint|prs?|pull)',
    r'\bhow\s*(is|are|many)\s*(the|our)?\s*(team|backend|frontend|platform|prs?|pull)',
    r'\b(story\s*points?|completed|committed)\b',
    r'\b(prs?|pull\s*requests?|code\s*review)\b.*\b(merged|time|stats|open|recent|raised|created|team|backend|frontend)\b',
    r'\b(merged|open|recent|raised|created)\b.*\b(prs?|pull\s*requests?)\b',
    r'\b(bugs?\s*fixed|deployment|incident)\b',
    r'\blist\s*(all\s*)?(teams?|metrics)\b',
    r'\b(what|how\s*many)\s+(prs?|pull\s*requests?)\b',
    r'\b(show|get|find)\s+(me\s+)?(prs?|pull\s*requests?)\b',
    r'\b(prs?|pull\s*requests?)\b.*\b(backend|frontend|platform|ml|engineering)\s*team\b',
    r'\b(backend|frontend|platform|ml)\b.*\b(prs?|pull\s*requests?)\b',
]


class VoiceOnboardingAgent(BaseAgent):
    """Voice-enabled onboarding agent with textbook knowledge and team metrics integration.

    Capabilities:
    - Real-time voice conversation handling
    - Textbook hierarchy querying for company knowledge
    - Team metrics access (velocity, sprint data, PRs, etc.)
    - Context-aware responses based on user's role and department
    - Streaming audio generation for low-latency responses
    - Zoom integration for meeting-based onboarding sessions
    """

    def __init__(self):
        super().__init__(
            name="voice_onboarding",
            description="Voice-enabled agent for onboarding with textbook knowledge and team metrics access",
        )
        self.hierarchy_manager = HierarchyManager()
        self.active_sessions: dict[str, dict[str, Any]] = {}
        self._analytics_connected = False

    def _is_team_metrics_query(self, query: str) -> bool:
        """Detect if the query is about team metrics."""
        query_lower = query.lower()
        for pattern in TEAM_METRICS_PATTERNS:
            if re.search(pattern, query_lower):
                return True
        return False

    def _extract_team_name(self, query: str) -> str | None:
        """Extract team name from query."""
        query_lower = query.lower()
        teams = ['backend', 'frontend', 'platform', 'ml platform', 'engineering', 'ml']
        for team in teams:
            if team in query_lower:
                return team.title()
        return None

    async def _ensure_analytics_connected(self) -> None:
        """Ensure internal analytics connector is connected."""
        if not self._analytics_connected:
            try:
                if not internal_analytics_connector.is_connected:
                    await internal_analytics_connector.connect()
                self._analytics_connected = True
            except Exception as e:
                logger.warning("Failed to connect analytics connector", error=str(e))

    async def _query_team_metrics(
        self,
        query: str,
        team_name: str | None = None,
    ) -> dict[str, Any]:
        """Query team metrics from Neo4j.

        Returns velocity, sprint data, PRs, and other team metrics.
        """
        await self._ensure_analytics_connected()

        results = {
            "type": "team_metrics",
            "data": {},
        }

        query_lower = query.lower()

        try:
            # Get velocity data
            if any(word in query_lower for word in ['velocity', 'sprint', 'points', 'completed', 'committed']):
                velocity = await internal_analytics_connector._get_team_velocity(
                    team_name=team_name,
                    num_sprints=5,
                )
                results["data"]["velocity"] = velocity

            # Get detailed metrics
            if any(word in query_lower for word in ['metrics', 'performance', 'health', 'doing', 'how']):
                metrics = await internal_analytics_connector._get_team_metrics(
                    team_name=team_name,
                )
                results["data"]["metrics"] = metrics

            # Get PR data
            if any(word in query_lower for word in ['pr', 'pull request', 'pull requests', 'code review', 'merged', 'prs']):
                prs = await internal_analytics_connector._get_pull_requests()
                results["data"]["pull_requests"] = prs

            # List all teams
            if 'list' in query_lower and 'team' in query_lower:
                teams = await internal_analytics_connector._list_teams()
                results["data"]["teams"] = teams

            # If we didn't get specific data, get general team metrics
            if not results["data"]:
                metrics = await internal_analytics_connector._get_team_metrics(
                    team_name=team_name,
                )
                results["data"]["metrics"] = metrics

        except Exception as e:
            logger.error("Failed to query team metrics", error=str(e))
            results["error"] = str(e)

        return results

    async def process(
        self,
        query: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Process a query through the voice agent.
        
        This implements the abstract method from BaseAgent.
        Routes to voice query processing with textbook knowledge.
        """
        session_id = context.get("session_id")
        
        # If we have an active session, use it
        if session_id and session_id in self.active_sessions:
            result = await self.process_voice_query(
                session_id=session_id,
                query=query,
                include_audio=context.get("include_audio", False),
            )
            return {
                "response": result["text"],
                "sources": result.get("sources", []),
                "metadata": {
                    "topics_covered": result.get("topics_covered", []),
                    "confidence": result.get("confidence", 0.9),
                },
            }
        
        # No active session - query textbook directly
        knowledge_results = await self._query_textbook(
            query=query,
            department=context.get("user_department"),
            role=context.get("user_role"),
        )
        
        response = await self._generate_response(
            query=query,
            session={
                "user_name": context.get("user_name", "there"),
                "user_role": context.get("user_role"),
                "user_department": context.get("user_department"),
                "messages": context.get("messages", []),
                "questions_asked": 0,
            },
            knowledge_results=knowledge_results,
        )
        
        return {
            "response": response["text"],
            "sources": response.get("sources", []),
            "metadata": {
                "confidence": response.get("confidence", 0.9),
            },
        }

    async def start_voice_session(
        self,
        user_id: str,
        user_name: str,
        user_role: str | None = None,
        user_department: str | None = None,
        session_type: str = "onboarding",
        zoom_meeting_id: str | None = None,
    ) -> dict[str, Any]:
        """Start a new voice onboarding session.
        
        Args:
            user_id: User identifier
            user_name: User's name for personalization
            user_role: User's role (e.g., "engineer", "product_manager")
            user_department: User's department
            session_type: Type of session (onboarding, qa, training)
            zoom_meeting_id: Optional Zoom meeting ID for integration
            
        Returns:
            Session details including session_id and WebSocket URL
        """
        session_id = str(uuid4())
        
        # Prepare initial context from textbook
        initial_context = await self._get_onboarding_context(
            role=user_role,
            department=user_department,
        )
        
        session = {
            "id": session_id,
            "user_id": user_id,
            "user_name": user_name,
            "user_role": user_role,
            "user_department": user_department,
            "session_type": session_type,
            "zoom_meeting_id": zoom_meeting_id,
            "created_at": datetime.utcnow().isoformat(),
            "messages": [],
            "context": initial_context,
            "topics_covered": [],
            "questions_asked": 0,
        }
        
        self.active_sessions[session_id] = session
        
        logger.info(
            "Voice onboarding session started",
            session_id=session_id,
            user_id=user_id,
            department=user_department,
        )
        
        return {
            "session_id": session_id,
            "websocket_url": f"/api/v1/voice/agent/ws/{session_id}",
            "user_name": user_name,
            "department": user_department,
            "initial_topics": [t.get("title") for t in initial_context.get("topics", [])],
        }

    async def process_voice_query(
        self,
        session_id: str,
        query: str,
        include_audio: bool = True,
    ) -> dict[str, Any]:
        """Process a voice query and return response with optional audio.

        Args:
            session_id: Active session ID
            query: Transcribed user query
            include_audio: Whether to generate audio response

        Returns:
            Response with text, audio (if requested), and metadata
        """
        session = self.active_sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Check if this is a team metrics query
        is_metrics_query = self._is_team_metrics_query(query)
        team_metrics = None
        knowledge_results = []

        if is_metrics_query:
            # Query team metrics
            team_name = self._extract_team_name(query) or session.get("user_department")
            team_metrics = await self._query_team_metrics(query, team_name)
            logger.info("Team metrics query detected", team=team_name, has_data=bool(team_metrics.get("data")))

        # Also retrieve knowledge from textbook (may have relevant context)
        knowledge_results = await self._query_textbook(
            query=query,
            department=session.get("user_department"),
            role=session.get("user_role"),
        )

        # Build context-aware response
        response = await self._generate_response(
            query=query,
            session=session,
            knowledge_results=knowledge_results,
            team_metrics=team_metrics,
        )
        
        # Update session state
        session["messages"].append({"role": "user", "content": query})
        session["messages"].append({"role": "assistant", "content": response["text"]})
        session["questions_asked"] += 1
        
        # Track topics covered
        for result in knowledge_results[:3]:
            topic = result.get("title", result.get("topic"))
            if topic and topic not in session["topics_covered"]:
                session["topics_covered"].append(topic)
        
        result = {
            "text": response["text"],
            "sources": response.get("sources", []),
            "topics_covered": session["topics_covered"],
            "confidence": response.get("confidence", 0.9),
        }
        
        # Generate audio if requested
        if include_audio:
            audio = await elevenlabs_client.synthesize(
                text=response["text"],
                model_id="eleven_turbo_v2_5",  # Low latency model
            )
            result["audio_base64"] = audio.hex() if audio else None
        
        return result

    async def stream_voice_response(
        self,
        session_id: str,
        query: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream voice response for real-time playback.

        Yields:
            Chunks containing either text or audio data
        """
        session = self.active_sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Check if this is a team metrics query
        is_metrics_query = self._is_team_metrics_query(query)
        team_metrics = None

        if is_metrics_query:
            team_name = self._extract_team_name(query) or session.get("user_department")
            team_metrics = await self._query_team_metrics(query, team_name)

        # Get knowledge context
        knowledge_results = await self._query_textbook(
            query=query,
            department=session.get("user_department"),
        )

        # Generate streaming response
        async for chunk in self._stream_response(query, session, knowledge_results, team_metrics):
            yield chunk

    async def _query_textbook(
        self,
        query: str,
        department: str | None = None,
        role: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Query the textbook hierarchy for relevant knowledge.
        
        Uses hybrid retrieval to find:
        - Semantically similar content
        - Structurally related topics
        - Department-specific knowledge
        """
        try:
            # Use hybrid retriever for comprehensive search
            results = await hybrid_retriever.retrieve(
                query=query,
                top_k=top_k,
                department=department,
                include_summaries=True,
            )
            
            # Enhance with role-specific filtering
            if role:
                role_relevant = [
                    r for r in results
                    if self._is_role_relevant(r, role)
                ]
                # Prioritize role-relevant results but keep others
                other = [r for r in results if r not in role_relevant]
                results = role_relevant + other

            logger.info(
                "Textbook query completed",
                query=query[:50],
                results_count=len(results),
            )
            
            return results
            
        except Exception as e:
            logger.error("Textbook query failed", error=str(e))
            return []

    def _is_role_relevant(self, result: dict[str, Any], role: str) -> bool:
        """Check if a result is relevant to the user's role."""
        role_keywords = {
            "engineer": ["code", "technical", "api", "development", "engineering"],
            "product_manager": ["product", "feature", "roadmap", "requirements"],
            "designer": ["design", "ux", "ui", "user experience"],
            "sales": ["sales", "customer", "pricing", "deals"],
            "marketing": ["marketing", "campaign", "brand", "content"],
        }
        
        keywords = role_keywords.get(role.lower(), [])
        text = (result.get("text", "") + result.get("title", "")).lower()
        
        return any(kw in text for kw in keywords)

    async def _get_onboarding_context(
        self,
        role: str | None = None,
        department: str | None = None,
    ) -> dict[str, Any]:
        """Get initial onboarding context from textbook hierarchy."""
        context = {
            "topics": [],
            "policies": [],
            "faqs": [],
        }
        
        try:
            # Get department-specific topics
            if department:
                topics = await hybrid_retriever.retrieve(
                    query=f"onboarding {department} getting started",
                    top_k=5,
                    department=department,
                )
                context["topics"] = topics
            
            # Get general onboarding policies
            policies = await hybrid_retriever.retrieve(
                query="company policies onboarding new employee",
                top_k=3,
            )
            context["policies"] = policies
            
            # Get common FAQs
            faqs = await hybrid_retriever.retrieve(
                query="frequently asked questions new employee",
                top_k=3,
            )
            context["faqs"] = faqs
            
        except Exception as e:
            logger.warning("Failed to get onboarding context", error=str(e))
        
        return context

    async def _generate_response(
        self,
        query: str,
        session: dict[str, Any],
        knowledge_results: list[dict[str, Any]],
        team_metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate a response using retrieved knowledge, team metrics, and LLM."""

        # Format knowledge context
        knowledge_context = self._format_knowledge_for_prompt(knowledge_results)

        # Format team metrics if available
        metrics_context = ""
        if team_metrics and team_metrics.get("data"):
            metrics_context = self._format_team_metrics_for_prompt(team_metrics["data"])

        # Determine if we have good knowledge to share
        has_knowledge = bool(knowledge_results and len(knowledge_results) > 0)
        has_metrics = bool(metrics_context)
        sources_mention = ""
        if has_knowledge:
            source_names = [r.get("title", r.get("source", "company docs")) for r in knowledge_results[:2] if r.get("title") or r.get("source")]
            if source_names:
                sources_mention = f"\nYou found this information from: {', '.join(source_names)}. Naturally mention your source when helpful."

        # Build data sections
        data_sections = ""
        if metrics_context:
            data_sections += f"""
TEAM METRICS DATA (from company analytics):
{metrics_context}
"""
        if knowledge_context and knowledge_context != "No specific information found in the company knowledge base for this topic.":
            data_sections += f"""
KNOWLEDGE FROM COMPANY TEXTBOOK:
{knowledge_context}
"""

        # Build system prompt for conversational explanation
        system = f"""You are a friendly and knowledgeable voice assistant helping employees learn about the company.
Your goal is to EXPLAIN and DISCUSS the user's questions in a natural, conversational way.

CONVERSATION STYLE:
- Speak like a helpful colleague, not a search engine
- Explain concepts clearly as if talking to a friend
- Share relevant details that help the person understand
- Be enthusiastic about helping them succeed
- Use natural phrases like "So basically...", "The key thing is...", "What's interesting is..."

USER CONTEXT:
- Name: {session.get('user_name', 'there')}
- Role: {session.get('user_role', 'New Employee')}
- Department: {session.get('user_department', 'General')}
{sources_mention}
{data_sections}

HOW TO RESPOND:
1. Start with a brief, direct answer to their question
2. Then explain the key details in an engaging way
3. Add relevant context that would be helpful to know
4. End with an invitation for follow-up questions

IMPORTANT FOR TEAM METRICS:
- When you have team metrics data, share specific numbers naturally
- Example: "The Backend team has been doing great! They completed 28 story points last sprint..."
- Compare across sprints if data is available to show trends
- Mention things like velocity, completion rate, PRs merged, etc.

IMPORTANT:
- Keep responses to 3-5 sentences for voice (people are listening, not reading)
- If you found specific information, explain it conversationally
- If information is limited, be honest and offer to help find more
- Sound natural when spoken aloud - avoid bullet points or formal structure
"""

        # Get conversation history
        messages = session.get("messages", [])[-6:]  # Keep last 6 messages for context
        messages.append({"role": "user", "content": query})

        # Call LLM
        result = await self._call_llm(
            messages=messages,
            system=system,
            max_tokens=500,  # Keep responses concise for voice
        )

        # Extract sources
        sources = [
            {
                "title": r.get("title", ""),
                "source_url": r.get("source_url"),
                "source": r.get("source"),
            }
            for r in knowledge_results[:3]
            if r.get("title")
        ]

        # Confidence is high if we have knowledge or team metrics data
        has_data = bool(knowledge_results) or bool(team_metrics and team_metrics.get("data"))

        return {
            "text": result["content"],
            "sources": sources,
            "confidence": 0.9 if has_data else 0.7,
        }

    async def _stream_response(
        self,
        query: str,
        session: dict[str, Any],
        knowledge_results: list[dict[str, Any]],
        team_metrics: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream response text and audio chunks."""

        # Generate full response first (for now)
        response = await self._generate_response(query, session, knowledge_results, team_metrics)
        
        # Yield text
        yield {"type": "text", "data": response["text"]}
        
        # Stream audio
        async for audio_chunk in elevenlabs_client.synthesize_stream(
            text=response["text"],
            model_id="eleven_turbo_v2_5",
        ):
            yield {"type": "audio", "data": base64.b64encode(audio_chunk).decode()}
        
        # Yield completion
        yield {
            "type": "complete",
            "sources": response.get("sources", []),
        }

    def _format_team_metrics_for_prompt(
        self,
        data: dict[str, Any],
        max_length: int = 1500,
    ) -> str:
        """Format team metrics data for inclusion in LLM prompt."""
        parts = []

        # Format velocity data
        if "velocity" in data:
            velocity_data = data["velocity"].get("data", [])
            if velocity_data:
                parts.append("SPRINT VELOCITY:")
                for v in velocity_data[:5]:
                    team = v.get("team", "Unknown")
                    sprint = v.get("sprint", "")
                    velocity = v.get("velocity", v.get("completed_points", 0))
                    committed = v.get("committed_points", 0)
                    completion_rate = round((velocity / committed * 100) if committed else 0)
                    parts.append(f"  - {team} ({sprint}): {velocity} points completed / {committed} committed ({completion_rate}% completion)")

        # Format detailed metrics
        if "metrics" in data:
            metrics_data = data["metrics"].get("data", [])
            if metrics_data:
                parts.append("\nDETAILED TEAM METRICS:")
                for m in metrics_data[:5]:
                    team = m.get("team", "Unknown")
                    sprint = m.get("sprint", "")
                    velocity = m.get("velocity", 0)
                    bugs = m.get("bugs_fixed", 0)
                    prs = m.get("prs_merged", 0)
                    review_time = m.get("code_review_time_hours", 0)
                    deployments = m.get("deployment_frequency", 0)
                    incidents = m.get("incident_count", 0)
                    parts.append(f"  - {team} ({sprint}):")
                    parts.append(f"    Velocity: {velocity} points, Bugs fixed: {bugs}, PRs merged: {prs}")
                    if review_time:
                        parts.append(f"    Code review time: {review_time}h avg, Deployments: {deployments}/week, Incidents: {incidents}")

        # Format PR data
        if "pull_requests" in data:
            pr_data = data["pull_requests"].get("data", [])
            if pr_data:
                parts.append("\nRECENT PULL REQUESTS:")
                for pr in pr_data[:5]:
                    number = pr.get("number", "")
                    title = pr.get("title", "")[:50]
                    state = pr.get("state", "")
                    author = pr.get("author", "")
                    parts.append(f"  - PR #{number}: {title} ({state}) by {author}")

        # Format teams list
        if "teams" in data:
            teams_data = data["teams"].get("teams", [])
            if teams_data:
                parts.append("\nALL TEAMS:")
                for t in teams_data:
                    team_name = t.get("team", "Unknown")
                    sprints = t.get("sprints", [])
                    if sprints:
                        recent = sprints[0] if sprints else {}
                        velocity = recent.get("velocity", 0)
                        parts.append(f"  - {team_name}: Recent velocity {velocity} points ({len(sprints)} sprints tracked)")

        if not parts:
            return "No team metrics data available."

        result = "\n".join(parts)
        return result[:max_length]

    def _format_knowledge_for_prompt(
        self,
        results: list[dict[str, Any]],
        max_length: int = 2500,
    ) -> str:
        """Format knowledge results for inclusion in LLM prompt.

        Structures knowledge in a way that's easy for the LLM to use
        when generating conversational explanations.
        """
        if not results:
            return "No specific information found in the company knowledge base for this topic."

        parts = []
        total_length = 0

        for i, r in enumerate(results, 1):
            title = r.get("title", "Information")
            text = r.get("text", r.get("content", ""))
            source = r.get("source", r.get("node_type", "company document"))
            department = r.get("department", "")

            # Clean and truncate text
            text = text.strip()[:600] if text else ""

            # Format as structured knowledge block
            dept_info = f" ({department})" if department else ""
            part = f"""SOURCE {i}: {title}{dept_info}
From: {source}
Content: {text}
---"""

            if total_length + len(part) > max_length:
                break

            parts.append(part)
            total_length += len(part)

        if not parts:
            return "Limited information available on this topic."

        return "\n".join(parts)

    async def end_session(self, session_id: str) -> dict[str, Any]:
        """End a voice onboarding session and return summary."""
        session = self.active_sessions.pop(session_id, None)
        
        if not session:
            return {"status": "not_found"}
        
        # Generate session summary
        summary = {
            "session_id": session_id,
            "duration_messages": len(session.get("messages", [])),
            "questions_asked": session.get("questions_asked", 0),
            "topics_covered": session.get("topics_covered", []),
            "user_department": session.get("user_department"),
        }
        
        # Store session for analytics
        try:
            await memory_manager.store_interaction({
                "user_id": session.get("user_id"),
                "session_type": "voice_onboarding",
                "summary": summary,
            })
        except Exception as e:
            logger.warning("Failed to store session", error=str(e))
        
        logger.info("Voice session ended", **summary)
        
        return summary

    def get_active_sessions(self) -> list[dict[str, Any]]:
        """Get list of active voice sessions."""
        return [
            {
                "session_id": s["id"],
                "user_name": s.get("user_name"),
                "department": s.get("user_department"),
                "questions_asked": s.get("questions_asked", 0),
                "created_at": s.get("created_at"),
                "zoom_meeting_id": s.get("zoom_meeting_id"),
            }
            for s in self.active_sessions.values()
        ]


# Singleton instance
voice_onboarding_agent = VoiceOnboardingAgent()
