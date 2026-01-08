# AI Agents: Complete Guide

## Table of Contents
1. [What are AI Agents?](#what-are-ai-agents)
2. [Agent Architecture](#agent-architecture)
3. [Types of Agents](#types-of-agents)
4. [How Agents Work](#how-agents-work)
5. [ReAct Pattern](#react-pattern)
6. [Agent Components](#agent-components)
7. [Real-World Examples](#real-world-examples)

---

## What are AI Agents?

An **AI Agent** is an autonomous system that can:
- **Perceive** its environment (receive user queries, tool outputs)
- **Reason** about what actions to take (decide which tools to use)
- **Act** on the environment (execute tools, make API calls)
- **Learn** from feedback (adjust strategy based on results)

### Traditional LLM vs AI Agent

```
┌─────────────────────────────────────────────────────────────┐
│                   Traditional LLM                           │
│                                                             │
│   User Query ──► LLM ──► Text Response                     │
│                                                             │
│   Limitation: Can only generate text, no external actions   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     AI Agent                                │
│                                                             │
│   User Query ──► Agent ──┬──► Text Response                │
│                          │                                  │
│                          ├──► Execute Tools                 │
│                          │     (Database, API, Files)       │
│                          │                                  │
│                          └──► Tool Results ──► Loop back    │
│                                                             │
│   Capability: Can interact with external systems            │
└─────────────────────────────────────────────────────────────┘
```

---

## Agent Architecture

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      AI Agent System                         │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                  Agent Brain (LLM)                     │ │
│  │  - Google Gemini / OpenAI GPT / Anthropic Claude       │ │
│  │  - Receives: User query + Tool definitions + History   │ │
│  │  - Outputs: Tool calls OR Final answer                 │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                   │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Agent Controller                          │ │
│  │  - Manages conversation history                        │ │
│  │  - Orchestrates tool execution                         │ │
│  │  - Implements safety checks                            │ │
│  │  - Controls iteration limits                           │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                   │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                Tool Registry                           │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │ │
│  │  │  Tool 1  │  │  Tool 2  │  │  Tool 3  │            │ │
│  │  │ Database │  │   API    │  │   File   │   ...      │ │
│  │  └──────────┘  └──────────┘  └──────────┘            │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                   │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              External Environment                      │ │
│  │  - Databases                                           │ │
│  │  - APIs                                                │ │
│  │  - File Systems                                        │ │
│  │  - Other Services                                      │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## Types of Agents

### 1. **Reactive Agents**
- Respond directly to stimuli
- No memory of past actions
- Simple pattern matching

**Example:**
```
User: "What's 2+2?"
Agent: "4"
```

### 2. **Model-Based Agents**
- Maintain internal state/model
- Remember past interactions
- Can reason about future states

**Example:**
```
User: "What's 2+2?"
Agent: "4"
User: "Multiply that by 3"
Agent: "12" (remembers previous answer)
```

### 3. **Goal-Based Agents**
- Work towards specific objectives
- Plan sequence of actions
- Evaluate success criteria

**Example:**
```
Goal: "Find top 10 customers by revenue"
Agent Plans:
1. List available tables
2. Get schema of customers and orders tables
3. Write JOIN query
4. Execute and format results
```

### 4. **Learning Agents**
- Improve from experience
- Adapt strategies over time
- Self-optimize

**Example:**
```
Agent learns that:
- Checking schema first reduces errors
- Adding LIMIT improves performance
- Certain query patterns work better
```

---

## How Agents Work

### The Agent Loop (Simplified)

```python
def agent_loop(user_query):
    """
    Simplified agent loop
    """
    history = []
    max_iterations = 10

    # Step 1: Send user query to LLM
    history.append({"role": "user", "content": user_query})

    for iteration in range(max_iterations):
        # Step 2: LLM decides action
        response = llm.generate(history, available_tools)

        # Step 3: Check what LLM wants to do
        if response.has_tool_calls():
            # LLM wants to use tools
            for tool_call in response.tool_calls:
                # Step 4: Execute the tool
                result = execute_tool(tool_call.name, tool_call.args)

                # Step 5: Add tool result to history
                history.append({
                    "role": "tool",
                    "tool": tool_call.name,
                    "result": result
                })
        else:
            # LLM has final answer
            return response.text

    return "Max iterations reached"
```

### Detailed Flow Diagram

```
┌─────────────────────┐
│   User Query        │
│ "Show top products" │
└──────────┬──────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│  Iteration 1: LLM Reasoning                  │
│  "I need to know what tables exist first"    │
│                                              │
│  Decision: Call list_tables()                │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│  Execute Tool: list_tables()                 │
│  Result: ["products", "orders", "customers"] │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│  Iteration 2: LLM Reasoning                  │
│  "Now I need schema of products table"       │
│                                              │
│  Decision: Call get_schema("products")       │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│  Execute Tool: get_schema("products")        │
│  Result: {columns: [id, name, price, ...]}   │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│  Iteration 3: LLM Reasoning                  │
│  "I can now write a query"                   │
│                                              │
│  Decision: Call execute_query(               │
│    "SELECT * FROM products ORDER BY sales    │
│     DESC LIMIT 10"                           │
│  )                                           │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│  Execute Tool: execute_query()               │
│  Result: 10 rows of product data             │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│  Iteration 4: LLM Reasoning                  │
│  "I have the data, format final answer"      │
│                                              │
│  Decision: No tool calls, return text        │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│  Final Answer to User                        │
│  "Here are the top 10 products:              │
│   1. Product A - $5000                       │
│   2. Product B - $4500..."                   │
└──────────────────────────────────────────────┘
```

---

## ReAct Pattern

**ReAct** = **Rea**soning + **Act**ing

This pattern makes agents more transparent and effective by having them "think out loud."

### Pattern Structure

```
Thought: [Agent explains its reasoning]
Action: [Agent calls a tool]
Observation: [Result from tool execution]
... (repeat as needed)
Thought: [Final reasoning]
Answer: [Response to user]
```

### Example: SQL Agent with ReAct

```
User: "Who are our top 5 customers?"

Thought: I need to find customer information. First, let me check
         what tables are available to understand the database structure.

Action: list_tables()

Observation: Tables: [customers, orders, order_items, products]

Thought: Good! I can see there's a customers table and an orders table.
         Now I need to understand the schema to write the correct query.

Action: get_table_schema("customers")

Observation: Columns: id, name, email, created_at

Action: get_table_schema("orders")

Observation: Columns: id, customer_id, total_amount, order_date

Thought: Perfect! I can join customers and orders tables, sum the
         total_amount grouped by customer, and order by total descending.

Action: execute_query(
  "SELECT c.name, SUM(o.total_amount) as total_spent
   FROM customers c
   JOIN orders o ON c.id = o.customer_id
   GROUP BY c.id, c.name
   ORDER BY total_spent DESC
   LIMIT 5"
)

Observation:
  [
    {"name": "Alice Corp", "total_spent": 15000},
    {"name": "Bob Industries", "total_spent": 12500},
    ...
  ]

Thought: I now have the top 5 customers by spending. Let me format
         this nicely for the user.

Answer: Here are your top 5 customers by total spending:

1. Alice Corp - $15,000
2. Bob Industries - $12,500
3. Charlie Co - $10,800
4. Delta Ltd - $9,200
5. Echo Systems - $8,500

These customers represent your highest value accounts.
```

### Benefits of ReAct

1. **Transparency**: User can see agent's reasoning
2. **Debuggability**: Easy to identify where agent went wrong
3. **Reliability**: Grounding in observations reduces hallucination
4. **Flexibility**: Agent can adapt strategy based on results

---

## Agent Components

### 1. **System Prompt (Instructions)**

Defines the agent's behavior and personality.

```python
SYSTEM_PROMPT = """
You are a SQL expert assistant helping users query their database.

Your capabilities:
- Explore database schema (tables, columns, relationships)
- Write efficient SQL queries
- Explain query results in simple terms

Your process:
1. Always check schema before writing queries
2. Validate table and column names exist
3. Use appropriate JOINs when querying related tables
4. Add LIMIT clauses to prevent huge result sets
5. Explain what the data shows

Safety rules:
- Only execute SELECT queries (read-only)
- Never DROP, DELETE, or UPDATE tables
- Alert user if requested data doesn't exist
"""
```

### 2. **Tool Definitions**

Describe what tools are available and how to use them.

```python
tools = [
    {
        "name": "list_tables",
        "description": "List all tables in the database",
        "parameters": {
            "type": "object",
            "properties": {
                "schema": {
                    "type": "string",
                    "description": "Database schema name (optional)"
                }
            }
        }
    }
]
```

### 3. **Conversation History**

Maintains context across the conversation.

```python
history = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": "What tables exist?"},
    {"role": "assistant", "content": "", "tool_calls": [...]},
    {"role": "tool", "name": "list_tables", "result": [...]},
    {"role": "assistant", "content": "I found 4 tables..."}
]
```

### 4. **Tool Executor**

Executes tools safely and returns results.

```python
def execute_tool(name, arguments):
    """
    Execute a tool and return result
    """
    tools = {
        'list_tables': list_tables,
        'get_schema': get_schema,
        'execute_query': execute_query
    }

    if name not in tools:
        return {"error": f"Tool {name} not found"}

    try:
        result = tools[name](**arguments)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 5. **Safety Guards**

Prevent dangerous operations and infinite loops.

```python
class AgentSafety:
    MAX_ITERATIONS = 15
    MAX_TOOL_ERRORS = 3
    FORBIDDEN_OPERATIONS = ['DROP', 'DELETE', 'UPDATE', 'TRUNCATE']

    @staticmethod
    def validate_query(query):
        """Check if query is safe"""
        for op in AgentSafety.FORBIDDEN_OPERATIONS:
            if op in query.upper():
                raise SecurityError(f"Operation {op} is not allowed")
        return True
```

---

## Real-World Examples

### Example 1: Coding Agent (like Aider)

```
User: "Add error handling to login function"

Agent Flow:
1. Tool: read_file("auth.py") → Get current code
2. Tool: analyze_code() → Understand structure
3. Reasoning: Identify where to add try-catch
4. Tool: edit_file("auth.py", changes) → Apply changes
5. Tool: run_tests() → Verify it works
6. Response: "Added error handling for network failures and invalid credentials"
```

### Example 2: Research Agent

```
User: "What's the latest on quantum computing?"

Agent Flow:
1. Tool: web_search("quantum computing 2024") → Get articles
2. Tool: extract_content(url1, url2) → Read top articles
3. Tool: summarize_text(content) → Create summary
4. Reasoning: Synthesize information
5. Response: "Recent breakthroughs include..."
```

### Example 3: SQL Agent (Our Use Case)

```
User: "Which product category has the highest revenue?"

Agent Flow:
1. Tool: list_tables() → See available tables
2. Tool: get_schema("products") → Check for category field
3. Tool: get_schema("order_items") → Check for revenue data
4. Tool: execute_query("SELECT ...") → Get revenue by category
5. Reasoning: Analyze results
6. Response: "Electronics category leads with $1.2M in revenue"
```

---

## Key Takeaways

### ✅ What Makes a Good Agent

1. **Clear Purpose**: Well-defined task scope
2. **Right Tools**: Access to necessary capabilities
3. **Smart Reasoning**: Good decision-making
4. **Error Recovery**: Handles failures gracefully
5. **Safety First**: Validates before acting
6. **Efficiency**: Minimizes unnecessary tool calls

### ⚠️ Common Pitfalls

1. **Infinite Loops**: Agent keeps calling tools without progress
2. **Tool Overuse**: Calling tools when answer is obvious
3. **Context Loss**: Forgetting important information from earlier
4. **Unsafe Operations**: Not validating tool inputs
5. **Poor Error Messages**: Not explaining failures to user

### 🎯 Best Practices

1. **Always set max iterations** to prevent runaway loops
2. **Log all tool calls** for debugging
3. **Validate inputs** before execution
4. **Provide clear tool descriptions** so LLM chooses correctly
5. **Test error scenarios** (network failures, invalid data)
6. **Monitor costs** (API calls can add up quickly)

---

## Next Steps

Now that you understand how agents work, proceed to:
1. [Gemini SDK Guide](./GEMINI_SDK_GUIDE.md) - Learn how to use Google's Gemini API
2. [Tool Creation Guide](./TOOL_CREATION_GUIDE.md) - Build custom tools
3. [Agent Loop Implementation](./AGENT_LOOP_IMPLEMENTATION.md) - Code the agent
4. [SQL Agent Example](./SQL_AGENT_EXAMPLE.md) - Complete working example

---

**Remember**: An AI agent is not magic - it's a structured loop of:
1. Reason about the problem
2. Choose appropriate tools
3. Execute tools
4. Process results
5. Repeat until solved
