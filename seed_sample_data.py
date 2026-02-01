#!/usr/bin/env python3
"""
Sample data seeding script for AI Internal Manager.
Populates PostgreSQL, Neo4j, and Qdrant with realistic test data.

Usage:
    python seed_sample_data.py

Requirements:
    - Docker containers running (PostgreSQL, Neo4j, Qdrant, Redis)
    - Environment variables configured (.env file)
"""

import asyncio
import json
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.config import settings
from src.models.base import Base
from src.models.user import User
from src.models.conversation import Conversation, Message
from src.models.onboarding import OnboardingProgress, OnboardingTask
from src.knowledge.graph.client import neo4j_client
from src.knowledge.indexing.embedder import embedder
from src.memory.short_term import redis_client

logger = structlog.get_logger()

# Sample Data Definitions
SAMPLE_USERS = [
    {
        "email": "alice.chen@company.com",
        "full_name": "Alice Chen",
        "role": "Senior Software Engineer",
        "department": "Engineering",
        "team": "Platform",
    },
    {
        "email": "bob.smith@company.com",
        "full_name": "Bob Smith",
        "role": "Product Manager",
        "department": "Product",
        "team": "Infrastructure",
    },
    {
        "email": "carol.williams@company.com",
        "full_name": "Carol Williams",
        "role": "DevOps Engineer",
        "department": "Engineering",
        "team": "Infrastructure",
    },
    {
        "email": "david.lee@company.com",
        "full_name": "David Lee",
        "role": "Data Scientist",
        "department": "Analytics",
        "team": "ML Platform",
    },
    {
        "email": "emma.wilson@company.com",
        "full_name": "Emma Wilson",
        "role": "Engineering Manager",
        "department": "Engineering",
        "team": "Platform",
    },
]

SAMPLE_DEPARTMENTS = [
    {
        "id": "dept-engineering",
        "title": "Engineering",
        "description": "Core product engineering team",
        "budget": 500000,
        "headcount": 25,
    },
    {
        "id": "dept-product",
        "title": "Product",
        "description": "Product management and strategy",
        "budget": 200000,
        "headcount": 8,
    },
    {
        "id": "dept-analytics",
        "title": "Analytics",
        "description": "Data and analytics platform",
        "budget": 300000,
        "headcount": 10,
    },
]

SAMPLE_SUBDEPARTMENTS = [
    {
        "id": "sub-platform",
        "title": "Platform Team",
        "department_id": "dept-engineering",
        "description": "Core platform infrastructure",
    },
    {
        "id": "sub-infra",
        "title": "Infrastructure Team",
        "department_id": "dept-engineering",
        "description": "Cloud infrastructure and DevOps",
    },
    {
        "id": "sub-ml",
        "title": "ML Platform",
        "department_id": "dept-analytics",
        "description": "Machine learning platform and models",
    },
]

SAMPLE_TOPICS = [
    {
        "id": "topic-auth",
        "title": "Authentication & Authorization",
        "sub_department_id": "sub-platform",
        "description": "OAuth, JWT, RBAC implementation",
        "importance": 0.95,
    },
    {
        "id": "topic-api",
        "title": "API Design",
        "sub_department_id": "sub-platform",
        "description": "REST API best practices and patterns",
        "importance": 0.9,
    },
    {
        "id": "topic-deployment",
        "title": "Deployment & CI/CD",
        "sub_department_id": "sub-infra",
        "description": "GitHub Actions, Kubernetes, deployment strategies",
        "importance": 0.95,
    },
    {
        "id": "topic-monitoring",
        "title": "Monitoring & Observability",
        "sub_department_id": "sub-infra",
        "description": "Prometheus, Grafana, log aggregation",
        "importance": 0.85,
    },
    {
        "id": "topic-ml-pipelines",
        "title": "ML Pipelines",
        "sub_department_id": "sub-ml",
        "description": "Data engineering for ML training and inference",
        "importance": 0.9,
    },
]

