# Coding Workflow Skill
**Description:** Complete end-to-end coding workflow: System Architecture → Implementation → Code Review → Explanation. Orchestrates multiple agents to deliver production-ready, well-documented code.
**Usage:** /coding-workflow [feature or system to build]

**Trigger this skill when:**
- User says "implement coding workflow", "full coding workflow", "complete development cycle"
- User wants a comprehensive, multi-stage development process
- User requests architecture planning + implementation + review + documentation
- Complex features that benefit from structured workflow

**Skip for:** Simple fixes, single-stage tasks, quick implementations that don't need full workflow

---

## Workflow Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CODING WORKFLOW                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Phase 1: SYSTEM ARCHITECTURE                               │
│  ├─ Agent: system-arch                                      │
│  ├─ Analyzes requirements, evaluates options                │
│  ├─ Creates architecture decision records (ADRs)            │
│  └─ OUTPUT: Approved architectural plan                     │
│           │                                                  │
│           ▼                                                  │
│  Phase 2: CODE IMPLEMENTATION                               │
│  ├─ Agent: code-implementation                              │
│  ├─ Plans implementation with checklist                     │
│  ├─ Writes production-quality code                          │
│  └─ OUTPUT: Completed implementation                        │
│           │                                                  │
│           ▼                                                  │
│  Phase 3: CODE REVIEW                                       │
│  ├─ Agent: code-reviewer                                    │
│  ├─ Reviews against plan and standards                      │
│  ├─ Identifies issues and improvements                      │
│  └─ OUTPUT: Review report + fixes applied                   │
│           │                                                  │
│           ▼                                                  │
│  Phase 4: HIGH-LEVEL EXPLANATION                            │
│  ├─ Agent: tutor                                            │
│  ├─ Creates comprehensive overview MD                       │
│  ├─ Explains architecture, implementation, key decisions    │
│  └─ OUTPUT: IMPLEMENTATION_OVERVIEW.md                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: System Architecture Planning

### Step 1.1: Invoke System Architecture Agent

**Action:** Launch system-arch agent with the task

```bash
/skill system-arch "[user's request]"
```

**What the system-arch agent does:**
- Analyzes current system state
- Evaluates architectural options and trade-offs
- Assesses impact on quality attributes (performance, scalability, security)
- Creates Architecture Decision Records (ADRs)
- Provides implementation planning with phases

### Step 1.2: Wait for Architecture Approval

**MANDATORY GATE:** Do NOT proceed until user explicitly approves the architecture.

**User signals approval:**
- "Looks good", "Approved", "Let's proceed", "Go ahead with Option A"
- "Yes, implement that"

**If user requests changes:**
- Update architecture plan
- Re-present for approval
- Iterate until approved

---

## Phase 2: Code Implementation

### Step 2.1: Invoke Code Implementation Agent

**Action:** Once architecture is approved, immediately invoke code-implementation agent

```bash
/skill code-implementation "Implement [feature name] according to the approved architecture plan"
```

**Context to pass:**
- Approved architectural decisions
- Components to create/modify
- Interface definitions and contracts
- Implementation phases from architecture
- Success criteria and verification requirements

**What the code-implementation agent does:**
- Creates detailed implementation plan
- Gets user approval on implementation approach
- Systematically implements with checklist tracking
- Writes tests (unit, integration, edge cases)
- Runs diagnostics and verification
- Follows test-driven development where feasible

### Step 2.2: Monitor Implementation Progress

**Track:**
- Checklist completion
- Test coverage
- Diagnostics results
- Any deviations from plan

---

## Phase 3: Code Review

### Step 3.1: Invoke Code Reviewer Agent

**Action:** After implementation completes, automatically invoke code-reviewer

```bash
/skill code-reviewer "Review [feature name] implementation"
```

**What the code-reviewer agent does:**
- Reviews against original architecture and plan
- Checks code quality and standards
- Validates test coverage
- Identifies issues, bugs, or improvements
- Provides actionable feedback

### Step 3.2: Address Review Findings

**If issues found:**
- Fix identified problems
- Re-run tests and diagnostics
- Update documentation if needed

**If review passes:**
- Proceed to explanation phase

