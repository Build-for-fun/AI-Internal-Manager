# Explain Skill
**Description:** Explain codebase concepts, architecture, and implementation details with examples when users ask questions about how the system works.
**Usage:** /explain [topic] [optional: depth=basic]

**Trigger this skill when:**
- User asks "how does X work?", "what is Y?", "explain this"
- User wants to understand code architecture, design decisions, or implementation patterns
- User needs conceptual clarification with concrete examples
- User asks about specific functions, modules, or data flows

**Skip for:** Simple syntax questions, "what's the error?" (use LSP), obvious code that's self-documenting

## Execution Workflow

### Step 1: Parse User Query
**Identify the core question:**
- What system/component are they asking about?
- What level of detail do they need?
- Are they asking for high-level architecture or specific implementation?
- Any specific file/function mentioned?

**Classify question type:**
| Type | Signal | Approach |
|------|--------|---------|
| Architecture | "how does routing work?", "explain the system" | High-level overview + component interactions |
| Implementation | "how does X function work?", "why is this here?" | Specific code walkthrough |
| Data Flow | "what happens when user asks Y?" | Trace request/response path |
| Design Decision | "why did you use pattern X?" | Explain trade-offs and rationale |

### Step 2: Gather Context
**Run targeted searches in parallel:**
```bash
# Find relevant files
background_task(agent="explore", prompt="Find all files related to [topic] in the codebase")
background_task(agent="librarian", prompt="Find documentation or patterns about [topic] in open source")

# Find usage examples  
background_task(agent="explore", prompt="Find usage examples of [topic] in tests and documentation")
```

**Focus search on:**
- Core implementation files for the topic
- Configuration files related to the topic
- Test files that demonstrate the concept
- Documentation or README sections
- Recent changes or additions

### Step 3: Analyze and Synthesize
**Read key files identified:**
- Use Read tool to examine main implementation
- Look for entry points, main classes/functions
- Identify data structures and algorithms
- Note design patterns and architectural choices

**Answer structure:**
1. **Core Concept** - What is this thing at a high level?
2. **Key Components** - What are the main parts?
3. **How It Works** - Step-by-step flow with code examples
4. **Why This Design** - Architectural reasoning and trade-offs
5. **Example Usage** - Concrete code snippet showing real usage
6. **Related Components** - What other parts interact with this?

### Step 4: Provide Examples
**Create minimal, focused examples:**

| Topic | Example Approach |
|--------|-----------------|
| **MCP Connection** | Show `client = MCPClient("name", "python3", ["server.py"]); await client.connect()` |
| **Query Routing** | Show `router = QueryAnalyzer(); result = router.analyze("search files")` |
| **Tool Discovery** | Show `await client._discover_tools(); print(client.tools)` |
| **Multi-agent Coordination** | Show `orchestrator = CrewAIOrchestrator(); await orchestrator.run_query()` |
| **Batch Processing** | Show `processor = BatchMCPProcessor(); results = await processor.process_batch()` |

**Example format:**
```python
# Example: How query routing works
from routing.query_analyzer import QueryAnalyzer

# 1. Create analyzer
analyzer = QueryAnalyzer()

# 2. Analyze user query
result = analyzer.analyze("find Python files with async functions")

# 3. Get routing decision
if result.intent == QueryIntent.CODE_ANALYSIS:
    print("Route to code analysis MCPs")
    print(f"Confidence: {result.confidence:.2f}")
```

## Topics and Explanations

### When asked about "Query Routing"
**Core flow to explain:**
1. User query enters CLI → MasterMCPServer
2. QueryAnalyzer analyzes for intent and keywords
3. AIRouter (if available) uses LLM for complex routing
4. LearningRouter adds user feedback and patterns
5. ToolRegistry matches against available MCP tools
6. Route to best MCP(s) with suggested tool/arguments

**Key files:** `query_analyzer.py`, `ai_router.py`, `learning_router.py`, `tool_registry.py`

### When asked about "MCP Connections"
**Core flow to explain:**
1. MCPClient/HTTPMCPClient created from config
2. `connect()` spawns subprocess or creates HTTP session
3. `_initialize()` sends MCP protocol handshake
4. `_discover_tools()` calls `tools/list` method
5. Tools stored as `MCPTool` objects in client.tools list
6. `call_tool()` executes via JSON-RPC

**Key files:** `mcp_client.py`, `master_mcp_server.py`

### When asked about "Tool Discovery"
**Core flow to explain:**
1. MCP server receives `tools/list` JSON-RPC request
2. Server responds with tool definitions including schemas
3. Client parses response and creates `MCPTool` objects
4. Tools registered in `ToolRegistry` with metadata
5. ToolRegistry provides search and matching capabilities

