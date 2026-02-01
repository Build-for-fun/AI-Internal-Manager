"""Voice agent system for onboarding.

Provides:
- ElevenLabs TTS integration with conversational AI
- Textbook knowledge retrieval for answering queries
- Zoom integration for meeting-based onboarding
"""

from src.voice.agent import VoiceOnboardingAgent
from src.voice.elevenlabs_client import ElevenLabsClient
from src.voice.zoom_integration import ZoomVoiceIntegration

__all__ = [
    "VoiceOnboardingAgent",
    "ElevenLabsClient",
    "ZoomVoiceIntegration",
]
