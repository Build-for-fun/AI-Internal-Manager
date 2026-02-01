"""Onboarding API endpoints."""

from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.onboarding.agent import onboarding_agent
from src.agents.onboarding.flows import ONBOARDING_FLOWS, get_flow_for_user
from src.models.database import get_db
from src.models.onboarding import OnboardingProgress, OnboardingTask
from src.models.user import User
from src.schemas.onboarding import (
    OnboardingProgressResponse,
    OnboardingStartRequest,
    OnboardingTaskResponse,
    OnboardingTaskUpdate,
    QuizQuestion,
    QuizResult,
    QuizSubmission,
)

logger = structlog.get_logger()

router = APIRouter()


# Reuse get_current_user from chat module
async def get_current_user(
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current user."""
    stmt = select(User).limit(1)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=str(uuid4()),
            email="dev@example.com",
            hashed_password="dev",
            full_name="Development User",
            role="Software Engineer",
            department="Engineering",
            team="Platform",
        )
        db.add(user)
        await db.commit()

    return user


@router.get("/flows")
async def list_flows():
    """List available onboarding flows."""
    return [
        {
            "id": flow.id,
            "name": flow.name,
            "description": flow.description,
            "target_roles": flow.target_roles,
            "target_departments": flow.target_departments,
            "task_count": len(flow.tasks),
        }
        for flow in ONBOARDING_FLOWS.values()
    ]


@router.get("/flows/{flow_id}")
async def get_flow(flow_id: str):
    """Get details of a specific onboarding flow."""
    flow = ONBOARDING_FLOWS.get(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    return {
        "id": flow.id,
        "name": flow.name,
        "description": flow.description,
        "target_roles": flow.target_roles,
        "target_departments": flow.target_departments,
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "phase": task.phase.value,
                "task_type": task.task_type,
                "is_required": task.is_required,
                "estimated_minutes": task.estimated_minutes,
                "voice_enabled": task.voice_enabled,
            }
            for task in flow.tasks
        ],
    }


@router.post("/start", response_model=OnboardingProgressResponse)
async def start_onboarding(
    request: OnboardingStartRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OnboardingProgressResponse:
    """Start or restart the onboarding process."""
    result = await onboarding_agent.start_onboarding(
        user_id=user.id,
        role=user.role,
        department=user.department,
    )

    # Get the created progress
    stmt = select(OnboardingProgress).where(
        OnboardingProgress.user_id == user.id
    )
    db_result = await db.execute(stmt)
    progress = db_result.scalar_one_or_none()

    if not progress:
        raise HTTPException(status_code=500, detail="Failed to create onboarding progress")

    # Get tasks
    tasks_stmt = select(OnboardingTask).where(
        OnboardingTask.onboarding_id == progress.id
    ).order_by(OnboardingTask.order)
    tasks_result = await db.execute(tasks_stmt)
    tasks = list(tasks_result.scalars().all())

    return OnboardingProgressResponse(
        id=progress.id,
        status=progress.status,
        progress_percentage=progress.progress_percentage,
        current_phase=progress.current_phase,
        onboarding_flow=progress.onboarding_flow,
        started_at=progress.started_at,
        completed_at=progress.completed_at,
        assessment_scores=progress.assessment_scores,
        tasks=[OnboardingTaskResponse.model_validate(t) for t in tasks],
    )


@router.get("/progress", response_model=OnboardingProgressResponse)
async def get_progress(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OnboardingProgressResponse:
    """Get current onboarding progress."""
    stmt = select(OnboardingProgress).where(
        OnboardingProgress.user_id == user.id
    )
    result = await db.execute(stmt)
    progress = result.scalar_one_or_none()

    if not progress:
        # Return empty progress
        return OnboardingProgressResponse(
            id="",
            status="not_started",
            progress_percentage=0,
            current_phase=None,
            onboarding_flow=None,
            started_at=None,
            completed_at=None,
            assessment_scores={},
            tasks=[],
        )

    # Get tasks
    tasks_stmt = select(OnboardingTask).where(
        OnboardingTask.onboarding_id == progress.id
    ).order_by(OnboardingTask.order)
    tasks_result = await db.execute(tasks_stmt)
    tasks = list(tasks_result.scalars().all())

    return OnboardingProgressResponse(
        id=progress.id,
        status=progress.status,
        progress_percentage=progress.progress_percentage,
        current_phase=progress.current_phase,
        onboarding_flow=progress.onboarding_flow,
        started_at=progress.started_at,
        completed_at=progress.completed_at,
        assessment_scores=progress.assessment_scores,
        tasks=[OnboardingTaskResponse.model_validate(t) for t in tasks],
    )


@router.get("/tasks/{task_id}", response_model=OnboardingTaskResponse)
async def get_task(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OnboardingTaskResponse:
    """Get details of a specific onboarding task."""
    # Get user's progress
    progress_stmt = select(OnboardingProgress).where(
        OnboardingProgress.user_id == user.id
    )
    progress_result = await db.execute(progress_stmt)
    progress = progress_result.scalar_one_or_none()

    if not progress:
        raise HTTPException(status_code=404, detail="No onboarding in progress")

    # Get task
    task_stmt = select(OnboardingTask).where(
        OnboardingTask.id == task_id,
        OnboardingTask.onboarding_id == progress.id,
    )
    task_result = await db.execute(task_stmt)
    task = task_result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return OnboardingTaskResponse.model_validate(task)


@router.patch("/tasks/{task_id}", response_model=OnboardingTaskResponse)
async def update_task(
    task_id: str,
    request: OnboardingTaskUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OnboardingTaskResponse:
    """Update an onboarding task status."""
    result = await onboarding_agent.complete_task(
        user_id=user.id,
        task_id=task_id,
        completion_data=request.completion_data,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # Get updated task
    task_stmt = select(OnboardingTask).where(OnboardingTask.id == task_id)
    task_result = await db.execute(task_stmt)
    task = task_result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return OnboardingTaskResponse.model_validate(task)


@router.post("/tasks/{task_id}/complete")
async def complete_task(
    task_id: str,
    completion_data: dict = None,
    user: User = Depends(get_current_user),
):
    """Mark a task as completed."""
    result = await onboarding_agent.complete_task(
        user_id=user.id,
        task_id=task_id,
        completion_data=completion_data,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/tasks/{task_id}/content")
async def get_task_content(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the content for a task (from knowledge graph)."""
    # Get task
    progress_stmt = select(OnboardingProgress).where(
        OnboardingProgress.user_id == user.id
    )
    progress_result = await db.execute(progress_stmt)
    progress = progress_result.scalar_one_or_none()

    if not progress:
        raise HTTPException(status_code=404, detail="No onboarding in progress")

    task_stmt = select(OnboardingTask).where(
        OnboardingTask.id == task_id,
        OnboardingTask.onboarding_id == progress.id,
    )
    task_result = await db.execute(task_stmt)
    task = task_result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get content from knowledge graph if available
    content = {
        "task_id": task_id,
        "title": task.title,
        "description": task.description,
        "type": task.task_type,
    }

    if task.content_ref:
        from src.knowledge.graph.client import neo4j_client

        node = await neo4j_client.get_node(task.content_ref)
        if node:
            content["knowledge_content"] = {
                "title": node.get("title"),
                "content": node.get("content"),
                "metadata": node,
            }

    return content


@router.get("/quiz/{task_id}/questions", response_model=list[QuizQuestion])
async def get_quiz_questions(
    task_id: str,
    user: User = Depends(get_current_user),
) -> list[QuizQuestion]:
    """Get quiz questions for a knowledge check task."""
    # Generate quiz questions based on completed topics
    # This would typically be more sophisticated
    questions = [
        QuizQuestion(
            id="q1",
            question="What is the primary code review platform used at the company?",
            options=["GitHub", "GitLab", "Bitbucket", "Gerrit"],
            topic="code_review",
        ),
        QuizQuestion(
            id="q2",
            question="How are sprint planning sessions typically conducted?",
            options=[
                "Weekly on Mondays",
                "Bi-weekly on Wednesdays",
                "Monthly on the first day",
                "As needed",
            ],
            topic="sprint_process",
        ),
        QuizQuestion(
            id="q3",
            question="What is the standard PR approval requirement?",
            options=[
                "1 approval",
                "2 approvals",
                "3 approvals",
                "Manager approval only",
            ],
            topic="code_review",
        ),
    ]

    return questions


@router.post("/quiz/{task_id}/submit", response_model=QuizResult)
async def submit_quiz_answer(
    task_id: str,
    submission: QuizSubmission,
    user: User = Depends(get_current_user),
) -> QuizResult:
    """Submit an answer for a quiz question."""
    # Validate answer (simplified - would look up actual answers)
    correct_answers = {
        "q1": 0,  # GitHub
        "q2": 1,  # Bi-weekly
        "q3": 1,  # 2 approvals
    }

    correct_answer = correct_answers.get(submission.question_id, 0)
    is_correct = submission.answer == correct_answer

    explanations = {
        "q1": "We use GitHub for all code hosting and review.",
        "q2": "Sprint planning happens bi-weekly on Wednesdays.",
        "q3": "All PRs require at least 2 approvals before merging.",
    }

    return QuizResult(
        question_id=submission.question_id,
        correct=is_correct,
        correct_answer=correct_answer,
        explanation=explanations.get(submission.question_id),
    )


@router.get("/recommended")
async def get_recommended_content(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recommended content based on user's progress and role."""
    # Get user's onboarding progress
    stmt = select(OnboardingProgress).where(
        OnboardingProgress.user_id == user.id
    )
    result = await db.execute(stmt)
    progress = result.scalar_one_or_none()

    recommendations = []

    # Get flow for user
    flow = get_flow_for_user(user.role, user.department)

    if progress:
        # Find incomplete tasks
        tasks_stmt = select(OnboardingTask).where(
            OnboardingTask.onboarding_id == progress.id,
            OnboardingTask.status != "completed",
        ).order_by(OnboardingTask.order).limit(3)
        tasks_result = await db.execute(tasks_stmt)
        incomplete_tasks = list(tasks_result.scalars().all())

        for task in incomplete_tasks:
            recommendations.append({
                "type": "task",
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "priority": "high" if task.is_required else "medium",
            })
    else:
        # Recommend starting onboarding
        recommendations.append({
            "type": "action",
            "id": "start_onboarding",
            "title": f"Start {flow.name}",
            "description": "Begin your personalized onboarding journey",
            "priority": "high",
        })

    # Add role-specific recommendations
    if user.department == "Engineering":
        recommendations.append({
            "type": "resource",
            "id": "eng_handbook",
            "title": "Engineering Handbook",
            "description": "Comprehensive guide to engineering practices",
            "priority": "medium",
        })

    return {
        "user_role": user.role,
        "user_department": user.department,
        "recommendations": recommendations[:5],
    }
