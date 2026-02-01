# Code Reviewer Skill
**Description:** Review completed code against plans, standards, and best practices. Identify issues, validate implementation, provide actionable feedback.
**Usage:** /code-reviewer [files or feature to review]

**Trigger this skill when:**
- A major implementation step has been completed
- User says "review this code", "check my implementation"
- After code-architect or code-implementation skill completes
- Before merging or deploying significant changes
- User wants validation against a plan or spec

**Skip for:** Explaining code (use tutor), bug fixing (use bug-fix), writing new code (use code-architect)

---

## Phase 1: Context Gathering

### Step 1.1: Identify Review Scope

| Input | How to Get |
|-------|------------|
| Files changed | `git diff`, `git status`, or user-specified |
| Original plan | Check todos, recent messages, or ask user |
| Coding standards | Read CLAUDE.md, project conventions |
| Related code | Fire `explore` agent for similar patterns |

### Step 1.2: Understand Intent
- What was this code supposed to accomplish?
- What plan or spec was it based on?
- What are the acceptance criteria?

---

## Phase 2: Review Analysis

### 2.1: Plan Alignment Check

| Question | Action if Failed |
|----------|------------------|
| Does implementation match the plan? | Flag deviation, assess impact |
| Are all planned features present? | List missing items |
| Are there unplanned additions? | Flag scope creep |
| Were assumptions valid? | Note invalid assumptions |

### 2.2: Code Quality Assessment

**Structure & Organization:**
- [ ] Follows project file/folder conventions
- [ ] Appropriate separation of concerns
- [ ] Logical code organization

**Naming & Readability:**
- [ ] Clear, descriptive names
- [ ] Consistent naming conventions
- [ ] Self-documenting code

**Error Handling:**
- [ ] Appropriate error handling
- [ ] No silent failures
- [ ] Meaningful error messages

**Type Safety:**
- [ ] Proper type annotations
- [ ] No `any` types or suppressions
- [ ] Type guards where needed

**Performance:**
- [ ] No obvious inefficiencies
- [ ] Appropriate data structures
- [ ] No unnecessary operations

### 2.3: Architecture & Design

- [ ] Follows SOLID principles
- [ ] Proper abstraction levels
- [ ] Loose coupling between components
- [ ] Integrates well with existing code

### 2.4: Security Check

- [ ] Input validation present
- [ ] No hardcoded secrets
- [ ] Proper authentication/authorization
- [ ] Safe data handling

### 2.5: Testing Assessment

- [ ] Tests exist for new code
- [ ] Tests cover happy path
- [ ] Tests cover edge cases
- [ ] Tests are maintainable

---

## Phase 3: Issue Classification

### Severity Levels

| Level | Definition | Action Required |
|-------|------------|-----------------|
| **CRITICAL** | Breaks functionality, security vulnerability, data loss risk | Must fix before merge |
| **HIGH** | Significant bug, major deviation from plan, performance issue | Should fix before merge |
| **MEDIUM** | Code smell, minor deviation, maintainability concern | Fix in this PR or follow-up |
| **LOW** | Style issues, minor improvements, suggestions | Nice to have |

### Issue Template

```markdown
### [SEVERITY] Issue Title

**Location:** `file:line`

**Problem:** 
[Clear description of what's wrong]

**Impact:**
[Why this matters]

**Recommendation:**
[Specific fix with code example if helpful]
```

---

## Phase 4: Review Output

### Review Report Structure

```markdown
## Code Review Summary

### Overview
- **Files Reviewed:** [count]
- **Plan Alignment:** [ALIGNED / DEVIATIONS FOUND]
- **Overall Quality:** [GOOD / NEEDS WORK / CRITICAL ISSUES]

### What Was Done Well
- [Positive point 1]
- [Positive point 2]

### Plan Alignment
| Planned | Implemented | Status |
|---------|-------------|--------|
| [Feature 1] | [Description] | [checkmark] / [x] |

### Issues Found

#### Critical (Must Fix)
[List critical issues]

#### High (Should Fix)
[List high issues]

#### Medium (Recommended)
[List medium issues]

#### Low (Suggestions)
[List low issues]

### Recommendations
1. [Actionable recommendation 1]
2. [Actionable recommendation 2]

### Verdict
[ ] APPROVED - Ready to merge
[ ] APPROVED WITH COMMENTS - Minor fixes needed
[ ] CHANGES REQUESTED - Must address issues before merge
[ ] REJECTED - Significant rework needed
```

---

## Phase 5: Follow-up

### If Issues Found:
1. Communicate findings clearly
2. Be specific about what needs to change
3. Provide code examples for fixes when helpful
4. Offer to re-review after fixes

### If Approved:
1. Confirm code is ready
2. Note any follow-up tasks for later
3. Acknowledge good work

---

## Quality Guidelines

**ALWAYS:**
- Start with positives before issues
- Be specific and actionable
- Provide examples for complex fixes
- Classify issues by severity
- Check against the original plan
- Run `lsp_diagnostics` on reviewed files

**NEVER:**
- Be vague ("this looks wrong")
- Nitpick style when logic issues exist
- Approve code with critical issues
- Skip security considerations
- Ignore the original plan/spec

---

## Communication Style

- **Constructive:** Focus on improvement, not criticism
- **Specific:** "Line 42 has X issue" not "there are issues"
- **Actionable:** Every issue has a clear fix path
- **Balanced:** Acknowledge what's good, not just problems
