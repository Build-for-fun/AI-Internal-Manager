"""Voice API endpoints for voice-enabled onboarding.

Integrates:
- Deepgram for Speech-to-Text (STT)
- ElevenLabs for Text-to-Speech (TTS)
"""

import asyncio
import base64
import json
from typing import Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.onboarding.agent import onboarding_agent
from src.config import settings
from src.models.conversation import Conversation, ConversationType, Message
from src.models.database import get_db
from src.models.user import User
from src.schemas.onboarding import VoiceSessionRequest, VoiceSessionResponse

logger = structlog.get_logger()

router = APIRouter()

# Store active voice sessions
active_sessions: dict[str, dict[str, Any]] = {}


async def get_current_user(
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current user (dev placeholder)."""
    stmt = select(User).limit(1)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=str(uuid4()),
            email="dev@example.com",
            hashed_password="dev",
            full_name="Development User",
            role="Software Engineer",
            department="Engineering",
            team="Platform",
        )
        db.add(user)
        await db.commit()

    return user


class DeepgramSTT:
    """Deepgram Speech-to-Text client."""

    def __init__(self):
        self.api_key = settings.deepgram_api_key.get_secret_value()

    async def transcribe_stream(self, websocket: WebSocket):
        """Stream audio to Deepgram and yield transcriptions."""
        import httpx

        async with httpx.AsyncClient() as client:
            # Deepgram streaming endpoint
            url = "wss://api.deepgram.com/v1/listen"
            params = {
                "encoding": "linear16",
                "sample_rate": 16000,
                "channels": 1,
                "model": "nova-2",
                "smart_format": True,
                "interim_results": True,
            }

            # This is a simplified implementation
            # In production, use websockets to stream to Deepgram
            pass

    async def transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio data to text."""
        import httpx

        if not self.api_key:
            logger.warning("Deepgram API key not configured")
            return ""

        async with httpx.AsyncClient() as client:
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

            logger.error("Deepgram error", status=response.status_code)
            return ""


class ElevenLabsTTS:
    """ElevenLabs Text-to-Speech client."""

    def __init__(self):
        self.api_key = settings.elevenlabs_api_key.get_secret_value()
        self.voice_id = settings.elevenlabs_voice_id

    async def synthesize(self, text: str) -> bytes:
        """Synthesize text to speech audio."""
        import httpx

        if not self.api_key:
            logger.warning("ElevenLabs API key not configured")
            return b""

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}",
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                    },
                },
            )

            if response.status_code == 200:
                return response.content

            logger.error("ElevenLabs error", status=response.status_code)
            return b""

    async def synthesize_stream(self, text: str):
        """Stream synthesized audio chunks."""
        import httpx

        if not self.api_key:
            return

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream",
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                    },
                },
            ) as response:
                async for chunk in response.aiter_bytes(chunk_size=1024):
                    yield chunk


# Initialize clients
stt_client = DeepgramSTT()
tts_client = ElevenLabsTTS()