---

## Phase 4: High-Level Explanation

### Step 4.1: Invoke Explanation Skill

**Action:** Create comprehensive overview document

```bash
/skill explain "Create high-level overview of [feature name] implementation"
```

### Step 4.2: Generate IMPLEMENTATION_OVERVIEW.md

**Create document with:**

```markdown
# [Feature Name] Implementation Overview

## Executive Summary
[High-level description of what was built]

## Architecture Decisions
### ADR Summary
- **Decision:** [Key architectural choice]
- **Rationale:** [Why this approach]
- **Trade-offs:** [What we gained/lost]

## System Design
### Components
[Diagram or description of major components]

### Data Flow
[How data moves through the system]

### Key Interfaces
[Critical APIs and contracts]

## Implementation Details
### Files Modified/Created
| File | Purpose | Key Changes |
|------|---------|-------------|
| path/to/file | [Description] | [What changed] |

### Design Patterns Used
- [Pattern 1]: [Where and why]
- [Pattern 2]: [Where and why]

### Key Technical Decisions
1. **[Decision]**: [Rationale]
2. **[Decision]**: [Rationale]

## Testing Strategy
### Test Coverage
- Unit Tests: [Coverage %]
- Integration Tests: [What's tested]
- Edge Cases: [Scenarios covered]

### Verification Results
[Summary of test runs]

## Usage Examples
### Basic Usage
```[language]
[Code example]
```

### Advanced Usage
```[language]
[Code example]
```

## Security Considerations
[Security measures implemented]

## Performance Characteristics
[Performance implications and optimizations]

## Future Enhancements
[Potential improvements or next steps]

## References
- Architecture Decision Records
- Related Documentation
- External Resources
```

### Step 4.3: Save Overview Document

**Action:** Write IMPLEMENTATION_OVERVIEW.md to project root or docs folder

---

## Complete Workflow Script

### Automated Execution

**When user says:** "implement coding workflow [feature description]"

**Execute in sequence:**

```typescript
// Phase 1: Architecture
const archResult = await invokeSkill('system-arch', task)
await waitForUserApproval()

// Phase 2: Implementation
const implResult = await invokeSkill('code-implementation', {
  task,
  architecture: archResult,
  requirements: archResult.requirements,
  constraints: archResult.constraints
})

// Phase 3: Review
const reviewResult = await invokeSkill('code-reviewer', {
  implementation: implResult,
  plan: implResult.plan,
  standards: projectStandards
})

if (reviewResult.issues.length > 0) {
  await fixIssues(reviewResult.issues)
  await rerunTests()
}

// Phase 4: Explanation
await invokeSkill('explain', {
  feature: task,
  architecture: archResult,
  implementation: implResult,
  review: reviewResult,
  outputFile: 'IMPLEMENTATION_OVERVIEW.md'
})

console.log('✅ Coding workflow complete!')
console.log('📄 See IMPLEMENTATION_OVERVIEW.md for details')
```

---

## Quality Gates (MANDATORY)

### Gate 1: Architecture Approval
❌ **STOP** if not approved
✅ **PROCEED** if approved

### Gate 2: Implementation Completion
✅ All checklist items completed
✅ All tests passing
✅ Diagnostics clean

### Gate 3: Code Review
✅ No critical issues
✅ All findings addressed
✅ Standards compliance

### Gate 4: Documentation
✅ Overview document created
✅ Examples included
✅ Architecture documented

---

## Usage Examples

### Example 1: New Feature

```
User: "implement coding workflow: Add real-time notification system"
Assistant Flow:
1. Phase 1: System Architecture
   - Analyzes WebSocket, email, SMS architectures
   - Evaluates Message Broker (RabbitMQ vs Kafka vs Redis) options
   - Presents trade-off analysis
   - User approves architecture

2. Phase 2: Implementation  
   - Creates implementation plan with checklist
   - Implements notification service, channels, preferences
   - Writes comprehensive tests
   - Runs diagnostics

3. Phase 3: Code Review
   - Reviews against architectural plan
   - Validates test coverage
   - Checks security (input validation, authentication)
   - Provides feedback, fixes applied

4. Phase 4: Explanation
   - Creates IMPLEMENTATION_OVERVIEW.md
   - Documents architecture decisions
   - Provides usage examples
   - Explains design patterns used
```

