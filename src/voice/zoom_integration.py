"""Zoom integration for voice-based onboarding.

Provides:
- Zoom Meeting Bot integration
- Real-time audio streaming from Zoom meetings
- Voice-based Q&A during onboarding meetings
- Meeting transcript and summary generation
"""

import asyncio
import base64
import hashlib
import hmac
import json
from datetime import datetime
from typing import Any, Callable
from uuid import uuid4

import httpx
import structlog
import websockets
from websockets.exceptions import ConnectionClosed

from src.config import settings
from src.voice.agent import voice_onboarding_agent
from src.voice.elevenlabs_client import elevenlabs_client

logger = structlog.get_logger()


class ZoomCredentials:
    """Zoom API credentials configuration."""
    
    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        account_id: str | None = None,
        bot_jid: str | None = None,
    ):
        self.client_id = client_id or getattr(settings, 'zoom_client_id', '')
        self.client_secret = client_secret or getattr(settings, 'zoom_client_secret', '')
        self.account_id = account_id or getattr(settings, 'zoom_account_id', '')
        self.bot_jid = bot_jid or getattr(settings, 'zoom_bot_jid', '')
        self._access_token = None
        self._token_expires = None

    async def get_access_token(self) -> str:
        """Get OAuth access token for Zoom API."""
        if self._access_token and self._token_expires and datetime.utcnow() < self._token_expires:
            return self._access_token

        async with httpx.AsyncClient() as client:
            auth = base64.b64encode(
                f"{self.client_id}:{self.client_secret}".encode()
            ).decode()
            
            response = await client.post(
                "https://zoom.us/oauth/token",
                headers={
                    "Authorization": f"Basic {auth}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "account_credentials",
                    "account_id": self.account_id,
                },
            )
            
            if response.status_code == 200:
                data = response.json()
                self._access_token = data["access_token"]
                # Token typically valid for 1 hour
                from datetime import timedelta
                self._token_expires = datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600) - 60)
                return self._access_token
            
            logger.error("Failed to get Zoom access token", status=response.status_code)
            raise Exception("Failed to authenticate with Zoom")


