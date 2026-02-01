"""Voice Agent API endpoints.

Enhanced voice endpoints for:
- Voice-based onboarding with textbook knowledge
- Zoom meeting integration
- Real-time voice streaming
"""

import asyncio
import base64
import json
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel

import websockets
from websockets.exceptions import ConnectionClosed

from src.voice.agent import voice_onboarding_agent
from src.voice.elevenlabs_client import elevenlabs_client
from src.voice.zoom_integration import zoom_integration, zoom_webhook_handler
from src.voice.zoom_bot import zoom_meeting_bot, test_zoom_connection
from src.voice.realtime_zoom import zoom_realtime_bot, playwright_zoom_bot
from src.api.v1.voice import stt_client  # Import STT client for audio transcription
from src.config import settings

# ElevenLabs Conversational AI Agent configuration
ELEVENLABS_AGENT_ID = "agent_4601kgc1063efqn8b3c4qea00sey"
ELEVENLABS_CONVAI_URL = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={ELEVENLABS_AGENT_ID}"

logger = structlog.get_logger()

router = APIRouter(prefix="/agent", tags=["voice-agent"])


# Request/Response Models
class VoiceSessionStartRequest(BaseModel):
    """Request to start a voice onboarding session."""
    user_id: str
    user_name: str
    user_role: str | None = None
    user_department: str | None = None
    session_type: str = "onboarding"


class VoiceQueryRequest(BaseModel):
    """Request to process a voice query."""
    query: str
    include_audio: bool = True


class ZoomJoinRequest(BaseModel):
    """Request to join a Zoom meeting."""
    meeting_id: str
    meeting_password: str | None = None
    display_name: str = "Onboarding Assistant"
    user_id: str | None = None
    user_department: str | None = None


class TextToSpeechRequest(BaseModel):
    """Request for text-to-speech synthesis."""
    text: str
    voice_id: str | None = None
    model_id: str = "eleven_turbo_v2_5"


# Voice Agent Endpoints
@router.post("/sessions")
async def start_voice_session(request: VoiceSessionStartRequest):
    """Start a new voice onboarding session.
    
    Creates a session for voice-based onboarding interactions
    with access to the company textbook knowledge base.
    """
    session = await voice_onboarding_agent.start_voice_session(
        user_id=request.user_id,
        user_name=request.user_name,
        user_role=request.user_role,
        user_department=request.user_department,
        session_type=request.session_type,
    )
    
    return session


@router.get("/sessions")
async def list_voice_sessions():
    """List all active voice sessions."""
    return {
        "sessions": voice_onboarding_agent.get_active_sessions(),
        "count": len(voice_onboarding_agent.active_sessions),
    }


@router.get("/sessions/{session_id}")
async def get_voice_session(session_id: str):
    """Get details of a specific voice session."""
    session = voice_onboarding_agent.active_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session["id"],
        "user_name": session.get("user_name"),
        "department": session.get("user_department"),
        "questions_asked": session.get("questions_asked", 0),
        "topics_covered": session.get("topics_covered", []),
        "message_count": len(session.get("messages", [])),
    }