SAMPLE_CONTEXTS = [
    {
        "id": "ctx-oauth-flow",
        "title": "OAuth 2.0 Implementation Flow",
        "topic_id": "topic-auth",
        "content": """
OAuth 2.0 is an authorization framework that enables applications to obtain limited access to user accounts
on an HTTP service. Our implementation uses the Authorization Code flow for web applications.

Key components:
1. Authorization Server - Manages user credentials and issues tokens
2. Resource Server - Hosts protected resources
3. Client Application - Application requesting access
4. User - Resource owner

Flow:
1. User clicks "Login with Company"
2. User is redirected to authorization server
3. User grants permission
4. Authorization code is returned to application
5. Application exchanges code for access token
6. Application uses access token to fetch user info

Best practices:
- Always use HTTPS
- Validate state parameter to prevent CSRF
- Use refresh tokens for long-lived sessions
- Implement token expiration (15-60 minutes)
- Store refresh tokens securely

References: RFC 6749, OAuth 2.0 Security Best Practices
        """,
        "source_type": "document",
        "source_id": "doc-oauth-001",
        "source_url": "https://internal.company.com/docs/auth/oauth",
        "importance": 0.95,
    },
    {
        "id": "ctx-jwt-guide",
        "title": "JWT Token Management",
        "topic_id": "topic-auth",
        "content": """
JSON Web Tokens (JWT) are a stateless way to represent claims between parties.

Token structure: header.payload.signature

Claims in our system:
- sub (subject): user ID
- iat (issued at): timestamp
- exp (expiration): timestamp (default: 1 hour)
- aud (audience): application identifier
- custom claims: user_role, team_id, permissions

Token rotation strategy:
- Access tokens: 1 hour expiration
- Refresh tokens: 30 days expiration
- Implement refresh token rotation (issue new refresh token with each use)

Security considerations:
- Never store JWTs in localStorage (use httpOnly cookies instead)
- Always validate signature using RS256 (asymmetric) in production
- Implement token blacklisting for logout
- Rotate signing keys quarterly

Common implementations:
- PyJWT library for Python
- jsonwebtoken library for Node.js
- Auth0 for managed JWT service
        """,
        "source_type": "document",
        "source_id": "doc-jwt-001",
        "importance": 0.9,
    },
    {
        "id": "ctx-api-versioning",
        "title": "API Versioning Strategy",
        "topic_id": "topic-api",
        "content": """
Our API uses URL-based versioning (v1, v2, etc.) for better backwards compatibility.

Current API versions:
- v1: Stable production API (2+ years old)
- v2: Current stable API (sunset path for v1)
- v3: Beta API (testing new features)

Versioning policy:
- Maintain at least 2 major versions
- Provide 12-month deprecation notice
- Support breaking changes only in major versions
- Use feature flags for experimental features

Endpoint structure:
/api/v1/resource
/api/v2/resource
/api/v3/resource

Deprecation headers:
Sunset: Sun, 31 Dec 2024 23:59:59 GMT
Deprecation: true
Link: <https://docs.company.com/api/v2>; rel="successor-version"

Migration guide:
https://docs.company.com/api/migration-v1-to-v2
        """,
        "source_type": "document",
        "source_id": "doc-api-versioning",
        "importance": 0.85,
    },
    {
        "id": "ctx-deployment-strategy",
        "title": "Deployment Strategy & Rollout",
        "topic_id": "topic-deployment",
        "content": """
We use a canary deployment strategy to minimize risk:

1. Canary (5% traffic): Monitor error rates, latency, custom metrics
2. Staged (25% traffic): Expand if canary metrics are healthy
3. Rolling (100% traffic): Full deployment over 15 minutes

Automation:
- GitHub Actions for CI/CD
- ArgoCD for GitOps
- Automatic rollback on error rate spike (>0.5%)

Pre-deployment checklist:
- [ ] All tests passing
- [ ] Code reviewed and approved
- [ ] Database migrations tested
- [ ] Rollback plan documented
- [ ] On-call engineer notified

Deployment timeline:
- Development: Immediate on merge to develop
- Staging: 1-2 hours after merge to staging
- Production: Coordinated with team, never Friday afternoon

Emergency hotfix process:
- Create hotfix branch from main
- Fast-track review (single approval)
- Direct merge to main and production branches
- Automated deployment to production

Monitoring during deployment:
- Error rate dashboard
- Latency percentiles (p50, p95, p99)
- Custom business metrics
- Slack notifications for anomalies
        """,
        "source_type": "document",
        "source_id": "doc-deployment",
        "importance": 0.95,
    },
    {
        "id": "ctx-ml-data-pipeline",
        "title": "Data Pipeline for ML Training",
        "topic_id": "topic-ml-pipelines",
        "content": """
Our ML data pipeline processes raw data into training-ready datasets.

Pipeline stages:
1. Data Ingestion: Collect from PostgreSQL, API events, external sources
2. Data Validation: Check schema, missing values, outliers
3. Feature Engineering: Create derived features, normalize
4. Data Versioning: Track datasets with DVC
5. Model Training: Distributed training on GPU cluster
6. Model Evaluation: Validate on holdout test set
7. Model Deployment: A/B test before full rollout

Tech stack:
- Airflow: Orchestration
- Pandas/Polars: Data processing
- DVC: Data versioning
- Weights & Biases: Experiment tracking
- TensorFlow/PyTorch: Training
- Seldon: Model serving

Data quality metrics:
- Completeness: No missing values
- Accuracy: Data matches expectations
- Consistency: No contradictions
- Timeliness: Data freshness < 1 day

SLAs:
- Pipeline completion: < 4 hours daily
- Data availability: 99.5%
- Model inference latency: < 100ms p95

Monitoring:
- Airflow DAG health
- Data distribution drift detection
- Model performance degradation alerts
        """,
        "source_type": "document",
        "source_id": "doc-ml-pipeline",
        "importance": 0.9,
    },
]

