# Sample Data Creation Guide

I've created comprehensive sample data for the AI Internal Manager system. Here's what was generated and how to use it.

## 📁 Files Created

### 1. **seed_sample_data.py** (24 KB)
The main Python script that populates all databases with realistic sample data.

**What it does:**
- Creates 5 sample users with different roles and departments
- Generates 3 conversations with 8 realistic chat messages
- Builds a Neo4j knowledge graph with 3 departments → 3 subdepartments → 5 topics → 5 contexts
- Creates 3 organizational decisions (monorepo, Next.js, PostgreSQL)
- Embeds and stores documents in Qdrant vector database
- Seeds Redis with sample conversation context
- Implements proper error handling and logging

**Key Features:**
- Async-first implementation using SQLAlchemy async
- Realistic content based on actual tech company practices
- Comprehensive document embeddings for semantic search
- Proper relationship setup in Neo4j graph
- Structured metadata for all entities

### 2. **seed_data.sh** (3.1 KB)
Bash script that orchestrates the seeding process with pre-flight checks.

**What it does:**
- Checks if Docker is running
- Verifies all services are available (PostgreSQL, Redis, Neo4j, Qdrant)
- Confirms .env file exists
- Installs Python dependencies if needed
- Runs the Python seed script
- Provides helpful next steps

**Usage:**
```bash
chmod +x seed_data.sh
./seed_data.sh
```

### 3. **sample_data_overview.json** (12 KB)
JSON reference showing the complete structure of all seeded data.

**Contents:**
- User profiles and team structure
- Organization hierarchy (departments → subdepartments)
- Knowledge topics and documentation
- Organizational decisions with rationale
- Sample conversation transcript
- Company policies and best practices
- FAQs and statistics

**Use for:**
- Understanding data relationships
- Reference documentation
- Sharing with team members
- Planning additional data

### 4. **SEED_DATA_README.md** (8 KB)
Comprehensive documentation explaining all aspects of sample data.

**Includes:**
- What data gets seeded and why
- Prerequisites and setup instructions
- Step-by-step running instructions
- Expected output examples
- How to query the data
- Troubleshooting guide
- How to customize and reset data

## 🚀 Quick Start

### Prerequisites
```bash
# 1. Start Docker services
cd docker
docker-compose up -d
cd ..

# 2. Ensure .env file exists with proper credentials
cat .env

# 3. Install Python dependencies
pip install -e ".[dev]"
```

### Run Seeding

**Option 1: Using the shell script (Recommended)**
```bash
./seed_data.sh
```

**Option 2: Direct Python execution**
```bash
python seed_sample_data.py
```

**Option 3: Using Poetry**
```bash
poetry run python seed_sample_data.py
```

### Verify Success
```bash
# Check PostgreSQL
psql -h localhost -U ai_manager -d ai_manager -c "SELECT COUNT(*) FROM users;"

# Check Neo4j (via browser)
# http://localhost:7474
# MATCH (n) RETURN COUNT(n) as total_nodes;

# Check Redis
redis-cli -h localhost KEYS "conv:*"

# Check Qdrant (via dashboard)
# http://localhost:6333/dashboard
```

## 📊 Sample Data Summary

### Users (5 total)
```
👤 Alice Chen               - Senior Software Engineer, Platform
👤 Bob Smith                - Product Manager, Infrastructure
👤 Carol Williams           - DevOps Engineer, Infrastructure
👤 David Lee                - Data Scientist, ML Platform
👤 Emma Wilson              - Engineering Manager, Platform
```

### Organization Structure
```
Engineering Department
├── Platform Team
│   ├── Topic: Authentication & Authorization
│   │   └── Context: OAuth 2.0 Implementation
│   │   └── Context: JWT Token Management
│   └── Topic: API Design
│       └── Context: API Versioning Strategy
└── Infrastructure Team
    ├── Topic: Deployment & CI/CD
    │   └── Context: Deployment Strategy & Rollout
    └── Topic: Monitoring & Observability

Product Department
Analytics Department
└── ML Platform Team
    └── Topic: ML Pipelines
        └── Context: Data Pipeline for ML Training
```