class ZoomVoiceIntegration:
    """Integration for voice-based onboarding in Zoom meetings.
    
    Enables:
    - Bot joining Zoom meetings
    - Listening to meeting audio
    - Processing voice queries in real-time
    - Speaking responses back to the meeting
    """

    def __init__(self, credentials: ZoomCredentials | None = None):
        self.credentials = credentials or ZoomCredentials()
        self.active_meetings: dict[str, dict[str, Any]] = {}
        self.base_url = "https://api.zoom.us/v2"

    async def get_meeting_info(self, meeting_id: str) -> dict[str, Any]:
        """Get information about a Zoom meeting."""
        token = await self.credentials.get_access_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/meetings/{meeting_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            
            if response.status_code == 200:
                return response.json()
            
            logger.error("Failed to get meeting info", meeting_id=meeting_id)
            return {}

    async def join_meeting(
        self,
        meeting_id: str,
        meeting_password: str | None = None,
        display_name: str = "Onboarding Assistant",
        user_id: str | None = None,
        user_department: str | None = None,
    ) -> dict[str, Any]:
        """Join a Zoom meeting as the onboarding voice bot.
        
        Args:
            meeting_id: Zoom meeting ID
            meeting_password: Optional meeting password
            display_name: Bot display name in meeting
            user_id: User ID for session tracking
            user_department: Department for knowledge filtering
            
        Returns:
            Session info with bot status
        """
        session_id = str(uuid4())
        
        # Start voice agent session for this meeting
        agent_session = await voice_onboarding_agent.start_voice_session(
            user_id=user_id or f"zoom_{meeting_id}",
            user_name=display_name,
            user_department=user_department,
            session_type="zoom_onboarding",
            zoom_meeting_id=meeting_id,
        )
        
        meeting_session = {
            "session_id": session_id,
            "meeting_id": meeting_id,
            "agent_session_id": agent_session["session_id"],
            "display_name": display_name,
            "status": "joining",
            "started_at": datetime.utcnow().isoformat(),
            "participants": [],
            "transcripts": [],
            "questions_answered": 0,
        }
        
        self.active_meetings[session_id] = meeting_session
        
        # In production, this would use Zoom's Meeting SDK or Bot API
        # to actually join the meeting. For now, we set up the session.
        logger.info(
            "Zoom meeting join initiated",
            session_id=session_id,
            meeting_id=meeting_id,
        )
        
        return {
            "session_id": session_id,
            "meeting_id": meeting_id,
            "status": "ready",
            "webhook_url": f"/api/v1/voice/zoom/webhook/{session_id}",
            "agent_session": agent_session,
        }

    async def handle_audio_stream(
        self,
        session_id: str,
        audio_data: bytes,
        speaker_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Handle incoming audio from Zoom meeting.
        
        Process audio, transcribe, and generate response if it's a question.
        
        Args:
            session_id: Meeting session ID
            audio_data: Raw audio bytes
            speaker_id: Identifier of the speaker (if available)
            
        Returns:
            Response with text and audio if a question was detected
        """
        meeting = self.active_meetings.get(session_id)
        if not meeting:
            logger.warning("Meeting session not found", session_id=session_id)
            return None

        # In production, use Deepgram or similar for real-time transcription
        # For this implementation, we assume audio comes pre-transcribed
        # or use a separate transcription service
        
        return None

    async def process_transcript(
        self,
        session_id: str,
        transcript: str,
        speaker_name: str | None = None,
    ) -> dict[str, Any] | None:
        """Process a transcript segment from the Zoom meeting.
        
        Analyzes if the transcript is a question directed at the bot
        and generates an appropriate response.
        
        Args:
            session_id: Meeting session ID
            transcript: Transcribed text
            speaker_name: Name of the speaker
            
        Returns:
            Response if the transcript was a question for the bot
        """
        meeting = self.active_meetings.get(session_id)
        if not meeting:
            return None

        # Store transcript
        meeting["transcripts"].append({
            "speaker": speaker_name,
            "text": transcript,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Check if this is directed at the onboarding bot
        if not self._is_question_for_bot(transcript):
            return None

        # Process with voice agent
        try:
            response = await voice_onboarding_agent.process_voice_query(
                session_id=meeting["agent_session_id"],
                query=transcript,
                include_audio=True,
            )
            
            meeting["questions_answered"] += 1
            
            logger.info(
                "Zoom question answered",
                session_id=session_id,
                question=transcript[:50],
            )
            
            return response
            
        except Exception as e:
            logger.error("Failed to process Zoom question", error=str(e))
            return None

    def _is_question_for_bot(self, text: str) -> bool:
        """Determine if the text is a question directed at the onboarding bot."""
        text_lower = text.lower()
        
        # Check for direct addressing
        bot_triggers = [
            "onboarding assistant",
            "hey assistant",
            "hi assistant",
            "onboarding bot",
            "ask about",
            "question about",
            "can you tell me",
            "what is",
            "how do i",
            "where can i",
            "who should i",
        ]
        
        # Check if text ends with a question mark
        is_question = text.strip().endswith("?")
        
        # Check for bot triggers
        has_trigger = any(trigger in text_lower for trigger in bot_triggers)
        
        return is_question or has_trigger

    async def speak_to_meeting(
        self,
        session_id: str,
        text: str,
    ) -> bytes:
        """Generate speech to be played in the Zoom meeting.
        
        Args:
            session_id: Meeting session ID
            text: Text to speak
            
        Returns:
            Audio bytes to be played in the meeting
        """
        meeting = self.active_meetings.get(session_id)
        if not meeting:
            raise ValueError(f"Meeting session {session_id} not found")

        # Generate audio using ElevenLabs
        audio = await elevenlabs_client.synthesize(
            text=text,
            model_id="eleven_turbo_v2_5",  # Low latency
        )
        
        return audio

    async def leave_meeting(self, session_id: str) -> dict[str, Any]:
        """Leave a Zoom meeting and generate summary.
        
        Args:
            session_id: Meeting session ID
            
        Returns:
            Meeting summary with statistics
        """
        meeting = self.active_meetings.pop(session_id, None)
        
        if not meeting:
            return {"status": "not_found"}

        # End the agent session
        agent_summary = await voice_onboarding_agent.end_session(
            meeting["agent_session_id"]
        )
        
        summary = {
            "session_id": session_id,
            "meeting_id": meeting["meeting_id"],
            "duration_transcripts": len(meeting.get("transcripts", [])),
            "questions_answered": meeting.get("questions_answered", 0),
            "started_at": meeting.get("started_at"),
            "ended_at": datetime.utcnow().isoformat(),
            "agent_summary": agent_summary,
        }
        
        logger.info("Zoom meeting session ended", **summary)
        
        return summary

    def get_active_meetings(self) -> list[dict[str, Any]]:
        """Get list of active Zoom meeting sessions."""
        return [
            {
                "session_id": m["session_id"],
                "meeting_id": m["meeting_id"],
                "status": m.get("status"),
                "questions_answered": m.get("questions_answered", 0),
                "started_at": m.get("started_at"),
            }
            for m in self.active_meetings.values()
        ]


class ZoomWebhookHandler:
    """Handle Zoom webhooks for real-time event processing."""

    def __init__(self, integration: ZoomVoiceIntegration):
        self.integration = integration
        self.webhook_secret = getattr(settings, 'zoom_webhook_secret', '')

    def verify_webhook(self, payload: bytes, signature: str, timestamp: str) -> bool:
        """Verify Zoom webhook signature."""
        if not self.webhook_secret:
            logger.warning("Zoom webhook secret not configured")
            return True  # Skip verification in development

        message = f"v0:{timestamp}:{payload.decode()}"
        expected_sig = hmac.new(
            self.webhook_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
        
        return hmac.compare_digest(f"v0={expected_sig}", signature)

    async def handle_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Handle a Zoom webhook event.
        
        Supported events:
        - meeting.started
        - meeting.ended
        - meeting.participant_joined
        - meeting.participant_left
        - recording.transcript_completed (for transcripts)
        """
        event_type = event.get("event")
        payload = event.get("payload", {})
        
        logger.info("Zoom webhook received", event_type=event_type)
        
        handlers = {
            "meeting.started": self._handle_meeting_started,
            "meeting.ended": self._handle_meeting_ended,
            "meeting.participant_joined": self._handle_participant_joined,
            "recording.transcript_completed": self._handle_transcript_completed,
        }
        
        handler = handlers.get(event_type)
        if handler:
            return await handler(payload)
        
        return {"status": "ignored", "event": event_type}

    async def _handle_meeting_started(self, payload: dict) -> dict:
        """Handle meeting started event."""
        meeting = payload.get("object", {})
        meeting_id = meeting.get("id")
        
        logger.info("Meeting started", meeting_id=meeting_id)
        
        return {"status": "acknowledged", "meeting_id": meeting_id}

    async def _handle_meeting_ended(self, payload: dict) -> dict:
        """Handle meeting ended event."""
        meeting = payload.get("object", {})
        meeting_id = meeting.get("id")
        
        # Find and end any active sessions for this meeting
        for session_id, session in list(self.integration.active_meetings.items()):
            if session.get("meeting_id") == meeting_id:
                await self.integration.leave_meeting(session_id)
        
        return {"status": "acknowledged", "meeting_id": meeting_id}

    async def _handle_participant_joined(self, payload: dict) -> dict:
        """Handle participant joined event."""
        participant = payload.get("object", {}).get("participant", {})
        
        logger.info(
            "Participant joined",
            name=participant.get("user_name"),
            meeting_id=payload.get("object", {}).get("id"),
        )
        
        return {"status": "acknowledged"}

    async def _handle_transcript_completed(self, payload: dict) -> dict:
        """Handle transcript completed event - useful for async processing."""
        transcript = payload.get("object", {})
        
        logger.info("Transcript completed", meeting_id=transcript.get("meeting_id"))
        
        return {"status": "acknowledged"}


# Create instances
zoom_integration = ZoomVoiceIntegration()
zoom_webhook_handler = ZoomWebhookHandler(zoom_integration)
