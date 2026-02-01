# System Architecture Skill
**Description:** Analyze system architecture, evaluate trade-offs, and provide comprehensive planning for architectural changes.
**Usage:** /system-arch [architecture question or proposed change]

**Trigger this skill when:**
- Planning major system architecture changes
- Evaluating new architectural patterns
- Assessing impact of architectural decisions
- Designing new system components
- Refactoring existing architecture
- User asks "should we use X pattern?", "how should we structure Y?"

**Skip for:** Code implementation (use code-architect), code review (use code-reviewer), testing (use integration-test-validator)

---

## Phase 1: Context Gathering

### Step 1.1: Understand Current State

| Input | How to Gather |
|-------|---------------|
| Current architecture | Fire `explore` agent, read docs |
| Existing patterns | Search for similar components |
| Dependencies | Check imports, configs |
| Constraints | Technical, business, resource |

### Step 1.2: Understand Proposed Change

| Question | Purpose |
|----------|---------|
| What is the goal? | Define success criteria |
| What components affected? | Scope the impact |
| What are the requirements? | Functional & non-functional |
| What constraints exist? | Identify limitations |

---

## Phase 2: Impact Assessment

### 2.1: System Structure Impact

**Component Analysis:**
- [ ] New components needed
- [ ] Existing components modified
- [ ] Components to deprecate
- [ ] Dependency changes

**Data Flow Changes:**
- [ ] New data paths
- [ ] Modified interfaces
- [ ] API changes
- [ ] Database schema changes

### 2.2: Quality Attribute Analysis

| Attribute | Impact | Assessment |
|-----------|--------|------------|
| **Performance** | [+/-/neutral] | [Details] |
| **Scalability** | [+/-/neutral] | [Details] |
| **Reliability** | [+/-/neutral] | [Details] |
| **Maintainability** | [+/-/neutral] | [Details] |
| **Security** | [+/-/neutral] | [Details] |
| **Cost** | [+/-/neutral] | [Details] |

### 2.3: Risk Assessment

| Risk Category | Risks Identified | Mitigation |
|---------------|------------------|------------|
| **Technical** | [List] | [Approaches] |
| **Operational** | [List] | [Approaches] |
| **Security** | [List] | [Approaches] |
| **Performance** | [List] | [Approaches] |

---

## Phase 3: Trade-off Analysis

### Trade-off Matrix

```markdown
## Trade-off Analysis: [Change Name]

### Option A: [Approach Name]
| Aspect | Positive | Negative |
|--------|----------|----------|
| Performance | [Benefits] | [Costs] |
| Complexity | [Benefits] | [Costs] |
| Maintainability | [Benefits] | [Costs] |
| Time to Implement | [Benefits] | [Costs] |

### Option B: [Approach Name]
[Same format]

### Comparison Summary
| Criterion | Option A | Option B | Winner |
|-----------|----------|----------|--------|
| Performance | [Score] | [Score] | [A/B] |
| Complexity | [Score] | [Score] | [A/B] |
| Time | [Score] | [Score] | [A/B] |
| Risk | [Score] | [Score] | [A/B] |

### Recommendation
[Which option and why]
```

---

## Phase 4: Common Patterns Reference

### Microservices
| Pros | Cons | Best For |
|------|------|----------|
| Independent deployment | Increased complexity | Large teams |
| Technology diversity | Distributed challenges | High scalability needs |
| Fault isolation | Service discovery | Diverse tech stacks |

### Event-Driven
| Pros | Cons | Best For |
|------|------|----------|
| Loose coupling | Eventual consistency | High throughput |
| Async processing | Debugging challenges | Real-time needs |
| Scalable pipelines | Message broker deps | Decoupled workflows |

### CQRS
| Pros | Cons | Best For |
|------|------|----------|
| Optimized read/write | Increased complexity | Complex domains |
| Scalable queries | Dual model maintenance | High read/write ratios |
| Domain clarity | Learning curve | Event sourcing |

