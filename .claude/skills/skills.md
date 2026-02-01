# Skills Directory

Skills are reusable workflows that guide the AI agent through complex, multi-step tasks. They capture institutional knowledge and best practices.

## Structure

```
skills/
├── skills.md                      ← You are here
├── bug-fix/                       ← Systematic bug fixing
│   ├── SKILL.md
│   └── examples.md
├── code-architect/                ← Plan + approval workflow
│   └── SKILL.md
├── code-implementation/           ← Plan → code → review
│   └── SKILL.md
├── code-reviewer/                 ← Review against standards
│   └── SKILL.md
├── document-changes/
│   └── SKILL.md
├── explain/
│   └── SKILL.md
├── integration-test-validator/    ← Unit/integration/system tests
│   └── SKILL.md
├── investigator/                  ← Deep investigation → approve → fix
│   └── SKILL.md
├── receiving-code-review/
│   └── SKILL.md
├── system-arch/                   ← Architecture analysis
│   └── SKILL.md
├── tutor/                         ← Code explanations
│   └── SKILL.md
├── cleanup.md                     ← Single-file legacy skill
├── technical-blog.md
└── test-cases.md
```

## Creating New Skills

**New skills should be created as folders**, not single files. This allows for:
- Supporting documentation
- Examples
- Templates
- Future expansion

### Folder Structure for New Skills

```
skill-name/
├── SKILL.md       ← Main skill file (required)
├── examples.md    ← Real-world examples (optional)
├── templates/     ← Reusable templates (optional)
└── assets/        ← Diagrams, images (optional)
```

### Skill File Format

```markdown
# Skill Name
**Description:** One-line description of what this skill does.
**Usage:** /skill-name [arguments]

**Trigger this skill when:**
- Condition 1
- Condition 2

**Skip for:** Cases where this skill shouldn't be used

## Execution Workflow

### Phase 1: [Name]
[Steps]

### Phase 2: [Name]
[Steps]

## Quality Guidelines

**ALWAYS:**
- Do this
- Do that

**NEVER:**
- Don't do this
```

## Existing Skills

| Skill | Purpose |
|-------|---------|
| `/bug-fix` | Systematic bug fixing with planning and delegation |
| `/code-architect` | Plan and implement code with approval workflow |
| `/code-implementation` | Plan → implement → verify → code-reviewer agent |
| `/code-reviewer` | Review code against plans, standards, best practices |
| `/integration-test-validator` | Unit, integration, and system testing validation |
| `/investigator` | Deep investigation of issues → present findings → approve → implement |
| `/system-arch` | Architecture analysis, trade-offs, and planning |
| `/tutor` | Explain code on demand (pairs with /explain) |
| `/cleanup` | Organize codebase structure before GitHub push |
| `/document-changes` | Document code changes for PRs/commits |
| `/explain` | Explain code or concepts clearly |
| `/receiving-code-review` | Handle and respond to code review feedback |
| `/technical-blog` | Write technical blog posts |
| `/test-cases` | Generate comprehensive test cases |

## Shared Location

This skills folder is shared between Claude Code and OpenCode via symlink:
```
.claude/skills/     ← Source of truth
.opencode/skills    → symlink to .claude/skills
```

Any skill created here works in both tools.
