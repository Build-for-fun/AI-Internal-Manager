"""Pydantic schemas for request/response validation."""

from src.schemas.auth import Token, TokenData, UserCreate, UserLogin, UserResponse
from src.schemas.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ConversationCreate,
    ConversationResponse,
    MessageResponse,
    StreamChunk,
)
from src.schemas.knowledge import (
    GraphNode,
    GraphRelationship,
    HierarchyResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from src.schemas.onboarding import (
    OnboardingProgressResponse,
    OnboardingStartRequest,
    OnboardingTaskResponse,
    OnboardingTaskUpdate,
)

__all__ = [
    # Auth
    "Token",
    "TokenData",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    # Chat
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "ConversationCreate",
    "ConversationResponse",
    "MessageResponse",
    "StreamChunk",
    # Knowledge
    "SearchRequest",
    "SearchResponse",
    "SearchResult",
    "GraphNode",
    "GraphRelationship",
    "HierarchyResponse",
    # Onboarding
    "OnboardingStartRequest",
    "OnboardingProgressResponse",
    "OnboardingTaskResponse",
    "OnboardingTaskUpdate",
]