@router.post("/sessions", response_model=VoiceSessionResponse)
async def create_voice_session(
    request: VoiceSessionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VoiceSessionResponse:
    """Create a new voice session for onboarding."""
    session_id = str(uuid4())

    conversation = Conversation(
        id=str(uuid4()),
        user_id=user.id,
        title="Voice Onboarding Session",
        conversation_type=ConversationType.VOICE.value,
        conversation_metadata={
            "topic": request.topic,
            "resume": request.resume,
            "user_role": request.user_role,
        },
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    active_sessions[session_id] = {
        "id": session_id,
        "topic": request.topic,
        "created_at": asyncio.get_event_loop().time(),
        "messages": [],
        "conversation_id": conversation.id,
        "user_id": user.id,
    }

    logger.info("Voice session created", session_id=session_id)

    return VoiceSessionResponse(
        session_id=session_id,
        websocket_url=f"/api/v1/voice/ws/{session_id}",
        current_topic=request.topic,
        estimated_duration_minutes=15,
    )


@router.get("/sessions/{session_id}")
async def get_voice_session(session_id: str):
    """Get voice session status."""
    session = active_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "topic": session.get("topic"),
        "message_count": len(session.get("messages", [])),
    }


@router.delete("/sessions/{session_id}")
async def end_voice_session(session_id: str):
    """End a voice session."""
    if session_id in active_sessions:
        del active_sessions[session_id]
        logger.info("Voice session ended", session_id=session_id)
        return {"status": "ended"}

    raise HTTPException(status_code=404, detail="Session not found")


@router.websocket("/ws/{session_id}")
async def voice_websocket(
    websocket: WebSocket,
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """WebSocket endpoint for voice streaming.

    Protocol:
    - Client sends: {"type": "audio", "data": "<base64 audio>"} or {"type": "text", "data": "<text>"}
    - Server sends: {"type": "audio", "data": "<base64 audio>"} and {"type": "text", "data": "<text>"}
    """
    await websocket.accept()

    session = active_sessions.get(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return

    logger.info("Voice WebSocket connected", session_id=session_id)

    try:
        # Send welcome message
        welcome_text = "Hello! I'm your onboarding assistant. How can I help you today?"
        welcome_audio = await tts_client.synthesize(welcome_text)

        await websocket.send_json({
            "type": "text",
            "data": welcome_text,
        })

        if welcome_audio:
            await websocket.send_json({
                "type": "audio",
                "data": base64.b64encode(welcome_audio).decode(),
            })

        while True:
            # Receive message
            data = await websocket.receive_text()
            message = json.loads(data)

            msg_type = message.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            user_text = ""

            if msg_type == "audio":
                # Transcribe audio
                audio_data = base64.b64decode(message.get("data", ""))
                user_text = await stt_client.transcribe_audio(audio_data)

                # Send transcription back
                await websocket.send_json({
                    "type": "transcription",
                    "data": user_text,
                })

            elif msg_type == "text":
                user_text = message.get("data", "")

            if not user_text:
                continue

            # Store message
            session["messages"].append({
                "role": "user",
                "content": user_text,
            })

            db.add(
                Message(
                    id=str(uuid4()),
                    conversation_id=session["conversation_id"],
                    role="user",
                    content=user_text,
                )
            )
            await db.commit()

            # Process with onboarding agent
            result = await onboarding_agent.process(
                query=user_text,
                context={
                    "user_id": message.get("user_id", ""),
                    "messages": session["messages"],
                },
            )

            response_text = result["response"]

            # Store response
            session["messages"].append({
                "role": "assistant",
                "content": response_text,
            })

            db.add(
                Message(
                    id=str(uuid4()),
                    conversation_id=session["conversation_id"],
                    role="assistant",
                    content=response_text,
                    agent="onboarding",
                )
            )
            await db.commit()

            # Send text response
            await websocket.send_json({
                "type": "text",
                "data": response_text,
            })

            # Synthesize and send audio
            response_audio = await tts_client.synthesize(response_text)
            if response_audio:
                await websocket.send_json({
                    "type": "audio",
                    "data": base64.b64encode(response_audio).decode(),
                })

    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected", session_id=session_id)
    except Exception as e:
        logger.error("Voice WebSocket error", error=str(e), session_id=session_id)
        await websocket.close(code=4000, reason=str(e))


@router.post("/synthesize")
async def synthesize_text(text: str):
    """Synthesize text to speech (non-streaming)."""
    from fastapi.responses import Response

    audio = await tts_client.synthesize(text)

    if not audio:
        raise HTTPException(status_code=500, detail="Failed to synthesize audio")

    return Response(
        content=audio,
        media_type="audio/mpeg",
    )


@router.post("/transcribe")
async def transcribe_audio(audio: bytes):
    """Transcribe audio to text (non-streaming)."""
    transcript = await stt_client.transcribe_audio(audio)

    return {"transcript": transcript}
