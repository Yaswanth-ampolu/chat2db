"""
PostgreSQL Database Tools for SQL Agent

This module provides tools for PostgreSQL database inspection and querying.
"""

import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, Optional, List
import json
from datetime import datetime, date, time
from decimal import Decimal


def serialize_db_value(obj):
    """
    Convert PostgreSQL objects to JSON-serializable types.

    Handles:
    - datetime, date, time -> ISO format strings
    - Decimal -> float
    - bytes/bytea -> base64 string (for display)
    - memoryview -> base64 string
    """
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, bytes):
        # For bytea data, return a readable representation
        try:
            # Try to decode as UTF-8 text
            return obj.decode('utf-8')
        except UnicodeDecodeError:
            # If binary data, return base64 for display
            import base64
            return f"<binary data: {len(obj)} bytes>"
    elif isinstance(obj, memoryview):
        return f"<binary data: {len(obj)} bytes>"
    return obj


def serialize_db_row(row):
    """Serialize a database row (dict) to JSON-safe format."""
    if isinstance(row, dict):
        return {key: serialize_db_value(value) for key, value in row.items()}
    return row


class PostgreSQLTools:
    """Collection of PostgreSQL database interaction tools for the AI agent."""

    def __init__(self, connection_params: Optional[Dict[str, str]] = None):
        """
        Initialize PostgreSQLTools.

        Args:
            connection_params: Dict with keys: host, port, database, user, password
        """
        self.connection_params = connection_params
        self._connection = None

    def test_connection(self) -> Dict[str, Any]:
        """
        Test database connection.

        Returns:
            Dict with success status and connection info
        """
        if not self.connection_params:
            return {
                "success": False,
                "error": "No connection parameters provided"
            }

        try:
            conn = psycopg2.connect(**self.connection_params)
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            cursor.close()
            conn.close()

            return {
                "success": True,
                "message": "Connection successful",
                "database": self.connection_params.get("database"),
                "version": version
            }
        except psycopg2.Error as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": "connection_error"
            }

    def connect(self, host: str, port: int, database: str, user: str, password: str) -> Dict[str, Any]:
        """
        Connect to PostgreSQL database.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Username
            password: Password

        Returns:
            Dict with connection status
        """
        self.connection_params = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password
        }

        return self.test_connection()

    def _get_connection(self):
        """Get database connection."""
        if not self.connection_params:
            raise Exception("No database connection configured. Use /db command to connect.")

        return psycopg2.connect(**self.connection_params)

    def list_schemas(self) -> Dict[str, Any]:
        """
        List all schemas in the database.

        Returns:
            Dict with schema list
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                ORDER BY schema_name
            """)

            schemas = cursor.fetchall()
            cursor.close()
            conn.close()

            return {
                "success": True,
                "schemas": [s["schema_name"] for s in schemas],
                "count": len(schemas)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": "database_error"
            }

    def list_tables(self, schema: str = "public") -> Dict[str, Any]:
        """
        List all tables in a schema.

        Args:
            schema: Schema name (default: 'public')

        Returns:
            Dict with table list
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Get tables with row counts
            cursor.execute(sql.SQL("""
                SELECT
                    t.table_name,
                    pg_total_relation_size(quote_ident(t.table_schema) || '.' || quote_ident(t.table_name)) as size_bytes,
                    (SELECT COUNT(*)
                     FROM information_schema.columns c
                     WHERE c.table_schema = t.table_schema
                     AND c.table_name = t.table_name) as column_count
                FROM information_schema.tables t
                WHERE t.table_schema = %s
                AND t.table_type = 'BASE TABLE'
                ORDER BY t.table_name
            """), [schema])

            tables = cursor.fetchall()

            # Get row counts for each table
            table_list = []
            for table in tables:
                try:
                    cursor.execute(
                        sql.SQL("SELECT COUNT(*) as row_count FROM {schema}.{table}").format(
                            schema=sql.Identifier(schema),
                            table=sql.Identifier(table["table_name"])
                        )
                    )
                    row_count = cursor.fetchone()["row_count"]
                except:
                    row_count = 0

                table_list.append({
                    "name": table["table_name"],
                    "schema": schema,
                    "row_count": row_count,
                    "column_count": table["column_count"],
                    "size_bytes": table["size_bytes"]
                })

            cursor.close()
            conn.close()

            return {
                "success": True,
                "schema": schema,
                "tables": table_list,
                "count": len(table_list)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": "database_error"
            }

    def inspect_schema(self, table_name: str, schema: str = "public") -> Dict[str, Any]:
        """
        Get detailed schema information for a table.

        Args:
            table_name: Table name
            schema: Schema name (default: 'public')

        Returns:
            Dict with schema information
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Get columns
            cursor.execute("""
                SELECT
                    c.column_name,
                    c.data_type,
                    c.character_maximum_length,
                    c.is_nullable,
                    c.column_default,
                    c.ordinal_position
                FROM information_schema.columns c
                WHERE c.table_schema = %s
                AND c.table_name = %s
                ORDER BY c.ordinal_position
            """, [schema, table_name])

            columns = cursor.fetchall()

            if not columns:
                cursor.close()
                conn.close()
                return {
                    "success": False,
                    "error": f"Table '{schema}.{table_name}' not found"
                }

            # Get primary keys
            cursor.execute("""
                SELECT a.attname as column_name
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = %s::regclass
                AND i.indisprimary
            """, [f"{schema}.{table_name}"])

            primary_keys = [row["column_name"] for row in cursor.fetchall()]

            # Get foreign keys
            cursor.execute("""
                SELECT
                    kcu.column_name,
                    ccu.table_schema AS foreign_table_schema,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = %s
                AND tc.table_name = %s
            """, [schema, table_name])

            foreign_keys = cursor.fetchall()

            # Get indexes
            cursor.execute("""
                SELECT
                    i.relname as index_name,
                    a.attname as column_name,
                    ix.indisunique as is_unique
                FROM pg_class t
                JOIN pg_index ix ON t.oid = ix.indrelid
                JOIN pg_class i ON i.oid = ix.indexrelid
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
                JOIN pg_namespace n ON n.oid = t.relnamespace
                WHERE n.nspname = %s
                AND t.relname = %s
                AND t.relkind = 'r'
            """, [schema, table_name])

            indexes = cursor.fetchall()

            # Get sample data (3 rows)
            cursor.execute(
                sql.SQL("SELECT * FROM {schema}.{table} LIMIT 3").format(
                    schema=sql.Identifier(schema),
                    table=sql.Identifier(table_name)
                )
            )
            sample_data = cursor.fetchall()

            cursor.close()
            conn.close()

            # Serialize sample data to handle datetime, bytea, etc.
            serialized_sample_data = [serialize_db_row(row) for row in sample_data]

            return {
                "success": True,
                "table": table_name,
                "schema": schema,
                "columns": [
                    {
                        "name": col["column_name"],
                        "type": col["data_type"],
                        "max_length": col["character_maximum_length"],
                        "nullable": col["is_nullable"] == "YES",
                        "default": col["column_default"],
                        "position": col["ordinal_position"],
                        "is_primary_key": col["column_name"] in primary_keys
                    }
                    for col in columns
                ],
                "primary_keys": primary_keys,
                "foreign_keys": [
                    {
                        "column": fk["column_name"],
                        "references_schema": fk["foreign_table_schema"],
                        "references_table": fk["foreign_table_name"],
                        "references_column": fk["foreign_column_name"]
                    }
                    for fk in foreign_keys
                ],
                "indexes": [
                    {
                        "name": idx["index_name"],
                        "column": idx["column_name"],
                        "unique": idx["is_unique"]
                    }
                    for idx in indexes
                ],
                "sample_data": serialized_sample_data
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": "database_error"
            }

    def validate_sql(self, sql_query: str) -> Dict[str, Any]:
        """
        Validate SQL query for safety and syntax.

        Args:
            sql_query: SQL query to validate

        Returns:
            Dict with validation results
        """
        # Safety checks
        forbidden_keywords = [
            'DELETE', 'DROP', 'TRUNCATE', 'UPDATE', 'INSERT',
            'ALTER', 'CREATE', 'GRANT', 'REVOKE'
        ]
        query_upper = sql_query.upper()

        for keyword in forbidden_keywords:
            if keyword in query_upper:
                return {
                    "success": False,
                    "valid": False,
                    "error": f"Forbidden operation: {keyword}",
                    "error_type": "permission_denied"
                }

        # Check if it's a SELECT query
        if not query_upper.strip().startswith('SELECT'):
            return {
                "success": False,
                "valid": False,
                "error": "Only SELECT queries are allowed",
                "error_type": "permission_denied"
            }

        # Check for LIMIT clause
        if 'LIMIT' not in query_upper:
            return {
                "success": True,
                "valid": True,
                "warning": "Query does not have LIMIT clause. Consider adding one.",
                "suggestion": f"{sql_query.rstrip(';')} LIMIT 100"
            }

        # Syntax validation using EXPLAIN
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(f"EXPLAIN {sql_query}")
            cursor.close()
            conn.close()

            return {
                "success": True,
                "valid": True,
                "message": "Query syntax is valid"
            }
        except psycopg2.Error as e:
            return {
                "success": True,
                "valid": False,
                "error": str(e),
                "error_type": "syntax_error"
            }

    def execute_query(self, sql_query: str, limit: int = 100) -> Dict[str, Any]:
        """
        Execute a SQL query and return results.

        IMPORTANT: This should only be called after user approval.

        Args:
            sql_query: SQL query to execute
            limit: Maximum rows to return

        Returns:
            Dict with query results
        """
        # Validate first
        validation = self.validate_sql(sql_query)
        if not validation.get("valid", False):
            return validation

        try:
            # Add LIMIT if not present
            query_upper = sql_query.upper()
            if 'LIMIT' not in query_upper:
                sql_query = f"{sql_query.rstrip(';')} LIMIT {limit}"

            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Execute query with timeout (30 seconds)
            cursor.execute("SET statement_timeout = 30000")
            cursor.execute(sql_query)

            rows = cursor.fetchall()
            column_names = [desc.name for desc in cursor.description]

            cursor.close()
            conn.close()

            # Serialize rows to handle datetime, bytea, and other non-JSON types
            serialized_rows = [serialize_db_row(row) for row in rows]

            return {
                "success": True,
                "query": sql_query,
                "columns": column_names,
                "data": serialized_rows,
                "row_count": len(serialized_rows)
            }

        except psycopg2.Error as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": "database_error",
                "query": sql_query
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": "runtime_error"
            }

    def get_table_relationships(self, table_name: str, schema: str = "public") -> Dict[str, Any]:
        """
        Get all relationships for a table (foreign keys in and out).

        Args:
            table_name: Table name
            schema: Schema name

        Returns:
            Dict with relationship information
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Outgoing foreign keys (this table references others)
            cursor.execute("""
                SELECT
                    kcu.column_name,
                    ccu.table_schema AS foreign_table_schema,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name,
                    rc.update_rule,
                    rc.delete_rule
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                JOIN information_schema.referential_constraints AS rc
                    ON tc.constraint_name = rc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = %s
                AND tc.table_name = %s
            """, [schema, table_name])

            outgoing_fks = cursor.fetchall()

            # Incoming foreign keys (other tables reference this one)
            cursor.execute("""
                SELECT
                    kcu.table_schema AS referencing_schema,
                    kcu.table_name AS referencing_table,
                    kcu.column_name AS referencing_column,
                    ccu.column_name AS referenced_column
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND ccu.table_schema = %s
                AND ccu.table_name = %s
            """, [schema, table_name])

            incoming_fks = cursor.fetchall()

            cursor.close()
            conn.close()

            return {
                "success": True,
                "table": table_name,
                "schema": schema,
                "outgoing_relationships": outgoing_fks,
                "incoming_relationships": incoming_fks
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": "database_error"
            }


# LangChain Tool Wrappers
def create_langchain_tools(db_tools: PostgreSQLTools):
    """
    Create LangChain Tool objects from PostgreSQLTools.

    Args:
        db_tools: PostgreSQLTools instance

    Returns:
        List of LangChain Tool objects
    """
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, Field
    from typing import Optional

    # Define input schemas for each tool
    class ListTablesInput(BaseModel):
        """Input for list_tables tool."""
        schema_name: str = Field(default="public", description="Database schema name")

    class InspectSchemaInput(BaseModel):
        """Input for inspect_schema tool."""
        table_name: str = Field(..., description="Name of the table to inspect")
        schema_name: str = Field(default="public", description="Database schema name")

    class GetRelationshipsInput(BaseModel):
        """Input for get_table_relationships tool."""
        table_name: str = Field(..., description="Name of the table")
        schema_name: str = Field(default="public", description="Database schema name")

    class ValidateSQLInput(BaseModel):
        """Input for validate_sql tool."""
        sql: str = Field(..., description="SQL query to validate")

    class ExecuteQueryInput(BaseModel):
        """Input for execute_query tool."""
        sql: str = Field(..., description="SQL query to execute")

    # Define tool functions
    def _list_schemas_func() -> str:
        """List all database schemas."""
        return json.dumps(db_tools.list_schemas())

    def _list_tables_func(schema_name: str = "public") -> str:
        """List tables in a schema."""
        return json.dumps(db_tools.list_tables(schema=schema_name))

    def _inspect_schema_func(table_name: str, schema_name: str = "public") -> str:
        """Inspect a table schema."""
        return json.dumps(db_tools.inspect_schema(table_name, schema=schema_name))

    def _get_relationships_func(table_name: str, schema_name: str = "public") -> str:
        """Get table relationships."""
        return json.dumps(db_tools.get_table_relationships(table_name, schema=schema_name))

    def _validate_sql_func(sql: str) -> str:
        """Validate SQL query."""
        return json.dumps(db_tools.validate_sql(sql))

    def _execute_query_func(sql: str) -> str:
        """Execute SQL query."""
        return json.dumps(db_tools.execute_query(sql))

    # Create tools with proper schemas
    tools = [
        StructuredTool.from_function(
            func=_list_schemas_func,
            name="list_schemas",
            description="List all schemas in the PostgreSQL database. Returns: JSON with list of schema names."
        ),
        StructuredTool.from_function(
            func=_list_tables_func,
            name="list_tables",
            description="List all tables in a schema. Input: schema_name (default: 'public'). Returns: JSON with list of tables.",
            args_schema=ListTablesInput
        ),
        StructuredTool.from_function(
            func=_inspect_schema_func,
            name="inspect_schema",
            description="Get detailed schema information for a table. Input: table_name (required), schema_name (default: 'public'). Returns: JSON with columns, types, constraints, indexes.",
            args_schema=InspectSchemaInput
        ),
        StructuredTool.from_function(
            func=_get_relationships_func,
            name="get_table_relationships",
            description="Get all foreign key relationships for a table. Input: table_name (required), schema_name (default: 'public'). Returns: JSON with relationships.",
            args_schema=GetRelationshipsInput
        ),
        StructuredTool.from_function(
            func=_validate_sql_func,
            name="validate_sql",
            description="Validate SQL query for safety and syntax. Input: sql (required). Returns: JSON with validation results.",
            args_schema=ValidateSQLInput
        ),
        StructuredTool.from_function(
            func=_execute_query_func,
            name="execute_query",
            description="Execute a SELECT SQL query. IMPORTANT: Requires user approval. Input: sql (required). Returns: JSON with query results.",
            args_schema=ExecuteQueryInput
        )
    ]

    return tools