@router.post("/sessions/{session_id}/query")
async def process_voice_query(session_id: str, request: VoiceQueryRequest):
    """Process a voice query and get response with optional audio.
    
    The query is processed against the textbook knowledge base
    to provide accurate, context-aware responses.
    """
    try:
        result = await voice_onboarding_agent.process_voice_query(
            session_id=session_id,
            query=request.query,
            include_audio=request.include_audio,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Voice query processing failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process query")


@router.delete("/sessions/{session_id}")
async def end_voice_session(session_id: str):
    """End a voice session and get summary."""
    summary = await voice_onboarding_agent.end_session(session_id)
    
    if summary.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Session not found")
    
    return summary


@router.websocket("/ws/{session_id}")
async def voice_agent_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time voice interaction.
    
    Protocol:
    - Client sends: {"type": "text", "query": "..."} or {"type": "audio", "data": "<base64>"}
    - Server sends: {"type": "text", "data": "..."} and {"type": "audio", "data": "<base64>"}
    """
    await websocket.accept()
    
    session = voice_onboarding_agent.active_sessions.get(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return
    
    logger.info("Voice agent WebSocket connected", session_id=session_id)
    
    try:
        # Send welcome message
        welcome = f"Hello {session.get('user_name', 'there')}! I'm your onboarding assistant. Feel free to ask me anything about the company!"
        welcome_audio = await elevenlabs_client.synthesize(welcome)

        await websocket.send_json({
            "type": "text",
            "data": welcome,
        })

        if welcome_audio:
            await websocket.send_json({
                "type": "audio",
                "data": base64.b64encode(welcome_audio).decode(),
            })

        # Send complete to signal audio is ready to play
        await websocket.send_json({
            "type": "complete",
            "sources": [],
        })
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            msg_type = message.get("type")
            
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            
            query = ""

            if msg_type == "text":
                query = message.get("query", message.get("data", ""))
            elif msg_type == "audio":
                # Transcribe audio using Deepgram STT
                audio_data = base64.b64decode(message.get("data", ""))
                query = await stt_client.transcribe_audio(audio_data)

                # Send transcription back to frontend
                if query:
                    await websocket.send_json({
                        "type": "transcription",
                        "data": query,
                    })
                    logger.info("Transcribed audio", session_id=session_id, text=query[:50])

            if not query:
                logger.warning("Empty query, skipping", session_id=session_id, msg_type=msg_type)
                continue
            
            # Process query and stream response
            async for chunk in voice_onboarding_agent.stream_voice_response(
                session_id=session_id,
                query=query,
            ):
                if chunk["type"] == "text":
                    await websocket.send_json({
                        "type": "text",
                        "data": chunk["data"],
                    })
                elif chunk["type"] == "audio":
                    await websocket.send_json({
                        "type": "audio",
                        "data": chunk["data"],
                    })
                elif chunk["type"] == "complete":
                    await websocket.send_json({
                        "type": "complete",
                        "sources": chunk.get("sources", []),
                    })
    
    except WebSocketDisconnect:
        logger.info("Voice agent WebSocket disconnected", session_id=session_id)
    except Exception as e:
        logger.error("Voice agent WebSocket error", error=str(e))
        await websocket.close(code=4000, reason=str(e))


# ============== ELEVENLABS CONVERSATIONAL AI AGENT ==============

@router.websocket("/convai/ws")
async def elevenlabs_convai_websocket(websocket: WebSocket):
    """WebSocket endpoint that bridges to ElevenLabs Conversational AI agent.

    This provides real-time voice-to-voice conversation using the ElevenLabs
    Conversational AI agent. The agent handles STT, conversation, and TTS.

    Protocol:
    - Client sends: {"type": "audio", "data": "<base64 audio>"}
    - Server sends: {"type": "audio", "data": "<base64 audio>"}
                   {"type": "transcript", "role": "user"|"agent", "text": "..."}
    """
    await websocket.accept()
    logger.info("ElevenLabs ConvAI WebSocket connected")

    elevenlabs_ws = None

    try:
        # Get API key
        api_key = settings.elevenlabs_api_key.get_secret_value()
        if not api_key:
            await websocket.send_json({"type": "error", "message": "ElevenLabs API key not configured"})
            await websocket.close(code=4001, reason="API key not configured")
            return

        # Connect to ElevenLabs Conversational AI
        headers = {"xi-api-key": api_key}
        elevenlabs_ws = await websockets.connect(
            ELEVENLABS_CONVAI_URL,
            extra_headers=headers,
            ping_interval=20,
            ping_timeout=20,
        )

        logger.info("Connected to ElevenLabs ConvAI", agent_id=ELEVENLABS_AGENT_ID)

        # Notify client we're connected
        await websocket.send_json({
            "type": "connected",
            "agent_id": ELEVENLABS_AGENT_ID,
        })

        async def forward_to_client():
            """Forward messages from ElevenLabs to the client."""
            try:
                async for message in elevenlabs_ws:
                    data = json.loads(message)
                    msg_type = data.get("type", "")

                    if msg_type == "audio":
                        # Forward audio chunk to client
                        await websocket.send_json({
                            "type": "audio",
                            "data": data.get("audio", ""),
                        })
                    elif msg_type == "user_transcript":
                        # User's speech was transcribed
                        await websocket.send_json({
                            "type": "transcript",
                            "role": "user",
                            "text": data.get("user_transcript", ""),
                        })
                    elif msg_type == "agent_response":
                        # Agent's text response
                        await websocket.send_json({
                            "type": "transcript",
                            "role": "agent",
                            "text": data.get("agent_response", ""),
                        })
                    elif msg_type == "interruption":
                        await websocket.send_json({"type": "interruption"})
                    elif msg_type == "ping":
                        await elevenlabs_ws.send(json.dumps({"type": "pong"}))
                    elif msg_type == "conversation_initiation_metadata":
                        # Session started
                        await websocket.send_json({
                            "type": "session_started",
                            "conversation_id": data.get("conversation_id"),
                        })

            except ConnectionClosed:
                logger.info("ElevenLabs connection closed")
            except Exception as e:
                logger.error("Error forwarding from ElevenLabs", error=str(e))

        async def forward_to_elevenlabs():
            """Forward messages from client to ElevenLabs."""
            try:
                while True:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    msg_type = message.get("type", "")

                    if msg_type == "audio":
                        # Forward audio to ElevenLabs
                        await elevenlabs_ws.send(json.dumps({
                            "user_audio_chunk": message.get("data", ""),
                        }))
                    elif msg_type == "ping":
                        await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                logger.info("Client disconnected")
            except Exception as e:
                logger.error("Error forwarding to ElevenLabs", error=str(e))

        # Run both forwarding tasks concurrently
        await asyncio.gather(
            forward_to_client(),
            forward_to_elevenlabs(),
            return_exceptions=True,
        )

    except Exception as e:
        logger.error("ElevenLabs ConvAI WebSocket error", error=str(e))
        await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        if elevenlabs_ws:
            await elevenlabs_ws.close()
        logger.info("ElevenLabs ConvAI WebSocket disconnected")


# ElevenLabs Direct Endpoints
@router.post("/synthesize")
async def synthesize_speech(request: TextToSpeechRequest):
    """Synthesize text to speech using ElevenLabs.
    
    Returns audio in MP3 format.
    """
    audio = await elevenlabs_client.synthesize(
        text=request.text,
        voice_id=request.voice_id,
        model_id=request.model_id,
    )
    
    if not audio:
        raise HTTPException(status_code=500, detail="Failed to synthesize audio")
    
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=speech.mp3"},
    )


@router.post("/synthesize/stream")
async def synthesize_speech_stream(request: TextToSpeechRequest):
    """Stream synthesized speech for lower latency.
    
    Returns chunked audio stream.
    """
    from fastapi.responses import StreamingResponse
    
    async def audio_stream():
        async for chunk in elevenlabs_client.synthesize_stream(
            text=request.text,
            voice_id=request.voice_id,
            model_id=request.model_id,
        ):
            yield chunk
    
    return StreamingResponse(
        audio_stream(),
        media_type="audio/mpeg",
    )


@router.get("/voices")
async def list_available_voices():
    """List available ElevenLabs voices."""
    voices = await elevenlabs_client.get_voices()
    return {
        "voices": voices,
        "default_voice_id": elevenlabs_client.default_voice_id,
        "preset_options": elevenlabs_client.voice_options,
    }


# Zoom Integration Endpoints
@router.post("/zoom/join")
async def join_zoom_meeting(request: ZoomJoinRequest):
    """Join a Zoom meeting as the onboarding voice bot.
    
    The bot will listen for questions and provide voice responses
    using the company textbook knowledge base.
    """
    result = await zoom_integration.join_meeting(
        meeting_id=request.meeting_id,
        meeting_password=request.meeting_password,
        display_name=request.display_name,
        user_id=request.user_id,
        user_department=request.user_department,
    )
    
    return result


@router.get("/zoom/meetings")
async def list_zoom_meetings():
    """List active Zoom meeting sessions."""
    return {
        "meetings": zoom_integration.get_active_meetings(),
        "count": len(zoom_integration.active_meetings),
    }


@router.post("/zoom/meetings/{session_id}/speak")
async def speak_in_zoom_meeting(session_id: str, text: str):
    """Make the bot speak in a Zoom meeting.
    
    Generates audio and returns it for playback in the meeting.
    """
    try:
        audio = await zoom_integration.speak_to_meeting(session_id, text)
        return Response(
            content=audio,
            media_type="audio/mpeg",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/zoom/meetings/{session_id}/process")
async def process_zoom_transcript(session_id: str, transcript: str, speaker_name: str | None = None):
    """Process a transcript from a Zoom meeting.
    
    If the transcript is a question for the bot, a response will be generated.
    """
    result = await zoom_integration.process_transcript(
        session_id=session_id,
        transcript=transcript,
        speaker_name=speaker_name,
    )
    
    if result:
        return result
    
    return {"status": "ignored", "reason": "Not a question for the bot"}


@router.delete("/zoom/meetings/{session_id}")
async def leave_zoom_meeting(session_id: str):
    """Leave a Zoom meeting and get session summary."""
    summary = await zoom_integration.leave_meeting(session_id)
    
    if summary.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Meeting session not found")
    
    return summary


@router.post("/zoom/webhook/{session_id}")
async def zoom_webhook(session_id: str, request: Request):
    """Handle Zoom webhook events for a specific session.
    
    Processes real-time events from Zoom meetings.
    """
    body = await request.body()
    
    # Verify webhook signature
    signature = request.headers.get("x-zm-signature", "")
    timestamp = request.headers.get("x-zm-request-timestamp", "")
    
    if not zoom_webhook_handler.verify_webhook(body, signature, timestamp):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    event = await request.json()
    result = await zoom_webhook_handler.handle_event(event)
    
    return result


@router.post("/zoom/webhook")
async def zoom_general_webhook(request: Request):
    """Handle general Zoom webhook events.
    
    Endpoint for Zoom webhook URL verification and general events.
    """
    body = await request.body()
    event = await request.json()
    
    # Handle URL verification challenge
    if event.get("event") == "endpoint.url_validation":
        plain_token = event.get("payload", {}).get("plainToken")
        if plain_token:
            import hashlib
            import hmac
            
            secret = getattr(zoom_webhook_handler, 'webhook_secret', '')
            encrypted = hmac.new(
                secret.encode(),
                plain_token.encode(),
                hashlib.sha256,
            ).hexdigest()
            
            return {
                "plainToken": plain_token,
                "encryptedToken": encrypted,
            }
    
    # Process other events
    result = await zoom_webhook_handler.handle_event(event)
    return result


# Zoom Bot Endpoints (for real meeting integration)
class ZoomBotStartRequest(BaseModel):
    """Request to start a Zoom bot session."""
    meeting_id: str
    passcode: str | None = None
    user_department: str | None = None


class ZoomSpeechRequest(BaseModel):
    """Request to process speech in a Zoom meeting."""
    transcript: str
    speaker_name: str | None = None


@router.get("/zoom/test")
async def test_zoom_api():
    """Test the Zoom API connection with configured credentials."""
    result = await test_zoom_connection()
    return result


@router.post("/zoom/bot/start")
async def start_zoom_bot(request: ZoomBotStartRequest):
    """Start a bot session for a Zoom meeting.
    
    This creates a session that can process speech and generate responses
    for the meeting. For real-time audio, use with a transcription service.
    """
    try:
        session = await zoom_meeting_bot.start_bot_session(
            meeting_id=request.meeting_id,
            passcode=request.passcode,
            user_department=request.user_department,
        )
        return session
    except Exception as e:
        logger.error("Failed to start Zoom bot", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/zoom/bot/list")
async def list_zoom_bots():
    """List all active Zoom bot sessions."""
    return {
        "bots": zoom_meeting_bot.get_active_bots(),
        "count": len(zoom_meeting_bot.active_bots),
    }


@router.post("/zoom/bot/{bot_id}/speech")
async def process_zoom_speech(bot_id: str, request: ZoomSpeechRequest):
    """Process speech from a Zoom meeting.
    
    Send transcribed speech to the bot and get a response if it's a question.
    Returns both text and audio for the response.
    """
    result = await zoom_meeting_bot.process_speech(
        bot_id=bot_id,
        transcript=request.transcript,
        speaker_name=request.speaker_name,
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Bot session not found")
    
    return result


@router.post("/zoom/bot/{bot_id}/speak")
async def make_bot_speak(bot_id: str, text: str):
    """Generate audio for the bot to speak in the meeting.
    
    Returns MP3 audio that can be played in the Zoom meeting.
    """
    try:
        audio = await zoom_meeting_bot.generate_audio_response(bot_id, text)
        return Response(
            content=audio,
            media_type="audio/mpeg",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/zoom/bot/{bot_id}")
async def end_zoom_bot(bot_id: str):
    """End a Zoom bot session and get summary."""
    summary = await zoom_meeting_bot.end_bot_session(bot_id)
    
    if summary.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Bot session not found")
    
    return summary


@router.get("/zoom/meeting/{meeting_id}")
async def get_zoom_meeting_info(meeting_id: str):
    """Get information about a Zoom meeting."""
    info = await zoom_meeting_bot.get_meeting_info(meeting_id)
    
    if not info:
        raise HTTPException(status_code=404, detail="Meeting not found or access denied")
    
    return info


@router.post("/zoom/meeting/create")
async def create_zoom_meeting(
    topic: str = "Onboarding Session",
    duration: int = 30,
):
    """Create a new Zoom meeting for onboarding.
    
    Returns meeting details including join URL.
    """
    meeting = await zoom_meeting_bot.create_meeting(
        topic=topic,
        duration=duration,
    )
    
    if not meeting:
        raise HTTPException(status_code=500, detail="Failed to create meeting")
    
    return meeting


# ============== REAL-TIME ZOOM BOT ENDPOINTS ==============

class RealtimeZoomJoinRequest(BaseModel):
    """Request to join a Zoom meeting with the real-time bot."""
    meeting_url: str
    bot_name: str = "Onboarding Assistant"
    user_department: str | None = None


class RealtimeSpeechRequest(BaseModel):
    """Request to process speech from a Zoom meeting."""
    transcript: str
    speaker_name: str | None = None


@router.post("/zoom/realtime/join")
async def join_zoom_realtime(request: RealtimeZoomJoinRequest):
    """Join a Zoom meeting with the real-time onboarding bot.
    
    The bot will listen to meeting audio and respond to questions
    about company onboarding using the knowledge base.
    
    Usage:
    1. Call this endpoint with the meeting URL
    2. Send transcripts using the /speech endpoint
    3. Play the audio responses in your meeting
    """
    try:
        session = await zoom_realtime_bot.join_meeting(
            meeting_url=request.meeting_url,
            bot_name=request.bot_name,
            user_department=request.user_department,
        )
        return session
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to join Zoom meeting", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/zoom/realtime/sessions")
async def list_realtime_sessions():
    """List all active real-time Zoom bot sessions."""
    return {
        "sessions": zoom_realtime_bot.list_sessions(),
        "count": len(zoom_realtime_bot.active_sessions),
    }


@router.get("/zoom/realtime/{session_id}")
async def get_realtime_session(session_id: str):
    """Get status and details of a real-time Zoom session."""
    status = await zoom_realtime_bot.get_session_status(session_id)
    
    if status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Session not found")
    
    return status


@router.post("/zoom/realtime/{session_id}/speech")
async def process_realtime_speech(session_id: str, request: RealtimeSpeechRequest):
    """Process speech from the Zoom meeting.
    
    Send what participants say, and the bot will respond if it's a question.
    Returns both text response and audio (base64) to play in the meeting.
    
    Example questions the bot can answer:
    - "What are the company policies?"
    - "How do I set up my development environment?"
    - "Who should I talk to about benefits?"
    """
    try:
        result = await zoom_realtime_bot.process_speech(
            session_id=session_id,
            transcript=request.transcript,
            speaker_name=request.speaker_name,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to process speech", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/zoom/realtime/{session_id}/speak")
async def make_realtime_bot_speak(session_id: str, text: str):
    """Make the bot speak custom text.
    
    Returns MP3 audio to play in the Zoom meeting.
    """
    try:
        audio = await zoom_realtime_bot.speak(session_id, text)
        return Response(
            content=audio,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=response.mp3"},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/zoom/realtime/{session_id}")
async def end_realtime_session(session_id: str):
    """End a real-time Zoom session and get summary."""
    summary = await zoom_realtime_bot.end_session(session_id)
    
    if summary.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Session not found")
    
    return summary


@router.websocket("/zoom/realtime/{session_id}/ws")
async def zoom_realtime_websocket(websocket: WebSocket, session_id: str):
    """WebSocket for real-time Zoom meeting interaction.
    
    Protocol:
    - Send: {"type": "speech", "transcript": "...", "speaker": "..."}
    - Receive: {"type": "response", "text": "...", "audio": "<base64>"}
    """
    await websocket.accept()
    
    session = zoom_realtime_bot.active_sessions.get(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return
    
    logger.info("Real-time Zoom WebSocket connected", session_id=session_id)
    
    try:
        # Send welcome message
        welcome = f"Hello! I'm {session['bot_name']}, your onboarding assistant. I'm listening to this meeting and ready to answer any questions!"
        welcome_audio = await elevenlabs_client.synthesize(welcome)
        
        await websocket.send_json({
            "type": "welcome",
            "text": welcome,
            "audio": base64.b64encode(welcome_audio).decode() if welcome_audio else None,
        })
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            
            if message.get("type") == "speech":
                transcript = message.get("transcript", "")
                speaker = message.get("speaker")
                
                if transcript:
                    result = await zoom_realtime_bot.process_speech(
                        session_id=session_id,
                        transcript=transcript,
                        speaker_name=speaker,
                    )
                    
                    if result.get("status") == "responded":
                        await websocket.send_json({
                            "type": "response",
                            "text": result.get("response_text"),
                            "audio": result.get("response_audio_base64"),
                            "sources": result.get("sources", []),
                        })
                    else:
                        await websocket.send_json({
                            "type": "acknowledged",
                            "transcript": transcript,
                            "status": result.get("status"),
                        })
    
    except WebSocketDisconnect:
        logger.info("Real-time Zoom WebSocket disconnected", session_id=session_id)
    except Exception as e:
        logger.error("Real-time Zoom WebSocket error", error=str(e))
        await websocket.close(code=4000, reason=str(e))


# ============== BROWSER-BASED ZOOM BOT (PLAYWRIGHT) ==============

class BrowserBotJoinRequest(BaseModel):
    """Request to join a Zoom meeting with browser bot."""
    meeting_url: str
    passcode: str | None = None
    bot_name: str = "Onboarding Assistant"
    user_department: str | None = None


@router.post("/zoom/browser/join")
async def join_zoom_with_browser(request: BrowserBotJoinRequest):
    """Join a Zoom meeting using a browser-based bot.
    
    This actually opens a browser and joins the Zoom web client.
    The bot will appear as a participant in the meeting.
    """
    try:
        result = await playwright_zoom_bot.join_meeting_browser(
            meeting_url=request.meeting_url,
            passcode=request.passcode,
            bot_name=request.bot_name,
            user_department=request.user_department,
        )
        return result
    except Exception as e:
        logger.error("Failed to join with browser bot", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/zoom/browser/list")
async def list_browser_bots():
    """List all active browser-based Zoom bots."""
    return {
        "bots": playwright_zoom_bot.list_bots(),
        "count": len(playwright_zoom_bot.active_bots),
    }


@router.get("/zoom/browser/{session_id}")
async def get_browser_bot_status(session_id: str):
    """Get status of a browser-based Zoom bot."""
    status = playwright_zoom_bot.get_status(session_id)
    if not status:
        raise HTTPException(status_code=404, detail="Bot session not found")
    return status


@router.post("/zoom/browser/{session_id}/speak")
async def browser_bot_speak(session_id: str, text: str):
    """Make the browser bot speak in the meeting.
    
    Generates audio and plays it through the browser into the meeting.
    """
    result = await playwright_zoom_bot.speak_in_meeting(session_id, text)
    return result


@router.delete("/zoom/browser/{session_id}")
async def leave_zoom_browser(session_id: str):
    """Leave the Zoom meeting and close the browser."""
    result = await playwright_zoom_bot.leave_meeting(session_id)
    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Bot session not found")
    return result
