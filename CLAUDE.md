# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

```bash
# Start all Docker services (PostgreSQL, Redis, Neo4j, Qdrant)
cd docker && docker-compose up -d

# Install Python dependencies
pip install -e ".[dev]"

# Run the API server
uvicorn src.main:app --reload

# Frontend (separate terminal)
cd frontend && npm install && npm run dev

# Run tests
pytest                              # All tests with coverage
pytest tests/unit                   # Unit tests only
pytest tests/integration            # Integration tests only
pytest -k "test_name"               # Run specific test
pytest --cov-report=html            # HTML coverage report

# Database migrations
alembic upgrade head                # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration

# Code quality
ruff check src tests                # Linting
ruff format src tests               # Formatting
mypy src                            # Type checking

# Celery (background tasks)
celery -A workers.celery_app worker --loglevel=info
celery -A workers.celery_app beat --loglevel=info

# Seed sample data (for development)
python seed_sample_data.py
```

### Docker Services

| Service | Port | Dashboard/Browser |
|---------|------|-------------------|
| PostgreSQL | 5432 | user: ai_manager |
| Redis | 6379 | - |
| Neo4j | 7687 | http://localhost:7474 |
| Qdrant | 6333 | http://localhost:6333/dashboard |

## Architecture Overview

### Multi-Agent Orchestration (LangGraph)

```
User Query → Intent Classification → Router → Specialized Agent → Response
```

The orchestrator (`src/agents/orchestrator/`) uses a LangGraph state machine with `ConversationState` (TypedDict). Key files:
- `graph.py` - State machine definition and transitions
- `intents.py` - Intent patterns for routing
- `agent.py` - Main orchestrator logic

**Specialized Agents** (all extend `BaseAgent` in `src/agents/base.py`):
- `knowledge/` - Hybrid search across Neo4j graph + Qdrant vectors
- `onboarding/` - Role-specific flows with voice support
- `team_analysis/` - Metrics from Jira/GitHub/Slack via MCP connectors

### Memory Hierarchy (src/memory/)

| Tier | Backend | TTL | Purpose |
|------|---------|-----|---------|
| Short-term | Redis | 1 hour | Active conversation context |
| User | Qdrant | Persistent | Individual preferences/history |
| Team | Qdrant | Persistent | Team decisions and norms |
| Org | Qdrant | Persistent | Company policies/best practices |

`MemoryManager` (`manager.py`) orchestrates retrieval across all tiers with re-ranking.

### Knowledge Graph (Neo4j)

Hierarchical structure: `Organization → Department → SubDepartment → Topic → Context`

Node types defined in `src/knowledge/graph/schema.py`: Department, SubDepartment, Topic, Context, Summary, Entity, Person, Project, Decision

### MCP Connectors (src/mcp/)

External integrations following `BaseMCPConnector` pattern:
- `jira/` - Issues, sprints, velocity
- `github/` - PRs, commits, code ownership
- `slack/` - Messages, decisions

### LLM Configuration

The system supports two LLM providers (configured via `LLM_PROVIDER` env var):
- `anthropic` - Uses Claude models directly
- `keywords_ai` - Routes through Keywords AI gateway

Embeddings: Voyage AI (default) or OpenAI (`EMBEDDING_PROVIDER` env var)

## Key Patterns

**Async-First**: All database ops, API calls, and agent logic use async/await.

**Singleton Services**: Connection-pooled clients imported directly:
- `from src.knowledge.graph.client import neo4j_client`
- `from src.memory.short_term import redis_client`
- `from src.knowledge.indexing.embedder import embedder`

**Agent Tool Loop**: Agents use `_run_with_tools()` for iterative Claude tool calling until completion.

**Pydantic Everywhere**:
- API schemas: `src/schemas/`
- DB models: `src/models/` (SQLAlchemy with async session)
- Config: `src/config.py` (Pydantic Settings)

## Adding New Components

### New Agent
1. Create directory under `src/agents/`
2. Extend `BaseAgent` in `agent.py`
3. Add intent pattern in `src/agents/orchestrator/intents.py`
4. Register node in `src/agents/orchestrator/graph.py`

### New MCP Connector
1. Create directory under `src/mcp/`
2. Extend `BaseMCPConnector` with typed tools
3. Register in `src/mcp/registry.py`

### New Neo4j Node Type
1. Add label to `src/knowledge/graph/schema.py`
2. Add Cypher templates in `queries.py`
3. Add client methods in `client.py`

## API Endpoints

Main entry points:
- `POST /api/v1/chat/conversations/{id}/messages` - Chat (streaming supported)
- `WebSocket /api/v1/chat/ws/{id}` - Real-time chat
- `WebSocket /api/v1/voice/ws/{id}` - Voice streaming
- `POST /api/v1/knowledge/search` - Semantic search
- `GET /api/v1/analytics/team/{id}/health` - Team metrics
- `GET /health` - Health check

## Environment Variables

Required:
```bash
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://localhost:6379/0
NEO4J_URI=bolt://localhost:7687
QDRANT_HOST=localhost

# LLM (one required)
ANTHROPIC_API_KEY=...
# OR
KEYWORDS_AI_API_KEY=...

# Embeddings (one required)
VOYAGE_API_KEY=...
# OR
OPENAI_API_KEY=...
```

Optional:
- `DEEPGRAM_API_KEY`, `ELEVENLABS_API_KEY` - Voice features
- `JIRA_BASE_URL`, `JIRA_API_TOKEN` - Jira integration
- `GITHUB_TOKEN` - GitHub integration
- `SLACK_BOT_TOKEN` - Slack integration

## Test Fixtures

`tests/conftest.py` provides mocks: `mock_llm`, `mock_neo4j`, `mock_redis`, `mock_qdrant`
