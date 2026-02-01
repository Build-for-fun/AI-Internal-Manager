---
name: agents
description: List and describe all available custom agents in this project
---

I will display all custom agents available in this project by reading the agent definition files.

## Available Custom Agents

!`cd /Users/ash/Desktop/Personal_Projects/documentation-mcp
for agent_file in .claude/agents/*.md; do
  echo "---"
  echo "### $(echo "$(basename "$agent_file" .md)" | sed 's/-/ /g' | awk '{for(i=1;i<=NF;i++)sub(/./,toupper(substr($i,1,1)),$i)}1')"
  echo ""
  echo "**File:** \`$agent_file\`"
  echo ""
  echo "**Description:**"
  grep -A 3 "^description:" "$agent_file" 2>/dev/null | sed 's/^description: *//' | head -2
  echo ""
done`

---

### Quick Reference

| Agent | Purpose |
|-------|---------|
| code-architect | Code implementation, feature development, refactoring |
| code-reviewer | Review completed work against plans and standards |
| integration-test-validator | Comprehensive testing (unit, integration, system) |
| system-arch | System architecture analysis and planning |
| tutor | Explain code and recent changes |

### How to Use

Simply describe what you need and I'll invoke the appropriate agent:
- "Architect a new feature for X" → Uses code-architect
- "Review the implementation of Y" → Uses code-reviewer  
- "Test the new Z feature" → Uses integration-test-validator
- "Analyze our system architecture" → Uses system-arch
- "Explain how this code works" → Uses tutor
