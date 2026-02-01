"""Onboarding agent for guiding new employees."""

from typing import Any

import structlog

from src.agents.base import BaseAgent
from src.agents.onboarding.flows import (
    OnboardingPhase,
    calculate_progress,
    get_flow_for_user,
    get_next_task,
)
from src.config import settings
from src.memory.manager import memory_manager

logger = structlog.get_logger()


class OnboardingAgent(BaseAgent):
    """Agent specialized in employee onboarding.

    This agent:
    1. Guides new employees through onboarding flows
    2. Provides role-specific information
    3. Answers onboarding-related questions
    4. Tracks progress and adapts content
    5. Supports voice interaction for accessible onboarding
    """

    def __init__(self):
        super().__init__(
            name="onboarding",
            description="Guides new employees through their onboarding journey",
        )

    async def process(
        self,
        query: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Process an onboarding query.

        Handles:
        - Starting/continuing onboarding
        - Answering onboarding questions
        - Providing task guidance
        - Progress tracking
        """
        user_id = context.get("user_id", "")
        user_name = context.get("user_name", "there")
        user_role = context.get("user_role")
        user_department = context.get("user_department")
        memory_context = context.get("memory_context", {})

        # Get user's onboarding state
        onboarding_state = await self._get_onboarding_state(user_id)

        # Get appropriate flow
        flow = get_flow_for_user(user_role, user_department)
        completed_tasks = onboarding_state.get("completed_tasks", [])
        progress, current_phase = calculate_progress(flow, completed_tasks)

        # Get next task
        next_task = get_next_task(flow, completed_tasks)

        # Get relevant onboarding context
        onboarding_context = await memory_manager.get_onboarding_context(
            user_id=user_id,
            role=user_role,
            department=user_department,
        )

        # Build system prompt
        system = f"""You are a friendly and helpful onboarding assistant for new employees.
Your role is to guide {user_name} through their onboarding journey.

USER PROFILE:
- Name: {user_name}
- Role: {user_role or 'Not specified'}
- Department: {user_department or 'Not specified'}

ONBOARDING STATUS:
- Flow: {flow.name}
- Progress: {progress}%
- Current Phase: {current_phase.value if current_phase else 'Complete'}
- Next Task: {next_task.title if next_task else 'All tasks completed!'}

GUIDELINES:
1. Be warm, welcoming, and encouraging
2. Provide clear, step-by-step guidance
3. Answer questions thoroughly but concisely
4. If asked about something outside onboarding scope, still try to help or direct them to the right resource
5. Celebrate progress and milestones
6. Offer to explain things in more detail if the user seems confused

CURRENT TASK DETAILS:
{self._format_task_details(next_task) if next_task else 'No pending tasks.'}

RELEVANT POLICIES AND INFORMATION:
{self._format_onboarding_context(onboarding_context)}
"""

        # Build messages
        messages = context.get("messages", [])
        messages.append({"role": "user", "content": query})

        # Call LLM
        result = await self._call_llm(
            messages=messages,
            system=system,
            max_tokens=1500,
        )

        return {
            "response": result["content"],
            "sources": [],
            "metadata": {
                "flow": flow.id,
                "progress": progress,
                "current_phase": current_phase.value if current_phase else None,
                "next_task_id": next_task.id if next_task else None,
                "usage": result.get("usage", {}),
            },
        }

    async def _get_onboarding_state(self, user_id: str) -> dict[str, Any]:
        """Get the user's current onboarding state from database."""
        from src.models.database import get_session
        from src.models.onboarding import OnboardingProgress

        from sqlalchemy import select

        async with get_session() as session:
            stmt = select(OnboardingProgress).where(
                OnboardingProgress.user_id == user_id
            )
            result = await session.execute(stmt)
            progress = result.scalar_one_or_none()

            if progress:
                # Get completed task IDs
                completed_tasks = [
                    task.id for task in progress.tasks
                    if task.status == "completed"
                ]
                return {
                    "status": progress.status,
                    "progress_percentage": progress.progress_percentage,
                    "current_phase": progress.current_phase,
                    "completed_tasks": completed_tasks,
                }

        return {
            "status": "not_started",
            "progress_percentage": 0,
            "current_phase": None,
            "completed_tasks": [],
        }

    def _format_task_details(self, task) -> str:
        """Format task details for the prompt."""
        if not task:
            return "No current task."

        return f"""
Task: {task.title}
Description: {task.description}
Type: {task.task_type}
Phase: {task.phase.value}
Estimated Time: {task.estimated_minutes} minutes
Voice Enabled: {'Yes' if task.voice_enabled else 'No'}
"""

    def _format_onboarding_context(self, context: dict[str, Any]) -> str:
        """Format onboarding context for the prompt."""
        parts = []

        if context.get("policies"):
            policies = context["policies"][:3]
            parts.append("Policies:\n" + "\n".join(
                f"- {p.get('title', 'Policy')}: {p.get('text', '')[:200]}"
                for p in policies
            ))

        if context.get("best_practices"):
            practices = context["best_practices"][:3]
            parts.append("Best Practices:\n" + "\n".join(
                f"- {p.get('title', 'Practice')}: {p.get('text', '')[:200]}"
                for p in practices
            ))

        if context.get("faqs"):
            faqs = context["faqs"][:3]
            parts.append("Common Questions:\n" + "\n".join(
                f"Q: {f.get('question', '')}\nA: {f.get('answer', '')[:200]}"
                for f in faqs
            ))

        return "\n\n".join(parts) if parts else "No additional context available."

    async def start_onboarding(
        self,
        user_id: str,
        role: str | None = None,
        department: str | None = None,
    ) -> dict[str, Any]:
        """Start or restart the onboarding process for a user."""
        from datetime import datetime

        from sqlalchemy import select

        from src.models.database import get_session
        from src.models.onboarding import OnboardingProgress, OnboardingTask, TaskStatus

        # Get appropriate flow
        flow = get_flow_for_user(role, department)

        async with get_session() as session:
            # Check for existing progress
            stmt = select(OnboardingProgress).where(
                OnboardingProgress.user_id == user_id
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Reset existing progress
                existing.status = "in_progress"
                existing.progress_percentage = 0
                existing.current_phase = flow.tasks[0].phase.value if flow.tasks else None
                existing.onboarding_flow = flow.id
                existing.started_at = datetime.utcnow()
                existing.completed_at = None
                # Clear existing tasks
                for task in existing.tasks:
                    await session.delete(task)
                progress = existing
            else:
                # Create new progress
                progress = OnboardingProgress(
                    user_id=user_id,
                    status="in_progress",
                    progress_percentage=0,
                    current_phase=flow.tasks[0].phase.value if flow.tasks else None,
                    onboarding_flow=flow.id,
                    started_at=datetime.utcnow(),
                )
                session.add(progress)

            await session.flush()

            # Create tasks
            for i, flow_task in enumerate(flow.tasks):
                task = OnboardingTask(
                    onboarding_id=progress.id,
                    title=flow_task.title,
                    description=flow_task.description,
                    phase=flow_task.phase.value,
                    order=i,
                    status=TaskStatus.PENDING.value,
                    task_type=flow_task.task_type,
                    content_ref=flow_task.content_ref,
                    is_required=flow_task.is_required,
                )
                session.add(task)

            await session.commit()

        return {
            "flow_id": flow.id,
            "flow_name": flow.name,
            "total_tasks": len(flow.tasks),
            "first_task": flow.tasks[0].title if flow.tasks else None,
        }

    async def complete_task(
        self,
        user_id: str,
        task_id: str,
        completion_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Mark a task as completed and update progress."""
        from datetime import datetime

        from sqlalchemy import select

        from src.models.database import get_session
        from src.models.onboarding import OnboardingProgress, OnboardingTask

        async with get_session() as session:
            # Get progress
            stmt = select(OnboardingProgress).where(
                OnboardingProgress.user_id == user_id
            )
            result = await session.execute(stmt)
            progress = result.scalar_one_or_none()

            if not progress:
                return {"error": "No onboarding in progress"}

            # Get and update task
            task_stmt = select(OnboardingTask).where(
                OnboardingTask.onboarding_id == progress.id,
                OnboardingTask.id == task_id,
            )
            task_result = await session.execute(task_stmt)
            task = task_result.scalar_one_or_none()

            if not task:
                return {"error": "Task not found"}

            task.status = "completed"
            task.completed_at = datetime.utcnow()
            task.completion_data = completion_data or {}

            # Calculate new progress
            all_tasks_stmt = select(OnboardingTask).where(
                OnboardingTask.onboarding_id == progress.id
            )
            all_tasks_result = await session.execute(all_tasks_stmt)
            all_tasks = all_tasks_result.scalars().all()

            completed_count = sum(1 for t in all_tasks if t.status == "completed")
            progress.progress_percentage = int((completed_count / len(all_tasks)) * 100)

            # Find next incomplete task for current phase
            for t in sorted(all_tasks, key=lambda x: x.order):
                if t.status != "completed":
                    progress.current_phase = t.phase
                    break
            else:
                # All done
                progress.current_phase = "complete"
                progress.status = "completed"
                progress.completed_at = datetime.utcnow()

            await session.commit()

            return {
                "task_completed": task.title,
                "progress": progress.progress_percentage,
                "current_phase": progress.current_phase,
                "status": progress.status,
            }


# Singleton instance
onboarding_agent = OnboardingAgent()
