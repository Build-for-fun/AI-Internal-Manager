# Document-Changes Skill
**Description:** Automatically analyze recent code changes and generate high-level documentation explaining what changed and why.
**Usage:** /document-changes

**Trigger this skill automatically after:**
- Writing 100+ lines of new code
- Modifying core functionality or architecture
- Adding new modules, classes, or major features
- Refactoring significant portions of code
- Changing API interfaces or data flows

**Skip for:** Minor bug fixes, formatting changes, config tweaks, simple tests

## Execution Workflow

### Step 1: Analyze Git Changes
**Run these commands in parallel:**
- `git status` - See which files are modified/added
- `git diff --stat` - Get high-level change statistics
- `git diff` - Review actual code changes

**Identify:**
- Which files had the most significant changes (focus on top 5)
- What type of change: new feature, refactor, bug fix, or architectural change
- Which components/modules were affected

### Step 2: Read and Understand Key Files
**Read the most modified files** (top 3-5 based on git diff):
- Use the Read tool to examine changed files
- Focus on understanding the WHAT and WHY, not line-by-line details
- Identify new classes, functions, or architectural patterns
- Note important design decisions or trade-offs

**Answer these questions:**
1. What problem does this code solve?
2. How does it integrate with existing code?
3. What are the critical functions/classes added or modified?
4. Are there any non-obvious design decisions?

### Step 3: Generate Documentation File
**Use the Write tool to create:** `docs/changes/YYYY-MM-DD_<feature-name>.md`

First, create the docs/changes directory if it doesn't exist using Bash.

**Write documentation using this structure:**

```markdown
# [Feature/Change Name]

**Date:** YYYY-MM-DD
**Files Modified:** [List 3-5 most important files]
**Impact:** [High/Medium/Low]

## Overview
2-3 sentences: What changed and why?

## Key Changes

### [Component/Module Name]
- **What changed:** [Brief description]
- **Why:** [Rationale]
- **Important detail:** [Critical implementation note if any]

## Architecture Impact
How this affects the overall system. New patterns introduced?

## Important Code Sections
- `filename.py:line` - Why this code matters
- `filename.py:line` - Why this code matters

## Future Considerations
Technical debt, TODOs, or future improvements to consider.
```

### Step 4: Present Summary to User
**Tell the user:**
1. What type of change was documented (feature/refactor/fix)
2. How many files were modified
3. Where the documentation was saved
4. Key architectural insights discovered

**Ask if they want to:**
- Update `CLAUDE.md` if development patterns changed
- Update `README.md` if user-facing functionality changed
- Create additional architecture documentation

## Quality Guidelines

**ALWAYS:**
- Explain the problem and solution before implementation details
- Focus on non-obvious decisions and important patterns
- Include `filename.py:line` references for critical code
- Write for programmers - assume intelligence, focus on "why"
- Keep it concise - 2-3 sentences per section maximum

**NEVER:**
- Explain line-by-line what the code does
- Document obvious implementation details
- List every parameter or function signature
- Write more than 1 page total for a single change

**Example of good high-level documentation:**
> The AIRouter now uses a three-tier fallback system: LLM-powered analysis,
> keyword matching, then direct tool match. This ensures graceful degradation
> when API keys are missing. Key implementation in `ai_router.py:89` caches
> MCP capabilities to reduce latency by ~200ms per query.

**Example of poor documentation:**
> We changed the AIRouter class. It has a method `route_query()` that takes
> a query string. The method checks for an API key on line 45, calls the LLM
> on line 52, and if that fails tries keyword matching on line 67...

## Important Notes

- **File naming:** Use `YYYY-MM-DD_feature-name.md` format (e.g., `2026-01-05_batch-processing.md`)
- **Location:** Always save to `docs/changes/` directory
- **Length:** Keep documentation under 1 page - focus on what matters
- **Audience:** Write for future you and other developers who need to understand the change quickly
