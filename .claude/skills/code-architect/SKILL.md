# Code Architect Skill
**Description:** Plan and implement code with approval workflow. Analyze requirements, create detailed plans, get approval, then execute systematically.
**Usage:** /code-architect [feature or implementation request]

**Trigger this skill when:**
- User requests a new feature implementation
- User needs code refactoring with planning
- Complex coding tasks requiring design decisions
- User says "implement", "build", "add feature", "refactor"
- Multi-file changes that benefit from upfront planning

**Skip for:** Simple one-line fixes, pure debugging, documentation-only tasks, code review

---

## Phase 1: Analysis & Planning

### Step 1.1: Understand Requirements

| Question | Purpose |
|----------|---------|
| What is the core functionality needed? | Define scope |
| What are the inputs and outputs? | Define interfaces |
| What constraints exist? | Identify limitations |
| What existing code is affected? | Map dependencies |

### Step 1.2: Gather Context

Run in parallel:
- Fire `explore` agent to find related code patterns
- Read existing code structure and conventions
- Check for similar implementations to follow
- Review project documentation (CLAUDE.md files)

### Step 1.3: Create Implementation Plan

```markdown
## Implementation Plan

### Overview
[High-level description of the approach]

### Key Design Decisions
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| [Choice 1] | [Why] | [Other options] |
| [Choice 2] | [Why] | [Other options] |

### Assumptions
- [Assumption 1]
- [Assumption 2]

### Files to Create/Modify
| File | Action | Changes |
|------|--------|---------|
| `path/to/file1` | Create | [Description] |
| `path/to/file2` | Modify | [Description] |

### Implementation Steps (Ordered)
1. [ ] [Step 1 - specific and actionable]
2. [ ] [Step 2 - specific and actionable]
3. [ ] [Step 3 - specific and actionable]

### Testing Strategy
- [How to verify this works]

### Potential Risks
- [Risk 1] - Mitigation: [approach]
```

---

## Phase 2: Approval Gate (MANDATORY)

**Before proceeding:**
1. Present the plan to the user
2. Highlight any assumptions or questions
3. Wait for explicit approval or feedback
4. If changes requested, update plan and re-present

**Never skip this phase.** Implementation without approval wastes effort.

---

## Phase 3: Implementation

### Step 3.1: Create Checklist
Convert plan steps into a trackable todo list using `todowrite`.

### Step 3.2: Execute Systematically
For each step:
1. Mark todo as `in_progress`
2. Make the changes
3. Run `lsp_diagnostics` on changed files
4. Mark todo as `completed`
5. Move to next step

### Step 3.3: Delegation Rules

**Delegate to subagents when:**
- Subtask is self-contained and complex
- Subtask requires deep specialized knowledge
- Parallel execution would improve efficiency

**Delegation prompt template:**
```
TASK: [Specific atomic goal]

CONTEXT:
- [Relevant code snippets]
- [Constraints and patterns to follow]

EXPECTED OUTCOME:
- [Specific deliverable]

MUST DO:
- [Requirement 1]
- [Requirement 2]

MUST NOT DO:
- [Forbidden action 1]
- [Forbidden action 2]
```

---

## Phase 4: Quality Assurance

### Self-Review Checklist
- [ ] All plan steps completed
- [ ] Code follows existing patterns
- [ ] Error handling implemented
- [ ] Edge cases considered
- [ ] `lsp_diagnostics` clean on all changed files
- [ ] No type suppressions added

### Verification
1. Run any relevant tests
2. Check integration points
3. Verify no regressions

---

## Phase 5: Completion

### Deliverables
Present to user:
- Summary of what was implemented
- Key files created/modified
- Usage examples or integration notes
- Any deviations from original plan (with reasoning)
- Suggested next steps or follow-up tasks

---

## Quality Guidelines

**ALWAYS:**
- Create a detailed plan before coding
- Wait for user approval
- Track progress with todos
- Follow existing code patterns
- Run diagnostics after changes
- Document deviations from plan

**NEVER:**
- Start coding without a plan
- Skip the approval gate
- Add functionality not in the plan
- Suppress type errors
- Leave broken code

---

## Best Practices Applied

| Principle | Application |
|-----------|-------------|
| **SOLID** | Single responsibility, dependency inversion |
| **DRY** | Abstract common patterns |
| **KISS** | Favor simplicity over cleverness |
| **YAGNI** | Don't add until needed |
| **Security** | Validate inputs, no hardcoded secrets |

---

## Escalation Triggers

**Consult Oracle if:**
- Architecture decision with significant trade-offs
- Unfamiliar patterns or technologies
- Performance/security concerns

**Ask User if:**
- Requirements are ambiguous
- Multiple valid approaches exist
- Scope creep detected