### Serverless
| Pros | Cons | Best For |
|------|------|----------|
| Auto scaling | Cold start latency | Variable workloads |
| Pay-per-use | Vendor lock-in | Cost-sensitive |
| Less infra mgmt | Limited customization | Rapid prototyping |

---

## Phase 5: Implementation Planning

### Planning Template

```markdown
## Architecture Change: [Name]

### Current State
- **Architecture:** [Description]
- **Components:** [List]
- **Data Flow:** [Description]

### Proposed Changes
- **New Components:** [List with purpose]
- **Modified Components:** [List with changes]
- **Removed Components:** [List with reason]
- **Interface Changes:** [API modifications]

### Implementation Phases

#### Phase 1: Foundation (Week 1-2)
- [ ] [Task 1]
- [ ] [Task 2]

#### Phase 2: Core Changes (Week 3-4)
- [ ] [Task 1]
- [ ] [Task 2]

#### Phase 3: Integration (Week 5-6)
- [ ] [Task 1]
- [ ] [Task 2]

#### Phase 4: Validation (Week 7-8)
- [ ] [Task 1]
- [ ] [Task 2]

### Rollback Strategy
- **Quick Rollback:** [Immediate steps]
- **Gradual Rollback:** [Phased approach]
- **Data Migration:** [Cleanup procedures]

### Success Metrics
| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| [Metric 1] | [Value] | [Value] | [Method] |
| [Metric 2] | [Value] | [Value] | [Method] |

### Dependencies
- [External dependency 1]
- [Team dependency 1]

### Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| [Risk 1] | [H/M/L] | [H/M/L] | [Approach] |
```

---

## Phase 6: Decision Output

### Architecture Decision Record (ADR)

```markdown
## ADR: [Title]

### Status
[Proposed / Accepted / Deprecated / Superseded]

### Context
[What is the issue we're seeing that motivates this decision?]

### Decision
[What is the change we're proposing/doing?]

### Consequences
**Positive:**
- [Consequence 1]

**Negative:**
- [Consequence 1]

**Neutral:**
- [Consequence 1]

### Alternatives Considered
1. [Alternative 1] - Rejected because [reason]
2. [Alternative 2] - Rejected because [reason]
```

---

## Phase 7: Transition to Implementation (MANDATORY)

**After architecture is approved by user:**

1. **IMMEDIATELY invoke the code-implementation skill**
   ```
   /code-implementation "Implement [architecture name] as specified in the approved architecture plan"
   ```

2. **Pass the following context to code-implementation:**
   - Architecture decision made
   - Components to create/modify
   - Interface definitions
   - Implementation phases from the plan
   - Success metrics and verification criteria

3. **Ensure code-implementation includes:**
   - Test cases for all new components
   - Integration tests for modified interfaces
   - Verification against architecture requirements

**DO NOT:**
- Leave architecture as a plan-only document
- Wait for user to explicitly ask for implementation
- Skip transition to implementation phase

**Example:**
```
User: "Looks good, let's proceed with Option A"
Assistant: "Great! I'll now transition to implementation. Invoking /code-implementation..."
```

---

## Quality Guidelines

**ALWAYS:**
- Consider multiple options before recommending
- Quantify trade-offs where possible
- Think about operational impact
- Consider security implications
- Provide rollback strategy
- Define success metrics

**NEVER:**
- Recommend without trade-off analysis
- Ignore non-functional requirements
- Skip security considerations
- Forget about operational complexity
- Assume one-size-fits-all

---

## Risk Thresholds

| Risk Level | Implementation Time | Components Affected | Reversibility |
|------------|---------------------|---------------------|---------------|
| **Low** | < 2 weeks | < 3 components | Easily reversible |
| **Medium** | 2-8 weeks | 3-10 components | Mostly reversible |
| **High** | > 8 weeks | > 10 components | Complex rollback |

---

## Escalation Triggers

**Consult Oracle if:**
- Multiple viable options with unclear winner
- Unfamiliar architectural patterns
- Security or performance concerns
- Cross-cutting concerns affect many systems

**Ask User if:**
- Business constraints unclear
- Resource availability unknown
- Timeline requirements ambiguous
- Stakeholder priorities needed
