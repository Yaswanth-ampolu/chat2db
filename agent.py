"""
Autonomous SQL Agent with Belief-Driven Loop Architecture

This agent behaves like a real exploratory engineer:
- Discovers database structure dynamically
- Maintains explicit beliefs about what it knows
- Uses a mutable TODO list that adapts based on observations
- Reflects after every query and replans as needed
- Never assumes - always verifies
- Never gives up on empty results - investigates why
"""

from typing import TypedDict, Annotated, Sequence, List, Dict, Any, Optional, AsyncGenerator, Set
from dataclasses import dataclass, field
from enum import Enum
import operator
import json
import logging
from pathlib import Path
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tools import PostgreSQLTools, create_langchain_tools

# Set up file logging for debugging
LOG_DIR = Path.home() / ".chat2sql" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "agent.log"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a'),
    ]
)
logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State of the agent conversation."""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    pending_approval: Optional[Dict[str, Any]]
    db_connected: Optional[bool]


class TodoStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


@dataclass
class TodoItem:
    """A mutable TODO item that can be reprioritized."""
    id: str
    description: str
    status: TodoStatus = TodoStatus.PENDING
    priority: int = 5  # 1 = highest, 10 = lowest
    result: Optional[str] = None
    blocked_reason: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority
        }


@dataclass
class BeliefState:
    """
    Tracks what the agent KNOWS (verified) vs ASSUMES.
    All beliefs must be grounded in actual query results.
    """
    # Verified facts from tool calls
    known_schemas: Set[str] = field(default_factory=set)
    known_tables: Dict[str, List[str]] = field(default_factory=dict)  # schema -> [tables]
    known_columns: Dict[str, List[Dict]] = field(default_factory=dict)  # table -> [columns]
    known_relationships: Dict[str, Dict] = field(default_factory=dict)  # table -> {fks, refs}

    # Row counts we've verified
    verified_row_counts: Dict[str, int] = field(default_factory=dict)  # table -> count

    # Sample data we've seen
    sampled_tables: Dict[str, List[Dict]] = field(default_factory=dict)  # table -> sample rows

    # Proven facts from queries
    proven_facts: List[str] = field(default_factory=list)

    # Assumptions that were disproven
    disproven_assumptions: List[str] = field(default_factory=list)

    # Current hypotheses being tested
    active_hypotheses: List[str] = field(default_factory=list)

    def has_explored_schemas(self) -> bool:
        return len(self.known_schemas) > 0

    def has_explored_tables(self, schema: str) -> bool:
        return schema in self.known_tables

    def has_inspected_table(self, table: str) -> bool:
        return table in self.known_columns

    def has_sampled_table(self, table: str) -> bool:
        return table in self.sampled_tables

    def add_proven_fact(self, fact: str):
        if fact not in self.proven_facts:
            self.proven_facts.append(fact)

    def add_disproven_assumption(self, assumption: str):
        if assumption not in self.disproven_assumptions:
            self.disproven_assumptions.append(assumption)

    def to_context_string(self) -> str:
        """Generate a context string for the LLM."""
        lines = ["## Current Knowledge State\n"]

        if self.known_schemas:
            lines.append(f"**Known Schemas:** {', '.join(self.known_schemas)}")
        else:
            lines.append("**Known Schemas:** Not yet discovered")

        if self.known_tables:
            lines.append("\n**Known Tables:**")
            for schema, tables in self.known_tables.items():
                lines.append(f"  {schema}: {', '.join(tables[:10])}")
                if len(tables) > 10:
                    lines.append(f"    ... and {len(tables) - 10} more")

        if self.known_columns:
            lines.append("\n**Inspected Tables:**")
            for table, columns in self.known_columns.items():
                col_names = [c.get("name", str(c)) for c in columns[:5]]
                lines.append(f"  {table}: {', '.join(col_names)}...")

        if self.verified_row_counts:
            lines.append("\n**Verified Row Counts:**")
            for table, count in self.verified_row_counts.items():
                lines.append(f"  {table}: {count} rows")

        if self.proven_facts:
            lines.append("\n**Proven Facts:**")
            for fact in self.proven_facts[-5:]:  # Last 5 facts
                lines.append(f"  ✓ {fact}")

        if self.disproven_assumptions:
            lines.append("\n**Disproven Assumptions:**")
            for assumption in self.disproven_assumptions[-3:]:
                lines.append(f"  ✗ {assumption}")

        return "\n".join(lines)


@dataclass
class HistoryEntry:
    """A single entry in the agent's action history."""
    action_type: str  # "tool_call", "observation", "reflection", "todo_update"
    tool_name: Optional[str] = None
    tool_args: Optional[Dict] = None
    result: Optional[Any] = None
    reflection: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "type": self.action_type,
            "tool": self.tool_name,
            "args": self.tool_args,
            "result_preview": str(self.result)[:200] if self.result else None,
            "error": self.error
        }


