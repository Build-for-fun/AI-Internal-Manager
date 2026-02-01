# Cleanup Skill
**Description:** Organize and clean up codebase structure before pushing to GitHub - arrange important code into proper folders, move auxiliary files, and ensure professional repository structure.
**Usage:** /cleanup

**Trigger this skill when:**
- User says "cleanup", "organize codebase", "prepare for GitHub"
- Before making a repository public
- Codebase has grown organically and needs structure
- Files are scattered in root directory
- Preparing for a major release or PR

**Skip for:** Already well-organized repos, single-file projects, documentation-only changes

## Execution Workflow

### Step 1: Analyze Current Structure
**Run these commands in parallel:**
- `find . -maxdepth 2 -type f -name "*.py" | head -30` - Python files
- `find . -maxdepth 2 -type f -name "*.js" -o -name "*.ts" | head -30` - JS/TS files
- `find . -maxdepth 1 -type f` - Root-level files
- `ls -la` - Full root directory listing
- `cat .gitignore 2>/dev/null || echo "No .gitignore"` - Check gitignore

**Identify:**
- Which files are in the root that shouldn't be (non-config code files)
- Existing folder structure patterns
- What language/framework the project uses
- Files that should be gitignored but aren't

### Step 2: Classify Files
**Categorize all root-level and misplaced files:**

| Category | Examples | Target Location |
|----------|----------|-----------------|
| **Core Source** | main.py, app.py, server.py, index.js | `src/` |
| **Tests** | test_*.py, *.test.js, *_spec.rb | `tests/` |
| **Examples** | example_*.py, demo_*.js | `examples/` |
| **Documentation** | *.md (except README), docs | `docs/` |
| **Config (keep root)** | package.json, pyproject.toml, .env.example, config.json | `.` (root) |
| **Scripts** | build.sh, deploy.sh, run_*.sh | `scripts/` |
| **Temporary/Debug** | debug.log, *.tmp, __pycache__ | DELETE or gitignore |
| **Personal/Local** | notes.txt, todo.txt, scratch.* | `personal/` (gitignored) |

**Answer these questions:**
1. What's the main entry point of the application?
2. Are there files that look like experiments/scratch work?
3. Are there any sensitive files that shouldn't be committed?
4. What's the existing naming convention?

### Step 3: Present Cleanup Plan (DO NOT EXECUTE YET)
**Show user a clear plan before making changes:**

```markdown
## Proposed Codebase Cleanup

### Files to Move
| File | From | To | Reason |
|------|------|-----|--------|
| example_usage.py | root | examples/ | Example code |
| test_flow.py | root | tests/ | Test file |

### Files to Delete
| File | Reason |
|------|--------|
| debug.log | Debug artifact |
| .DS_Store | OS file |

### Folders to Create
- `src/` - Core application code
- `tests/` - Test files
- `examples/` - Usage examples
- `scripts/` - Build/deploy scripts

### Files to Add to .gitignore
- `*.log`
- `__pycache__/`
- `.env`
- `personal/`

### Files to Keep in Root (Config)
- README.md
- requirements.txt / package.json
- .gitignore
- config.json.example
```

**ASK USER:** "Does this plan look good? Reply 'yes' to proceed or tell me what to change."

### Step 4: Execute Cleanup (After User Approval)
**Create directories first:**
```bash
mkdir -p src tests examples docs scripts personal
```

**Move files using git mv (preserves history):**
```bash
git mv source_file.py src/
git mv test_*.py tests/
git mv example_*.py examples/
```

**Update .gitignore:**
Add necessary entries for:
- `personal/` (personal notes, scratch files)
- `*.log`
- `__pycache__/`
- `.env`
- `*.pyc`
- `.DS_Store`
- `node_modules/` (if JS project)

**Clean up ignored files:**
```bash
# Remove files that should be gitignored
git rm --cached <file> # For tracked files that should be ignored
rm -rf __pycache__/    # Remove Python cache
rm -f *.log            # Remove log files
```

### Step 5: Update Imports (Critical)
**After moving files, fix broken imports:**

1. **Search for broken imports:**
   - Use grep to find imports referencing moved files
   - Check `from file import` and `import file` patterns

2. **Update import paths:**
   - If `utils.py` moved to `src/utils.py`, update imports
   - Consider adding `__init__.py` files for proper packages

3. **Verify nothing is broken:**
   ```bash
   python -m py_compile src/*.py  # Python syntax check
   # OR
   npx tsc --noEmit              # TypeScript check
   ```

### Step 6: Final Verification
**Run these checks:**
```bash
# Check git status
git status

# Verify no untracked important files
git status --porcelain | grep "^??"

# Run tests if they exist
pytest tests/ 2>/dev/null || npm test 2>/dev/null || echo "No test runner found"

# Check for broken imports (Python)
python -c "import sys; sys.path.insert(0, 'src'); import main" 2>&1 || echo "Check imports manually"
```

### Step 7: Present Summary to User
**Tell the user:**
1. How many files were moved
2. What folders were created
3. What was added to .gitignore
4. Any manual fixes needed (broken imports, etc.)

**Suggest next steps:**
- Review changes with `git diff --stat`
- Run full test suite
- Update README.md if structure changed significantly
- Commit with message: `chore: reorganize codebase structure`

## Standard Project Structure Templates

### Python Project
```
project/
├── src/
│   ├── __init__.py
│   ├── main.py          # Entry point
│   ├── module1.py
│   └── utils/
├── tests/
│   ├── __init__.py
│   ├── test_main.py
│   └── conftest.py
├── examples/
├── docs/
├── scripts/
├── personal/            # gitignored
├── .gitignore
├── README.md
├── requirements.txt
└── pyproject.toml
```

### Node.js/TypeScript Project
```
project/
├── src/
│   ├── index.ts
│   ├── routes/
│   └── utils/
├── tests/
├── examples/
├── docs/
├── scripts/
├── personal/            # gitignored
├── .gitignore
├── README.md
├── package.json
└── tsconfig.json
```

## Quality Guidelines

**ALWAYS:**
- Use `git mv` to preserve history (not `mv`)
- Ask user before deleting ANY file
- Back up before bulk operations
- Update imports after moving files
- Add `__init__.py` for Python packages
- Keep config files in root
- Create `.gitignore` if missing

**NEVER:**
- Delete files without asking
- Move files without showing plan first
- Break imports by moving without updating
- Commit .env, credentials, or API keys
- Move files already in correct location
- Create overly deep nesting (max 3 levels)

## Important Notes

- **Always show plan first** - Never execute moves without user approval
- **Preserve git history** - Use `git mv` instead of `mv`
- **Check imports** - Moving Python files breaks imports; must update
- **Personal folder** - Create `personal/` (gitignored) for scratch work
- **Minimal disruption** - If project works, don't over-organize
- **Follow existing conventions** - If project uses `lib/` instead of `src/`, follow that

## Common Cleanup Tasks Checklist

- [ ] Remove `__pycache__/` directories
- [ ] Remove `.pyc` files
- [ ] Remove `.DS_Store` files
- [ ] Remove `node_modules/` from git (if accidentally committed)
- [ ] Remove `.env` with secrets (replace with `.env.example`)
- [ ] Remove debug/log files
- [ ] Add comprehensive `.gitignore`
- [ ] Move test files to `tests/`
- [ ] Move example files to `examples/`
- [ ] Ensure README.md exists and is up to date
- [ ] Remove commented-out code blocks
- [ ] Remove unused imports (use linter)