SAMPLE_DECISIONS = [
    {
        "id": "decision-monorepo",
        "title": "Adopt Monorepo Structure",
        "content": "Migrated from multi-repo to monorepo using Turborepo",
        "decision_type": "technical",
        "status": "active",
        "rationale": """
Monorepo improves:
- Shared code reuse across services
- Atomic commits across packages
- Simplified dependency management
- Easier refactoring

Trade-offs:
- Larger repository size
- Requires discipline in package organization
- CI/CD must be optimized

Decision made: Jan 2024
        """,
    },
    {
        "id": "decision-nextjs",
        "title": "Standardize on Next.js for Frontend",
        "content": "All new frontend projects use Next.js with TypeScript",
        "decision_type": "technical",
        "status": "active",
        "rationale": "Unified stack, better performance, built-in SSR/SSG capabilities",
    },
    {
        "id": "decision-postgres",
        "title": "PostgreSQL as Primary Database",
        "content": "PostgreSQL is our main OLTP database",
        "decision_type": "technical",
        "status": "active",
        "rationale": "ACID compliance, rich features, strong ecosystem",
    },
]

SAMPLE_CONVERSATION_MESSAGES = [
    {
        "role": "user",
        "content": "What's the OAuth flow we're using?",
    },
    {
        "role": "assistant",
        "content": """We're implementing OAuth 2.0 using the Authorization Code flow. Here's the process:

1. User initiates login
2. They're redirected to our authorization server
3. After granting permission, they get an authorization code
4. The application exchanges the code for an access token
5. The token is used to fetch user information

This approach is secure because the user's credentials are never shared with the application directly. We also implement refresh tokens with a 30-day expiration for long-lived sessions.""",
        "agent": "knowledge",
        "sources": [
            {"title": "OAuth 2.0 Implementation Flow", "type": "documentation"}
        ],
    },
    {
        "role": "user",
        "content": "How do we handle token expiration?",
    },
    {
        "role": "assistant",
        "content": """For token management, we follow these practices:

Access tokens: 1-hour expiration (short-lived)
Refresh tokens: 30-day expiration (long-lived)
Token rotation: We issue a new refresh token with each use

When an access token expires, the client uses the refresh token to get a new access token without requiring the user to log in again. This balances security with user convenience.""",
        "agent": "knowledge",
        "sources": [
            {"title": "JWT Token Management", "type": "documentation"}
        ],
    },
]


async def create_database_session():
    """Create async database session."""
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
    )
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, async_session


async def seed_postgresql(async_session):
    """Seed PostgreSQL with users, conversations, and messages."""
    logger.info("Seeding PostgreSQL data...")

    async with async_session() as session:
        # Create users
        users = []
        for user_data in SAMPLE_USERS:
            user = User(
                id=str(uuid4()),
                email=user_data["email"],
                hashed_password="hashed_demo_password",
                full_name=user_data["full_name"],
                role=user_data["role"],
                department=user_data["department"],
                team=user_data["team"],
                is_active=True,
                is_superuser=False,
            )
            session.add(user)
            users.append(user)

        await session.flush()
        logger.info(f"Created {len(users)} users")

        # Create conversations for first 3 users
        for i, user in enumerate(users[:3]):
            conversation = Conversation(
                id=str(uuid4()),
                user_id=user.id,
                title=f"Sample Conversation {i+1}",
                conversation_type="chat",
                conversation_metadata={
                    "source": "sample_data",
                    "topic": "Technical Discussion",
                },
            )
            session.add(conversation)
            await session.flush()

            # Add sample messages to conversation
            base_time = datetime.utcnow() - timedelta(hours=2)
            for msg_idx, msg_data in enumerate(SAMPLE_CONVERSATION_MESSAGES):
                message = Message(
                    id=str(uuid4()),
                    conversation_id=conversation.id,
                    role=msg_data["role"],
                    content=msg_data["content"],
                    agent=msg_data.get("agent"),
                    sources=msg_data.get("sources"),
                    message_metadata={"sample": True},
                    created_at=base_time + timedelta(minutes=msg_idx * 5),
                )
                session.add(message)

        await session.commit()
        logger.info("Created sample conversations and messages")