**Key files:** `mcp_client.py:110`, `tool_registry.py`, `master_mcp_server.py:394`

### When asked about "Multi-Agent Orchestration"
**Core flow to explain:**
1. When query complexity > threshold, enable multi-agent
2. CrewAIOrchestrator creates specialist agents
3. Each agent gets subset of MCP tools relevant to their role
4. Agents execute in parallel, share context
5. Results aggregated and prioritized
6. Fallback to SimpleMultiMCPHandler if CrewAI unavailable

**Key files:** `agent_orchestrator_crewai.py`, `simple_multi_mcp.py`, `master_mcp_server.py:768`

### When asked about "Batch Processing"
**Core flow to explain:**
1. For >5 MCPs, switch to batch mode
2. BatchMCPProcessor groups calls by execution strategy
3. ToolCallInterceptor optimizes concurrent calls
4. SingleFileExecutor generates isolated execution scripts
5. DockerSandbox provides isolated execution environment
6. ResultAggregator combines and prioritizes results

**Key files:** `batch_mcp_processor.py`, `batch_executor.py`, `single_file_generator.py`

## Quality Guidelines

**ALWAYS:**
- Start with high-level concept before implementation details
- Use concrete code examples for each concept
- Show data flow arrows or numbered steps
- Include file paths and line numbers for key code
- Explain "why" behind design decisions
- Provide both simple and advanced examples when appropriate

**NEVER:**
- Explain line-by-line code without context
- Provide examples that don't actually work
- Skip architectural reasoning
- Assume user knows all terminology
- Give vague explanations without concrete examples

## Common Question Patterns

| User Question | Response Strategy |
|---------------|------------------|
| "How does routing work?" | Show QueryAnalyzer → AIRouter → ToolRegistry flow with example |
| "What happens when I run a query?" | Trace CLI → Server → Router → MCP → Response |
| "Why use CrewAI?" | Explain multi-agent benefits and fallback mechanism |
| "How are tools discovered?" | Show JSON-RPC tools/list → MCPTool → Registry flow |
| "What's batch processing?" | Explain >5 MCPs → batch mode → Docker isolation |
| "How do I add a new MCP?" | Show config.json format → auto-detection → registration |

## Depth Control

**Optional parameter: depth=[basic|detailed|expert]**

| Depth | Content Focus |
|--------|---------------|
| `basic` | High-level overview, main concepts, simple examples |
| `detailed` | Component interactions, code examples, design reasoning |  
| `expert` | Implementation details, edge cases, performance considerations |

**Default:** `depth=basic` unless user specifies otherwise

## Example Response Structure

```markdown
## How Query Routing Works

**Core Concept:** The system uses a multi-tier routing strategy to match user queries to the best available MCP tools.

### Key Components

1. **QueryAnalyzer** (`routing/query_analyzer.py`) - Rule-based intent detection
2. **AIRouter** (`routing/ai_router.py`) - LLM-powered routing for complex queries  
3. **ToolRegistry** (`tools/tool_registry.py`) - Tool matching and discovery
4. **LearningRouter** (`routing/learning_router.py`) - User feedback and pattern learning

### How It Works

```python
# 1. User query enters system
user_query = "find async functions in Python files"

# 2. QueryAnalyzer analyzes intent
analyzer = QueryAnalyzer()
result = analyzer.analyze(user_query)
# result.intent = QueryIntent.CODE_ANALYSIS
# result.confidence = 0.85

# 3. If high confidence, use script-based routing
if result.confidence > 0.8:
    # Use ToolRegistry for direct tool matching
    registry = get_registry()
    matches = registry.find_tools_for_query(user_query)
else:
    # Use AI for complex routing
    router = AIRouter()
    suggestions = router.analyze_query_with_ai(user_query)
```

### Why This Design

- **Fallback Chain:** Script → AI → Direct tool matching
- **Performance:** Quick rule-based routing for common patterns
- **Flexibility:** AI handles complex or ambiguous queries
- **Learning:** User feedback improves routing over time

### Example Usage

```python
# Simple routing example
from routing.query_analyzer import QueryAnalyzer
from tools.tool_registry import get_registry

analyzer = QueryAnalyzer()
registry = get_registry()

# Route a query
query = "analyze this Python code"
analysis = analyzer.analyze(query)
best_tools = registry.find_tools_for_query(query)

print(f"Intent: {analysis.intent}")
print(f"Best tools: {[t.name for t in best_tools[:3]]}")
```

### Related Components

- **MCP Discovery:** `server/mcp_client.py:_discover_tools()`
- **Tool Execution:** `server/master_mcp_server.py:_execute_tool()`
- **Result Aggregation:** `batch_mcp_sandbox/result_processor.py`
```

This structure ensures comprehensive explanations with concrete examples for any codebase question.