"""Role-specific onboarding flows."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OnboardingPhase(str, Enum):
    """Phases of the onboarding process."""

    WELCOME = "welcome"
    COMPANY_OVERVIEW = "company_overview"
    TEAM_INTRODUCTION = "team_introduction"
    TOOLS_SETUP = "tools_setup"
    PROCESSES = "processes"
    FIRST_TASKS = "first_tasks"
    KNOWLEDGE_CHECK = "knowledge_check"
    COMPLETE = "complete"


@dataclass
class OnboardingTask:
    """An individual onboarding task."""

    id: str
    title: str
    description: str
    phase: OnboardingPhase
    task_type: str  # "reading", "quiz", "interactive", "meeting", "voice_session"
    content_ref: str | None = None  # Reference to knowledge graph node
    is_required: bool = True
    estimated_minutes: int = 10
    voice_enabled: bool = False  # Can be done via voice


@dataclass
class OnboardingFlow:
    """A complete onboarding flow for a specific role."""

    id: str
    name: str
    description: str
    target_roles: list[str]
    target_departments: list[str]
    tasks: list[OnboardingTask] = field(default_factory=list)


# Define standard onboarding flows
ENGINEERING_FLOW = OnboardingFlow(
    id="engineering",
    name="Engineering Onboarding",
    description="Onboarding flow for software engineers",
    target_roles=["Software Engineer", "Senior Software Engineer", "Staff Engineer"],
    target_departments=["Engineering"],
    tasks=[
        OnboardingTask(
            id="eng_welcome",
            title="Welcome to Engineering",
            description="Introduction to the engineering organization",
            phase=OnboardingPhase.WELCOME,
            task_type="voice_session",
            voice_enabled=True,
            estimated_minutes=15,
        ),
        OnboardingTask(
            id="eng_company",
            title="Company Mission & Values",
            description="Learn about our mission, values, and culture",
            phase=OnboardingPhase.COMPANY_OVERVIEW,
            task_type="reading",
            estimated_minutes=20,
        ),
        OnboardingTask(
            id="eng_team",
            title="Meet Your Team",
            description="Introduction to your team structure and members",
            phase=OnboardingPhase.TEAM_INTRODUCTION,
            task_type="interactive",
            voice_enabled=True,
            estimated_minutes=30,
        ),
        OnboardingTask(
            id="eng_dev_setup",
            title="Development Environment Setup",
            description="Set up your local development environment",
            phase=OnboardingPhase.TOOLS_SETUP,
            task_type="interactive",
            estimated_minutes=60,
        ),
        OnboardingTask(
            id="eng_github",
            title="GitHub & Code Review",
            description="Learn our GitHub workflow and code review process",
            phase=OnboardingPhase.PROCESSES,
            task_type="reading",
            voice_enabled=True,
            estimated_minutes=20,
        ),
        OnboardingTask(
            id="eng_jira",
            title="Jira & Sprint Process",
            description="Understand our sprint planning and Jira workflow",
            phase=OnboardingPhase.PROCESSES,
            task_type="reading",
            voice_enabled=True,
            estimated_minutes=15,
        ),
        OnboardingTask(
            id="eng_ci_cd",
            title="CI/CD Pipeline",
            description="Learn about our deployment process",
            phase=OnboardingPhase.PROCESSES,
            task_type="reading",
            estimated_minutes=20,
        ),
        OnboardingTask(
            id="eng_first_pr",
            title="Your First Pull Request",
            description="Make your first contribution",
            phase=OnboardingPhase.FIRST_TASKS,
            task_type="interactive",
            estimated_minutes=120,
        ),
        OnboardingTask(
            id="eng_quiz",
            title="Knowledge Check",
            description="Test your understanding of engineering processes",
            phase=OnboardingPhase.KNOWLEDGE_CHECK,
            task_type="quiz",
            voice_enabled=True,
            estimated_minutes=15,
        ),
    ],
)

PRODUCT_FLOW = OnboardingFlow(
    id="product",
    name="Product Onboarding",
    description="Onboarding flow for product managers",
    target_roles=["Product Manager", "Senior Product Manager"],
    target_departments=["Product"],
    tasks=[
        OnboardingTask(
            id="pm_welcome",
            title="Welcome to Product",
            description="Introduction to the product organization",
            phase=OnboardingPhase.WELCOME,
            task_type="voice_session",
            voice_enabled=True,
            estimated_minutes=15,
        ),
        OnboardingTask(
            id="pm_company",
            title="Company Strategy",
            description="Understand our market position and strategy",
            phase=OnboardingPhase.COMPANY_OVERVIEW,
            task_type="reading",
            estimated_minutes=30,
        ),
        OnboardingTask(
            id="pm_products",
            title="Product Portfolio",
            description="Learn about our products and roadmap",
            phase=OnboardingPhase.COMPANY_OVERVIEW,
            task_type="interactive",
            voice_enabled=True,
            estimated_minutes=45,
        ),
        OnboardingTask(
            id="pm_tools",
            title="Product Tools Setup",
            description="Set up access to product management tools",
            phase=OnboardingPhase.TOOLS_SETUP,
            task_type="interactive",
            estimated_minutes=30,
        ),
        OnboardingTask(
            id="pm_processes",
            title="Product Development Process",
            description="Understand our product development lifecycle",
            phase=OnboardingPhase.PROCESSES,
            task_type="reading",
            voice_enabled=True,
            estimated_minutes=25,
        ),
    ],
)

GENERAL_FLOW = OnboardingFlow(
    id="general",
    name="General Onboarding",
    description="General onboarding for all employees",
    target_roles=[],  # Applies to all
    target_departments=[],  # Applies to all
    tasks=[
        OnboardingTask(
            id="gen_welcome",
            title="Welcome to the Company",
            description="Your first day introduction",
            phase=OnboardingPhase.WELCOME,
            task_type="voice_session",
            voice_enabled=True,
            estimated_minutes=15,
        ),
        OnboardingTask(
            id="gen_mission",
            title="Our Mission & Values",
            description="Learn about what drives us",
            phase=OnboardingPhase.COMPANY_OVERVIEW,
            task_type="reading",
            estimated_minutes=15,
        ),
        OnboardingTask(
            id="gen_policies",
            title="Company Policies",
            description="Important policies you should know",
            phase=OnboardingPhase.COMPANY_OVERVIEW,
            task_type="reading",
            estimated_minutes=20,
        ),
        OnboardingTask(
            id="gen_tools",
            title="Essential Tools",
            description="Set up your essential work tools",
            phase=OnboardingPhase.TOOLS_SETUP,
            task_type="interactive",
            estimated_minutes=30,
        ),
    ],
)

# All available flows
ONBOARDING_FLOWS = {
    "engineering": ENGINEERING_FLOW,
    "product": PRODUCT_FLOW,
    "general": GENERAL_FLOW,
}


def get_flow_for_user(
    role: str | None = None,
    department: str | None = None,
) -> OnboardingFlow:
    """Get the appropriate onboarding flow for a user.

    Matches based on role and department.
    Falls back to general flow if no specific match.
    """
    for flow in ONBOARDING_FLOWS.values():
        # Check role match
        if role and role in flow.target_roles:
            return flow
        # Check department match
        if department and department in flow.target_departments:
            return flow

    return GENERAL_FLOW


def get_next_task(
    flow: OnboardingFlow,
    completed_task_ids: list[str],
) -> OnboardingTask | None:
    """Get the next task to complete in the flow."""
    for task in flow.tasks:
        if task.id not in completed_task_ids:
            return task
    return None


def calculate_progress(
    flow: OnboardingFlow,
    completed_task_ids: list[str],
) -> tuple[int, OnboardingPhase | None]:
    """Calculate progress percentage and current phase.

    Returns:
        (progress_percentage, current_phase)
    """
    if not flow.tasks:
        return 100, OnboardingPhase.COMPLETE

    completed_count = sum(1 for t in flow.tasks if t.id in completed_task_ids)
    progress = int((completed_count / len(flow.tasks)) * 100)

    # Find current phase
    current_phase = None
    for task in flow.tasks:
        if task.id not in completed_task_ids:
            current_phase = task.phase
            break

    if current_phase is None and completed_count == len(flow.tasks):
        current_phase = OnboardingPhase.COMPLETE

    return progress, current_phase
