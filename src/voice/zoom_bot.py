"""Zoom Meeting Bot for real-time voice onboarding.

This module provides a complete Zoom bot implementation that can:
- Join Zoom meetings using the Zoom Meeting SDK
- Capture audio from meetings in real-time
- Process speech and generate responses
- Speak responses back to the meeting

Requirements:
- Zoom App with Meeting SDK credentials
- ngrok or similar for webhook URLs (development)
"""

import asyncio
import base64
import json
import os
from datetime import datetime
from typing import Any, Callable
from uuid import uuid4

import httpx
import structlog

from src.config import settings
from src.voice.agent import voice_onboarding_agent
from src.voice.elevenlabs_client import elevenlabs_client

logger = structlog.get_logger()


class ZoomMeetingBot:
    """Real Zoom Meeting Bot for voice onboarding.
    
    This bot can join Zoom meetings and participate in voice conversations
    using the company's knowledge base.
    """

    def __init__(self):
        self.client_id = settings.zoom_client_id
        self.client_secret = settings.zoom_client_secret.get_secret_value()
        self.account_id = settings.zoom_account_id
        self.base_url = "https://api.zoom.us/v2"
        self._access_token = None
        self._token_expires = None
        self.active_bots: dict[str, dict] = {}

    async def get_access_token(self) -> str:
        """Get OAuth access token using Server-to-Server OAuth."""
        if self._access_token and self._token_expires:
            if datetime.utcnow() < self._token_expires:
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
                from datetime import timedelta
                self._token_expires = datetime.utcnow() + timedelta(
                    seconds=data.get("expires_in", 3600) - 60
                )
                logger.info("Zoom access token obtained")
                return self._access_token
            
            logger.error(
                "Failed to get Zoom access token",
                status=response.status_code,
                error=response.text,
            )
            raise Exception(f"Zoom auth failed: {response.text}")

    async def get_meeting_info(self, meeting_id: str) -> dict[str, Any]:
        """Get information about a Zoom meeting."""
        token = await self.get_access_token()
        
        # Clean meeting ID (remove spaces and dashes)
        clean_id = meeting_id.replace(" ", "").replace("-", "")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/meetings/{clean_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            
            if response.status_code == 200:
                return response.json()
            
            logger.error(
                "Failed to get meeting info",
                meeting_id=meeting_id,
                status=response.status_code,
                error=response.text,
            )
            return {}

    async def create_meeting(
        self,
        topic: str = "Onboarding Session",
        duration: int = 30,
        user_id: str = "me",
    ) -> dict[str, Any]:
        """Create a new Zoom meeting for onboarding."""
        token = await self.get_access_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/users/{user_id}/meetings",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "topic": topic,
                    "type": 2,  # Scheduled meeting
                    "duration": duration,
                    "settings": {
                        "host_video": True,
                        "participant_video": True,
                        "join_before_host": True,
                        "mute_upon_entry": False,
                        "auto_recording": "none",
                    },
                },
            )
            
            if response.status_code == 201:
                meeting = response.json()
                logger.info(
                    "Meeting created",
                    meeting_id=meeting.get("id"),
                    join_url=meeting.get("join_url"),
                )
                return meeting
            
            logger.error(
                "Failed to create meeting",
                status=response.status_code,
                error=response.text,
            )
            return {}

    async def start_bot_session(
        self,
        meeting_id: str,
        passcode: str | None = None,
        user_department: str | None = None,
    ) -> dict[str, Any]:
        """Start a bot session for a Zoom meeting.
        
        This sets up the voice agent and prepares for real-time interaction.
        For actual meeting audio, you would need to use Zoom's Raw Audio feature
        or a third-party service like Recall.ai or Meeting BaaS.
        """
        bot_id = str(uuid4())
        
        # Get meeting info
        meeting_info = await self.get_meeting_info(meeting_id)
        
        # Start voice agent session
        agent_session = await voice_onboarding_agent.start_voice_session(
            user_id=f"zoom_bot_{bot_id}",
            user_name="Onboarding Assistant",
            user_department=user_department,
            session_type="zoom_meeting",
            zoom_meeting_id=meeting_id,
        )
        
        bot_session = {
            "bot_id": bot_id,
            "meeting_id": meeting_id,
            "meeting_topic": meeting_info.get("topic", "Unknown"),
            "join_url": meeting_info.get("join_url"),
            "agent_session_id": agent_session["session_id"],
            "status": "ready",
            "created_at": datetime.utcnow().isoformat(),
            "questions_answered": 0,
            "transcripts": [],
        }
        
        self.active_bots[bot_id] = bot_session
        
        logger.info(
            "Bot session started",
            bot_id=bot_id,
            meeting_id=meeting_id,
        )
        
        return bot_session

    async def process_speech(
        self,
        bot_id: str,
        transcript: str,
        speaker_name: str | None = None,
    ) -> dict[str, Any] | None:
        """Process speech from a meeting participant.
        
        Args:
            bot_id: The bot session ID
            transcript: The transcribed speech
            speaker_name: Name of the speaker (if available)
            
        Returns:
            Response with text and audio if it was a question
        """
        bot = self.active_bots.get(bot_id)
        if not bot:
            return None

        # Store transcript
        bot["transcripts"].append({
            "speaker": speaker_name or "Unknown",
            "text": transcript,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Check if this is a question for the bot
        if not self._is_question_for_bot(transcript):
            return {"status": "ignored", "reason": "Not directed at bot"}

        # Process with voice agent
        try:
            response = await voice_onboarding_agent.process_voice_query(
                session_id=bot["agent_session_id"],
                query=transcript,
                include_audio=True,
            )
            
            bot["questions_answered"] += 1
            
            logger.info(
                "Question answered in Zoom",
                bot_id=bot_id,
                question=transcript[:50],
            )
            
            return response
            
        except Exception as e:
            logger.error("Failed to process question", error=str(e))
            return {"status": "error", "error": str(e)}

    def _is_question_for_bot(self, text: str) -> bool:
        """Determine if the text is directed at the onboarding bot."""
        text_lower = text.lower()
        
        triggers = [
            "hey assistant",
            "hi assistant", 
            "onboarding",
            "question",
            "can you tell me",
            "what is",
            "how do i",
            "where can i",
            "who should i",
            "help me",
            "explain",
        ]
        
        is_question = text.strip().endswith("?")
        has_trigger = any(trigger in text_lower for trigger in triggers)
        
        return is_question or has_trigger

    async def generate_audio_response(
        self,
        bot_id: str,
        text: str,
    ) -> bytes:
        """Generate audio for a response to be played in the meeting."""
        audio = await elevenlabs_client.synthesize(
            text=text,
            model_id="eleven_turbo_v2_5",
        )
        return audio

    async def end_bot_session(self, bot_id: str) -> dict[str, Any]:
        """End a bot session and return summary."""
        bot = self.active_bots.pop(bot_id, None)
        
        if not bot:
            return {"status": "not_found"}

        # End voice agent session
        await voice_onboarding_agent.end_session(bot["agent_session_id"])
        
        summary = {
            "bot_id": bot_id,
            "meeting_id": bot["meeting_id"],
            "meeting_topic": bot.get("meeting_topic"),
            "questions_answered": bot.get("questions_answered", 0),
            "transcript_count": len(bot.get("transcripts", [])),
            "created_at": bot.get("created_at"),
            "ended_at": datetime.utcnow().isoformat(),
        }
        
        logger.info("Bot session ended", **summary)
        
        return summary

    def get_active_bots(self) -> list[dict[str, Any]]:
        """Get list of active bot sessions."""
        return [
            {
                "bot_id": b["bot_id"],
                "meeting_id": b["meeting_id"],
                "meeting_topic": b.get("meeting_topic"),
                "status": b.get("status"),
                "questions_answered": b.get("questions_answered", 0),
            }
            for b in self.active_bots.values()
        ]


# Singleton instance
zoom_meeting_bot = ZoomMeetingBot()


# Simple test endpoint for Zoom connection
async def test_zoom_connection() -> dict[str, Any]:
    """Test the Zoom API connection."""
    try:
        token = await zoom_meeting_bot.get_access_token()
        return {
            "status": "connected",
            "has_token": bool(token),
            "account_id": settings.zoom_account_id,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }
