# Test Cases Skill
**Description:** Run test cases for debugging purposes, including full test suites or targeted tests for specific functions/code sections.
**Usage:** /test-cases [optional: function_name or file_path]

**Trigger this skill when:**
- User says "run tests", "test this", "debug with tests"
- User wants to verify a specific function works correctly
- User says "test this function", "check if X works"
- After implementing a feature that needs verification
- Debugging and need to isolate behavior
- User provides code snippet to test

**Skip for:** Code reviews without execution, documentation tasks, pure refactoring without behavior change

## Execution Workflow

### Step 0: Detect Test Mode
**Parse user intent:**

| User Request | Mode | Action |
|--------------|------|--------|
| "run tests", "run test suite" | **Full Suite** | Run all project tests |
| "test function X", "test this function" | **Targeted** | Test specific function |
| "test this code", "check if this works" + code snippet | **Snippet** | Create and run ephemeral test |
| "test file X", "test module Y" | **File/Module** | Run tests for specific file |

### Step 1: Detect Project Test Framework
**Run these commands in parallel:**
```bash
# Python projects
ls -la pytest.ini pyproject.toml setup.cfg conftest.py 2>/dev/null
cat pyproject.toml 2>/dev/null | grep -A5 "\[tool.pytest"

# JavaScript/TypeScript projects
ls -la jest.config.* vitest.config.* 2>/dev/null
cat package.json 2>/dev/null | grep -E "(jest|vitest|mocha|ava)"

# Go projects
ls -la *_test.go 2>/dev/null | head -5

# Check for test directories
ls -d tests/ test/ __tests__/ spec/ 2>/dev/null
```

**Identify:**
- Test framework (pytest, jest, vitest, go test, etc.)
- Test directory location
- Configuration files present
- Coverage settings

### Step 2A: Full Suite Mode
**Run the appropriate command:**

| Framework | Command |
|-----------|---------|
| pytest | `python -m pytest -v --tb=short` |
| pytest (with coverage) | `python -m pytest -v --cov=src --tb=short` |
| jest | `npm test` or `npx jest --verbose` |
| vitest | `npx vitest run` |
| go test | `go test -v ./...` |
| cargo | `cargo test` |

**Capture and present:**
- Total tests run
- Passed / Failed / Skipped counts
- Failed test names and error messages
- Stack traces for failures

### Step 2B: Targeted Function Mode
**When user wants to test a specific function:**

1. **Locate the function:**
   ```bash
   # Find function definition
   grep -rn "def function_name" --include="*.py"
   grep -rn "function function_name\|const function_name" --include="*.js" --include="*.ts"
   ```

2. **Find existing tests for it:**
   ```bash
   grep -rn "test.*function_name\|function_name" tests/ --include="*.py"
   grep -rn "describe.*function_name\|it.*function_name" __tests__/ --include="*.test.*"
   ```

3. **If tests exist, run only those:**
   ```bash
   # pytest - run specific test
   python -m pytest tests/test_module.py::test_function_name -v

   # pytest - run tests matching name
   python -m pytest -k "function_name" -v

   # jest - run specific test
   npx jest --testNamePattern="function_name"

   # go - run specific test
   go test -v -run TestFunctionName
   ```

4. **If NO tests exist, offer to create one:**
   - Read the function implementation
   - Generate a minimal test case
   - Ask user to confirm before creating

### Step 2C: Snippet Test Mode
**When user provides code to test or wants to verify behavior:**

1. **Create ephemeral test file:**
   ```python
   # For Python - create tests/test_debug_snippet.py
   """Ephemeral test for debugging - safe to delete"""
   import pytest
   
   # Import from user's module if needed
   # from src.module import function_to_test
   
   def test_snippet():
       # User's code/assertion here
       result = <user_code>
       assert result == expected, f"Got {result}"
   ```

2. **Run the ephemeral test:**
   ```bash
   python -m pytest tests/test_debug_snippet.py -v -s
   ```

3. **Show output with print statements captured:**
   - Use `-s` flag to show prints
   - Show assertion details on failure
   - Display local variables if test fails

4. **Clean up (ask user):**
   - Offer to keep or delete the ephemeral test
   - If useful, offer to rename to permanent test

### Step 3: Analyze Failures
**When tests fail, provide:**

| Information | How to Get |
|-------------|------------|
| Error message | Parse test output |
| Stack trace | Show relevant lines only |
| Failed assertion | Show expected vs actual |
| Related code | Read the failing function |
| Suggested fix | Analyze error pattern |

**Common failure patterns:**