### Example 2: System Refactoring

```
User: "implement coding workflow: Refactor authentication system to support OAuth2"

Assistant Flow:
1. Architecture phase analyzes current auth system
2. Proposes OAuth2 integration strategy (Passport.js vs custom)
3. User approves approach
4. Implementation phase refactors systematically  
5. Code review validates security and standards
6. Documentation explains migration path
```

---

## Implementation Notes

### Agent Invocation

**Use Skill tool to invoke each phase:**

```python
# Phase 1
invoke_skill("system-arch", user_request)

# Phase 2 (after approval)
invoke_skill("code-implementation", {
  "task": user_request,
  "context": architecture_result
})

# Phase 3 (after implementation)
invoke_skill("code-reviewer", {
  "implementation": impl_result
})

# Phase 4 (after review)
invoke_skill("explain", {
  "feature": user_request,
  "output": "IMPLEMENTATION_OVERVIEW.md"
})
```

### State Management

**Track workflow state:**

```json
{
  "phase": "architecture|implementation|review|explanation",
  "status": "in_progress|blocked|completed",
  "artifacts": {
    "architecture_adr": "path/to/adr.md",
    "implementation_checklist": [],
    "review_report": {},
    "overview_doc": "IMPLEMENTATION_OVERVIEW.md"
  },
  "approvals": {
    "architecture": false,
    "implementation": false,
    "review": false
  }
}
```

---

## Quality Checklist

Before marking workflow complete, verify:

- [ ] Architecture approved by user
- [ ] Architecture Decision Records created
- [ ] Implementation plan followed
- [ ] All tests passing (unit, integration, edge cases)
- [ ] Code review completed with no critical issues  
- [ ] All review findings addressed
- [ ] IMPLEMENTATION_OVERVIEW.md created
- [ ] Overview includes architecture decisions
- [ ] Overview includes usage examples
- [ ] All code properly documented
- [ ] No technical debt introduced
- [ ] Security considerations addressed
- [ ] Performance implications documented

---

## Failure Handling

### If Architecture Phase Fails
- Gather more requirements
- Consult with user on constraints
- Evaluate alternative approaches
- Do NOT proceed to implementation

### If Implementation Phase Fails
- Review implementation plan
- Break into smaller subtasks
- Consult code-implementation agent documentation
- Consider delegating complex subtasks

### If Review Phase Fails
- Address all critical issues
- Re-run tests after fixes
- Request re-review if needed
- Do NOT proceed to explanation until review passes

### If Explanation Phase Fails
- Review architecture and implementation artifacts
- Consult with tutor agent
- Ensure all context is available
- Regenerate with clearer instructions

---

## Best Practices

**DO:**
- Wait for explicit approval at each gate
- Track progress with checklists
- Document decisions and rationale
- Keep user informed of progress
- Test thoroughly at each phase
- Follow project coding standards
- Create comprehensive documentation

**DON'T:**
- Skip approval gates
- Rush through phases
- Ignore review findings
- Skip testing
- Over-engineer solutions
- Deviate from approved architecture
- Leave documentation incomplete

---

## Success Metrics

**Workflow is successful when:**
- User is satisfied with delivered feature
- All quality gates passed
- Code is production-ready
- Documentation is comprehensive
- Tests provide adequate coverage (>80%)
- No critical security issues
- Performance meets requirements
- Future maintainability is ensured

---

## Troubleshooting

**Problem:** User unsure about architecture options
**Solution:** Provide detailed trade-off analysis with pros/cons

**Problem:** Implementation taking too long
**Solution:** Break into smaller milestones, parallelize work

**Problem:** Review finds many issues
**Solution:** Fix systematically, address root causes, re-review

**Problem:** Documentation unclear
**Solution:** Add more examples, explain design decisions better

---

## Related Skills

- `/system-arch` - Architecture planning only
- `/code-implementation` - Implementation only
- `/code-reviewer` - Review only
- `/explain` - Explanation only

Use `/coding-workflow` when you want ALL phases in sequence.
