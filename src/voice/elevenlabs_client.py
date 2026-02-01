"""Enhanced ElevenLabs client with Conversational AI support.

Features:
- Text-to-Speech synthesis
- Streaming audio generation
- Conversational AI WebSocket integration
- Voice cloning support
- Multi-language support
"""

import asyncio
import base64
import json
from typing import Any, AsyncGenerator, Callable
from uuid import uuid4

import httpx
import structlog
import websockets
from websockets.exceptions import ConnectionClosed

from src.config import settings

logger = structlog.get_logger()


class ElevenLabsClient:
    """Advanced ElevenLabs client with Conversational AI capabilities."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.elevenlabs_api_key.get_secret_value()
        self.base_url = "https://api.elevenlabs.io/v1"
        self.ws_url = "wss://api.elevenlabs.io/v1"
        self.default_voice_id = settings.elevenlabs_voice_id
        
        # Available voices for different personas
        self.voice_options = {
            "rachel": "21m00Tcm4TlvDq8ikWAM",  # Rachel - Professional female
            "josh": "TxGEqnHWrfWFTfGW9XjX",  # Josh - Professional male
            "bella": "EXAVITQu4vr4xnSDxMaL",  # Bella - Warm female
            "arnold": "VR6AewLTigWG4xSOukaG",  # Arnold - Deep male
            "elli": "MF3mGyEYCl7XYWbV9V6O",  # Elli - Young female
        }

    @property
    def headers(self) -> dict[str, str]:
        return {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    async def get_voices(self) -> list[dict[str, Any]]:
        """Get available voices."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/voices",
                headers=self.headers,
            )
            if response.status_code == 200:
                return response.json().get("voices", [])
            logger.error("Failed to get voices", status=response.status_code)
            return []

    async def synthesize(
        self,
        text: str,
        voice_id: str | None = None,
        model_id: str = "eleven_turbo_v2_5",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True,
    ) -> bytes:
        """Synthesize text to speech audio.
        
        Args:
            text: Text to synthesize
            voice_id: ElevenLabs voice ID (defaults to configured voice)
            model_id: Model to use (eleven_turbo_v2_5 for low latency)
            stability: Voice stability (0-1)
            similarity_boost: Voice clarity (0-1)
            style: Style exaggeration (0-1)
            use_speaker_boost: Enhance speaker similarity
            
        Returns:
            Audio bytes in MP3 format
        """
        voice = voice_id or self.default_voice_id

        if not self.api_key:
            logger.warning("ElevenLabs API key not configured")
            return b""

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/text-to-speech/{voice}",
                headers=self.headers,
                json={
                    "text": text,
                    "model_id": model_id,
                    "voice_settings": {
                        "stability": stability,
                        "similarity_boost": similarity_boost,
                        "style": style,
                        "use_speaker_boost": use_speaker_boost,
                    },
                },
            )

            if response.status_code == 200:
                logger.info("Audio synthesized", text_length=len(text), voice=voice)
                return response.content

            logger.error(
                "ElevenLabs synthesis error",
                status=response.status_code,
                response=response.text,
            )
            return b""

    async def synthesize_stream(
        self,
        text: str,
        voice_id: str | None = None,
        model_id: str = "eleven_turbo_v2_5",
        chunk_size: int = 1024,
    ) -> AsyncGenerator[bytes, None]:
        """Stream synthesized audio chunks for real-time playback.
        
        Yields audio chunks as they're generated for lower latency.
        """
        voice = voice_id or self.default_voice_id

        if not self.api_key:
            return

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/text-to-speech/{voice}/stream",
                headers=self.headers,
                json={
                    "text": text,
                    "model_id": model_id,
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                    },
                    "optimize_streaming_latency": 3,  # Maximum optimization
                },
            ) as response:
                if response.status_code == 200:
                    async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                        yield chunk
                else:
                    logger.error("Stream synthesis failed", status=response.status_code)

    async def input_streaming(
        self,
        text_iterator: AsyncGenerator[str, None],
        voice_id: str | None = None,
    ) -> AsyncGenerator[bytes, None]:
        """Stream text input and get audio output - ideal for LLM streaming.
        
        This allows feeding streaming LLM output directly to ElevenLabs
        for minimal end-to-end latency.
        """
        voice = voice_id or self.default_voice_id
        uri = f"{self.ws_url}/text-to-speech/{voice}/stream-input?model_id=eleven_turbo_v2_5"

        async with websockets.connect(uri, extra_headers={"xi-api-key": self.api_key}) as ws:
            # Send BOS (Beginning of Stream)
            await ws.send(json.dumps({
                "text": " ",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                },
                "generation_config": {
                    "chunk_length_schedule": [120, 160, 250, 290],
                },
                "xi_api_key": self.api_key,
            }))

            # Stream text chunks
            async def send_text():
                async for text_chunk in text_iterator:
                    await ws.send(json.dumps({"text": text_chunk}))
                # Send EOS (End of Stream)
                await ws.send(json.dumps({"text": ""}))

            # Start sending text in background
            send_task = asyncio.create_task(send_text())

            # Receive audio chunks
            try:
                while True:
                    response = await ws.recv()
                    data = json.loads(response)
                    
                    if data.get("audio"):
                        yield base64.b64decode(data["audio"])
                    
                    if data.get("isFinal"):
                        break
            except ConnectionClosed:
                pass
            finally:
                send_task.cancel()