@dataclass
class AgentHistory:
    """Tracks all agent actions for learning and debugging."""
    entries: List[HistoryEntry] = field(default_factory=list)

    def add_tool_call(self, tool_name: str, args: Dict):
        self.entries.append(HistoryEntry(
            action_type="tool_call",
            tool_name=tool_name,
            tool_args=args
        ))

    def add_observation(self, tool_name: str, result: Any, error: Optional[str] = None):
        self.entries.append(HistoryEntry(
            action_type="observation",
            tool_name=tool_name,
            result=result,
            error=error
        ))

    def add_reflection(self, reflection: str):
        self.entries.append(HistoryEntry(
            action_type="reflection",
            reflection=reflection
        ))

    def get_recent_errors(self) -> List[str]:
        errors = []
        for entry in reversed(self.entries[-10:]):
            if entry.error:
                errors.append(entry.error)
        return errors

    def get_empty_result_count(self) -> int:
        count = 0
        for entry in self.entries:
            if entry.action_type == "observation" and entry.tool_name == "execute_query":
                if isinstance(entry.result, dict) and len(entry.result.get("rows", [])) == 0:
                    count += 1
        return count


class AgentEvent:
    """Events emitted during agent execution for UI streaming."""
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    RESPONSE = "response"
    APPROVAL_NEEDED = "approval_needed"
    ERROR = "error"
    BELIEF_UPDATE = "belief_update"
    TODO_UPDATE = "todo_update"
    REFLECTION = "reflection"
    PHASE = "phase"

    def __init__(self, event_type: str, data: Any = None):
        self.type = event_type
        self.data = data or {}

    def __repr__(self):
        return f"AgentEvent({self.type}, {self.data})"