async def seed_neo4j():
    """Seed Neo4j with knowledge graph (textbook architecture).

    Structure:
    - Department (chapter)
      - SubDepartment (section)
        - Topic (subsection)
          - Context (individual knowledge pieces from chats/docs)
          - Summary (consolidated summaries)
    """
    logger.info("Seeding Neo4j knowledge graph...")

    try:
        # Connect to Neo4j first
        await neo4j_client.connect()

        # Create departments (chapters)
        for dept in SAMPLE_DEPARTMENTS:
            await neo4j_client.create_or_update_node(
                node_type="Department",
                properties=dept,
            )
        logger.info(f"Created {len(SAMPLE_DEPARTMENTS)} departments (chapters)")

        # Create subdepartments (sections)
        for sub in SAMPLE_SUBDEPARTMENTS:
            await neo4j_client.create_or_update_node(
                node_type="SubDepartment",
                properties=sub,
            )
            # Create relationship to department
            await neo4j_client.create_relationship_by_type(
                from_type="Department",
                from_id=sub["department_id"],
                to_type="SubDepartment",
                to_id=sub["id"],
                relationship_type="HAS_SUBDEPARTMENT",
            )
        logger.info(f"Created {len(SAMPLE_SUBDEPARTMENTS)} subdepartments (sections)")

        # Create topics (subsections)
        for topic in SAMPLE_TOPICS:
            await neo4j_client.create_or_update_node(
                node_type="Topic",
                properties=topic,
            )
            # Create relationship to subdepartment
            await neo4j_client.create_relationship_by_type(
                from_type="SubDepartment",
                from_id=topic["sub_department_id"],
                to_type="Topic",
                to_id=topic["id"],
                relationship_type="HAS_TOPIC",
            )
        logger.info(f"Created {len(SAMPLE_TOPICS)} topics (subsections)")

        # Create context nodes (individual knowledge pieces)
        for context in SAMPLE_CONTEXTS:
            await neo4j_client.create_or_update_node(
                node_type="Context",
                properties=context,
            )
            # Create relationship to topic
            await neo4j_client.create_relationship_by_type(
                from_type="Topic",
                from_id=context["topic_id"],
                to_type="Context",
                to_id=context["id"],
                relationship_type="HAS_CONTEXT",
            )
        logger.info(f"Created {len(SAMPLE_CONTEXTS)} context nodes")

        # Create decision nodes
        for decision in SAMPLE_DECISIONS:
            await neo4j_client.create_or_update_node(
                node_type="Decision",
                properties=decision,
            )
        logger.info(f"Created {len(SAMPLE_DECISIONS)} decision nodes")

        logger.info("Neo4j knowledge graph seeding complete")

    except Exception as e:
        logger.error("Error seeding Neo4j", error=str(e))
        raise


