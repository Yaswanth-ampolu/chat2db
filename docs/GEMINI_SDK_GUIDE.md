# Gemini SDK Guide: Function Calling & Agents

## Table of Contents
1. [Introduction to Gemini](#introduction-to-gemini)
2. [Setup and Installation](#setup-and-installation)
3. [Basic Function Calling](#basic-function-calling)
4. [Multi-Turn Conversations](#multi-turn-conversations)
5. [Tool Definition Format](#tool-definition-format)
6. [Handling Function Results](#handling-function-results)
7. [Complete Agent Example](#complete-agent-example)
8. [Best Practices](#best-practices)

---

## Introduction to Gemini

**Google Gemini** is a family of multimodal AI models with powerful function calling capabilities.

### Why Gemini for Agents?

✅ **Native Function Calling**: Built-in support for tools
✅ **Multimodal**: Can process text, images, video, audio
✅ **Context Window**: Up to 1M tokens (Gemini 1.5 Pro)
✅ **Parallel Function Calls**: Can call multiple tools at once
✅ **Streaming**: Real-time response generation
✅ **Cost-Effective**: Competitive pricing

### Models Available

| Model | Use Case | Context Window | Speed |
|-------|----------|----------------|-------|
| `gemini-1.5-pro` | Complex reasoning, agents | 2M tokens | Medium |
| `gemini-1.5-flash` | Fast responses, simple tasks | 1M tokens | Fast |
| `gemini-1.0-pro` | Legacy support | 32K tokens | Medium |

---

## Setup and Installation

### Python Installation

```bash
pip install google-generativeai
```

### Node.js Installation

```bash
npm install @google/generative-ai
```

### Get API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the key
4. Set environment variable:

```bash
export GEMINI_API_KEY="your-api-key-here"
```

---

## Basic Function Calling

### Python Example

```python
import google.generativeai as genai
import os

# Configure API
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Define tools
tools = [
    {
        "function_declarations": [
            {
                "name": "get_weather",
                "description": "Get the current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City name, e.g., 'San Francisco'"
                        },
                        "unit": {
                            "type": "string",
                            "description": "Temperature unit",
                            "enum": ["celsius", "fahrenheit"]
                        }
                    },
                    "required": ["location"]
                }
            }
        ]
    }
]

# Create model with tools
model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    tools=tools
)

# Send query
chat = model.start_chat()
response = chat.send_message("What's the weather in Tokyo?")

# Check for function calls
if response.candidates[0].content.parts:
    part = response.candidates[0].content.parts[0]

    if hasattr(part, 'function_call'):
        function_call = part.function_call
        print(f"Function: {function_call.name}")
        print(f"Arguments: {dict(function_call.args)}")

        # Output:
        # Function: get_weather
        # Arguments: {'location': 'Tokyo', 'unit': 'celsius'}
```

### Node.js Example

```javascript
const { GoogleGenerativeAI } = require("@google/generative-ai");

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

// Define tools
const tools = [{
    functionDeclarations: [
        {
            name: "get_weather",
            description: "Get the current weather for a location",
            parameters: {
                type: "object",
                properties: {
                    location: {
                        type: "string",
                        description: "City name"
                    },
                    unit: {
                        type: "string",
                        enum: ["celsius", "fahrenheit"]
                    }
                },
                required: ["location"]
            }
        }
    ]
}];

async function main() {
    const model = genAI.getGenerativeModel({
        model: "gemini-1.5-pro",
        tools: tools
    });

    const chat = model.startChat();
    const result = await chat.sendMessage("What's the weather in Tokyo?");
    const response = result.response;

    // Check for function calls
    const functionCalls = response.functionCalls();
    if (functionCalls && functionCalls.length > 0) {
        functionCalls.forEach(call => {
            console.log(`Function: ${call.name}`);
            console.log(`Arguments:`, call.args);
        });
    }
}

main();
```

---

## Multi-Turn Conversations

The key to building agents is handling multi-turn conversations where function results are fed back to the model.

### Python Multi-Turn Pattern

```python
import google.generativeai as genai

def execute_function(name, args):
    """Execute the actual function"""
    functions = {
        'get_weather': lambda loc, unit='celsius': {
            "temperature": 22,
            "condition": "Sunny",
            "location": loc,
            "unit": unit
        }
    }
    return functions[name](**args)

# Configure
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

tools = [...]  # Tool definitions

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    tools=tools
)

chat = model.start_chat()

# User query
response = chat.send_message("What's the weather in Paris?")

# Agent loop
while True:
    # Check if there are function calls
    if not response.candidates[0].content.parts:
        break

    part = response.candidates[0].content.parts[0]

    if hasattr(part, 'function_call'):
        function_call = part.function_call

        # Execute the function
        result = execute_function(
            function_call.name,
            dict(function_call.args)
        )

        # Send result back to model
        response = chat.send_message(
            genai.protos.Content(
                parts=[
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=function_call.name,
                            response={"result": result}
                        )
                    )
                ]
            )
        )
    else:
        # Final text response
        print(response.text)
        break
```

### Node.js Multi-Turn Pattern

```javascript
const { GoogleGenerativeAI } = require("@google/generative-ai");

async function executeFunction(name, args) {
    const functions = {
        get_weather: (location, unit = 'celsius') => ({
            temperature: 22,
            condition: "Sunny",
            location: location,
            unit: unit
        })
    };
    return functions[name](args.location, args.unit);
}

async function agentLoop(userQuery) {
    const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

    const model = genAI.getGenerativeModel({
        model: "gemini-1.5-pro",
        tools: tools
    });

    const chat = model.startChat();
    let result = await chat.sendMessage(userQuery);
    let response = result.response;

    // Loop until no more function calls
    while (response.functionCalls && response.functionCalls.length > 0) {
        const functionCalls = response.functionCalls;

        // Execute all function calls
        const functionResponses = await Promise.all(
            functionCalls.map(async (call) => {
                const functionResult = await executeFunction(call.name, call.args);

                return {
                    functionResponse: {
                        name: call.name,
                        response: functionResult
                    }
                };
            })
        );

        // Send function results back
        result = await chat.sendMessage(functionResponses);
        response = result.response;
    }

    // Return final text answer
    return response.text();
}

// Usage
agentLoop("What's the weather in Paris?")
    .then(answer => console.log(answer));
```

---

## Tool Definition Format

### Structure

```python
{
    "function_declarations": [
        {
            "name": "function_name",           # Unique identifier
            "description": "What it does",     # LLM uses this to decide
            "parameters": {                    # JSON Schema format
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "Param description"
                    },
                    "param2": {
                        "type": "number",
                        "enum": [1, 2, 3]      # Optional: restrict values
                    }
                },
                "required": ["param1"]          # Optional: required params
            }
        }
    ]
}
```

### Best Practices for Tool Definitions

#### 1. **Clear Naming**
```python
# ❌ Bad
{"name": "func1"}

# ✅ Good
{"name": "get_customer_orders"}
```

#### 2. **Descriptive Documentation**
```python
# ❌ Bad
{"description": "Gets data"}

# ✅ Good
{
    "description": "Retrieve all orders for a specific customer, "
                   "including order items, total amount, and status. "
                   "Results are sorted by order date descending."
}
```

#### 3. **Detailed Parameters**
```python
# ❌ Bad
{
    "properties": {
        "id": {"type": "string"}
    }
}

# ✅ Good
{
    "properties": {
        "customer_id": {
            "type": "string",
            "description": "Unique customer identifier (UUID format)"
        },
        "limit": {
            "type": "number",
            "description": "Maximum number of orders to return (default: 10, max: 100)",
            "minimum": 1,
            "maximum": 100
        },
        "include_items": {
            "type": "boolean",
            "description": "Include order line items in response (default: false)"
        }
    }
}
```

### Complete SQL Tool Definitions Example

```python
sql_tools = [
    {
        "function_declarations": [
            {
                "name": "list_tables",
                "description": (
                    "List all tables in the database with their row counts. "
                    "Use this first to understand the database structure before querying."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "schema": {
                            "type": "string",
                            "description": "Database schema name (default: 'public')"
                        }
                    }
                }
            },
            {
                "name": "get_table_schema",
                "description": (
                    "Get detailed column information for a specific table including "
                    "column names, data types, nullable status, and default values. "
                    "Use this before writing queries to ensure correct column names."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table_name": {
                            "type": "string",
                            "description": "Exact name of the table"
                        },
                        "include_samples": {
                            "type": "boolean",
                            "description": "Include 3 sample rows to see actual data (default: false)"
                        },
                        "include_indexes": {
                            "type": "boolean",
                            "description": "Include index information (default: false)"
                        }
                    },
                    "required": ["table_name"]
                }
            },
            {
                "name": "execute_query",
                "description": (
                    "Execute a SELECT query on the database. Only read-only queries "
                    "are allowed (SELECT statements only). No DML operations "
                    "(INSERT/UPDATE/DELETE) or DDL operations (CREATE/DROP/ALTER)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "SQL SELECT query to execute"
                        },
                        "limit": {
                            "type": "number",
                            "description": "Maximum rows to return (default: 100, max: 1000)",
                            "minimum": 1,
                            "maximum": 1000
                        },
                        "explain": {
                            "type": "boolean",
                            "description": "Return query execution plan instead of results (default: false)"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_table_relationships",
                "description": (
                    "Get foreign key relationships for a table showing how it "
                    "connects to other tables. Useful for understanding JOINs."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table_name": {
                            "type": "string",
                            "description": "Table name to analyze"
                        }
                    },
                    "required": ["table_name"]
                }
            }
        ]
    }
]
```

---

## Handling Function Results

### Sending Results Back to Gemini

#### Python - Simple Format
```python
response = chat.send_message(
    genai.protos.Content(
        parts=[
            genai.protos.Part(
                function_response=genai.protos.FunctionResponse(
                    name="function_name",
                    response={"result": your_result}
                )
            )
        ]
    )
)
```

#### Python - Multiple Function Results
```python
parts = []
for call in function_calls:
    result = execute_function(call.name, dict(call.args))
    parts.append(
        genai.protos.Part(
            function_response=genai.protos.FunctionResponse(
                name=call.name,
                response={"result": result}
            )
        )
    )

response = chat.send_message(genai.protos.Content(parts=parts))
```

#### Node.js Format
```javascript
const functionResponses = functionCalls.map(call => ({
    functionResponse: {
        name: call.name,
        response: executeFunction(call.name, call.args)
    }
}));

const result = await chat.sendMessage(functionResponses);
```

### Error Handling in Function Results

```python
def execute_function_safely(name, args):
    """Execute function with error handling"""
    try:
        result = actual_function(name, args)
        return {
            "success": True,
            "data": result
        }
    except ValueError as e:
        return {
            "success": False,
            "error": f"Invalid input: {str(e)}",
            "type": "validation_error"
        }
    except PermissionError as e:
        return {
            "success": False,
            "error": "Permission denied",
            "type": "permission_error"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "type": "runtime_error"
        }

# Send error back to model
response = chat.send_message(
    genai.protos.Content(
        parts=[
            genai.protos.Part(
                function_response=genai.protos.FunctionResponse(
                    name=function_name,
                    response={
                        "error": error_details,
                        "suggestion": "Try a different approach"
                    }
                )
            )
        ]
    )
)

# Gemini will see the error and try a different strategy
```

---

## Complete Agent Example

### Full Python SQL Agent

```python
import google.generativeai as genai
import os
from typing import Dict, Any, List
import json

class GeminiSQLAgent:
    def __init__(self, api_key: str, db_connection):
        genai.configure(api_key=api_key)
        self.db = db_connection
        self.max_iterations = 15

        # Define SQL tools
        self.tools = [{
            "function_declarations": [
                {
                    "name": "list_tables",
                    "description": "List all database tables",
                    "parameters": {"type": "object", "properties": {}}
                },
                {
                    "name": "get_schema",
                    "description": "Get table schema with column details",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "table": {"type": "string"}
                        },
                        "required": ["table"]
                    }
                },
                {
                    "name": "run_query",
                    "description": "Execute SELECT query",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sql": {"type": "string"}
                        },
                        "required": ["sql"]
                    }
                }
            ]
        }]

        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-pro",
            tools=self.tools,
            system_instruction="""
You are a SQL expert. Always:
1. Check available tables first
2. Get schema before querying
3. Write efficient queries
4. Explain results clearly
            """
        )

    def list_tables(self) -> List[str]:
        """Get all table names"""
        result = self.db.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        )
        return [row[0] for row in result]

    def get_schema(self, table: str) -> Dict[str, Any]:
        """Get table schema"""
        result = self.db.execute(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = '{table}'
        """)
        return {
            "table": table,
            "columns": [
                {
                    "name": row[0],
                    "type": row[1],
                    "nullable": row[2]
                }
                for row in result
            ]
        }

    def run_query(self, sql: str) -> Dict[str, Any]:
        """Execute SQL query"""
        # Validate
        if not sql.strip().upper().startswith('SELECT'):
            return {"error": "Only SELECT queries allowed"}

        try:
            result = self.db.execute(sql)
            return {
                "rows": [dict(row) for row in result],
                "count": len(result)
            }
        except Exception as e:
            return {"error": str(e)}

    def execute_function(self, name: str, args: Dict) -> Any:
        """Route function call to implementation"""
        functions = {
            'list_tables': lambda: self.list_tables(),
            'get_schema': lambda: self.get_schema(args['table']),
            'run_query': lambda: self.run_query(args['sql'])
        }
        return functions[name]()

    def chat(self, user_query: str) -> str:
        """Main agent loop"""
        chat = self.model.start_chat()
        response = chat.send_message(user_query)

        for iteration in range(self.max_iterations):
            # Check for function calls
            if not response.candidates[0].content.parts:
                break

            part = response.candidates[0].content.parts[0]

            if hasattr(part, 'function_call'):
                fc = part.function_call
                print(f"[{iteration+1}] Calling: {fc.name}")

                # Execute function
                result = self.execute_function(fc.name, dict(fc.args))
                print(f"[{iteration+1}] Result: {result}")

                # Send result back
                response = chat.send_message(
                    genai.protos.Content(
                        parts=[
                            genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=fc.name,
                                    response={"result": result}
                                )
                            )
                        ]
                    )
                )
            else:
                # Final answer
                return response.text

        return "Max iterations reached"

# Usage
if __name__ == "__main__":
    agent = GeminiSQLAgent(
        api_key=os.environ["GEMINI_API_KEY"],
        db_connection=my_db_connection
    )

    answer = agent.chat("Who are the top 5 customers?")
    print(answer)
```

---

## Best Practices

### 1. **System Instructions**

Always provide clear system instructions:

```python
system_instruction = """
You are a SQL expert assistant.

Process:
1. ALWAYS use list_tables() first to see what's available
2. ALWAYS use get_schema() before writing queries
3. Validate all table/column names exist
4. Write clean, efficient SQL
5. Explain results in simple terms

Rules:
- Only SELECT queries
- Add LIMIT clauses
- Handle errors gracefully
- Be concise but helpful
"""
```

### 2. **Conversation History Management**

```python
# Get history
history = chat.getHistory()

# Trim if too long
if len(history) > 20:
    # Keep system prompt + recent messages
    history = [history[0]] + history[-15:]
```

### 3. **Parallel Function Calls**

Gemini can call multiple functions at once:

```python
response = chat.send_message("Get schema for users and orders tables")

# Gemini might return:
# function_calls = [
#     {"name": "get_schema", "args": {"table": "users"}},
#     {"name": "get_schema", "args": {"table": "orders"}}
# ]

# Execute in parallel
results = await asyncio.gather(*[
    execute_function(call.name, call.args)
    for call in function_calls
])
```

### 4. **Token Management**

Monitor token usage:

```python
response = chat.send_message(query)

# Check token counts
usage = response.usage_metadata
print(f"Prompt tokens: {usage.prompt_token_count}")
print(f"Response tokens: {usage.candidates_token_count}")
print(f"Total: {usage.total_token_count}")
```

### 5. **Streaming Responses**

For real-time user feedback:

```python
response = chat.send_message(query, stream=True)

for chunk in response:
    if chunk.text:
        print(chunk.text, end="", flush=True)
```

---

## Common Patterns

### Pattern 1: Retry on Error

```python
max_retries = 3
for attempt in range(max_retries):
    try:
        result = execute_function(name, args)
        break
    except Exception as e:
        if attempt == max_retries - 1:
            result = {"error": str(e)}
        else:
            await asyncio.sleep(2 ** attempt)
```

### Pattern 2: Validate Before Execute

```python
def execute_query(sql):
    # Validate syntax
    if not is_valid_sql(sql):
        return {"error": "Invalid SQL syntax"}

    # Check permissions
    if has_forbidden_operations(sql):
        return {"error": "Forbidden operation"}

    # Execute
    return run_sql(sql)
```

### Pattern 3: Add Context to Results

```python
result = execute_function(name, args)

# Add metadata
enhanced_result = {
    "data": result,
    "metadata": {
        "timestamp": datetime.now(),
        "function": name,
        "execution_time": elapsed_time
    }
}
```

---

## Next Steps

- [Tool Creation Guide](./TOOL_CREATION_GUIDE.md) - Build custom tools
- [Agent Loop Implementation](./AGENT_LOOP_IMPLEMENTATION.md) - Advanced patterns
- [SQL Agent Complete Example](./SQL_AGENT_EXAMPLE.md) - Full working code

## Official Resources

- [Gemini API Documentation](https://ai.google.dev/gemini-api/docs)
- [Function Calling Guide](https://ai.google.dev/gemini-api/docs/function-calling)
- [Gemini Cookbook](https://github.com/google-gemini/cookbook)