class SQLAgent:
    """
    Autonomous SQL Agent with Belief-Driven Loop Architecture.

    This agent:
    1. Assesses environment before planning
    2. Maintains explicit beliefs about database structure
    3. Uses mutable TODO lists that adapt based on observations
    4. Reflects after every query and replans
    5. Never assumes - always verifies
    6. Never gives up - investigates failures
    """

    def __init__(self, llm, db_tools: PostgreSQLTools):
        self.llm = llm
        self.db_tools = db_tools
        self.tools = create_langchain_tools(db_tools)
        self.tool_map = {tool.name: tool for tool in self.tools}
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # Agent state
        self.beliefs = BeliefState()
        self.todos: List[TodoItem] = []
        self.history = AgentHistory()
        self.current_goal = ""
        self.goal_satisfied = False

    def _reset_state(self):
        """Reset agent state for a new query."""
        self.beliefs = BeliefState()
        self.todos = []
        self.history = AgentHistory()
        self.goal_satisfied = False

    def _create_system_prompt(self) -> str:
        """Create the system prompt with current belief state."""
        return f"""You are an autonomous SQL exploration agent. You think like a cautious database engineer dropped into an unknown production database.

## Your Approach
1. EXPLORE before assuming - never guess table/column names
2. VERIFY with queries - don't trust names alone
3. ADAPT when things fail - empty results mean investigate more
4. REFLECT after every action - update your understanding

## Current Knowledge
{self.beliefs.to_context_string()}

## Current TODO List
{self._format_todos()}

## Available Tools
- list_schemas(): Discover all schemas - ALWAYS call first if schemas unknown
- list_tables(schema_name): Discover tables in a schema
- inspect_schema(table_name, schema_name='public'): Get column details for a table
- get_table_relationships(table_name, schema_name='public'): Get foreign keys
- validate_sql(sql): Check if SQL is valid before running
- execute_query(sql): Run a SELECT query (requires user approval)

## Critical Rules
1. If you don't know the schemas, call list_schemas() FIRST
2. If you don't know the tables, call list_tables() BEFORE querying
3. If you haven't inspected a table, call inspect_schema() BEFORE querying it
4. If a query returns 0 rows, INVESTIGATE - don't just report "no data"
5. After EVERY tool result, reflect: What did I learn? What should I do next?
6. Update your TODO list based on observations
7. Never conclude "data doesn't exist" without thorough exploration

## Response Format
After using tools, provide your reasoning:
1. What did I observe?
2. What does this confirm or disprove?
3. What should I do next?
4. Is the user's goal satisfied?

If goal is satisfied, give a complete answer based on VERIFIED data only."""

    def _format_todos(self) -> str:
        """Format current TODO list."""
        if not self.todos:
            return "No TODOs yet - environment assessment needed"

        lines = []
        for todo in sorted(self.todos, key=lambda t: (t.status != TodoStatus.IN_PROGRESS, t.priority)):
            status_icon = {
                TodoStatus.PENDING: "⬜",
                TodoStatus.IN_PROGRESS: "🔄",
                TodoStatus.COMPLETED: "✅",
                TodoStatus.BLOCKED: "⛔",
                TodoStatus.CANCELLED: "❌"
            }.get(todo.status, "?")
            lines.append(f"{status_icon} [{todo.priority}] {todo.description}")
        return "\n".join(lines) if lines else "No active TODOs"

    def _add_todo(self, description: str, priority: int = 5) -> TodoItem:
        """Add a new TODO item."""
        todo_id = f"todo_{len(self.todos) + 1}"
        todo = TodoItem(id=todo_id, description=description, priority=priority)
        self.todos.append(todo)
        return todo

    def _get_next_todo(self) -> Optional[TodoItem]:
        """Get highest priority pending TODO."""
        pending = [t for t in self.todos if t.status == TodoStatus.PENDING]
        if pending:
            return min(pending, key=lambda t: t.priority)
        return None

    def _complete_todo(self, todo_id: str, result: str = ""):
        """Mark a TODO as completed."""
        for todo in self.todos:
            if todo.id == todo_id:
                todo.status = TodoStatus.COMPLETED
                todo.result = result
                break

    def _update_beliefs_from_result(self, tool_name: str, args: Dict, result: Any):
        """Update belief state based on tool result."""
        logger.debug(f"Updating beliefs from {tool_name}: args={args}")

        try:
            if isinstance(result, str):
                result = json.loads(result)
        except:
            pass

        logger.debug(f"Parsed result type: {type(result)}, keys: {result.keys() if isinstance(result, dict) else 'N/A'}")

        if not isinstance(result, dict):
            return

        if "error" in result:
            logger.warning(f"Tool {tool_name} returned error: {result.get('error')}")
            return

        if tool_name == "list_schemas":
            schemas = result.get("schemas", [])
            self.beliefs.known_schemas = set(schemas)
            self.beliefs.add_proven_fact(f"Database has {len(schemas)} schemas: {', '.join(schemas)}")
            logger.info(f"Discovered schemas: {schemas}")

        elif tool_name == "list_tables":
            schema = args.get("schema_name", "public")
            tables = result.get("tables", [])
            table_names = [t.get("name", t) if isinstance(t, dict) else t for t in tables]
            self.beliefs.known_tables[schema] = table_names
            self.beliefs.add_proven_fact(f"Schema '{schema}' has {len(table_names)} tables")
            logger.info(f"Discovered {len(table_names)} tables in {schema}")

        elif tool_name == "inspect_schema":
            table = args.get("table_name", "")
            schema = args.get("schema_name", "public")
            full_name = f"{schema}.{table}"
            columns = result.get("columns", [])
            self.beliefs.known_columns[full_name] = columns
            col_names = [c.get("name", c) for c in columns]
            self.beliefs.add_proven_fact(f"Table '{full_name}' has columns: {', '.join(col_names[:5])}...")
            logger.info(f"Inspected {full_name}: {len(columns)} columns")

        elif tool_name == "get_table_relationships":
            table = args.get("table_name", "")
            schema = args.get("schema_name", "public")
            full_name = f"{schema}.{table}"
            self.beliefs.known_relationships[full_name] = result
            logger.info(f"Got relationships for {full_name}")

        elif tool_name == "execute_query":
            # IMPORTANT: tools.py uses "data" not "rows"
            rows = result.get("data", result.get("rows", []))
            row_count = result.get("row_count", len(rows) if rows else 0)
            sql = args.get("sql", "").lower()

            logger.info(f"Query result: {row_count} rows returned")
            logger.debug(f"Query data: {rows[:3] if rows else 'empty'}")  # Log first 3 rows

            # Track row counts from COUNT queries
            if "count(*)" in sql or "count(1)" in sql:
                if rows and len(rows) >= 1:
                    # COUNT returns a single row with the count value
                    first_row = rows[0]
                    count_val = list(first_row.values())[0] if first_row else 0
                    logger.info(f"COUNT query result: {count_val}")

                    # Try to extract table name from query
                    if "from " in sql:
                        table_part = sql.split("from ")[1].split()[0].strip()
                        self.beliefs.verified_row_counts[table_part] = count_val
                        self.beliefs.add_proven_fact(f"Table '{table_part}' has {count_val} rows")

            # Track sampled data
            if rows:
                if "from " in sql:
                    table_part = sql.split("from ")[1].split()[0].strip()
                    if table_part not in self.beliefs.sampled_tables:
                        self.beliefs.sampled_tables[table_part] = rows[:5]
                        self.beliefs.add_proven_fact(f"Sampled {len(rows)} rows from '{table_part}'")
            elif "select" in sql:
                # Empty result - record this
                if "from " in sql:
                    table_part = sql.split("from ")[1].split()[0].strip()
                    self.beliefs.add_proven_fact(f"Query on '{table_part}' returned 0 rows (might need different conditions)")
                    logger.warning(f"Empty result from query on {table_part}")

    async def _assess_environment(self) -> AsyncGenerator[AgentEvent, None]:
        """Phase 1: Discover database structure before planning."""
        yield AgentEvent(AgentEvent.PHASE, {"phase": "environment_assessment", "message": "Discovering database structure..."})

        # Step 1: Discover schemas if unknown
        if not self.beliefs.has_explored_schemas():
            yield AgentEvent(AgentEvent.TOOL_CALL, {"tool": "list_schemas", "args": {}})

            try:
                result = self.db_tools.list_schemas()
                self.history.add_observation("list_schemas", result)
                self._update_beliefs_from_result("list_schemas", {}, result)
                yield AgentEvent(AgentEvent.TOOL_RESULT, {"tool": "list_schemas", "result": result})
            except Exception as e:
                self.history.add_observation("list_schemas", None, str(e))
                yield AgentEvent(AgentEvent.TOOL_RESULT, {"tool": "list_schemas", "result": {"error": str(e)}})

        # Step 2: Discover tables in each schema
        for schema in list(self.beliefs.known_schemas):
            if not self.beliefs.has_explored_tables(schema):
                yield AgentEvent(AgentEvent.TOOL_CALL, {"tool": "list_tables", "args": {"schema_name": schema}})

                try:
                    result = self.db_tools.list_tables(schema)
                    self.history.add_observation("list_tables", result)
                    self._update_beliefs_from_result("list_tables", {"schema_name": schema}, result)
                    yield AgentEvent(AgentEvent.TOOL_RESULT, {"tool": "list_tables", "result": result})
                except Exception as e:
                    self.history.add_observation("list_tables", None, str(e))
                    yield AgentEvent(AgentEvent.TOOL_RESULT, {"tool": "list_tables", "result": {"error": str(e)}})

        yield AgentEvent(AgentEvent.BELIEF_UPDATE, {"beliefs": self.beliefs.to_context_string()})

    async def _generate_initial_todos(self, user_goal: str) -> AsyncGenerator[AgentEvent, None]:
        """Generate initial TODO list based on user goal and current beliefs."""
        yield AgentEvent(AgentEvent.PHASE, {"phase": "planning", "message": "Creating investigation plan..."})

        # Use LLM to generate TODOs based on goal and current knowledge
        planning_prompt = f"""Based on the user's goal and current database knowledge, create a TODO list.

User Goal: {user_goal}

{self.beliefs.to_context_string()}

Create 3-7 specific, actionable TODO items to satisfy this goal.
Consider:
1. What tables might be relevant?
2. What do we need to verify before querying?
3. What data do we need to retrieve?

Output as JSON array:
[
  {{"description": "...", "priority": 1-10}},
  ...
]

Lower priority number = more urgent. Start with exploration tasks."""

        try:
            response = await self.llm.ainvoke([HumanMessage(content=planning_prompt)])
            content = response.content.strip()

            # Parse JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            todos_data = json.loads(content.strip())

            for todo_data in todos_data:
                self._add_todo(
                    description=todo_data.get("description", "Unknown task"),
                    priority=todo_data.get("priority", 5)
                )
        except Exception as e:
            # Fallback: create basic TODOs
            self._add_todo("Identify relevant tables for the user's request", priority=1)
            self._add_todo("Inspect schema of candidate tables", priority=2)
            self._add_todo("Query data to answer user's question", priority=3)
            self._add_todo("Verify results and provide answer", priority=4)

        yield AgentEvent(AgentEvent.TODO_UPDATE, {"todos": [t.to_dict() for t in self.todos]})

    async def _reflect_and_replan(self, tool_name: str, result: Any, current_todo: Optional[TodoItem]) -> AsyncGenerator[AgentEvent, None]:
        """Reflect on result and update plan."""
        logger.debug(f"Reflecting on {tool_name} result")

        # Parse result
        try:
            if isinstance(result, str):
                parsed_result = json.loads(result)
            else:
                parsed_result = result
        except:
            parsed_result = {"raw": str(result)}

        logger.debug(f"Parsed result for reflection: {str(parsed_result)[:500]}")

        # Check for empty results or errors
        is_empty = False
        is_error = False
        actual_data = None
        row_count = 0

        if isinstance(parsed_result, dict):
            if "error" in parsed_result:
                is_error = True
                logger.warning(f"Tool returned error: {parsed_result.get('error')}")
            elif tool_name == "execute_query":
                # IMPORTANT: tools.py uses "data" not "rows"
                actual_data = parsed_result.get("data", parsed_result.get("rows", []))
                row_count = parsed_result.get("row_count", len(actual_data) if actual_data else 0)
                is_empty = row_count == 0
                logger.info(f"Query reflection: {row_count} rows, is_empty={is_empty}")

        # Build clear reflection prompt with ACTUAL data
        result_summary = json.dumps(parsed_result)[:1500]  # Increased limit
        if tool_name == "execute_query" and actual_data:
            result_summary = f"Row count: {row_count}. Data: {json.dumps(actual_data[:10])}"  # Show up to 10 rows

        reflection_prompt = f"""Reflect on this tool result and decide next steps.

## Tool Execution
Tool: {tool_name}
Current TODO: {current_todo.description if current_todo else 'None'}

## ACTUAL RESULT (this is the real data - do not hallucinate):
{result_summary}

## Status
- Is Empty/Error: {is_empty or is_error}
- Row Count: {row_count}

## User Goal: {self.current_goal}

## Current Knowledge:
{self.beliefs.to_context_string()}

## Instructions
Based on the ACTUAL RESULT above (not what you expect), answer:
1. What does this result tell us? (Use the actual data values!)
2. Is the current TODO complete, blocked, or needs more work?
3. Should we add new TODOs?
4. If result was empty/error, what should we investigate?
5. Is the user's goal satisfied based on the ACTUAL data?

Output as JSON:
{{
  "observation": "what the ACTUAL result tells us (include specific values from the data)",
  "todo_status": "completed|blocked|continue",
  "new_todos": [{{"description": "...", "priority": 1-10}}],
  "goal_satisfied": true/false,
  "next_action": "what to do next"
}}"""

        try:
            response = await self.llm.ainvoke([HumanMessage(content=reflection_prompt)])
            content = response.content.strip()
            logger.debug(f"Reflection LLM response: {content[:500]}")

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            reflection = json.loads(content.strip())
            logger.info(f"Reflection: obs='{reflection.get('observation', '')[:100]}', goal_satisfied={reflection.get('goal_satisfied')}")

            # Update TODO status
            if current_todo:
                status = reflection.get("todo_status", "continue")
                if status == "completed":
                    current_todo.status = TodoStatus.COMPLETED
                    current_todo.result = reflection.get("observation", "")
                elif status == "blocked":
                    current_todo.status = TodoStatus.BLOCKED
                    current_todo.blocked_reason = reflection.get("observation", "")

            # Add new TODOs
            for new_todo in reflection.get("new_todos", []):
                self._add_todo(
                    description=new_todo.get("description", ""),
                    priority=new_todo.get("priority", 5)
                )

            # Check goal satisfaction
            self.goal_satisfied = reflection.get("goal_satisfied", False)

            # Record reflection
            self.history.add_reflection(reflection.get("observation", ""))

            yield AgentEvent(AgentEvent.REFLECTION, {
                "observation": reflection.get("observation", ""),
                "next_action": reflection.get("next_action", ""),
                "goal_satisfied": self.goal_satisfied
            })

        except Exception as e:
            logger.error(f"Reflection failed: {e}")
            # Basic reflection on failure
            if is_empty and tool_name == "execute_query":
                self._add_todo("Investigate why query returned no results", priority=1)
                self._add_todo("Check table row count", priority=2)
                self._add_todo("Sample table data without filters", priority=3)

            yield AgentEvent(AgentEvent.REFLECTION, {
                "observation": f"Error in reflection: {e}",
                "next_action": "Continue with next TODO"
            })

        yield AgentEvent(AgentEvent.TODO_UPDATE, {"todos": [t.to_dict() for t in self.todos]})

    async def process_message_streaming(
        self,
        user_message: str,
        state: Optional[AgentState] = None
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Main agent loop: Assess → Plan → Execute → Observe → Reflect → Repeat
        """
        logger.info(f"=== NEW MESSAGE: {user_message} ===")

        if state is None:
            state = {
                "messages": [],
                "pending_approval": None,
                "db_connected": bool(self.db_tools.connection_params)
            }

        # Reset state for new query
        self._reset_state()
        self.current_goal = user_message

        messages = list(state.get("messages", []))
        messages.append(HumanMessage(content=user_message))

        # Phase 1: Environment Assessment
        logger.info("Phase 1: Environment Assessment")
        yield AgentEvent(AgentEvent.THINKING, {"phase": "assessment"})
        async for event in self._assess_environment():
            yield event

        # Phase 2: Generate Initial TODOs
        logger.info("Phase 2: Planning")
        async for event in self._generate_initial_todos(user_message):
            yield event

        # Phase 3: Main Agent Loop
        logger.info("Phase 3: Execution Loop")
        max_iterations = 30
        iteration = 0

        while not self.goal_satisfied and iteration < max_iterations:
            iteration += 1
            logger.debug(f"Loop iteration {iteration}")

            # Check if we have pending TODOs
            current_todo = self._get_next_todo()
            if not current_todo:
                # No more TODOs - check if goal is satisfied
                if not self.goal_satisfied:
                    # Add fallback TODO
                    self._add_todo("Verify if user's goal can be satisfied with current data", priority=1)
                    current_todo = self._get_next_todo()
                else:
                    break

            if not current_todo:
                break

            current_todo.status = TodoStatus.IN_PROGRESS
            logger.info(f"Working on TODO: {current_todo.description}")

            yield AgentEvent(AgentEvent.THINKING, {
                "iteration": iteration,
                "todo": current_todo.description
            })

            # Generate action for current TODO
            system_prompt = self._create_system_prompt()

            action_prompt = f"""Current TODO: {current_todo.description}

Based on your current knowledge and this TODO, decide what tool to use next.
If you need to query data, use execute_query.
If you need to explore structure, use list_tables, inspect_schema, etc.

Think step by step:
1. What do I need to accomplish this TODO?
2. What tool should I use?
3. What are the exact arguments?

Then call the appropriate tool."""

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="messages"),
                ("human", action_prompt)
            ])

            chain = prompt | self.llm_with_tools

            try:
                response = await chain.ainvoke({"messages": messages})
                messages.append(response)
            except Exception as e:
                yield AgentEvent(AgentEvent.ERROR, {"error": str(e)})
                continue

            # Process tool calls
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_call_id = tool_call["id"]

                    logger.info(f"Tool call: {tool_name}({tool_args})")
                    self.history.add_tool_call(tool_name, tool_args)

                    # Handle execute_query - needs approval
                    if tool_name == "execute_query":
                        sql = tool_args.get("sql", "")
                        logger.info(f"SQL requires approval: {sql}")

                        yield AgentEvent(AgentEvent.APPROVAL_NEEDED, {
                            "sql": sql,
                            "tool_call_id": tool_call_id,
                            "messages": messages,
                            "current_todo": current_todo.to_dict() if current_todo else None,
                            "db_connected": state.get("db_connected", False)
                        })
                        return

                    # Execute other tools
                    yield AgentEvent(AgentEvent.TOOL_CALL, {"tool": tool_name, "args": tool_args})

                    tool = self.tool_map.get(tool_name)
                    if tool:
                        try:
                            result = tool.func(**tool_args) if tool_args else tool.func()
                            logger.debug(f"Tool {tool_name} result: {str(result)[:500]}")
                        except Exception as e:
                            result = json.dumps({"error": str(e)})
                            logger.error(f"Tool {tool_name} error: {e}")
                    else:
                        result = json.dumps({"error": f"Tool '{tool_name}' not found"})
                        logger.error(f"Tool not found: {tool_name}")

                    self.history.add_observation(tool_name, result)
                    self._update_beliefs_from_result(tool_name, tool_args, result)

                    yield AgentEvent(AgentEvent.TOOL_RESULT, {"tool": tool_name, "result": result})

                    messages.append(ToolMessage(content=str(result), tool_call_id=tool_call_id))

                    # Reflect and replan after each tool result
                    async for event in self._reflect_and_replan(tool_name, result, current_todo):
                        yield event

            else:
                # No tool call - LLM gave text response
                if hasattr(response, 'content') and response.content:
                    # Check if this is the final answer
                    if current_todo:
                        current_todo.status = TodoStatus.COMPLETED
                        current_todo.result = response.content

                    # Check if all TODOs are done
                    pending = [t for t in self.todos if t.status == TodoStatus.PENDING]
                    if not pending:
                        self.goal_satisfied = True

        # Generate final response
        yield AgentEvent(AgentEvent.PHASE, {"phase": "synthesis", "message": "Synthesizing final answer..."})

        final_prompt = f"""Based on your exploration and verified data, provide a complete answer to the user.

User's Question: {self.current_goal}

{self.beliefs.to_context_string()}

Completed TODOs:
{chr(10).join([f"✓ {t.description}: {t.result}" for t in self.todos if t.status == TodoStatus.COMPLETED])}

Provide a clear, comprehensive answer based ONLY on verified data.
If something couldn't be determined, explain why and what was tried."""

        try:
            final_response = await self.llm.ainvoke([HumanMessage(content=final_prompt)])
            final_content = final_response.content
        except Exception as e:
            final_content = f"Error generating final response: {e}"

        messages.append(AIMessage(content=final_content))

        yield AgentEvent(AgentEvent.RESPONSE, {
            "content": final_content,
            "state": {
                "messages": messages,
                "pending_approval": None,
                "db_connected": state.get("db_connected", False)
            },
            "beliefs": self.beliefs.to_context_string(),
            "todos": [t.to_dict() for t in self.todos]
        })

    async def continue_after_approval(
        self,
        approved: bool,
        sql: str,
        tool_call_id: str,
        state: Dict[str, Any]
    ) -> AsyncGenerator[AgentEvent, None]:
        """Continue the agent loop after SQL approval."""
        logger.info(f"=== CONTINUE AFTER APPROVAL: approved={approved}, sql={sql[:50]} ===")

        messages = state.get("messages", [])
        current_todo_data = state.get("current_todo")

        # Find the current TODO
        current_todo = None
        if current_todo_data:
            for todo in self.todos:
                if todo.id == current_todo_data.get("id"):
                    current_todo = todo
                    break

        if not approved:
            result = {"success": False, "error": "Query rejected by user"}
            self.beliefs.add_disproven_assumption(f"Query '{sql[:50]}...' was rejected by user")
            logger.info("Query rejected by user")

            # Add TODO to try alternative approach
            self._add_todo("Find alternative approach after query rejection", priority=1)
        else:
            yield AgentEvent(AgentEvent.TOOL_CALL, {"tool": "execute_query", "args": {"sql": sql}})

            try:
                result = self.db_tools.execute_query(sql)
                logger.info(f"Query executed. Result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
                logger.debug(f"Query result: {str(result)[:1000]}")
            except Exception as e:
                result = {"error": str(e)}
                logger.error(f"Query execution error: {e}")

            self.history.add_observation("execute_query", result)
            self._update_beliefs_from_result("execute_query", {"sql": sql}, result)

        result_str = json.dumps(result) if isinstance(result, dict) else str(result)
        messages.append(ToolMessage(content=result_str, tool_call_id=tool_call_id))

        yield AgentEvent(AgentEvent.TOOL_RESULT, {"tool": "execute_query", "result": result})

        # Reflect on result
        async for event in self._reflect_and_replan("execute_query", result, current_todo):
            yield event

        # Continue the main loop
        max_iterations = 20
        iteration = 0

        while not self.goal_satisfied and iteration < max_iterations:
            iteration += 1

            current_todo = self._get_next_todo()
            if not current_todo:
                pending = [t for t in self.todos if t.status == TodoStatus.PENDING]
                if not pending:
                    self.goal_satisfied = True
                    break
                continue

            current_todo.status = TodoStatus.IN_PROGRESS

            yield AgentEvent(AgentEvent.THINKING, {
                "iteration": iteration,
                "todo": current_todo.description
            })

            system_prompt = self._create_system_prompt()

            action_prompt = f"""Current TODO: {current_todo.description}

Based on your current knowledge, decide what tool to use next."""

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="messages"),
                ("human", action_prompt)
            ])

            chain = prompt | self.llm_with_tools

            try:
                response = await chain.ainvoke({"messages": messages})
                messages.append(response)
            except Exception as e:
                yield AgentEvent(AgentEvent.ERROR, {"error": str(e)})
                continue

            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tc_id = tool_call["id"]

                    if tool_name == "execute_query":
                        yield AgentEvent(AgentEvent.APPROVAL_NEEDED, {
                            "sql": tool_args.get("sql", ""),
                            "tool_call_id": tc_id,
                            "messages": messages,
                            "current_todo": current_todo.to_dict() if current_todo else None,
                            "db_connected": state.get("db_connected", False)
                        })
                        return

                    yield AgentEvent(AgentEvent.TOOL_CALL, {"tool": tool_name, "args": tool_args})

                    tool = self.tool_map.get(tool_name)
                    try:
                        result = tool.func(**tool_args) if tool and tool_args else (
                            tool.func() if tool else json.dumps({"error": "Tool not found"})
                        )
                    except Exception as e:
                        result = json.dumps({"error": str(e)})

                    self._update_beliefs_from_result(tool_name, tool_args, result)

                    yield AgentEvent(AgentEvent.TOOL_RESULT, {"tool": tool_name, "result": result})
                    messages.append(ToolMessage(content=str(result), tool_call_id=tc_id))

                    async for event in self._reflect_and_replan(tool_name, result, current_todo):
                        yield event
            else:
                if current_todo:
                    current_todo.status = TodoStatus.COMPLETED
                    current_todo.result = response.content if hasattr(response, 'content') else ""

        # Final response
        final_prompt = f"""Based on your exploration, provide a complete answer.

User's Question: {self.current_goal}

{self.beliefs.to_context_string()}"""

        try:
            final_response = await self.llm.ainvoke([HumanMessage(content=final_prompt)])
            final_content = final_response.content
        except:
            final_content = "\n".join([f"- {t.result}" for t in self.todos if t.result])

        yield AgentEvent(AgentEvent.RESPONSE, {
            "content": final_content,
            "state": {"messages": messages, "pending_approval": None, "db_connected": state.get("db_connected", False)}
        })

    # Backwards compatibility
    async def process_message(self, user_message: str, state: Optional[AgentState] = None):
        final_response = ""
        final_state = state or {}

        async for event in self.process_message_streaming(user_message, state):
            if event.type == AgentEvent.RESPONSE:
                final_response = event.data.get("content", "")
                final_state = event.data.get("state", state)
            elif event.type == AgentEvent.APPROVAL_NEEDED:
                return (f"Execute this query?\n```sql\n{event.data['sql']}\n```", event.data, state)
            elif event.type == AgentEvent.ERROR:
                final_response = f"Error: {event.data.get('error')}"

        return final_response, None, final_state

    async def execute_approved_query(self, approval_data: Dict[str, Any], approved: bool):
        final_response = ""
        final_state = {}

        async for event in self.continue_after_approval(
            approved=approved,
            sql=approval_data.get("sql", ""),
            tool_call_id=approval_data.get("tool_call_id", ""),
            state=approval_data
        ):
            if event.type == AgentEvent.RESPONSE:
                final_response = event.data.get("content", "")
                final_state = event.data.get("state", {})

        return final_response, final_state

    def get_conversation_history(self, state: AgentState) -> List[Dict[str, str]]:
        history = []
        for msg in state.get("messages", []):
            if isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage) and msg.content:
                history.append({"role": "assistant", "content": msg.content})
        return history

    @staticmethod
    def create_agent(provider: str, api_key: str, model: str, db_tools: PostgreSQLTools) -> 'SQLAgent':
        provider = provider.lower()

        if provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model=model, google_api_key=api_key, temperature=0,
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


from api_models import FALLBACK_MODELS
PROVIDER_MODELS = FALLBACK_MODELS
