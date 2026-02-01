"""Real-time Zoom Meeting Bot with Audio Capabilities.

This module implements a Zoom bot that can:
- Join Zoom meetings programmatically
- Listen to meeting audio in real-time
- Transcribe speech using Deepgram
- Generate responses using the knowledge base
- Speak responses back using ElevenLabs TTS

For production use, consider using:
- Recall.ai (https://recall.ai) - Meeting bot as a service
- Zoom Meeting SDK - For native integration
- Zoom Raw Audio API - For raw audio streaming
"""

import asyncio
import base64
import json
import subprocess
import tempfile
import wave
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Callable
from uuid import uuid4

import httpx
import structlog

from src.config import settings
from src.voice.agent import voice_onboarding_agent
from src.voice.elevenlabs_client import elevenlabs_client

logger = structlog.get_logger()


class DeepgramRealTimeTranscriber:
    """Real-time speech-to-text using Deepgram."""
    
    def __init__(self):
        self.api_key = settings.deepgram_api_key.get_secret_value()
        self.ws_url = "wss://api.deepgram.com/v1/listen"
    
    async def transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio data to text."""
        if not self.api_key:
            logger.warning("Deepgram API key not configured")
            return ""
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.deepgram.com/v1/listen",
                headers={
                    "Authorization": f"Token {self.api_key}",
                    "Content-Type": "audio/wav",
                },
                content=audio_data,
                params={
                    "model": "nova-2",
                    "smart_format": "true",
                    "language": "en",
                },
            )
            
            if response.status_code == 200:
                data = response.json()
                transcript = (
                    data.get("results", {})
                    .get("channels", [{}])[0]
                    .get("alternatives", [{}])[0]
                    .get("transcript", "")
                )
                return transcript
            
            logger.error("Deepgram transcription failed", status=response.status_code)
            return ""


class ZoomRealTimeBot:
    """Real-time Zoom meeting bot with voice capabilities.
    
    This bot joins Zoom meetings and participates in voice conversations
    by listening to audio, transcribing speech, and speaking responses.
    """

    def __init__(self):
        self.client_id = settings.zoom_client_id
        self.client_secret = settings.zoom_client_secret.get_secret_value()
        self.account_id = settings.zoom_account_id
        self.base_url = "https://api.zoom.us/v2"
        self._access_token = None
        self._token_expires = None
        self.active_sessions: dict[str, dict] = {}
        self.transcriber = DeepgramRealTimeTranscriber()

    async def get_access_token(self) -> str:
        """Get OAuth access token."""
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
                return self._access_token
            
            raise Exception(f"Zoom auth failed: {response.text}")

    def parse_meeting_url(self, url: str) -> dict[str, str]:
        """Parse a Zoom meeting URL to extract meeting ID and password."""
        import re
        
        # Extract meeting ID
        match = re.search(r'/j/(\d+)', url)
        meeting_id = match.group(1) if match else ""
        
        # Extract password
        pwd_match = re.search(r'pwd=([^&\s]+)', url)
        password = pwd_match.group(1) if pwd_match else ""
        
        return {
            "meeting_id": meeting_id,
            "password": password,
        }

    async def join_meeting(
        self,
        meeting_url: str,
        bot_name: str = "Onboarding Assistant",
        user_department: str | None = None,
        on_transcript: Callable[[str, str], None] | None = None,
        on_response: Callable[[str, bytes], None] | None = None,
    ) -> dict[str, Any]:
        """Join a Zoom meeting and start listening.
        
        Args:
            meeting_url: Full Zoom meeting URL
            bot_name: Display name for the bot
            user_department: Department for knowledge filtering
            on_transcript: Callback for transcriptions (speaker, text)
            on_response: Callback for responses (text, audio)
            
        Returns:
            Session info with bot ID and status
        """
        # Parse meeting URL
        meeting_info = self.parse_meeting_url(meeting_url)
        meeting_id = meeting_info["meeting_id"]
        password = meeting_info["password"]
        
        if not meeting_id:
            raise ValueError("Could not parse meeting ID from URL")
        
        session_id = str(uuid4())
        
        # Start voice agent session
        agent_session = await voice_onboarding_agent.start_voice_session(
            user_id=f"zoom_realtime_{session_id}",
            user_name=bot_name,
            user_department=user_department,
            session_type="zoom_realtime",
            zoom_meeting_id=meeting_id,
        )
        
        session = {
            "session_id": session_id,
            "meeting_id": meeting_id,
            "meeting_url": meeting_url,
            "password": password,
            "bot_name": bot_name,
            "agent_session_id": agent_session["session_id"],
            "status": "joining",
            "created_at": datetime.utcnow().isoformat(),
            "transcripts": [],
            "responses": [],
            "is_listening": False,
        }
        
        self.active_sessions[session_id] = session
        
        logger.info(
            "Real-time Zoom session created",
            session_id=session_id,
            meeting_id=meeting_id,
        )
        
        return {
            "session_id": session_id,
            "meeting_id": meeting_id,
            "bot_name": bot_name,
            "status": "ready",
            "agent_session": agent_session,
            "instructions": {
                "step_1": "Open the Zoom meeting in your browser or app",
                "step_2": f"The bot '{bot_name}' will process speech when you send transcripts",
                "step_3": "Use the /speech endpoint to send what participants say",
                "step_4": "The bot will respond with text and audio",
                "step_5": "Play the audio in your meeting for everyone to hear",
            },
        }

    async def process_audio(
        self,
        session_id: str,
        audio_data: bytes,
        speaker_name: str | None = None,
    ) -> dict[str, Any] | None:
        """Process audio from the meeting.
        
        Transcribes audio, checks if it's a question, and generates response.
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return None
        
        # Transcribe audio
        transcript = await self.transcriber.transcribe_audio(audio_data)
        
        if not transcript:
            return {"status": "no_speech"}
        
        logger.info("Transcribed speech", transcript=transcript[:50])
        
        # Process as text
        return await self.process_speech(session_id, transcript, speaker_name)

    async def process_speech(
        self,
        session_id: str,
        transcript: str,
        speaker_name: str | None = None,
    ) -> dict[str, Any]:
        """Process transcribed speech and generate response.
        
        Args:
            session_id: The bot session ID
            transcript: What was said in the meeting
            speaker_name: Who said it (optional)
            
        Returns:
            Response with text and audio to play in the meeting
        """
        session = self.active_sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Store transcript
        session["transcripts"].append({
            "speaker": speaker_name or "Participant",
            "text": transcript,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Check if this is directed at the bot
        if not self._should_respond(transcript):
            return {
                "status": "ignored",
                "reason": "Not a question or command for the bot",
                "transcript": transcript,
            }
        
        # Process with voice agent
        try:
            response = await voice_onboarding_agent.process_voice_query(
                session_id=session["agent_session_id"],
                query=transcript,
                include_audio=True,
            )
            
            # Generate audio response
            audio_bytes = await elevenlabs_client.synthesize(
                text=response["text"],
                model_id="eleven_turbo_v2_5",
            )
            
            # Store response
            session["responses"].append({
                "query": transcript,
                "response": response["text"],
                "timestamp": datetime.utcnow().isoformat(),
            })
            
            logger.info(
                "Generated response for Zoom",
                query=transcript[:50],
                response=response["text"][:50],
            )
            
            return {
                "status": "responded",
                "transcript": transcript,
                "response_text": response["text"],
                "response_audio_base64": base64.b64encode(audio_bytes).decode() if audio_bytes else None,
                "sources": response.get("sources", []),
                "topics_covered": response.get("topics_covered", []),
            }
            
        except Exception as e:
            logger.error("Failed to generate response", error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "transcript": transcript,
            }

    def _should_respond(self, text: str) -> bool:
        """Determine if the bot should respond to this text."""
        text_lower = text.lower().strip()
        
        # Always respond to questions
        if text_lower.endswith("?"):
            return True
        
        # Respond to direct triggers
        triggers = [
            "hey assistant",
            "hi assistant",
            "assistant",
            "onboarding bot",
            "tell me",
            "explain",
            "what is",
            "what are",
            "how do",
            "how can",
            "where is",
            "where can",
            "who is",
            "who should",
            "can you",
            "could you",
            "help me",
            "i need",
            "question",
        ]
        
        return any(trigger in text_lower for trigger in triggers)

    async def speak(
        self,
        session_id: str,
        text: str,
    ) -> bytes:
        """Generate audio for the bot to speak.
        
        Returns audio bytes that should be played in the Zoom meeting.
        """
        session = self.active_sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        audio = await elevenlabs_client.synthesize(
            text=text,
            model_id="eleven_turbo_v2_5",
        )
        
        logger.info("Generated speech audio", text=text[:50], audio_size=len(audio))
        
        return audio

    async def get_session_status(self, session_id: str) -> dict[str, Any]:
        """Get the current status of a bot session."""
        session = self.active_sessions.get(session_id)
        if not session:
            return {"status": "not_found"}
        
        return {
            "session_id": session_id,
            "meeting_id": session["meeting_id"],
            "bot_name": session["bot_name"],
            "status": session["status"],
            "transcript_count": len(session["transcripts"]),
            "response_count": len(session["responses"]),
            "created_at": session["created_at"],
            "recent_transcripts": session["transcripts"][-5:],
            "recent_responses": session["responses"][-3:],
        }

    async def end_session(self, session_id: str) -> dict[str, Any]:
        """End a bot session and get summary."""
        session = self.active_sessions.pop(session_id, None)
        
        if not session:
            return {"status": "not_found"}
        
        # End voice agent session
        await voice_onboarding_agent.end_session(session["agent_session_id"])
        
        summary = {
            "session_id": session_id,
            "meeting_id": session["meeting_id"],
            "total_transcripts": len(session["transcripts"]),
            "total_responses": len(session["responses"]),
            "created_at": session["created_at"],
            "ended_at": datetime.utcnow().isoformat(),
            "all_transcripts": session["transcripts"],
            "all_responses": session["responses"],
        }
        
        logger.info("Zoom bot session ended", **{k: v for k, v in summary.items() if k not in ["all_transcripts", "all_responses"]})
        
        return summary

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all active bot sessions."""
        return [
            {
                "session_id": s["session_id"],
                "meeting_id": s["meeting_id"],
                "bot_name": s["bot_name"],
                "status": s["status"],
                "response_count": len(s["responses"]),
            }
            for s in self.active_sessions.values()
        ]


class PlaywrightZoomBot:
    """Zoom bot that joins meetings via browser using Playwright.
    
    This bot can actually join Zoom meetings via the web client
    and interact with the meeting.
    """

    def __init__(self):
        self.active_bots: dict[str, dict] = {}

    async def join_meeting_browser(
        self,
        meeting_url: str,
        passcode: str | None = None,
        bot_name: str = "Onboarding Assistant",
        user_department: str | None = None,
    ) -> dict[str, Any]:
        """Join a Zoom meeting using a browser.
        
        Opens a Chromium browser and joins the Zoom web client.
        """
        import re
        from playwright.async_api import async_playwright

        session_id = str(uuid4())
        
        # Parse meeting info from URL
        match = re.search(r'/j/(\d+)', meeting_url)
        meeting_id = match.group(1) if match else ""
        
        # Extract password from URL if present
        if not passcode:
            pwd_match = re.search(r'pwd=([^&\s]+)', meeting_url)
            passcode = pwd_match.group(1) if pwd_match else None

        # Start voice agent session
        agent_session = await voice_onboarding_agent.start_voice_session(
            user_id=f"playwright_zoom_{session_id}",
            user_name=bot_name,
            user_department=user_department,
            session_type="zoom_browser",
            zoom_meeting_id=meeting_id,
        )

        session = {
            "session_id": session_id,
            "meeting_id": meeting_id,
            "meeting_url": meeting_url,
            "passcode": passcode,
            "bot_name": bot_name,
            "agent_session_id": agent_session["session_id"],
            "status": "launching",
            "created_at": datetime.utcnow().isoformat(),
            "browser": None,
            "page": None,
            "playwright": None,
        }

        self.active_bots[session_id] = session

        # Launch browser in background task
        asyncio.create_task(self._launch_and_join(session_id))

        return {
            "session_id": session_id,
            "meeting_id": meeting_id,
            "bot_name": bot_name,
            "status": "launching",
            "message": "Browser is launching. The bot will join the meeting shortly.",
            "agent_session": agent_session,
        }

    async def _launch_and_join(self, session_id: str):
        """Background task to launch browser and join meeting."""
        from playwright.async_api import async_playwright

        session = self.active_bots.get(session_id)
        if not session:
            return

        try:
            logger.info("Launching browser for Zoom", session_id=session_id)
            
            playwright = await async_playwright().start()
            session["playwright"] = playwright

            # Launch browser
            # Use headless=True for server environments, False for interactive use
            # Set ZOOM_BOT_HEADLESS=false to see the browser
            import os
            headless = os.environ.get("ZOOM_BOT_HEADLESS", "true").lower() != "false"

            browser = await playwright.chromium.launch(
                headless=headless,
                args=[
                    "--use-fake-ui-for-media-stream",
                    "--use-fake-device-for-media-stream",
                    "--auto-accept-camera-and-microphone-capture",
                    "--disable-web-security",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ]
            )
            session["browser"] = browser
            session["status"] = "browser_launched"

            # Create context with permissions
            context = await browser.new_context(
                permissions=["microphone", "camera"],
                viewport={"width": 1280, "height": 720},
            )

            page = await context.new_page()
            session["page"] = page
            session["status"] = "navigating"

            # Convert to web client URL
            meeting_url = session["meeting_url"]
            web_url = meeting_url.replace("/j/", "/wc/join/")
            if "?" in web_url:
                web_url = web_url.split("?")[0]
            
            logger.info("Navigating to Zoom", url=web_url)
            await page.goto(web_url)
            await asyncio.sleep(3)

            session["status"] = "waiting_for_form"

            # Try to fill in the name
            try:
                name_input = await page.wait_for_selector(
                    '#inputname, input[placeholder*="name" i], input[name="name"]',
                    timeout=15000
                )
                if name_input:
                    await name_input.fill(session["bot_name"])
                    logger.info("Filled bot name")
            except Exception as e:
                logger.warning("Could not find name input", error=str(e))

            # Fill password if needed
            if session.get("passcode"):
                try:
                    pwd_input = await page.wait_for_selector(
                        '#inputpasscode, input[type="password"], input[placeholder*="password" i], input[placeholder*="passcode" i]',
                        timeout=5000
                    )
                    if pwd_input:
                        await pwd_input.fill(session["passcode"])
                        logger.info("Filled passcode")
                except Exception as e:
                    logger.warning("Could not find password input", error=str(e))

            session["status"] = "clicking_join"

            # Click join button
            try:
                join_btn = await page.wait_for_selector(
                    'button:has-text("Join"), button:has-text("join"), #joinBtn, .zm-btn--primary',
                    timeout=5000
                )
                if join_btn:
                    await join_btn.click()
                    logger.info("Clicked join button")
            except Exception as e:
                logger.warning("Could not find join button", error=str(e))

            await asyncio.sleep(5)
            
            # Check for "Join Audio" or similar buttons
            try:
                audio_btn = await page.wait_for_selector(
                    'button:has-text("Join Audio"), button:has-text("Computer Audio")',
                    timeout=10000
                )
                if audio_btn:
                    await audio_btn.click()
                    logger.info("Clicked audio join button")
            except Exception:
                pass

            session["status"] = "in_meeting"
            logger.info("Bot joined meeting successfully", session_id=session_id)

            # Keep session alive
            while session_id in self.active_bots:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error("Failed to join meeting", error=str(e), session_id=session_id)
            session["status"] = "error"
            session["error"] = str(e)

    async def speak_in_meeting(self, session_id: str, text: str) -> dict[str, Any]:
        """Make the bot speak in the meeting by playing audio."""
        session = self.active_bots.get(session_id)
        if not session:
            return {"status": "error", "error": "Session not found"}

        if not session.get("page"):
            return {"status": "error", "error": "Browser not ready"}

        # Generate audio
        audio = await elevenlabs_client.synthesize(
            text=text,
            model_id="eleven_turbo_v2_5",
        )

        if audio:
            # Play audio through browser
            audio_b64 = base64.b64encode(audio).decode()
            try:
                await session["page"].evaluate(f"""
                    (async () => {{
                        const audio = new Audio('data:audio/mp3;base64,{audio_b64}');
                        audio.volume = 1.0;
                        await audio.play();
                    }})();
                """)
                return {"status": "spoken", "text": text}
            except Exception as e:
                return {"status": "error", "error": str(e), "audio_available": True}
        
        return {"status": "error", "error": "Failed to generate audio"}

    async def leave_meeting(self, session_id: str) -> dict[str, Any]:
        """Leave the meeting and close browser."""
        session = self.active_bots.pop(session_id, None)
        
        if not session:
            return {"status": "not_found"}

        # Close browser
        try:
            if session.get("browser"):
                await session["browser"].close()
            if session.get("playwright"):
                await session["playwright"].stop()
        except Exception as e:
            logger.warning("Error closing browser", error=str(e))

        # End voice agent session
        try:
            await voice_onboarding_agent.end_session(session["agent_session_id"])
        except Exception:
            pass

        return {
            "session_id": session_id,
            "status": "left",
            "meeting_id": session.get("meeting_id"),
        }

    def get_status(self, session_id: str) -> dict[str, Any] | None:
        """Get bot session status."""
        session = self.active_bots.get(session_id)
        if not session:
            return None
        
        return {
            "session_id": session_id,
            "meeting_id": session.get("meeting_id"),
            "status": session.get("status"),
            "bot_name": session.get("bot_name"),
            "error": session.get("error"),
        }

    def list_bots(self) -> list[dict]:
        """List all active browser bots."""
        return [
            {
                "session_id": s["session_id"],
                "meeting_id": s.get("meeting_id"),
                "status": s.get("status"),
                "bot_name": s.get("bot_name"),
            }
            for s in self.active_bots.values()
        ]


# Singleton instances
zoom_realtime_bot = ZoomRealTimeBot()
playwright_zoom_bot = PlaywrightZoomBot()
