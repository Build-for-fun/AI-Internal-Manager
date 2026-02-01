"""Voice Onboarding Agent with Textbook Knowledge Integration.

This agent:
- Handles voice-based queries from new employees
- Retrieves relevant knowledge from the textbook hierarchy
- Provides spoken responses using ElevenLabs TTS
- Integrates with Zoom for meeting-based onboarding
"""

import asyncio
import base64
from datetime import datetime
from typing import Any, AsyncGenerator
from uuid import uuid4

import structlog

from src.agents.base import BaseAgent
from src.agents.knowledge.retrieval import hybrid_retriever
from src.config import settings
from src.knowledge.textbook.hierarchy import HierarchyManager
from src.memory.manager import memory_manager
from src.voice.elevenlabs_client import elevenlabs_client

logger = structlog.get_logger()


class VoiceOnboardingAgent(BaseAgent):
    """Voice-enabled onboarding agent with textbook knowledge integration.
    
    Capabilities:
    - Real-time voice conversation handling
    - Textbook hierarchy querying for company knowledge
    - Context-aware responses based on user's role and department
    - Streaming audio generation for low-latency responses
    - Zoom integration for meeting-based onboarding sessions
    """

    def __init__(self):
        super().__init__(
            name="voice_onboarding",
            description="Voice-enabled agent for onboarding with textbook knowledge access",
        )
        self.hierarchy_manager = HierarchyManager()
        self.active_sessions: dict[str, dict[str, Any]] = {}

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

        # Retrieve relevant knowledge from textbook
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

        # Get knowledge context
        knowledge_results = await self._query_textbook(
            query=query,
            department=session.get("user_department"),
        )
        
        # Generate streaming response
        async for chunk in self._stream_response(query, session, knowledge_results):
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
    ) -> dict[str, Any]:
        """Generate a response using retrieved knowledge and LLM."""

        # Format knowledge context
        knowledge_context = self._format_knowledge_for_prompt(knowledge_results)

        # Determine if we have good knowledge to share
        has_knowledge = bool(knowledge_results and len(knowledge_results) > 0)
        sources_mention = ""
        if has_knowledge:
            source_names = [r.get("title", r.get("source", "company docs")) for r in knowledge_results[:2] if r.get("title") or r.get("source")]
            if source_names:
                sources_mention = f"\nYou found this information from: {', '.join(source_names)}. Naturally mention your source when helpful."

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

KNOWLEDGE FROM COMPANY TEXTBOOK:
{knowledge_context}

HOW TO RESPOND:
1. Start with a brief, direct answer to their question
2. Then explain the key details in an engaging way
3. Add relevant context that would be helpful to know
4. End with an invitation for follow-up questions

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

        return {
            "text": result["content"],
            "sources": sources,
            "confidence": 0.9 if knowledge_results else 0.7,
        }

    async def _stream_response(
        self,
        query: str,
        session: dict[str, Any],
        knowledge_results: list[dict[str, Any]],
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream response text and audio chunks."""
        
        # Generate full response first (for now)
        response = await self._generate_response(query, session, knowledge_results)
        
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
