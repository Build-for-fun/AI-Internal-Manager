# Complete Coding Workflow Guide

## Overview

The Coding Workflow is a comprehensive, multi-stage development process that orchestrates system architecture, code implementation, code review, and documentation into a single streamlined workflow.

## Quick Start

To use the complete workflow, simply say:

```
implement coding workflow: [your feature description]
```

**Example:**
```
implement coding workflow: Add user authentication with OAuth2 and JWT tokens
```

## Workflow Stages

### 🏗️ Stage 1: System Architecture (system-arch agent)
**What happens:**
- Analyzes your requirements and current system
- Evaluates multiple architectural approaches
- Creates trade-off analysis for each option
- Documents decisions in Architecture Decision Records (ADRs)
- Proposes implementation phases

**What you do:**
- Review the proposed architecture
- Provide feedback if needed
- **Approve** the architecture to proceed

**Approval signals:** "Looks good", "Approved", "Let's proceed", "Go with Option A"

### 💻 Stage 2: Code Implementation (code-implementation agent)
**What happens:**
- Creates detailed implementation plan with checklist
- **Waits for your approval** of implementation approach
- Systematically implements code following the plan
- Writes comprehensive tests (unit, integration, edge cases)
- Runs diagnostics and verification
- Tracks progress with checklist updates

**What you do:**
- Review the implementation plan
- Approve the approach
- Monitor progress through checklist updates

### 🔍 Stage 3: Code Review (code-reviewer agent)
**What happens:**
- Reviews code against original architecture and plan
- Validates implementation quality and standards
- Checks test coverage and completeness
- Identifies issues, bugs, or improvements
- Provides actionable feedback with specific recommendations

**What you do:**
- Review the code review report
- Approve fixes or request changes

### 📚 Stage 4: Explanation (tutor agent)
**What happens:**
- Creates comprehensive `IMPLEMENTATION_OVERVIEW.md`
- Documents architecture decisions and rationale
- Explains design patterns and technical choices
- Provides usage examples
- Includes security and performance considerations
- Lists future enhancement opportunities

**What you do:**
- Read the overview document
- Reference it for future maintenance

## Manual Stage Invocation

You can also invoke individual stages:

### Architecture Only
```
/system-arch "Add real-time notification system"
```

### Implementation Only
```
/code-implementation "Implement user authentication"
```

### Review Only
```
/code-reviewer "Review authentication implementation"
```

### Explanation Only
```
/explain "Explain the authentication system implementation"
```

## Agent Details

### system-arch Agent
- **Purpose:** Architecture planning and design
- **Model:** Default or configured model
- **Output:** Architecture Decision Records, implementation plans
- **Automatically transitions to:** code-implementation (after approval)

### code-implementation Agent (renamed from code-architect)
- **Purpose:** Code planning and implementation
- **Model:** Opus (high capability for complex implementation)
- **Color:** Red
- **Output:** Production-ready code, tests, diagnostics
- **Automatically invokes:** code-reviewer (after completion)

### code-reviewer Agent
- **Purpose:** Code quality validation
- **Model:** Default or configured model
- **Output:** Review report, issue list, recommendations
- **Automatically triggers:** Fix cycle if issues found

### tutor Agent
- **Purpose:** Code explanation and documentation
- **Model:** Default or configured model
- **Output:** IMPLEMENTATION_OVERVIEW.md with comprehensive documentation

## Quality Gates

The workflow includes mandatory quality gates:

| Gate | Requirement | Block if Failed |
|------|-------------|-----------------|
| **Gate 1: Architecture Approval** | User must explicitly approve | ✅ Yes - Cannot proceed to implementation |
| **Gate 2: Implementation Complete** | All checklist items done, tests passing | ✅ Yes - Cannot proceed to review |
| **Gate 3: Code Review** | No critical issues, standards met | ✅ Yes - Cannot proceed to documentation |
| **Gate 4: Documentation** | Overview created with examples | ⚠️  Warning - Should complete for full workflow |

## Workflow State Tracking

The workflow maintains state across all phases:

```json
{
  "phase": "architecture|implementation|review|explanation",
  "status": "in_progress|waiting_approval|completed",
  "approvals": {
    "architecture": true/false,
    "implementation_plan": true/false,
    "code_review": true/false
  },
  "artifacts": {
    "adr": "path/to/architecture-decision.md",
    "checklist": ["Task 1", "Task 2"...],
    "review_report": {...},
    "overview": "IMPLEMENTATION_OVERVIEW.md"
  }
}
```

## Example Session

```
User: "implement coding workflow: Add rate limiting to API endpoints"