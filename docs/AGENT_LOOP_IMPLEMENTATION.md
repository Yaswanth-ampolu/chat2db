# Agent Loop Implementation Guide

## Table of Contents
1. [What is the Agent Loop?](#what-is-the-agent-loop)
2. [Loop Architecture](#loop-architecture)
3. [Basic Implementation](#basic-implementation)
4. [Advanced Patterns](#advanced-patterns)
5. [State Management](#state-management)
6. [Error Recovery](#error-recovery)
7. [Performance Optimization](#performance-optimization)
8. [Complete Example](#complete-example)

---

## What is the Agent Loop?

The **agent loop** is the core mechanism that allows an AI to iteratively use tools until it solves the user's problem.

### Without Agent Loop (Static)

```
User: "Show me top customers"
   ↓
AI: "Here's a query..." (might be wrong, can't check)
```

### With Agent Loop (Dynamic)

```
User: "Show me top customers"
   ↓
Iteration 1: AI → list_tables() → sees "customers", "orders" tables
   ↓
Iteration 2: AI → get_schema("customers") → sees column structure
   ↓
Iteration 3: AI → get_schema("orders") → sees order details
   ↓
Iteration 4: AI → execute_query("SELECT...JOIN...") → gets actual data
   ↓
Iteration 5: AI → formats answer with insights
   ↓
Final Answer: "Here are your top 10 customers by revenue..."
```

---

## Loop Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────┐
│              AGENT LOOP                         │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  1. User Query Input                     │  │
│  └──────────────┬───────────────────────────┘  │
│                 │                               │
│                 ▼                               │
│  ┌──────────────────────────────────────────┐  │
│  │  2. Send to LLM with Tool Definitions    │  │
│  └──────────────┬───────────────────────────┘  │
│                 │                               │
│                 ▼                               │
│  ┌──────────────────────────────────────────┐  │
│  │  3. LLM Response                         │  │
│  │     - Text OR                            │  │
│  │     - Function Call(s)                   │  │
│  └──────────────┬───────────────────────────┘  │
│                 │                               │
│        ┌────────┴────────┐                      │
│        │                 │                      │
│    Text Only        Function Call(s)            │
│        │                 │                      │
│        ▼                 ▼                      │
│  ┌──────────┐  ┌────────────────────────┐      │
│  │  RETURN  │  │  4. Execute Tools      │      │
│  │  ANSWER  │  └────────┬───────────────┘      │
│  └──────────┘           │                      │
│                         ▼                      │
│              ┌──────────────────────────┐      │
│              │  5. Add Results to       │      │
│              │     Conversation History │      │
│              └──────────┬───────────────┘      │
│                         │                      │
│                         ▼                      │
│              ┌──────────────────────────┐      │
│              │  6. Iteration Check:     │      │
│              │     - Max iterations?    │      │
│              │     - Error threshold?   │      │
│              └──────────┬───────────────┘      │
│                         │                      │
│                         │ Continue             │
│                         └──────┐               │
│                                │               │
│  ┌─────────────────────────────┘               │
│  │                                             │
│  └──► Loop back to step 2                     │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## Basic Implementation

### Minimal Agent Loop (Python)

```python
import google.generativeai as genai

def simple_agent_loop(user_query, tools, max_iterations=10):
    """
    Simplest possible agent loop
    """
    # Configure
    genai.configure(api_key=YOUR_API_KEY)

    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro",
        tools=tools
    )

    # Start conversation
    chat = model.start_chat()
    response = chat.send_message(user_query)

    # Loop
    for iteration in range(max_iterations):
        # Check if there are function calls
        if not response.candidates[0].content.parts:
            break

        part = response.candidates[0].content.parts[0]

        if hasattr(part, 'function_call'):
            fc = part.function_call

            # Execute the function
            result = execute_tool(fc.name, dict(fc.args))

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
            # Text response - we're done
            return response.text

    return "Max iterations reached"

# Usage
answer = simple_agent_loop(
    "What are the top 5 products?",
    my_tools
)
print(answer)
```

### Minimal Agent Loop (Node.js)

```javascript
const { GoogleGenerativeAI } = require("@google/generative-ai");

async function simpleAgentLoop(userQuery, tools, maxIterations = 10) {
    const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

    const model = genAI.getGenerativeModel({
        model: "gemini-1.5-pro",
        tools: tools
    });

    const chat = model.startChat();
    let result = await chat.sendMessage(userQuery);
    let response = result.response;

    // Loop
    for (let iteration = 0; iteration < maxIterations; iteration++) {
        const functionCalls = response.functionCalls();

        if (!functionCalls || functionCalls.length === 0) {
            // Text response - done
            return response.text();
        }

        // Execute all function calls
        const functionResponses = await Promise.all(
            functionCalls.map(async (call) => {
                const result = await executeTool(call.name, call.args);

                return {
                    functionResponse: {
                        name: call.name,
                        response: result
                    }
                };
            })
        );

        // Send results back
        result = await chat.sendMessage(functionResponses);
        response = result.response;
    }

    return "Max iterations reached";
}

// Usage
const answer = await simpleAgentLoop(
    "What are the top 5 products?",
    myTools
);
console.log(answer);
```

---

## Advanced Patterns

### Pattern 1: Loop with Logging

```python
class AgentLoop:
    """Agent loop with comprehensive logging"""

    def __init__(self, model, tools, max_iterations=15):
        self.model = model
        self.tools = tools
        self.max_iterations = max_iterations
        self.logs = []

    def log(self, level, message, data=None):
        """Add log entry"""
        entry = {
            "level": level,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        self.logs.append(entry)
        print(f"[{level}] {message}")

    async def run(self, user_query):
        """Execute agent loop with logging"""
        self.log("INFO", f"Starting agent with query: {user_query}")

        chat = self.model.start_chat()
        response = chat.send_message(user_query)

        for iteration in range(self.max_iterations):
            self.log("INFO", f"Iteration {iteration + 1}/{self.max_iterations}")

            # Check for function calls
            if not response.candidates[0].content.parts:
                self.log("WARNING", "No parts in response")
                break

            part = response.candidates[0].content.parts[0]

            if hasattr(part, 'function_call'):
                fc = part.function_call
                self.log(
                    "INFO",
                    f"LLM called tool: {fc.name}",
                    {"arguments": dict(fc.args)}
                )

                try:
                    # Execute tool
                    result = self.execute_tool(fc.name, dict(fc.args))

                    self.log(
                        "SUCCESS",
                        f"Tool executed: {fc.name}",
                        {"result_preview": str(result)[:200]}
                    )

                    # Send back to LLM
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

                except Exception as e:
                    self.log(
                        "ERROR",
                        f"Tool execution failed: {fc.name}",
                        {"error": str(e)}
                    )

                    # Send error to LLM
                    error_response = {
                        "error": str(e),
                        "suggestion": "Try a different approach"
                    }

                    response = chat.send_message(
                        genai.protos.Content(
                            parts=[
                                genai.protos.Part(
                                    function_response=genai.protos.FunctionResponse(
                                        name=fc.name,
                                        response=error_response
                                    )
                                )
                            ]
                        )
                    )

            else:
                # Final text answer
                final_answer = response.text
                self.log(
                    "SUCCESS",
                    "Agent completed",
                    {"iterations": iteration + 1}
                )
                return {
                    "answer": final_answer,
                    "iterations": iteration + 1,
                    "logs": self.logs
                }

        # Max iterations reached
        self.log("WARNING", "Max iterations reached")
        return {
            "answer": "I couldn't complete the task within the iteration limit.",
            "iterations": self.max_iterations,
            "logs": self.logs,
            "exceeded": True
        }

    def execute_tool(self, name, args):
        """Execute a tool"""
        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")

        return self.tools[name](**args)

    def get_logs(self):
        """Get execution logs"""
        return self.logs

    def get_summary(self):
        """Get execution summary"""
        total = len(self.logs)
        errors = len([l for l in self.logs if l["level"] == "ERROR"])
        successes = len([l for l in self.logs if l["level"] == "SUCCESS"])

        return {
            "total_logs": total,
            "errors": errors,
            "successes": successes,
            "tool_calls": [
                l for l in self.logs
                if "Tool executed" in l["message"] or "LLM called tool" in l["message"]
            ]
        }
```

### Pattern 2: Loop with State Machine

```python
from enum import Enum

class AgentState(Enum):
    """Agent states"""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING_TOOL = "executing_tool"
    PROCESSING_RESULT = "processing_result"
    COMPLETED = "completed"
    ERROR = "error"

class StatefulAgentLoop:
    """Agent loop with explicit state management"""

    def __init__(self, model, tools):
        self.model = model
        self.tools = tools
        self.state = AgentState.IDLE
        self.history = []
        self.current_iteration = 0

    def transition(self, new_state, data=None):
        """Transition to new state"""
        old_state = self.state
        self.state = new_state

        print(f"State: {old_state.value} → {new_state.value}")

        # Log transition
        self.history.append({
            "from": old_state.value,
            "to": new_state.value,
            "iteration": self.current_iteration,
            "data": data
        })

    async def run(self, user_query):
        """Run agent with state transitions"""
        self.transition(AgentState.THINKING, {"query": user_query})

        chat = self.model.start_chat()
        response = chat.send_message(user_query)

        while self.current_iteration < 15:
            self.current_iteration += 1

            # Check response type
            if not response.candidates[0].content.parts:
                self.transition(AgentState.ERROR, {"reason": "Empty response"})
                break

            part = response.candidates[0].content.parts[0]

            if hasattr(part, 'function_call'):
                # LLM wants to use a tool
                fc = part.function_call
                self.transition(
                    AgentState.EXECUTING_TOOL,
                    {"tool": fc.name, "args": dict(fc.args)}
                )

                try:
                    # Execute
                    result = self.tools[fc.name](**dict(fc.args))

                    self.transition(
                        AgentState.PROCESSING_RESULT,
                        {"tool": fc.name, "success": True}
                    )

                    # Send back to LLM
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

                    self.transition(AgentState.THINKING)

                except Exception as e:
                    self.transition(
                        AgentState.ERROR,
                        {"tool": fc.name, "error": str(e)}
                    )
                    break

            else:
                # Final answer
                self.transition(
                    AgentState.COMPLETED,
                    {"answer": response.text}
                )
                return {
                    "answer": response.text,
                    "state_history": self.history,
                    "iterations": self.current_iteration
                }

        return {
            "error": "Max iterations or error",
            "state_history": self.history
        }
```

### Pattern 3: Parallel Tool Execution

```python
import asyncio

class ParallelAgentLoop:
    """Agent that can execute multiple tools in parallel"""

    async def execute_tools_parallel(self, function_calls):
        """Execute multiple tool calls in parallel"""

        tasks = []
        for fc in function_calls:
            task = self.execute_tool_async(fc.name, dict(fc.args))
            tasks.append((fc.name, task))

        # Execute all in parallel
        results = []
        for name, task in tasks:
            try:
                result = await task
                results.append({
                    "name": name,
                    "result": result,
                    "success": True
                })
            except Exception as e:
                results.append({
                    "name": name,
                    "error": str(e),
                    "success": False
                })

        return results

    async def execute_tool_async(self, name, args):
        """Async tool execution"""
        # Wrap synchronous tool in async
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.tools[name],
            **args
        )
        return result

    async def run(self, user_query):
        """Run agent with parallel execution"""
        chat = self.model.start_chat()
        response = chat.send_message(user_query)

        for iteration in range(self.max_iterations):
            if not response.candidates[0].content.parts:
                break

            function_calls = [
                part.function_call
                for part in response.candidates[0].content.parts
                if hasattr(part, 'function_call')
            ]

            if not function_calls:
                # Text response
                return response.text

            # Execute all tools in parallel
            results = await self.execute_tools_parallel(function_calls)

            # Format responses
            parts = []
            for res in results:
                parts.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=res["name"],
                            response={
                                "result": res.get("result"),
                                "error": res.get("error")
                            }
                        )
                    )
                )

            # Send all results back at once
            response = chat.send_message(genai.protos.Content(parts=parts))

        return "Max iterations reached"
```

---

## State Management

### Conversation History

```python
class ConversationManager:
    """Manages conversation history and context"""

    def __init__(self, max_history=50):
        self.history = []
        self.max_history = max_history

    def add_user_message(self, content):
        """Add user message"""
        self.history.append({
            "role": "user",
            "content": content,
            "timestamp": datetime.now()
        })
        self._trim_if_needed()

    def add_assistant_message(self, content, tool_calls=None):
        """Add assistant message"""
        message = {
            "role": "assistant",
            "content": content,
            "timestamp": datetime.now()
        }
        if tool_calls:
            message["tool_calls"] = tool_calls

        self.history.append(message)
        self._trim_if_needed()

    def add_tool_result(self, tool_name, result):
        """Add tool execution result"""
        self.history.append({
            "role": "tool",
            "tool": tool_name,
            "result": result,
            "timestamp": datetime.now()
        })
        self._trim_if_needed()

    def _trim_if_needed(self):
        """Trim history if too long"""
        if len(self.history) > self.max_history:
            # Keep first message (usually system prompt) + recent messages
            self.history = [self.history[0]] + self.history[-(self.max_history-1):]

    def get_formatted_history(self):
        """Get history in LLM format"""
        return [
            {
                "role": msg["role"],
                "content": msg.get("content", "")
            }
            for msg in self.history
        ]

    def get_context_summary(self):
        """Get summary of conversation"""
        return {
            "total_messages": len(self.history),
            "user_messages": len([m for m in self.history if m["role"] == "user"]),
            "assistant_messages": len([m for m in self.history if m["role"] == "assistant"]),
            "tool_calls": len([m for m in self.history if m["role"] == "tool"])
        }
```

---

## Error Recovery

### Retry Strategy

```python
class RetryStrategy:
    """Handle failures with retry logic"""

    def __init__(self, max_retries=3, backoff_factor=2):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    async def execute_with_retry(self, tool_func, *args, **kwargs):
        """Execute tool with exponential backoff retry"""
        last_error = None

        for attempt in range(self.max_retries):
            try:
                result = await tool_func(*args, **kwargs)
                return {"success": True, "result": result}

            except ConnectionError as e:
                # Retry on connection errors
                last_error = e
                wait_time = self.backoff_factor ** attempt
                print(f"Connection error, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

            except ValueError as e:
                # Don't retry on validation errors
                return {
                    "success": False,
                    "error": str(e),
                    "error_type": "validation",
                    "retryable": False
                }

            except Exception as e:
                # Retry other errors
                last_error = e
                wait_time = self.backoff_factor ** attempt
                await asyncio.sleep(wait_time)

        # All retries failed
        return {
            "success": False,
            "error": str(last_error),
            "error_type": "retry_exhausted",
            "attempts": self.max_retries
        }
```

### Circuit Breaker

```python
class CircuitBreaker:
    """Prevent repeated failures"""

    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker"""

        if self.state == "open":
            # Check if timeout has passed
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half_open"
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)

            # Success - reset if in half_open
            if self.state == "half_open":
                self.state = "closed"
                self.failures = 0

            return result

        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()

            if self.failures >= self.failure_threshold:
                self.state = "open"
                print(f"Circuit breaker OPENED after {self.failures} failures")

            raise e
```

---

## Performance Optimization

### Caching

```python
from functools import lru_cache
import hashlib

class AgentCache:
    """Cache tool results"""

    def __init__(self, ttl=300):
        self.cache = {}
        self.ttl = ttl

    def key(self, tool_name, args):
        """Generate cache key"""
        args_str = json.dumps(args, sort_keys=True)
        return f"{tool_name}:{hashlib.md5(args_str.encode()).hexdigest()}"

    def get(self, tool_name, args):
        """Get cached result"""
        k = self.key(tool_name, args)

        if k in self.cache:
            timestamp, result = self.cache[k]

            if time.time() - timestamp < self.ttl:
                print(f"Cache HIT: {tool_name}")
                return result
            else:
                del self.cache[k]

        return None

    def set(self, tool_name, args, result):
        """Cache result"""
        k = self.key(tool_name, args)
        self.cache[k] = (time.time(), result)
        print(f"Cache SET: {tool_name}")

# Usage in agent loop
def execute_tool_cached(name, args):
    # Check cache first
    cached = cache.get(name, args)
    if cached:
        return cached

    # Execute tool
    result = execute_tool(name, args)

    # Cache result
    cache.set(name, args, result)

    return result
```

### Streaming Responses

```python
async def streaming_agent_loop(user_query, tools):
    """Agent loop with streaming output"""

    chat = model.start_chat()

    # Stream initial response
    response = chat.send_message(user_query, stream=True)

    for chunk in response:
        # Check for function calls
        if chunk.candidates and chunk.candidates[0].content.parts:
            part = chunk.candidates[0].content.parts[0]

            if hasattr(part, 'function_call'):
                # Execute tool
                fc = part.function_call
                print(f"\n[Calling {fc.name}...]")

                result = execute_tool(fc.name, dict(fc.args))

                # Send result and stream next response
                response = chat.send_message(
                    genai.protos.Content(...),
                    stream=True
                )

                # Continue streaming
                for chunk in response:
                    if chunk.text:
                        print(chunk.text, end="", flush=True)
            else:
                # Stream text
                if chunk.text:
                    print(chunk.text, end="", flush=True)
```

---

## Complete Example

Here's a production-ready agent loop:

```python
import google.generativeai as genai
from typing import Dict, List, Any, Callable
import time
import logging
from datetime import datetime

class ProductionAgentLoop:
    """Production-ready agent loop with all features"""

    def __init__(
        self,
        api_key: str,
        tools: Dict[str, Callable],
        tool_declarations: List[Dict],
        max_iterations: int = 15,
        max_errors: int = 3,
        enable_caching: bool = True,
        enable_logging: bool = True
    ):
        """Initialize agent"""

        # Configure Gemini
        genai.configure(api_key=api_key)

        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-pro",
            tools=[{"function_declarations": tool_declarations}],
            system_instruction="""
You are a helpful SQL assistant. Always:
1. Explore schema before querying
2. Write efficient queries
3. Explain results clearly
4. Handle errors gracefully
            """
        )

        self.tools = tools
        self.max_iterations = max_iterations
        self.max_errors = max_errors

        # Features
        self.cache = AgentCache() if enable_caching else None
        self.logger = self._setup_logger() if enable_logging else None

        # Metrics
        self.metrics = {
            "total_queries": 0,
            "total_tool_calls": 0,
            "total_errors": 0,
            "total_iterations": 0
        }

    def _setup_logger(self):
        """Setup logging"""
        logger = logging.getLogger("agent")
        logger.setLevel(logging.INFO)

        handler = logging.FileHandler("agent.log")
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(handler)

        return logger

    def log(self, level, message, data=None):
        """Log message"""
        if self.logger:
            log_msg = f"{message} | {data}" if data else message
            getattr(self.logger, level.lower())(log_msg)

    def execute_tool(self, name: str, args: Dict) -> Any:
        """Execute tool with caching"""

        # Check cache
        if self.cache:
            cached = self.cache.get(name, args)
            if cached:
                self.log("info", f"Cache hit: {name}")
                return cached

        # Execute
        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")

        result = self.tools[name](**args)

        # Cache result
        if self.cache:
            self.cache.set(name, args, result)

        return result

    async def run(self, user_query: str) -> Dict[str, Any]:
        """Execute agent loop"""

        start_time = time.time()
        self.metrics["total_queries"] += 1

        self.log("info", "Starting agent", {"query": user_query})

        try:
            chat = self.model.start_chat()
            response = chat.send_message(user_query)

            error_count = 0

            for iteration in range(self.max_iterations):
                self.metrics["total_iterations"] += 1

                self.log("info", f"Iteration {iteration + 1}")

                # Check for function calls
                if not response.candidates[0].content.parts:
                    break

                part = response.candidates[0].content.parts[0]

                if hasattr(part, 'function_call'):
                    fc = part.function_call
                    self.metrics["total_tool_calls"] += 1

                    self.log(
                        "info",
                        f"Tool call: {fc.name}",
                        {"args": dict(fc.args)}
                    )

                    try:
                        # Execute tool
                        result = self.execute_tool(fc.name, dict(fc.args))

                        self.log("info", f"Tool success: {fc.name}")

                        # Send result
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

                    except Exception as e:
                        error_count += 1
                        self.metrics["total_errors"] += 1

                        self.log(
                            "error",
                            f"Tool error: {fc.name}",
                            {"error": str(e)}
                        )

                        # Send error to LLM
                        response = chat.send_message(
                            genai.protos.Content(
                                parts=[
                                    genai.protos.Part(
                                        function_response=genai.protos.FunctionResponse(
                                            name=fc.name,
                                            response={
                                                "error": str(e),
                                                "suggestion": "Try a different approach"
                                            }
                                        )
                                    )
                                ]
                            )
                        )

                        # Check error threshold
                        if error_count >= self.max_errors:
                            self.log("error", "Max errors reached")
                            return {
                                "success": False,
                                "error": "Too many errors occurred",
                                "iterations": iteration + 1
                            }

                else:
                    # Final answer
                    final_answer = response.text
                    execution_time = time.time() - start_time

                    self.log(
                        "info",
                        "Agent completed",
                        {
                            "iterations": iteration + 1,
                            "time": execution_time
                        }
                    )

                    return {
                        "success": True,
                        "answer": final_answer,
                        "iterations": iteration + 1,
                        "execution_time": execution_time,
                        "metrics": self.metrics
                    }

            # Max iterations
            self.log("warning", "Max iterations reached")
            return {
                "success": False,
                "error": "Max iterations reached",
                "iterations": self.max_iterations,
                "partial_answer": response.text if response else None
            }

        except Exception as e:
            self.log("error", "Agent failed", {"error": str(e)})
            return {
                "success": False,
                "error": str(e)
            }

    def get_metrics(self):
        """Get agent metrics"""
        return self.metrics

# Usage
agent = ProductionAgentLoop(
    api_key=os.environ["GEMINI_API_KEY"],
    tools=my_tools,
    tool_declarations=my_tool_declarations
)

result = await agent.run("What are the top 10 customers?")
print(result["answer"])
print(f"Completed in {result['iterations']} iterations")
```

---

## Key Takeaways

### ✅ Essential Components

1. **Loop Control**: Max iterations, error thresholds
2. **State Management**: Track conversation history
3. **Error Handling**: Graceful failures, retries
4. **Logging**: Track execution for debugging
5. **Metrics**: Monitor performance

### ⚠️ Common Pitfalls

1. **Infinite Loops**: Always set max_iterations
2. **Memory Leaks**: Trim conversation history
3. **Error Cascade**: One error causing many more
4. **Poor Logging**: Can't debug without logs
5. **No Caching**: Repeated expensive operations

### 🎯 Best Practices

1. **Start simple** - Basic loop first, add features incrementally
2. **Log everything** - You'll need it for debugging
3. **Set limits** - Max iterations, errors, time
4. **Cache wisely** - Cache expensive operations
5. **Handle errors** - Send errors back to LLM to recover
6. **Monitor metrics** - Track performance over time

---

## Next Steps

- [SQL Agent Complete Example](./SQL_AGENT_EXAMPLE.md) - Full working implementation
- [Production Deployment](./PRODUCTION_GUIDE.md) - Deploy to production
- [Testing Guide](./TESTING_GUIDE.md) - Test your agent thoroughly

---

**Remember**: The agent loop is the heart of your AI agent. Make it robust, observable, and efficient!
