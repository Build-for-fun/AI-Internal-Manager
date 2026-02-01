# Tutor Skill
**Description:** Explain code or changes clearly when the user asks for an explanation or walkthrough.
**Usage:** /tutor [what to explain]

**Trigger this skill when:**
- User asks to explain newly written or existing code
- User wants a walkthrough of how the implementation works
- Code implementation flow requests a follow-up explanation

**Skip for:** Bug fixing, feature planning, or when the user did not ask for an explanation

## Execution Workflow

1) **Scope the ask**
- Identify which files/functions to explain and the desired depth (basic/detailed/expert)
- Ask if they want a high-level overview, flow, or line-level key points

2) **Gather context**
- Read the relevant files/functions
- Identify entry points, main data flow, key decisions, and side effects

3) **Explain concisely** (default to structured output)
```
## What it does
[one or two sentences]

## How it works
- Step-by-step flow (numbered)
- Key functions/classes
- Important data structures

## Why this design (if relevant)
- Trade-offs / rationale

## Usage
- Minimal example or call site
```

4) **Tailor depth**
- If user specifies depth: basic/detailed/expert, adjust detail accordingly

5) **Verify accuracy**
- Ensure the explanation references actual code paths you read
- Avoid speculation; cite file paths and function names

## Quality Guidelines

**ALWAYS:**
- Be concise; prioritize clarity over verbosity
- Cite file paths and function names you inspected
- Include a short usage/example when helpful
- Note side effects, error handling, and edge cases if relevant

**NEVER:**
- Invent behavior you didn’t verify
- Provide line-by-line dumps without synthesis
- Omit the “how it works” flow