class ElevenLabsConversationalAI:
    """ElevenLabs Conversational AI for real-time voice interactions.
    
    Uses the Conversational AI WebSocket API for:
    - Real-time speech-to-speech conversations
    - Low latency voice interactions
    - Custom agent responses
    """

    def __init__(
        self,
        api_key: str | None = None,
        agent_id: str | None = None,
    ):
        self.api_key = api_key or settings.elevenlabs_api_key.get_secret_value()
        self.agent_id = agent_id
        self.ws_url = "wss://api.elevenlabs.io/v1/convai/conversation"
        self.connection = None
        self.session_id = None

    async def start_conversation(
        self,
        on_transcript: Callable[[str, str], None] | None = None,
        on_audio: Callable[[bytes], None] | None = None,
        on_agent_response: Callable[[str], None] | None = None,
        custom_llm_callback: Callable[[str], str] | None = None,
    ) -> str:
        """Start a conversational AI session.
        
        Args:
            on_transcript: Callback for transcriptions (role, text)
            on_audio: Callback for audio chunks
            on_agent_response: Callback for agent text responses
            custom_llm_callback: Custom LLM handler for responses
            
        Returns:
            Session ID
        """
        self.session_id = str(uuid4())
        
        # Build WebSocket URL
        url = f"{self.ws_url}?agent_id={self.agent_id}" if self.agent_id else self.ws_url
        
        headers = {"xi-api-key": self.api_key}
        
        self.connection = await websockets.connect(url, extra_headers=headers)
        
        # Send initialization
        await self.connection.send(json.dumps({
            "type": "conversation_initiation_client_data",
            "conversation_config_override": {
                "agent": {
                    "prompt": {
                        "prompt": "You are a helpful onboarding assistant that helps new employees learn about the company.",
                    },
                },
            },
        }))

        logger.info("Conversational AI session started", session_id=self.session_id)
        return self.session_id

    async def send_audio(self, audio_data: bytes):
        """Send audio data to the conversation."""
        if self.connection:
            await self.connection.send(json.dumps({
                "type": "audio",
                "data": base64.b64encode(audio_data).decode(),
            }))

    async def receive_responses(self) -> AsyncGenerator[dict[str, Any], None]:
        """Receive responses from the conversation."""
        if not self.connection:
            return

        try:
            async for message in self.connection:
                data = json.loads(message)
                yield data
        except ConnectionClosed:
            logger.info("Conversation ended", session_id=self.session_id)

    async def end_conversation(self):
        """End the conversation session."""
        if self.connection:
            await self.connection.close()
            self.connection = None
            logger.info("Conversation ended", session_id=self.session_id)


# Singleton instance
elevenlabs_client = ElevenLabsClient()