### Knowledge Documents (5 total)
1. **OAuth 2.0 Implementation Flow** - Authorization code flow, token management
2. **JWT Token Management** - Token structure, rotation strategy, security
3. **API Versioning Strategy** - URL-based versioning, deprecation policy
4. **Deployment Strategy & Rollout** - Canary deployments, rollback, monitoring
5. **Data Pipeline for ML Training** - Airflow, data validation, model training

### Organizational Decisions (3 total)
1. **Monorepo adoption** - Turborepo for unified codebase
2. **Next.js standardization** - Frontend framework choice
3. **PostgreSQL as primary DB** - OLTP database selection

### Policies (3 total)
- Code Review Standards
- On-Call Rotation Policy
- Testing Requirements

### Best Practices (2 total)
- Database Query Optimization
- Error Handling Best Practices

### Sample Conversation (8 messages)
A realistic OAuth discussion between Alice and the system:
- User asks about OAuth flow
- Assistant provides comprehensive explanation
- User asks follow-up about token expiration
- Assistant gives implementation details

## 💾 Database Coverage

### PostgreSQL (Relational)
- **users**: 5 users with roles and departments
- **conversations**: 3 conversations per user
- **messages**: 8+ messages with agent metadata
- **onboarding_progress**: Sample onboarding records
- **onboarding_tasks**: Onboarding checklist items

### Neo4j (Knowledge Graph)
- **Departments**: 3 total
- **SubDepartments**: 3 total
- **Topics**: 5 total
- **Contexts**: 5 total
- **Decisions**: 3 total
- **Relationships**: HAS_SUBDEPARTMENT, HAS_TOPIC, HAS_CONTEXT, etc.

### Qdrant (Vector Store)
- **ai_manager_knowledge**: 5 documentation embeddings
- **ai_manager_org_memory**: 3 decision + 3 policy + 2 best practice embeddings
- **Embeddings**: 1024-dimensional vectors for semantic search

### Redis (Short-term Memory)
- **Conversation sessions**: Sample conversation with 4 messages
- **Context metadata**: User and agent information
- **TTL**: 1 hour automatic expiration

## 🔍 Testing with Sample Data

### Chat Interface Testing
1. Start the system:
   ```bash
   # Terminal 1: Backend
   uvicorn src.main:app --reload

   # Terminal 2: Frontend
   cd frontend && npm run dev
   ```

2. Open http://localhost:3000 and navigate to Chat

3. Try these sample queries:
   - "What is OAuth?" → Retrieves OAuth documentation
   - "How do we deploy?" → Gets deployment strategy
   - "Explain JWT tokens" → Shows JWT best practices
   - "Tell me about API versioning" → API design docs
   - "What are our team policies?" → Company policies

### Expected Behavior
- Messages are stored in PostgreSQL
- Knowledge agent retrieves from Neo4j/Qdrant
- Sources are displayed showing referenced documents
- Conversation context is maintained in Redis

### API Testing
```bash
# Create a conversation
curl -X POST http://localhost:8000/api/v1/chat/conversations \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "conversation_type": "chat"}'

# Send a message
curl -X POST http://localhost:8000/api/v1/chat/conversations/{conversation_id}/messages \
  -H "Content-Type: application/json" \
  -d '{"message": "What is OAuth?", "stream": false}'

# List conversations
curl http://localhost:8000/api/v1/chat/conversations

# Search knowledge
curl -X POST http://localhost:8000/api/v1/knowledge/search \
  -H "Content-Type: application/json" \
  -d '{"query": "deployment strategy"}'
```

## 🔧 Customization

### Adding More Users
Edit `seed_sample_data.py` and add to `SAMPLE_USERS`:
```python
SAMPLE_USERS.append({
    "email": "frank.johnson@company.com",
    "full_name": "Frank Johnson",
    "role": "Security Engineer",
    "department": "Engineering",
    "team": "Security",
})
```

