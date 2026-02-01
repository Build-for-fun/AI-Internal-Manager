# AI Internal Manager

A multi-agent AI system for internal company knowledge management, team analytics, and employee onboarding.

## Features

- **Knowledge Management**: Hierarchical "textbook-style" knowledge graph with semantic search
- **Multi-Agent System**: Specialized agents for knowledge retrieval, onboarding, and team analysis
- **MCP Connectors**: Integration with Jira, GitHub, and Slack
- **Voice Onboarding**: Voice-enabled onboarding using Deepgram STT and ElevenLabs TTS
- **Team Analytics**: Health metrics, velocity tracking, and bottleneck detection

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR AGENT                          │
│  [Intent Classifier] → [Router] → [State Manager (LangGraph)]   │
└───────────────────────────┬─────────────────────────────────────┘
            ┌───────────────┼───────────────┬───────────────┐
            ▼               ▼               ▼               ▼
   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
   │  Knowledge  │  │  Onboarding │  │    Team     │  │   Direct    │
   │    Agent    │  │    Agent    │  │  Analysis   │  │  Response   │
   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────────────┘
          └─────────────────┼─────────────────┘
                            ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │                     SHARED SERVICES LAYER                       │
   │  [Memory Manager]  [MCP Registry]  [Knowledge Graph]  [Tools]   │
   └─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| API Framework | FastAPI |
| Agent Framework | LangGraph |
| LLM | Anthropic Claude |
| Embeddings | Voyage AI / OpenAI |
| Knowledge Graph | Neo4j |
| Vector Database | Qdrant |
| Primary Database | PostgreSQL |
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
