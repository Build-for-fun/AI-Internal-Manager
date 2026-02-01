# Integration Test Validator Skill
**Description:** Comprehensive testing validation - unit, integration, and system tests. Verify code works correctly and integrates properly with existing systems.
**Usage:** /integration-test-validator [feature or files to test]

**Trigger this skill when:**
- Code has been reviewed and approved
- User says "test this", "validate the implementation"
- After code-reviewer skill approves changes
- Before deployment of significant features
- User wants comprehensive test coverage assessment

**Skip for:** Writing code (use code-architect), reviewing code (use code-reviewer), explaining code (use tutor)

---

## Phase 1: Test Planning

### Step 1.1: Analyze Code Under Test

| Analysis | Purpose |
|----------|---------|
| Entry points | What functions/methods to test |
| Integration points | External dependencies, APIs, databases |
| Data flow | How data moves through the system |
| Edge cases | Boundary conditions, error states |

### Step 1.2: Identify Test Scenarios

**Unit Test Scenarios:**
- Valid inputs → expected outputs
- Edge cases: empty, null, boundary values
- Error handling: invalid types, out-of-range
- All code paths exercised

**Integration Test Scenarios:**
- Component interactions
- API contract validation
- Database operations (CRUD, transactions)
- External service integrations
- Authentication/authorization flows

**System Test Scenarios:**
- End-to-end user workflows
- Full application context
- Regression checks
- Concurrent operations
- Load scenarios (if applicable)

---

## Phase 2: Test Execution

### 2.1: Unit Tests

**Checklist:**
- [ ] Test each function with valid inputs
- [ ] Test edge cases (empty, null, boundary)
- [ ] Test error handling paths
- [ ] Verify return types match expected
- [ ] Check side effects are correct
- [ ] Test performance-critical code

**Arrange-Act-Assert Pattern:**
```
1. ARRANGE: Set up test data and preconditions
2. ACT: Execute the function under test
3. ASSERT: Verify the outcome matches expected
```

### 2.2: Integration Tests

**Checklist:**
- [ ] Test data flow between components
- [ ] Verify API contracts (input/output schemas)
- [ ] Test database operations with rollback
- [ ] Validate external service error handling
- [ ] Check state management across components
- [ ] Test authentication flows

### 2.3: System Tests

**Checklist:**
- [ ] Complete user workflow tests
- [ ] Regression tests on existing features
- [ ] Concurrent operation tests
- [ ] Error recovery scenarios
- [ ] Logging and monitoring verification

---

## Phase 3: Security Testing

### Security Checklist

| Category | Tests |
|----------|-------|
| **Input Validation** | SQL injection, XSS, command injection |
| **Authentication** | Bypass attempts, session handling |
| **Authorization** | Privilege escalation, access control |
| **Data Protection** | Sensitive data exposure, encryption |
| **Error Handling** | Information leakage in errors |

---

## Phase 4: Test Results

### Results Format

```markdown
## Test Execution Report

### Summary
| Category | Total | Passed | Failed | Skipped |
|----------|-------|--------|--------|---------|
| Unit | [n] | [n] | [n] | [n] |
| Integration | [n] | [n] | [n] | [n] |
| System | [n] | [n] | [n] | [n] |
| Security | [n] | [n] | [n] | [n] |

### Overall Status
[ ] READY FOR DEPLOYMENT - All tests pass
[ ] ISSUES FOUND - Failures need attention
[ ] CRITICAL FAILURES - Blocking issues

---

### Unit Test Results

#### Passed
- [checkmark] `function_name` - [description]

#### Failed
- [x] `function_name` - [failure reason]
  - **Expected:** [value]
  - **Actual:** [value]
  - **Fix:** [recommendation]

---

### Integration Test Results
[Same format as unit tests]

---

### System Test Results
[Same format as unit tests]

---

### Security Test Results
[Same format as unit tests]

---

### Issues Identified

#### Critical (Blocking)
| Issue | Location | Impact | Recommendation |
|-------|----------|--------|----------------|
| [Issue] | `file:line` | [Impact] | [Fix] |

#### High (Should Fix)
[Same format]

#### Medium (Recommended)
[Same format]

---

### Regression Check
[ ] No regressions detected
[ ] Potential regressions found:
    - [Description of regression]

---

### Final Recommendation
[Clear statement: deploy / fix issues first / major rework needed]
```

---

## Phase 5: Issue Resolution Support

### For Failed Tests:

1. **Identify Root Cause**
   - Is it a code bug or test bug?
   - Is the test correct about expected behavior?

2. **Provide Fix Guidance**
   ```markdown
   **Test Failure:** [test name]
   **Root Cause:** [why it failed]
   **Recommended Fix:**
   ```[code]
   [specific code change]
   ```
   ```

3. **Re-test After Fixes**
   - Verify the fix works
   - Check for new regressions

---

## Testing Standards

### Test Quality Criteria

| Criterion | Requirement |
|-----------|-------------|
| **Independence** | Each test runs independently |
| **Repeatability** | Same result every run |
| **Clarity** | Clear what's being tested |
| **Speed** | Unit tests are fast |
| **Coverage** | Critical paths covered |

### Test Data Guidelines

- Use realistic, representative data
- Include edge cases and boundaries
- Don't use production data with PII
- Clean up test data after tests

---

## Quality Guidelines

**ALWAYS:**
- Test all critical code paths
- Include edge cases and error scenarios
- Verify security-sensitive operations
- Check for regressions
- Provide actionable failure analysis
- Clean up test artifacts

**NEVER:**
- Skip security tests
- Ignore failed tests
- Use flaky test data
- Leave test data in production systems
- Approve with critical test failures

---

## Escalation Triggers

**Consult Oracle if:**
- Complex test architecture decisions
- Unclear expected behavior
- Performance testing guidance needed

**Ask User if:**
- Expected behavior is ambiguous
- Test data requirements unclear
- Acceptance criteria not defined
