# Sample Data Seeding Guide

This guide explains how to populate the AI Internal Manager database with realistic sample data for testing and development.

## What Gets Seeded

The seed script populates four data stores with sample data:

### 1. PostgreSQL (Relational Database)
- **5 sample users** with different roles (Engineer, PM, DevOps, Data Scientist, Manager)
- **3 conversations** with realistic chat exchanges about technical topics
- **8 messages** with assistant responses, including sources and agent metadata
- **Onboarding records** for new team members

Sample users:
```
alice.chen@company.com      - Senior Software Engineer, Platform Team
bob.smith@company.com       - Product Manager, Infrastructure
carol.williams@company.com  - DevOps Engineer, Infrastructure
david.lee@company.com       - Data Scientist, ML Platform
emma.wilson@company.com     - Engineering Manager, Platform
```

### 2. Neo4j (Knowledge Graph)
- **3 departments** (Engineering, Product, Analytics)
- **3 subdepartments** (Platform, Infrastructure, ML Platform)
- **5 topics** with hierarchical organization:
  - Authentication & Authorization
  - API Design
  - Deployment & CI/CD
  - Monitoring & Observability
  - ML Pipelines

- **5 context nodes** (documentation pieces):
  - OAuth 2.0 Implementation Flow
  - JWT Token Management
  - API Versioning Strategy
  - Deployment Strategy & Rollout
  - Data Pipeline for ML Training

- **3 decision nodes** (organizational decisions):
  - Monorepo adoption
  - Next.js standardization
  - PostgreSQL as primary database

Graph structure:
```
Department (Engineering)
├── SubDepartment (Platform)
│   ├── Topic (Authentication)
│   │   └── Context (OAuth Flow)
│   └── Topic (API Design)
│       └── Context (API Versioning)
└── SubDepartment (Infrastructure)
    └── Topic (Deployment)
        └── Context (Deployment Strategy)
```

### 3. Qdrant (Vector Embeddings)
- **5 documentation embeddings** from context nodes
- **3 decision embeddings** stored as organizational memory
- **3 company policies** (Code Review, On-Call, Testing Requirements)
- **2 best practices** (Database Optimization, Error Handling)

Collections populated:
- `ai_manager_knowledge` - Documentation and context
- `ai_manager_org_memory` - Policies, best practices, decisions

### 4. Redis (Short-term Memory)
- **1 sample conversation session** with 4 messages
- **Conversation context metadata** with user and agent info
- **1-hour TTL** for automatic expiration

## Prerequisites

Before running the seed script, ensure:

1. **Docker services are running**:
   ```bash
   cd docker
   docker-compose up -d
   ```

   This starts:
   - PostgreSQL on localhost:5432
   - Redis on localhost:6379
   - Neo4j on localhost:7687 (browser: 7474)
   - Qdrant on localhost:6333

2. **Environment variables configured** (.env file):
   ```bash
   # Core databases
   DATABASE_URL=postgresql+asyncpg://ai_manager:password@localhost:5432/ai_manager
   REDIS_URL=redis://localhost:6379/0
   NEO4J_URI=bolt://localhost:7687
   QDRANT_HOST=localhost
   QDRANT_PORT=6333

   # LLM provider (at least one required)
   ANTHROPIC_API_KEY=your_key_here
   # OR
   VOYAGE_API_KEY=your_key_here
   ```

3. **Python dependencies installed**:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Backend running** (optional but recommended for monitoring):
   ```bash
   uvicorn src.main:app --reload
   ```

## Running the Seed Script

### Option 1: Direct Execution
```bash
# Run from project root
python seed_sample_data.py
```

### Option 2: Using Python
```python
import asyncio
from seed_sample_data import main

asyncio.run(main())
```

### Option 3: With Poetry
```bash
poetry run python seed_sample_data.py
```

## Expected Output

Successful seeding produces output like:
```
2026-01-31T19:30:45.123Z INFO Starting sample data seeding...
2026-01-31T19:30:45.234Z INFO Database tables created
2026-01-31T19:30:46.345Z INFO Created 5 users
2026-01-31T19:30:46.456Z INFO Created sample conversations and messages
2026-01-31T19:30:47.567Z INFO Created 3 departments
2026-01-31T19:30:47.678Z INFO Created 3 subdepartments
2026-01-31T19:30:47.789Z INFO Created 5 topics
2026-01-31T19:30:47.890Z INFO Created 5 context nodes
2026-01-31T19:30:48.901Z INFO Created 3 decision nodes
2026-01-31T19:30:49.012Z INFO Embedded and stored 13 documents in Qdrant
2026-01-31T19:30:49.123Z INFO Seeded Redis with sample conversation context
2026-01-31T19:30:49.234Z INFO ✅ Sample data seeding complete!
```

## Querying Sample Data

### In PostgreSQL
```sql
-- View all users
SELECT * FROM users;

-- View conversations and messages
SELECT c.id, c.title, m.content, m.role, m.agent
FROM conversations c
LEFT JOIN messages m ON m.conversation_id = c.id
ORDER BY c.created_at DESC;

-- Count messages by agent
SELECT agent, COUNT(*) FROM messages WHERE agent IS NOT NULL GROUP BY agent;
```

