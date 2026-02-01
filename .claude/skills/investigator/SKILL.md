# Investigator Skill
**Description:** Deep investigation of issues, bugs, or unexpected behavior. Research root causes, gather evidence, present findings, then hand off to code-implementation upon approval.
**Usage:** /investigator [issue description or error]

**Trigger this skill when:**
- User reports an issue without clear root cause
- User says "why is this happening?", "investigate this", "look into this"
- Unexpected behavior that needs diagnosis
- User mentions in GitHub issue or PR
- Complex bugs requiring deep analysis before fixing

**Skip for:** Known bugs with clear fixes (use bug-fix), feature requests (use code-architect), code explanation (use tutor)

---

## Core Philosophy

**Investigate FIRST, implement LATER.**

This skill is about understanding the problem thoroughly before proposing solutions. No code changes until the user approves your findings.

```
USER REPORTS ISSUE
       ↓
   INVESTIGATE (you are here)
       ↓
   PRESENT FINDINGS
       ↓
   USER APPROVES? ──NO──→ Refine investigation
       ↓ YES
   INVOKE /code-implementation
```

---

## Phase 1: Issue Intake

### Step 1.1: Capture the Problem

| Question | Purpose |
|----------|---------|
| What is the observed behavior? | Understand the symptom |
| What is the expected behavior? | Define success |
| When does it occur? | Identify triggers |
| Is it reproducible? | Assess reliability |
| Any error messages/logs? | Get direct evidence |

### Step 1.2: Clarify if Needed

If issue is vague, ask ONE clarifying question:
```
I want to investigate this properly. 
Could you clarify: [specific question]?
```

**Do NOT proceed with guesses.** Vague issues lead to wasted investigation.

---

## Phase 2: Deep Investigation

### Step 2.1: Launch Parallel Searches

Fire multiple agents simultaneously:

```
// Codebase exploration
background_task(agent="explore", prompt="Find code related to [issue area]")
background_task(agent="explore", prompt="Find error handling for [component]")
background_task(agent="explore", prompt="Find recent changes to [affected files]")

// If external libraries involved
background_task(agent="librarian", prompt="Known issues with [library] related to [symptom]")
```

### Step 2.2: Evidence Gathering

**Direct Investigation:**
- Read the relevant code paths
- Check error handling and edge cases
- Review recent git changes (`git log`, `git diff`)
- Check configuration files
- Look for similar patterns that work

**Tools to Use:**
| Tool | Purpose |
|------|---------|
| `explore` agent | Find related code patterns |
| `grep` | Search for specific strings |
| `ast_grep_search` | Find code patterns |
| `lsp_diagnostics` | Check for type errors |
| `git log/diff` | Check recent changes |
| `librarian` agent | External docs if library issue |

### Step 2.3: Root Cause Analysis

**Trace the problem:**
1. Start from the symptom (error, wrong behavior)
2. Work backwards through the code path
3. Identify where expected != actual
4. Determine WHY the divergence happens

**Common Root Causes:**
| Category | Examples |
|----------|----------|
| **Logic Error** | Wrong condition, missing case, off-by-one |
| **Data Issue** | Null/undefined, wrong type, stale data |
| **Race Condition** | Timing, async order, state mutation |
| **Configuration** | Wrong settings, missing env vars |
| **Dependency** | Version mismatch, breaking change |
| **Integration** | API contract violation, schema mismatch |

### Step 2.4: Verify Hypothesis

Before presenting findings:
- [ ] Can you explain HOW the bug occurs step-by-step?
- [ ] Does your theory explain ALL the symptoms?
- [ ] Have you ruled out alternative causes?
- [ ] Do you have evidence (code, logs, behavior)?

**If unsure:** Investigate more or state uncertainty clearly.

---

## Phase 3: Present Findings (MANDATORY)

### Investigation Report Template

