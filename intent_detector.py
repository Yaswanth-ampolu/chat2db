"""
Intent Detection for Fast Query Processing

Detects SIMPLE user intents and maps them directly to tool calls
without needing LLM reasoning.

IMPORTANT: This should only handle very simple, single-purpose queries.
Complex queries with multiple parts should go to the full agent.
"""

import re
from typing import Optional
from tools import PostgreSQLTools
import json


class IntentDetector:
    """Detect simple user intents and execute common queries directly."""

    def __init__(self, db_tools: PostgreSQLTools):
        self.db_tools = db_tools

    def process_message(self, user_input: str) -> Optional[str]:
        """
        Process user message and return quick response if intent is detected.

        ONLY handles very simple, single-purpose queries like:
        - "list schemas"
        - "show tables"
        - "describe users table"

        Complex queries with multiple parts, "and", comparisons, etc.
        should return None to let the full agent handle them.

        Args:
            user_input: User's message

        Returns:
            Response string if simple intent detected, None otherwise
        """
        if not self.db_tools.connection_params:
            return None  # Let LLM handle - no DB connected

        text = user_input.lower().strip()

        # IMPORTANT: If the query is complex, let the agent handle it
        if self._is_complex_query(text):
            return None

        # Try to match simple intents only
        try:
            # List schemas - very simple queries only
            if self._is_simple_list_schemas(text):
                return self._handle_list_schemas()

            # List tables - very simple queries only
            if self._is_simple_list_tables(text):
                return self._handle_list_tables()

            # Inspect table schema - simple queries only
            table_name = self._extract_simple_table_schema(text)
            if table_name:
                return self._handle_inspect_table(table_name)

        except Exception as e:
            # If anything fails, let LLM handle it
            return None

        # No simple intent matched - let full agent handle
        return None

    def _is_complex_query(self, text: str) -> bool:
        """
        Check if this is a complex query that should go to the full agent.

        Complex queries include:
        - Multiple questions (contains "and", "also", "as well")
        - Comparisons or analytics ("top", "most", "least", "compare")
        - Time-based queries ("this month", "last week", "recent")
        - Aggregations that need SQL ("how many", "count", "total", "sum", "average")
        - Relationship questions ("related", "relationship", "foreign key", "join")
        - Any query longer than ~8 words (likely complex)
        """
        # Multiple questions or compound requests
        if any(word in text for word in [' and ', ' also ', ' as well', ' plus ', ' with ']):
            return True

        # Analytics/comparison queries
        if any(word in text for word in ['top ', 'most ', 'least ', 'best ', 'worst ', 'compare', 'between']):
            return True

        # Time-based queries
        if any(word in text for word in ['today', 'yesterday', 'this week', 'last week', 'this month', 'last month', 'recent', 'latest']):
            return True

        # Aggregation queries that need SQL
        if any(phrase in text for phrase in ['how many', 'count of', 'total', 'sum of', 'average', 'avg ']):
            return True

        # Relationship queries
        if any(word in text for word in ['relationship', 'related', 'foreign', 'join', 'connect']):
            return True

        # Filter/condition queries
        if any(word in text for word in ['where ', 'filter', 'find ', 'search ', 'get all', 'show me all']):
            return True

        # Long queries are likely complex
        word_count = len(text.split())
        if word_count > 8:
            return True

        return False

    def _is_simple_list_schemas(self, text: str) -> bool:
        """Check if this is a simple 'list schemas' query."""
        simple_patterns = [
            r'^list\s+schemas?$',
            r'^show\s+schemas?$',
            r'^what\s+schemas?\s*(are there|exist|do i have)?$',
            r'^schemas?$',
            r'^get\s+schemas?$',
        ]
        return any(re.match(p, text) for p in simple_patterns)

    def _is_simple_list_tables(self, text: str) -> bool:
        """Check if this is a simple 'list tables' query."""
        simple_patterns = [
            r'^list\s+(all\s+)?tables?$',
            r'^show\s+(all\s+)?tables?$',
            r'^what\s+tables?\s*(are there|exist|do i have)?$',
            r'^tables?$',
            r'^get\s+(all\s+)?tables?$',
        ]
        return any(re.match(p, text) for p in simple_patterns)

    def _extract_simple_table_schema(self, text: str) -> Optional[str]:
        """Extract table name from simple schema inspection queries."""
        simple_patterns = [
            r'^describe\s+(\w+)$',
            r'^describe\s+(\w+)\s+table$',
            r'^show\s+(\w+)\s+schema$',
            r'^(\w+)\s+table\s+schema$',
            r'^schema\s+of\s+(\w+)$',
            r'^columns\s+in\s+(\w+)$',
            r'^inspect\s+(\w+)$',
        ]
        for p in simple_patterns:
            match = re.match(p, text)
            if match:
                return match.group(1)
        return None

    # --- Intent Handlers (same as before) ---

    def _handle_list_schemas(self) -> str:
        """Handle list schemas intent."""
        result = self.db_tools.list_schemas()
        data = json.loads(result) if isinstance(result, str) else result

        if data.get("error"):
            return f"Error: {data['error']}"

        schemas = data.get("schemas", [])
        if not schemas:
            return "No schemas found in the database."

        response = f"**Found {len(schemas)} schemas:**\n\n"
        for schema in schemas:
            response += f"  - `{schema}`\n"
        return response

    def _handle_list_tables(self) -> str:
        """Handle list tables intent."""
        schema_result = self.db_tools.list_schemas()
        schema_data = json.loads(schema_result) if isinstance(schema_result, str) else schema_result

        if schema_data.get("error"):
            return f"Error: {schema_data['error']}"

        schemas = schema_data.get("schemas", [])

        response = "**Tables in database:**\n\n"
        total_tables = 0

        for schema in schemas:
            result = self.db_tools.list_tables(schema)
            data = json.loads(result) if isinstance(result, str) else result

            tables = data.get("tables", [])
            if tables:
                table_names = [t.get('name', t) if isinstance(t, dict) else t for t in tables]
                response += f"**Schema `{schema}`:** ({len(table_names)} tables)\n"
                for table in table_names[:10]:
                    response += f"  - `{table}`\n"
                if len(table_names) > 10:
                    response += f"  ... and {len(table_names) - 10} more\n"
                response += "\n"
                total_tables += len(table_names)

        if total_tables == 0:
            return "No tables found in the database."

        return response + f"**Total: {total_tables} tables**"

    def _handle_inspect_table(self, table_name: str) -> str:
        """Handle inspect table schema intent."""
        schema_result = self.db_tools.list_schemas()
        schema_data = json.loads(schema_result) if isinstance(schema_result, str) else schema_result
        schemas = schema_data.get("schemas", ["public"])

        for schema in schemas:
            result = self.db_tools.inspect_schema(table_name, schema)
            data = json.loads(result) if isinstance(result, str) else result

            if not data.get("error"):
                columns = data.get("columns", [])
                if columns:
                    response = f"**Table `{schema}.{table_name}` structure:**\n\n"
                    response += "| Column | Type | Nullable | Default |\n"
                    response += "|--------|------|----------|--------|\n"

                    for col in columns:
                        name = col.get("name", "?")
                        dtype = col.get("type", "?")
                        nullable = "Yes" if col.get("nullable") else "No"
                        default = col.get("default", "-") or "-"
                        if len(str(default)) > 20:
                            default = str(default)[:17] + "..."
                        response += f"| `{name}` | {dtype} | {nullable} | {default} |\n"

                    return response

        return f"Table `{table_name}` not found in any schema."
