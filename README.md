# NexusAI: Internal Knowledge Manager

A multi-agent AI system for internal company knowledge management, team analytics, and employee onboarding.

## Features

- **Knowledge Management**: Hierarchical "textbook-style" knowledge graph with semantic search
- **Multi-Agent System**: Specialized agents for knowledge retrieval, onboarding, and team analysis
- **MCP Connectors**: Integration with Jira, GitHub, and Slack
- **Voice Onboarding**: Voice-enabled onboarding using Deepgram STT and ElevenLabs TTS
- **Team Analytics**: Health metrics, velocity tracking, and bottleneck detection

## Technical Design

### System Diagram

![System Diagram](images/arch.png)

### Design Overview

The system is a multi-agent, service-oriented architecture built around a LangGraph orchestrator. The FastAPI layer provides REST and WebSocket endpoints that handle user sessions, authentication, and request routing. Each request flows through an intent classifier and router to choose the right agent and tools, ensuring low-latency paths for direct responses and deeper pipelines for knowledge retrieval or analytics.

### Request Lifecycle

1. **Client request** hits the FastAPI gateway (REST or WebSocket).
2. **Orchestrator** classifies intent and routes to a specialized agent.
3. **Agent execution** uses tools and shared services (memory, knowledge, MCP connectors).
4. **LLM calls** are handled through Keywords AI (OpenAI-compatible proxy), with model selection controlled by configuration.
5. **Response streaming** returns partial tokens for chat and voice workflows.

### Data and Storage

- **Supabase Postgres** is the primary system of record for users, conversations, onboarding flows, and analytics.
- **Neo4j** stores hierarchical knowledge and relationships (textbook-style graph).
- **Qdrant** indexes embeddings for fast semantic retrieval.
- **Redis** provides low-latency caching and backs Celery queues.

This separation optimizes for query patterns: transactional records in Postgres, graph traversal in Neo4j, and vector similarity in Qdrant.

### Agent and Memory Model

- **Orchestrator** maintains session state and manages tool access using a shared memory interface.
- **Short-term memory** stores the immediate conversation context.
- **Org/team/user memory** enables durable personalization and cross-session continuity.
- **Knowledge agent** resolves facts by combining graph traversal and semantic retrieval.

### Ingestion and Knowledge Indexing

- **MCP connectors** pull data from GitHub/Jira/Slack on schedules or user demand.
- **Indexing pipeline** chunks and embeds documents, writes embeddings to Qdrant, and links canonical entities in Neo4j.
- **Consistency** is maintained with background Celery tasks to keep graph and vector indexes aligned.

### Voice Onboarding

- **Deepgram** handles speech-to-text.
- **ElevenLabs** handles text-to-speech.
- A dedicated WebSocket stream supports low-latency bidirectional audio.

### Deployment and Operations

- **Docker Compose** orchestrates local services (API, workers, Redis, Neo4j, Qdrant).
- **Observability** captures logs and optional traces to diagnose latency or LLM/tool errors.
- **Configuration** is centralized via environment variables for easy switching between providers.

### Service Screenshots

**Keywords AI**

![Keywords AI](images/Screenshot%202026-02-01%20at%204.42.46%E2%80%AFAM.png)



![Supabase](images/Screenshot%202026-02-01%20at%204.42.56%E2%80%AFAM.png)



![Docker](images/Screenshot%202026-02-01%20at%204.43.05%E2%80%AFAM.png)


![Screenshot 4.43.23](images/Screenshot%202026-02-01%20at%204.43.23%E2%80%AFAM.png)

![Screenshot 4.43.32](images/Screenshot%202026-02-01%20at%204.43.32%E2%80%AFAM.png)

![Screenshot 4.43.39](images/Screenshot%202026-02-01%20at%204.43.39%E2%80%AFAM.png)

**Supabase**

![Screenshot 4.44.00](images/Screenshot%202026-02-01%20at%204.44.00%E2%80%AFAM.png)

**Docker**