```markdown
## Investigation Report: [Issue Title]

### Issue Summary
**Reported:** [What user described]
**Observed:** [What I found/reproduced]

---

### Root Cause Identified

**Location:** `file/path:line` (or multiple locations)

**What's Happening:**
[Clear explanation of the bug mechanism - 2-3 sentences]

**Why It's Happening:**
[Technical explanation of the root cause]

**Evidence:**
- [Code snippet or log that proves this]
- [Behavior that confirms hypothesis]

---

### Confidence Level
[ ] HIGH - Root cause confirmed with clear evidence
[ ] MEDIUM - Strong hypothesis, some uncertainty
[ ] LOW - Multiple possible causes, needs more info

---

### Proposed Fix

**Approach:** [Brief description of how to fix]

**Files to Change:**
- `path/to/file1` - [what change]
- `path/to/file2` - [what change]

**Estimated Complexity:** [Low / Medium / High]

**Risks:**
- [Potential risk 1]
- [Potential risk 2]

---

### Alternative Approaches (if any)
1. [Alternative 1] - Pros/Cons
2. [Alternative 2] - Pros/Cons

---

### Questions/Uncertainties
- [Any remaining questions]
- [Areas needing user input]

---

### Next Steps

Awaiting your approval to proceed with the fix.

**Options:**
1. **Approve** - I'll invoke /code-implementation to implement the fix
2. **Reject/Modify** - Tell me what to investigate further
3. **Ask Questions** - I'll clarify anything unclear
```

---

## Phase 4: Approval Gate (MANDATORY)

### Wait for User Response

**DO NOT proceed to implementation without explicit approval.**

| User Response | Action |
|---------------|--------|
| "Approved", "Go ahead", "Fix it" | Proceed to Phase 5 |
| "Not sure about X", questions | Answer questions, re-present if needed |
| "I think it's Y instead" | Re-investigate with new direction |
| "Rejected", "Wrong" | Ask what was wrong, re-investigate |

### If User Approves with Modifications

1. Update your understanding based on feedback
2. Confirm the updated approach
3. Then proceed to implementation

---

## Phase 5: Hand Off to Implementation

### Invoke Code Implementation Skill

Upon approval, invoke the `/code-implementation` skill with full context:

```markdown
/code-implementation

## Task: Fix [Issue Title]

### Background
[Brief issue description]

### Root Cause (from investigation)
[Summary of findings]

### Approved Fix Approach
[The approach user approved]

### Files to Modify
- `path/to/file1` - [change description]
- `path/to/file2` - [change description]

### Success Criteria
- [ ] [Specific testable outcome]
- [ ] [Specific testable outcome]
- [ ] No regressions in related functionality

### Verification
[How to verify the fix works]
```

**After implementation completes:**
- Report back to user with summary
- Confirm the issue is resolved

---

## Quality Guidelines

**ALWAYS:**
- Gather evidence before forming hypothesis
- Use multiple search angles (parallel agents)
- Present findings BEFORE proposing fixes
- Wait for explicit approval
- State confidence level honestly
- Hand off to code-implementation for actual fixes

**NEVER:**
- Guess at root cause without investigation
- Start fixing before user approves
- Present multiple weak hypotheses as "possibilities"
- Skip the approval gate
- Implement fixes directly (that's code-implementation's job)

---

## Investigation Anti-Patterns

| Bad Practice | Why It's Bad | Do This Instead |
|--------------|--------------|-----------------|
| Guessing root cause | Wastes time on wrong fixes | Investigate with evidence |
| "It might be X or Y or Z" | Unhelpful, no commitment | Pick most likely, state confidence |
| Fixing without approval | User may disagree with approach | Always present findings first |
| Surface-level search | Misses real root cause | Deep dive with multiple angles |
| Ignoring user's theory | They often have valuable context | Consider their input seriously |

---

## Escalation Triggers

**Consult Oracle if:**
- Root cause unclear after thorough investigation
- Multiple equally plausible hypotheses
- Architecture-level issue discovered
- Security vulnerability found

**Ask User if:**
- Need access to logs/data you can't see
- Business logic unclear (intended behavior?)
- Multiple valid fix approaches with trade-offs
- Issue may be intentional behavior
