# AI Internal Manager - Claude Code Guide

## Quick Reference

### Common Commands

```bash
# Start development environment
cd docker && docker-compose up -d

# Install dependencies
pip install -e ".[dev]"

# Run the API server
uvicorn src.main:app --reload

# Run tests
pytest                          # All tests with coverage
pytest tests/unit              # Unit tests only
pytest tests/integration       # Integration tests only
pytest tests/e2e               # End-to-end tests only
pytest -k "test_name"          # Run specific test

# Database migrations
alembic upgrade head           # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration

# Code quality
ruff check src tests           # Linting
ruff format src tests          # Formatting
mypy src                       # Type checking

# Start Celery worker
celery -A workers.celery_app worker --loglevel=info

# Start Celery beat (scheduler)
celery -A workers.celery_app beat --loglevel=info
```

### Services (Docker Compose)

- **PostgreSQL**: localhost:5432 (user: ai_manager, db: ai_manager)
- **Redis**: localhost:6379
- **Neo4j**: localhost:7687 (browser: localhost:7474)
- **Qdrant**: localhost:6333 (dashboard: localhost:6333/dashboard)

## Architecture Overview

### Multi-Agent System with LangGraph

The system uses a **LangGraph state machine** for agent orchestration:

```
User Query → Intent Classification → Router → Specialized Agent → Response
```

**Key agents:**
- `src/agents/orchestrator/` - Main orchestrator with intent classification and routing
- `src/agents/knowledge/` - Knowledge retrieval using hybrid search
- `src/agents/onboarding/` - Role-specific onboarding with voice support
- `src/agents/team_analysis/` - Team metrics and bottleneck detection

The orchestrator uses `ConversationState` (TypedDict) to manage state across agent transitions. See `src/agents/orchestrator/graph.py` for the state machine definition.

### Memory Hierarchy

Four-tier memory system in `src/memory/`:

1. **Short-term** (Redis, 1hr TTL): Active conversation context
2. **User memory** (Qdrant): Individual preferences and history
3. **Team memory** (Qdrant): Team decisions and norms
4. **Org memory** (Qdrant): Company policies and best practices

`MemoryManager` (`src/memory/manager.py`) orchestrates retrieval across all tiers with re-ranking.

### Knowledge Graph (Neo4j)

Hierarchical "textbook" structure:

```
Organization → Department → SubDepartment → Topic → Context
```

**Node types**: `Department`, `SubDepartment`, `Topic`, `Context`, `Summary`, `Entity`, `Person`

Schema defined in `src/knowledge/graph/schema.py`. Use `src/knowledge/graph/client.py` for CRUD operations.

### MCP Connectors

External service integrations in `src/mcp/`:

- **Jira** (`src/mcp/jira/`): Issues, sprints, velocity, blockers
- **GitHub** (`src/mcp/github/`): PRs, commits, code ownership
- **Slack** (`src/mcp/slack/`): Messages, decisions, communication patterns

Each connector extends `BaseMCPConnector` and provides typed tools.

## Project Structure

```
src/
├── main.py                 # FastAPI entry point
├── config.py               # Pydantic Settings
├── api/v1/                 # REST + WebSocket endpoints
├── agents/                 # Agent implementations
│   ├── base.py             # BaseAgent ABC
│   └── orchestrator/       # LangGraph state machine
├── mcp/                    # External service connectors
├── knowledge/              # Knowledge graph + embeddings
│   ├── graph/              # Neo4j operations
│   └── indexing/           # Embedding generation
├── memory/                 # 4-tier memory system
├── models/                 # SQLAlchemy models
└── schemas/                # Pydantic request/response schemas

workers/
├── celery_app.py           # Celery + beat configuration
└── tasks/                  # Ingestion & consolidation tasks
```

## Key Patterns

### Async-First

All database operations, API calls, and agent logic are async. Use `async/await` throughout.

### Singleton Services

Service clients are singletons for connection pooling:
- `src/knowledge/graph/client.py` → `neo4j_client`
- `src/memory/short_term.py` → `redis_client`
- `src/knowledge/indexing/embedder.py` → `embedder`

### Agent Tool Use

Agents extend `BaseAgent` and use `_run_with_tools()` for iterative tool calling with Claude:

```python
async def _run_with_tools(self, messages, tools, max_iterations=10):
    # Loops until Claude returns without tool_use blocks
```

### Pydantic Models

- API schemas: `src/schemas/` (request/response validation)
- Database models: `src/models/` (SQLAlchemy with async session)
- Config: `src/config.py` (Pydantic Settings, env vars)

## Testing

```bash
pytest                                    # Full test suite
pytest --cov-report=html                  # HTML coverage report
pytest tests/unit/agents/                 # Test specific module
```

Test fixtures in `tests/conftest.py` provide mocks for:
- LLM client (`mock_llm`)
- Neo4j client (`mock_neo4j`)
- Redis client (`mock_redis`)
- Qdrant client (`mock_qdrant`)

## Environment Variables

Required in `.env`:

```bash
# Core databases
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://localhost:6379/0
NEO4J_URI=bolt://localhost:7687
QDRANT_HOST=localhost

# LLM (required)
ANTHROPIC_API_KEY=...

# Embeddings (one required)
VOYAGE_API_KEY=...
# or OPENAI_API_KEY=...
```

Optional for full functionality:
- `DEEPGRAM_API_KEY` / `ELEVENLABS_API_KEY` - Voice features
- `JIRA_BASE_URL` / `JIRA_API_TOKEN` - Jira integration
- `GITHUB_TOKEN` - GitHub integration
- `SLACK_BOT_TOKEN` - Slack integration

## Data Pipelines

Celery tasks in `workers/tasks/`:

- **Ingestion** (`ingestion.py`): Fetch from Jira/GitHub/Slack → normalize → embed → store
- **Consolidation** (`consolidation.py`): Generate weekly/monthly summaries

Schedules defined in `workers/celery_app.py` using Celery Beat.

## API Endpoints

Main entry points:
- `POST /api/v1/chat/conversations/{id}/messages` - Chat with streaming
- `WebSocket /api/v1/chat/ws/{id}` - Real-time chat
- `WebSocket /api/v1/voice/ws/{id}` - Voice streaming
- `POST /api/v1/knowledge/search` - Semantic search
- `GET /api/v1/analytics/team/{id}/health` - Team health metrics

Health check: `GET /health`

## Common Tasks

### Adding a New Agent

1. Create directory under `src/agents/`
2. Extend `BaseAgent` in `agent.py`
3. Define tools specific to the agent
4. Add intent pattern in `src/agents/orchestrator/intents.py`
5. Register in orchestrator graph (`src/agents/orchestrator/graph.py`)

### Adding a New MCP Connector

1. Create directory under `src/mcp/`
2. Extend `BaseMCPConnector` in `connector.py`
3. Define tool schemas in `tools.py`
4. Register in `src/mcp/registry.py`

### Adding New Neo4j Node Types

1. Add node label to `src/knowledge/graph/schema.py`
2. Create Cypher query templates in `src/knowledge/graph/queries.py`
3. Add client methods in `src/knowledge/graph/client.py`