![Screenshot 4.46.51](images/Screenshot%202026-02-01%20at%204.46.51%E2%80%AFAM.png)

![Screenshot 4.48.08](images/Screenshot%202026-02-01%20at%204.48.08%E2%80%AFAM.png)

## Tech Stack

| Component | Technology |
|-----------|------------|
| API Framework | FastAPI |
| Agent Framework | LangGraph |
| LLM | Keywords AI (OpenAI-compatible) / Anthropic (optional) |
| Embeddings | Voyage AI / OpenAI |
| Knowledge Graph | Neo4j |
| Vector Database | Qdrant |
| Primary Database | Supabase Postgres |
| Cache/Queue | Redis |
| Task Queue | Celery |
| Voice | Deepgram + ElevenLabs |

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- API keys for Anthropic, Voyage AI (or OpenAI for embeddings)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd ai-internal-manager
```

2. Copy environment file and configure:
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Start services with Docker Compose:
```bash
cd docker
docker-compose up -d
```

4. Run database migrations:
```bash
alembic upgrade head
```

5. Start the API server:
```bash
uvicorn src.main:app --reload
```

### Development Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
```

2. Install dependencies:
```bash
pip install -e ".[dev]"
```

3. Run tests:
```bash
pytest
```

## API Endpoints

### Chat
- `POST /api/v1/chat/conversations` - Create conversation
- `POST /api/v1/chat/conversations/{id}/messages` - Send message
- `WebSocket /api/v1/chat/ws/{id}` - Real-time chat

### Voice
- `POST /api/v1/voice/sessions` - Create voice session
- `WebSocket /api/v1/voice/ws/{id}` - Voice streaming

### Knowledge
- `POST /api/v1/knowledge/search` - Semantic search
- `GET /api/v1/knowledge/graph/hierarchy` - Get knowledge structure
- `GET /api/v1/knowledge/graph/node/{id}` - Get node details

### Onboarding
- `GET /api/v1/onboarding/flows` - List onboarding flows
- `POST /api/v1/onboarding/start` - Start onboarding
- `GET /api/v1/onboarding/progress` - Get progress

### Analytics
- `GET /api/v1/analytics/team/{id}/health` - Team health score
- `GET /api/v1/analytics/team/{id}/velocity` - Sprint velocity
- `GET /api/v1/analytics/team/{id}/bottlenecks` - Identified bottlenecks

## Configuration

Key environment variables:

```bash
# Core
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/ai_manager
REDIS_URL=redis://localhost:6379/0
NEO4J_URI=bolt://localhost:7687
QDRANT_HOST=localhost

# LLM
ANTHROPIC_API_KEY=your-key

# Embeddings
VOYAGE_API_KEY=your-key  # or use OPENAI_API_KEY

# Voice (optional)
DEEPGRAM_API_KEY=your-key
ELEVENLABS_API_KEY=your-key

# External Services (optional)
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_API_TOKEN=your-token
GITHUB_TOKEN=your-token
SLACK_BOT_TOKEN=your-token
```

## Project Structure

```
ai-internal-manager/
├── docker/                 # Docker configuration
├── src/
│   ├── api/v1/            # REST + WebSocket endpoints
│   ├── agents/            # Agent implementations
│   │   ├── orchestrator/  # Main orchestrator with LangGraph
│   │   ├── knowledge/     # Knowledge retrieval agent
│   │   ├── onboarding/    # Onboarding agent
│   │   └── team_analysis/ # Team analytics agent
│   ├── mcp/               # MCP connectors
│   │   ├── jira/
│   │   ├── github/
│   │   └── slack/
│   ├── knowledge/         # Knowledge graph management
│   │   ├── graph/         # Neo4j operations
│   │   ├── textbook/      # Hierarchy management
│   │   └── indexing/      # Embeddings and chunking
│   ├── memory/            # Memory system
│   ├── models/            # SQLAlchemy models
│   └── schemas/           # Pydantic schemas
├── workers/               # Celery workers
├── alembic/               # Database migrations
└── tests/                 # Test suite
```

## License

MIT