### Adding More Topics
Add to `SAMPLE_TOPICS`:
```python
SAMPLE_TOPICS.append({
    "id": "topic-security",
    "title": "Security & Compliance",
    "sub_department_id": "sub-platform",
    "description": "Security best practices...",
    "importance": 0.95,
})
```

### Adding More Documentation
Add to `SAMPLE_CONTEXTS`:
```python
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

After modifications, re-run:
```bash
python seed_sample_data.py
```

## 🔄 Resetting Data

To clear all sample data and start fresh:

**PostgreSQL:**
```sql
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS onboarding_tasks CASCADE;
DROP TABLE IF EXISTS onboarding_progress CASCADE;
DROP TABLE IF EXISTS users CASCADE;
```

**Neo4j:**
```cypher
MATCH (n) DETACH DELETE n;
```

**Qdrant:**
```bash
curl -X DELETE http://localhost:6333/collections/ai_manager_knowledge
curl -X DELETE http://localhost:6333/collections/ai_manager_org_memory
curl -X DELETE http://localhost:6333/collections/ai_manager_user_memory
curl -X DELETE http://localhost:6333/collections/ai_manager_team_memory
```

**Redis:**
```bash
redis-cli FLUSHALL
```

Then re-seed:
```bash
./seed_data.sh
```

## 📈 Data Statistics

| Item | Count |
|------|-------|
| Users | 5 |
| Departments | 3 |
| Sub-departments | 3 |
| Topics | 5 |
| Contexts (Docs) | 5 |
| Decisions | 3 |
| Policies | 3 |
| Best Practices | 2 |
| Vector Embeddings | 13 |
| Sample Messages | 8 |
| Conversations | 3 |

## ⚙️ Technical Details

### Async Architecture
- Uses Python `asyncio` for concurrent operations
- SQLAlchemy async session management
- Proper error handling and logging with structlog

### Vector Embeddings
- Default: Voyage AI embeddings (1024 dimensions)
- Fallback: OpenAI embeddings
- Distance metric: COSINE similarity

### Data Integrity
- All IDs are UUIDs for global uniqueness
- Proper timestamps (UTC) for all records
- Soft deletes in PostgreSQL (deleted_at field)
- Relationships enforced in Neo4j

### Performance
- Batch operations where possible
- Proper indexing on frequently queried fields
- Connection pooling for database access
- Caching in Redis for hot data

## 🆘 Troubleshooting

### "Could not connect to PostgreSQL"
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check logs
docker logs postgres_container_name

# Verify DATABASE_URL in .env
echo $DATABASE_URL
```

### "Neo4j authentication failed"
```bash
# Access Neo4j browser
open http://localhost:7474

# Default credentials: neo4j / password
# Change password in docker-compose.yml if needed
```

### "Qdrant embeddings failed"
```bash
# Check if API key is set
echo $VOYAGE_API_KEY

# Check Qdrant is running
curl http://localhost:6333/health
```

### "ImportError: No module named 'src'"
```bash
# Install package in development mode
pip install -e ".[dev]"
```

## 📚 Next Steps

After seeding sample data:

1. **Test Chat Interface**: Try various queries to verify knowledge retrieval
2. **Explore Dashboards**: Check Neo4j browser and Qdrant dashboard
3. **Query Directly**: Use SQL, Cypher, and API endpoints to understand data flow
4. **Add Custom Data**: Extend with your own documents and conversations
5. **Performance Testing**: Load test with larger datasets
6. **Feature Development**: Build new agents or analytics on top of data

## 📝 Notes

- Sample data is realistic and based on actual tech company practices
- All content is educational and for development/testing only
- Embeddings are computed in real-time (may take a few seconds)
- Data is persistent across restarts (stored in Docker volumes)
- To completely clean slate: remove Docker volumes and re-run seeding

---

For detailed information, see:
- **SEED_DATA_README.md** - Complete seeding documentation
- **sample_data_overview.json** - JSON reference of all data
- **seed_sample_data.py** - Python implementation details