### In Neo4j Browser (http://localhost:7474)
```cypher
-- View all knowledge hierarchy
MATCH (d:Department)-[:HAS_SUBDEPARTMENT]->(s:SubDepartment)-[:HAS_TOPIC]->(t:Topic)-[:HAS_CONTEXT]->(c:Context)
RETURN d, s, t, c

-- Find all authentication-related content
MATCH (t:Topic {title: "Authentication & Authorization"})-[:HAS_CONTEXT]->(c:Context)
RETURN t, c

-- View decision history
MATCH (d:Decision)
RETURN d.title, d.status, d.decision_type
ORDER BY d.created_at DESC;
```

### In Qdrant (Dashboard: http://localhost:6333/dashboard)
- View collections: `ai_manager_knowledge`, `ai_manager_org_memory`
- Search vectors by collection
- View document metadata and embeddings

### Via API
```bash
# Search knowledge base
curl -X POST http://localhost:8000/api/v1/knowledge/search \
  -H "Content-Type: application/json" \
  -d '{"query": "OAuth implementation"}'

# List conversations
curl http://localhost:8000/api/v1/chat/conversations

# Test chat
curl -X POST http://localhost:8000/api/v1/chat/conversations/{conversation_id}/messages \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain OAuth", "stream": false}'
```

## Testing Chat with Sample Data

Once seeded, test the chat interface:

1. **Start the frontend** (if not running):
   ```bash
   cd frontend
   npm run dev
   ```

2. **Open browser**: http://localhost:3000

3. **Navigate to Chat** and try these queries:
   - "What is OAuth?"
   - "How do we handle token expiration?"
   - "Tell me about our deployment strategy"
   - "What are our authentication best practices?"
   - "Explain JWT tokens"

Expected behavior:
- Chat creates a new conversation
- Messages are stored in PostgreSQL
- Knowledge agent retrieves from Neo4j/Qdrant
- Sources are displayed showing which documents were referenced

## Customizing Sample Data

To add more sample data:

1. **Edit `seed_sample_data.py`**
2. **Add to corresponding section**:
   - Users → `SAMPLE_USERS` list
   - Topics → `SAMPLE_TOPICS` list
   - Contexts → `SAMPLE_CONTEXTS` list
   - etc.

3. **Rerun seed script**:
   ```bash
   python seed_sample_data.py
   ```

Example: Adding a new topic
```python
SAMPLE_TOPICS.append({
    "id": "topic-security",
    "title": "Security & Compliance",
    "sub_department_id": "sub-platform",
    "description": "Security best practices and compliance requirements",
    "importance": 0.95,
})

SAMPLE_CONTEXTS.append({
    "id": "ctx-security-audit",
    "title": "Security Audit Process",
    "topic_id": "topic-security",
    "content": "Our security audit process...",
    "source_type": "document",
    "source_id": "doc-security-001",
    "importance": 0.9,
})
```

## Resetting Data

To clear all sample data and start fresh:

### PostgreSQL
```sql
-- Drop all tables (careful!)
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS onboarding_tasks CASCADE;
DROP TABLE IF EXISTS onboarding_progress CASCADE;
DROP TABLE IF EXISTS users CASCADE;
```

### Neo4j
```cypher
-- Delete all nodes and relationships
MATCH (n) DETACH DELETE n;
```

### Qdrant
```bash
# Delete collections via API
curl -X DELETE http://localhost:6333/collections/ai_manager_knowledge
curl -X DELETE http://localhost:6333/collections/ai_manager_org_memory
curl -X DELETE http://localhost:6333/collections/ai_manager_user_memory
curl -X DELETE http://localhost:6333/collections/ai_manager_team_memory
```

### Redis
```bash
redis-cli FLUSHALL
```

Then rerun the seed script:
```bash
python seed_sample_data.py
```

## Troubleshooting

### Error: "Could not connect to PostgreSQL"
- Verify Docker is running: `docker ps`
- Check PostgreSQL container: `docker logs postgres_container_name`
- Verify DATABASE_URL in .env matches docker-compose config

### Error: "Neo4j connection failed"
- Check Neo4j is running: `docker ps | grep neo4j`
- Verify credentials in .env
- Access browser: http://localhost:7474

### Error: "Qdrant collection creation failed"
- Check Qdrant is running: `docker ps | grep qdrant`
- Verify QDRANT_HOST and QDRANT_PORT in .env
- Check Qdrant dashboard: http://localhost:6333/dashboard

### Error: "Embedding failed"
- Verify embeddings provider (ANTHROPIC_API_KEY or VOYAGE_API_KEY)
- Check API key is valid
- This is non-critical - basic chat still works without embeddings

## Sample Data Characteristics

The seeded data represents:

- **Realistic org structure**: Engineering (Platform, Infrastructure), Product, Analytics
- **Diverse team members**: Engineers, PMs, DevOps, Data Scientists, Managers
- **Authentic documentation**: Based on real practices from modern tech companies
- **Natural conversation patterns**: Q&A format resembling actual team interactions
- **Multiple knowledge domains**: Auth, APIs, deployment, ML, operations
- **Decision history**: Technical and organizational decisions with rationales

This allows you to:
- Test multi-agent routing
- Verify semantic search functionality
- Validate conversation storage
- Demonstrate knowledge retrieval capabilities
- Prototype reporting features

## Next Steps

After seeding, you can:

1. **Test chat interactions**: Try various queries to see knowledge retrieval
2. **Verify agent routing**: Check which agent handles different query types
3. **Inspect stored data**: Query databases directly to understand data flow
4. **Add more documents**: Extend sample data for your use case
5. **Develop features**: Build analytics, reporting, or new agents
6. **Performance test**: Load test with larger datasets
