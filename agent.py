"""
AI Agent with ReAct (Reason-Act) Pattern

This agent thinks freely and uses tools dynamically like Claude Code.
No rigid pre-planning - just continuous reasoning and tool usage until the task is done.
"""

from typing import TypedDict, Annotated, Sequence, List, Dict, Any, Optional, AsyncGenerator
import operator
import json
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tools import PostgreSQLTools, create_langchain_tools


class AgentState(TypedDict):
    """State of the agent conversation."""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    pending_approval: Optional[Dict[str, Any]]
    db_connected: Optional[bool]


class AgentEvent:
    """Represents an event during agent execution for streaming."""

    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    RESPONSE = "response"
    APPROVAL_NEEDED = "approval_needed"
    ERROR = "error"

    def __init__(self, event_type: str, data: Any = None):
        self.type = event_type
        self.data = data or {}

    def __repr__(self):
        return f"AgentEvent({self.type}, {self.data})"


class SQLAgent:
    """SQL Agent with ReAct pattern - thinks freely, uses tools dynamically."""

    def __init__(self, llm, db_tools: PostgreSQLTools):
        """Initialize SQL Agent."""
        self.llm = llm
        self.db_tools = db_tools
        self.tools = create_langchain_tools(db_tools)
        self.tool_map = {tool.name: tool for tool in self.tools}

        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)

    def _create_system_prompt(self) -> str:
        """Create the system prompt for the agent."""
        return """You are an expert PostgreSQL database assistant. You help users explore databases and answer questions about their data.

## How You Work
You think step-by-step and use tools to gather information. After each tool result, you analyze what you learned and decide what to do next. You continue until you have enough information to fully answer the user's question.

## Available Tools
- list_schemas(): Get all schemas in the database - ALWAYS start here if unsure about structure
- list_tables(schema_name): Get all tables in a schema
- inspect_schema(table_name, schema_name='public'): Get columns and types for a table
- get_table_relationships(table_name, schema_name='public'): Get foreign key relationships
- validate_sql(sql): Check if a SQL query is valid and safe
- execute_query(sql): Execute a SELECT query (requires user approval)

## Critical Rules
1. ALWAYS explore first - if you don't know the database structure, use list_schemas() and list_tables()
2. NEVER assume table names - verify they exist first
3. NEVER give up - if something doesn't exist, look for alternatives
4. When you need actual data, use execute_query() - don't just describe what you would do
5. Be thorough - use multiple tools if needed to fully answer the question
6. After getting data, EXPLAIN it clearly to the user

## Example Reasoning
User: "How many users are there?"
1. First, I'll list tables to find the users table
2. [calls list_tables] Found 'users' table
3. Now I'll query the count
4. [calls execute_query with SELECT COUNT(*)] Got result: 150
5. "There are 150 users in the database."

Think step by step. Use tools. Get real data. Answer completely."""

    async def process_message_streaming(
        self,
        user_message: str,
        state: Optional[AgentState] = None
    ) -> AsyncGenerator[AgentEvent, None]:
        """Process message with ReAct loop - think, act, observe, repeat."""

        if state is None:
            state = {
                "messages": [],
                "pending_approval": None,
                "db_connected": bool(self.db_tools.connection_params)
            }

        # Build conversation messages
        messages = list(state.get("messages", []))

        # Add system prompt at the start
        system_prompt = self._create_system_prompt()

        # Add the user's message
        messages.append(HumanMessage(content=user_message))

        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="messages"),
        ])

        chain = prompt | self.llm_with_tools

        # ReAct loop - continue until LLM gives final answer (no tool calls)
        max_iterations = 30  # Safety limit
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            yield AgentEvent(AgentEvent.THINKING, {"iteration": iteration})

            try:
                response = await chain.ainvoke({"messages": messages})
                messages.append(response)
            except Exception as e:
                yield AgentEvent(AgentEvent.ERROR, {"error": str(e)})
                return

            # Check if LLM wants to use tools
            if hasattr(response, 'tool_calls') and response.tool_calls:
                # Process each tool call
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_input = tool_call["args"]
                    tool_call_id = tool_call["id"]

                    # Special handling for execute_query - needs approval
                    if tool_name == "execute_query":
                        sql_query = tool_input.get("sql", "")

                        yield AgentEvent(AgentEvent.APPROVAL_NEEDED, {
                            "sql": sql_query,
                            "tool_call_id": tool_call_id,
                            "messages": messages,
                            "db_connected": state.get("db_connected", False)
                        })
                        return  # Wait for approval

                    # Execute other tools immediately
                    yield AgentEvent(AgentEvent.TOOL_CALL, {
                        "tool": tool_name,
                        "args": tool_input
                    })

                    tool = self.tool_map.get(tool_name)
                    if tool:
                        try:
                            result = tool.func(**tool_input) if tool_input else tool.func()
                        except Exception as e:
                            result = json.dumps({"error": str(e)})
                    else:
                        result = json.dumps({"error": f"Tool '{tool_name}' not found"})

                    yield AgentEvent(AgentEvent.TOOL_RESULT, {
                        "tool": tool_name,
                        "result": result
                    })

                    # Add tool result to messages so LLM sees it
                    tool_message = ToolMessage(content=str(result), tool_call_id=tool_call_id)
                    messages.append(tool_message)

                # Continue the loop - LLM will process tool results
                continue

            else:
                # No tool calls - LLM is giving final answer
                final_response = response.content if hasattr(response, 'content') else ""

                yield AgentEvent(AgentEvent.RESPONSE, {
                    "content": final_response,
                    "state": {
                        "messages": messages,
                        "pending_approval": None,
                        "db_connected": state.get("db_connected", False)
                    }
                })
                return

        # Reached max iterations
        yield AgentEvent(AgentEvent.ERROR, {
            "error": f"Reached maximum iterations ({max_iterations}). The task may be too complex."
        })

    async def continue_after_approval(
        self,
        approved: bool,
        sql: str,
        tool_call_id: str,
        state: Dict[str, Any]
    ) -> AsyncGenerator[AgentEvent, None]:
        """Continue execution after SQL approval."""

        messages = state.get("messages", [])
        db_connected = state.get("db_connected", False)

        if not approved:
            # User rejected - add rejection message and continue
            tool_message = ToolMessage(
                content=json.dumps({
                    "success": False,
                    "error": "Query rejected by user. Try a different approach or ask the user for guidance."
                }),
                tool_call_id=tool_call_id
            )
            messages.append(tool_message)

            yield AgentEvent(AgentEvent.TOOL_RESULT, {
                "tool": "execute_query",
                "result": "Query rejected by user"
            })
        else:
            # Execute the approved query
            yield AgentEvent(AgentEvent.TOOL_CALL, {
                "tool": "execute_query",
                "args": {"sql": sql}
            })

            try:
                query_result = self.db_tools.execute_query(sql)
            except Exception as e:
                query_result = {"error": str(e)}

            result_str = json.dumps(query_result) if isinstance(query_result, dict) else str(query_result)

            tool_message = ToolMessage(
                content=result_str,
                tool_call_id=tool_call_id
            )
            messages.append(tool_message)

            yield AgentEvent(AgentEvent.TOOL_RESULT, {
                "tool": "execute_query",
                "result": query_result
            })

        # Continue the ReAct loop
        system_prompt = self._create_system_prompt()

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="messages"),
        ])

        chain = prompt | self.llm_with_tools

        max_iterations = 20
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            yield AgentEvent(AgentEvent.THINKING, {"iteration": iteration})

            try:
                response = await chain.ainvoke({"messages": messages})
                messages.append(response)
            except Exception as e:
                yield AgentEvent(AgentEvent.ERROR, {"error": str(e)})
                return

            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_input = tool_call["args"]
                    tc_id = tool_call["id"]

                    if tool_name == "execute_query":
                        yield AgentEvent(AgentEvent.APPROVAL_NEEDED, {
                            "sql": tool_input.get("sql", ""),
                            "tool_call_id": tc_id,
                            "messages": messages,
                            "db_connected": db_connected
                        })
                        return

                    yield AgentEvent(AgentEvent.TOOL_CALL, {
                        "tool": tool_name,
                        "args": tool_input
                    })

                    tool = self.tool_map.get(tool_name)
                    try:
                        result = tool.func(**tool_input) if tool and tool_input else (
                            tool.func() if tool else json.dumps({"error": "Tool not found"})
                        )
                    except Exception as e:
                        result = json.dumps({"error": str(e)})

                    yield AgentEvent(AgentEvent.TOOL_RESULT, {
                        "tool": tool_name,
                        "result": result
                    })

                    messages.append(ToolMessage(content=str(result), tool_call_id=tc_id))

                continue
            else:
                final_response = response.content if hasattr(response, 'content') else ""

                yield AgentEvent(AgentEvent.RESPONSE, {
                    "content": final_response,
                    "state": {
                        "messages": messages,
                        "pending_approval": None,
                        "db_connected": db_connected
                    }
                })
                return

        yield AgentEvent(AgentEvent.ERROR, {"error": "Reached maximum iterations"})

    # Backwards compatibility methods
    async def process_message(self, user_message: str, state: Optional[AgentState] = None):
        """Non-streaming version for backwards compatibility."""
        final_response = ""
        final_state = state or {}

        async for event in self.process_message_streaming(user_message, state):
            if event.type == AgentEvent.RESPONSE:
                final_response = event.data.get("content", "")
                final_state = event.data.get("state", state)
            elif event.type == AgentEvent.APPROVAL_NEEDED:
                return (
                    f"I want to execute:\n```sql\n{event.data['sql']}\n```\nApprove?",
                    event.data,
                    event.data.get("state", state)
                )
            elif event.type == AgentEvent.ERROR:
                final_response = f"Error: {event.data.get('error', 'Unknown')}"

        return final_response, None, final_state

    async def execute_approved_query(self, approval_data: Dict[str, Any], approved: bool):
        """Non-streaming approval handler."""
        final_response = ""
        final_state = approval_data.get("state", {})

        async for event in self.continue_after_approval(
            approved=approved,
            sql=approval_data.get("sql", ""),
            tool_call_id=approval_data.get("tool_call_id", ""),
            state=approval_data
        ):
            if event.type == AgentEvent.RESPONSE:
                final_response = event.data.get("content", "")
                final_state = event.data.get("state", final_state)
            elif event.type == AgentEvent.ERROR:
                final_response = f"Error: {event.data.get('error', 'Unknown')}"

        return final_response, final_state

    def get_conversation_history(self, state: AgentState) -> List[Dict[str, str]]:
        """Get conversation history."""
        history = []
        for msg in state.get("messages", []):
            if isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                if hasattr(msg, 'content') and msg.content:
                    history.append({"role": "assistant", "content": msg.content})
        return history

    @staticmethod
    def create_agent(provider: str, api_key: str, model: str, db_tools: PostgreSQLTools) -> 'SQLAgent':
        """Create an agent with specified provider."""
        provider = provider.lower()

        if provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model=model,
                google_api_key=api_key,
                temperature=0,
                convert_system_message_to_human=True
            )
        elif provider == "openai":
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model=model, api_key=api_key, temperature=0)
        elif provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(model=model, api_key=api_key, temperature=0)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        return SQLAgent(llm, db_tools)


# Import fallback models
from api_models import FALLBACK_MODELS
PROVIDER_MODELS = FALLBACK_MODELS