| Error Pattern | Likely Cause | Suggestion |
|---------------|--------------|------------|
| `AssertionError: X != Y` | Logic error | Compare expected vs actual |
| `ImportError` | Module not found | Check import paths, __init__.py |
| `AttributeError` | Missing attribute | Check object structure |
| `TypeError` | Wrong argument types | Check function signature |
| `KeyError` | Missing dict key | Check data structure |
| `TimeoutError` | Async/slow test | Add timeout, mock slow ops |

### Step 4: Present Results
**Format output clearly:**

```markdown
## Test Results

**Mode:** [Full Suite / Targeted / Snippet]
**Framework:** pytest v8.x
**Duration:** 2.3s

### Summary
- **Passed:** 15
- **Failed:** 2
- **Skipped:** 1

### Failed Tests

#### test_user_authentication
**File:** tests/test_auth.py:45
**Error:** AssertionError: expected True, got False
**Relevant Code:**
```python
def test_user_authentication():
    result = authenticate("user", "wrong_pass")
    assert result == True  # <-- Fails here
```
**Suggestion:** Check password validation logic in `src/auth.py:23`

---

### Next Steps
- [ ] Fix `test_user_authentication` - check auth logic
- [ ] Re-run with `pytest tests/test_auth.py -v`
```

## Quick Test Commands Reference

### Python (pytest)
```bash
# Run all tests
python -m pytest -v

# Run specific file
python -m pytest tests/test_file.py -v

# Run specific test function
python -m pytest tests/test_file.py::test_function -v

# Run tests matching pattern
python -m pytest -k "auth" -v

# Run with print output visible
python -m pytest -v -s

# Run with coverage
python -m pytest --cov=src --cov-report=term-missing

# Run failed tests only (from last run)
python -m pytest --lf -v

# Stop on first failure
python -m pytest -x -v

# Show local variables on failure
python -m pytest -v --tb=long --showlocals
```

### JavaScript (Jest/Vitest)
```bash
# Jest - all tests
npx jest --verbose

# Jest - specific file
npx jest tests/auth.test.js --verbose

# Jest - matching pattern
npx jest --testNamePattern="authentication"

# Jest - watch mode
npx jest --watch

# Vitest - all tests
npx vitest run

# Vitest - specific file
npx vitest run tests/auth.test.ts

# Vitest - watch mode
npx vitest
```

### Go
```bash
# All tests
go test -v ./...

# Specific package
go test -v ./pkg/auth

# Specific test function
go test -v -run TestAuthentication

# With coverage
go test -v -cover ./...

# Race detection
go test -v -race ./...
```

## Creating Quick Debug Tests

### Python - Inline Debug Test
```python
# tests/test_debug.py - DELETE AFTER DEBUGGING
"""Quick debug test - delete when done"""
import pytest

def test_debug_function():
    """Test the specific behavior I'm debugging"""
    from src.module import my_function
    
    # Test case 1: Basic input
    result = my_function("input")
    print(f"Result: {result}")  # Will show with -s flag
    assert result == "expected"
    
    # Test case 2: Edge case
    result2 = my_function("")
    assert result2 is None, f"Expected None for empty input, got {result2}"
```

### Python - Test Specific Function Behavior
```python
# Test to understand function behavior
def test_understand_behavior():
    """Exploratory test to understand how X works"""
    from src.module import mysterious_function
    
    inputs = ["a", "b", "", None, 123, [], {}]
    for inp in inputs:
        try:
            result = mysterious_function(inp)
            print(f"Input: {inp!r} -> Output: {result!r}")
        except Exception as e:
            print(f"Input: {inp!r} -> Exception: {e}")
```

## Quality Guidelines

**ALWAYS:**
- Show clear pass/fail summary first
- Include file:line references for failures
- Provide actionable suggestions for failures
- Clean up ephemeral test files after use
- Use verbose mode (-v) for clarity
- Capture print statements (-s) for debugging

**NEVER:**
- Run tests that modify production data
- Skip showing error details
- Leave ephemeral test files without asking
- Run the entire suite when user asks for specific test
- Ignore test framework configuration

## Important Notes

- **Ephemeral tests:** Always mark debug tests clearly with comments like "DELETE AFTER DEBUGGING"
- **Isolation:** Use pytest fixtures or setup/teardown for clean test state
- **Mocking:** Suggest mocks for external services (API calls, DB, etc.)
- **Speed:** For quick checks, use `-x` to stop on first failure
- **Verbosity:** Default to verbose output; debugging needs details
- **Coverage:** Only run coverage for full suite, not targeted tests