async def seed_qdrant():
    """Seed Qdrant with vector embeddings for textbook knowledge."""
    logger.info("Seeding Qdrant embeddings...")

    try:
        # Initialize collections first
        await embedder.init_collections()
        logger.info("Qdrant collections initialized")
        # Prepare embedding documents
        documents = []

        # Add context documents as org knowledge
        for context in SAMPLE_CONTEXTS:
            documents.append(
                {
                    "text": f"{context['title']}\n{context['content']}",
                    "type": "documentation",
                    "title": context["title"],
                    "topic": context["topic_id"],
                    "source": context["source_type"],
                    "importance": context["importance"],
                    "collection": "knowledge",
                }
            )

        # Add decision documents as organizational memory
        for decision in SAMPLE_DECISIONS:
            documents.append(
                {
                    "text": f"{decision['title']}\n{decision['content']}\n{decision['rationale']}",
                    "type": "decision",
                    "title": decision["title"],
                    "decision_type": decision["decision_type"],
                    "status": decision["status"],
                    "collection": "org_memory",
                }
            )

        # Add organizational policies
        policies = [
            {
                "text": """Code Review Policy: All code changes require at least one approval from another engineer before merging to main.
For critical infrastructure changes, require two approvals. Reviews should focus on correctness, performance, security, and maintainability.""",
                "type": "policy",
                "policy_type": "code_review",
                "title": "Code Review Standards",
                "department": "Engineering",
                "collection": "org_memory",
            },
            {
                "text": """On-Call Rotation: Engineers rotate on-call duty weekly. On-call engineers are responsible for responding to production incidents within 15 minutes.
Escalation path: Primary -> Secondary -> Manager. Each engineer gets 2 weeks off every 8 weeks.""",
                "type": "policy",
                "policy_type": "incident_response",
                "title": "On-Call Policy",
                "department": "Engineering",
                "collection": "org_memory",
            },
            {
                "text": """Testing Requirements: All code changes must maintain or improve test coverage. Minimum coverage for new code: 80%.
Unit tests for business logic, integration tests for APIs, e2e tests for critical user flows.""",
                "type": "policy",
                "policy_type": "testing",
                "title": "Testing Policy",
                "department": "Engineering",
                "collection": "org_memory",
            },
        ]
        documents.extend(policies)

        # Add best practices
        best_practices = [
            {
                "text": """Database Query Optimization: Use EXPLAIN ANALYZE to understand query performance.
Index heavily-filtered columns. Avoid SELECT *, fetch only needed columns.
Use connection pooling with reasonable limits (20-50 connections per service).""",
                "type": "best_practice",
                "category": "Database",
                "title": "Database Query Optimization",
                "source_team": "Platform",
                "collection": "org_memory",
            },
            {
                "text": """Error Handling: Always catch specific exceptions, not generic Exception.
Log errors with context: user_id, request_id, stack trace.
Return meaningful error messages to clients (without exposing internal details).
Implement exponential backoff for retries.""",
                "type": "best_practice",
                "category": "Error Handling",
                "title": "Error Handling Best Practices",
                "source_team": "Platform",
                "collection": "org_memory",
            },
        ]
        documents.extend(best_practices)

        # Embed and store documents
        embedded_docs = await embedder.embed_and_store(documents)
        logger.info(f"Embedded and stored {len(embedded_docs)} documents in Qdrant")

    except Exception as e:
        logger.error("Error seeding Qdrant", error=str(e))
        # Don't raise - embeddings are optional for basic functionality


async def seed_redis():
    """Seed Redis with sample conversation context."""
    logger.info("Seeding Redis short-term memory...")

    try:
        # Store a sample conversation context
        sample_conversation_id = str(uuid4())
        conversation_key = f"conv:{sample_conversation_id}"

        # Add sample messages to Redis list
        for i, msg in enumerate(SAMPLE_CONVERSATION_MESSAGES):
            await redis_client.rpush(
                conversation_key,
                json.dumps(
                    {
                        "role": msg["role"],
                        "content": msg["content"],
                        "timestamp": (
                            datetime.utcnow() - timedelta(hours=2 - i * 0.2)
                        ).isoformat(),
                    }
                ),
            )

        # Set context metadata
        context_key = f"ctx:{sample_conversation_id}"
        await redis_client.set(
            context_key,
            json.dumps(
                {
                    "user_id": "sample-user",
                    "agent": "knowledge",
                    "state": "conversation_active",
                    "created_at": datetime.utcnow().isoformat(),
                }
            ),
        )

        logger.info("Seeded Redis with sample conversation context")

    except Exception as e:
        logger.warning("Error seeding Redis (non-critical)", error=str(e))


async def main():
    """Run all seeding operations."""
    logger.info("Starting sample data seeding...")

    try:
        # Create database engine and session
        engine, async_session = await create_database_session()

        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")

        # Seed data
        await seed_postgresql(async_session)
        await seed_neo4j()
        await seed_qdrant()
        await seed_redis()

        logger.info("✅ Sample data seeding complete!")
        logger.info(
            "You can now test the chat interface at http://localhost:3000"
        )

    except Exception as e:
        logger.error("Error during seeding", error=str(e), exc_info=True)
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
