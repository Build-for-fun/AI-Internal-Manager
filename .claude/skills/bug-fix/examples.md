# Bug Fix Examples
**Description:** Collection of real-world bug patterns and how they were successfully resolved. Reference this when encountering similar issues.
**Usage:** Reference from `/bug-fix` when identifying root causes

---

## Quick Reference: Error Pattern Recognition

| Error Message | Root Cause | Fix Strategy |
|---------------|------------|--------------|
| `cannot import name 'X' from 'module'` | X not exported in `__init__.py` | Add to `__init__.py` exports |
| `No module named 'X'` | Wrong import path or missing file | Fix path or create file |
| `object.__init__() takes exactly one argument` | Parent class fallback to `object` | Fix conditional import or super() call |
| `'X' is possibly unbound` | Import inside try/except failed | Add fallback assignment before try block |
| `Argument to class must be a base class` | Class inheriting from non-class | Fix the parent class import |

---

## Example 1: The LearningRouter Import Chain Bug

### Error
```
TypeError: object.__init__() takes exactly one argument (the instance to initialize)
```

### How It Was Found
1. User ran `python src/cli.py`
2. Error occurred during MCP initialization
3. Traced through: CLI → MasterMCPServer → LearningRouter → AIRouter

### Root Cause Analysis

**The Chain:**
```
routing/__init__.py didn't export AIRouter
    → learning_router's "from .ai_router import AIRouter" worked
    → But src/__init__.py's "from .routing import AIRouter" failed
    → LearningRouter inherited from fallback `object` instead of AIRouter
    → super().__init__(model, provider) called on object → TypeError
```

**The Problematic Code:**
```python
# routing/__init__.py - MISSING AIRouter export
from .query_analyzer import QueryAnalyzer
from .learning_router import LearningRouter
# AIRouter NOT exported!

# learning_router.py
try:
    from .ai_router import AIRouter
except ImportError:
    AIRouter = object  # Fallback triggered in some contexts

class LearningRouter(AIRouter):
    def __init__(self, model, provider):
        super().__init__(model, provider)  # FAILS when AIRouter is object
```

### Fix Applied

**Step 1:** Added AIRouter to routing/__init__.py exports
```python
from .ai_router import AIRouter
__all__ = [..., "AIRouter"]
```

**Step 2:** Added multiple import path fallbacks
```python
try:
    from .ai_router import AIRouter
except ImportError:
    try:
        from ai_router import AIRouter
    except ImportError:
        AIRouter = object
```

**Step 3:** Guarded super().__init__() call
```python
def __init__(self, model, provider):
    if AIRouter is not object:
        super().__init__(model, provider)
    else:
        self.model = model
        self.provider = provider
        self.is_available = False
```

### Verification Commands Used
```bash
python -c "from src.routing import AIRouter; print('OK')"
python -c "from src import MCPCLI; print('OK')"
python src/cli.py  # Full integration test
```

### Key Learnings
- Import errors cascade through module chains
- Different import contexts can resolve the same module differently
- Always check `__init__.py` exports when "cannot import name" occurs
- Conditional imports with class inheritance need guarded super() calls

---

## Example 2: Wrong Relative Import Path

### Error
```
ModuleNotFoundError: No module named 'src.simple_multi_mcp'
```

### How It Was Found
1. CLI showed "No multi-MCP handler available" 
2. Checked import in master_mcp_server.py
3. Found import path didn't match actual file location

### Root Cause
```python
# master_mcp_server.py tried:
from src.simple_multi_mcp import SimpleMultiMCPHandler

# But file was at:
src/utils/simple_multi_mcp.py
```

### Fix Applied
```python
# Changed to correct relative import:
from ..utils.simple_multi_mcp import SimpleMultiMCPHandler
```

### Diagnosis Command
```bash
find . -name "simple_multi_mcp.py"
# Output: ./src/utils/simple_multi_mcp.py
```

---

## Adding New Examples

When you successfully fix a bug, add it here with:

1. **Error** - Exact error message
2. **How It Was Found** - Steps to reproduce/discover
3. **Root Cause Analysis** - Why it happened
4. **Fix Applied** - Code changes made
5. **Verification Commands** - How you confirmed the fix
6. **Key Learnings** - What to remember for next time
