"""FastAPI application entry point."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1 import analytics, chat, knowledge, onboarding, voice, voice_agent, rbac
from src.config import settings

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting AI Internal Manager", version=settings.app_version)

    # Initialize database connections
    from src.models.database import init_db
    await init_db()
    logger.info("Database initialized")

    # Initialize Neo4j connection
    try:
        from src.knowledge.graph.client import neo4j_client
        await neo4j_client.connect()
        logger.info("Neo4j connected")
    except Exception as e:
        logger.warning("Failed to connect to Neo4j", error=str(e))

    # Initialize Qdrant collections
    try:
        from src.knowledge.indexing.embedder import embedder
        await embedder.init_collections()
        logger.info("Qdrant collections initialized")
    except Exception as e:
        logger.warning("Failed to initialize Qdrant collections", error=str(e))

    # Initialize Redis
    try:
        from src.memory.short_term import redis_client
        await redis_client.connect()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning("Failed to connect to Redis", error=str(e))

    yield

    # Shutdown
    logger.info("Shutting down AI Internal Manager")
    try:
        await neo4j_client.close()
    except Exception:
        pass
    try:
        await redis_client.close()
    except Exception:
        pass


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-agent AI system for internal company knowledge management, team analytics, and employee onboarding",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix=f"{settings.api_prefix}/chat", tags=["Chat"])
app.include_router(voice.router, prefix=f"{settings.api_prefix}/voice", tags=["Voice"])
app.include_router(voice_agent.router, prefix=f"{settings.api_prefix}/voice", tags=["Voice Agent"])
app.include_router(knowledge.router, prefix=f"{settings.api_prefix}/knowledge", tags=["Knowledge"])
app.include_router(onboarding.router, prefix=f"{settings.api_prefix}/onboarding", tags=["Onboarding"])
app.include_router(analytics.router, prefix=f"{settings.api_prefix}/analytics", tags=["Analytics"])
app.include_router(rbac.router, prefix=f"{settings.api_prefix}/rbac", tags=["RBAC"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint for Kubernetes."""
    # Check all dependencies
    checks = {}

    # Check PostgreSQL
    try:
        from src.models.database import get_session
        async with get_session() as session:
            await session.execute("SELECT 1")
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {str(e)}"

    # Check Redis
    try:
        from src.memory.short_term import redis_client
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"

    # Check Neo4j
    try:
        from src.knowledge.graph.client import neo4j_client
        await neo4j_client.verify_connectivity()
        checks["neo4j"] = "ok"
    except Exception as e:
        checks["neo4j"] = f"error: {str(e)}"

    all_ok = all(v == "ok" for v in checks.values())

    return {
        "status": "ready" if all_ok else "degraded",
        "checks": checks,
    }
