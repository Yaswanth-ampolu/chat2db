# Tool Creation Guide for AI Agents

## Table of Contents
1. [What is a Tool?](#what-is-a-tool)
2. [Tool Anatomy](#tool-anatomy)
3. [Creating Database Tools](#creating-database-tools)
4. [Tool Registration](#tool-registration)
5. [Error Handling](#error-handling)
6. [Testing Tools](#testing-tools)
7. [Advanced Patterns](#advanced-patterns)

---

## What is a Tool?

A **tool** is a function that an AI agent can call to perform actions or retrieve information.

### Tool vs Regular Function

```
Regular Function:
├─ You call it directly in code
├─ You know when to use it
└─ You provide exact arguments

Agent Tool:
├─ AI decides when to call it
├─ AI determines arguments from context
└─ You define what it can do via description
```

### Example: Weather Tool

```python
# Regular function (you control)
def get_weather(city):
    return fetch_weather_api(city)

weather = get_weather("Tokyo")  # You decide


# Agent tool (AI controls)
weather_tool = {
    "name": "get_weather",
    "description": "Get current weather for a city",  # AI reads this
    "parameters": {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "City name"  # AI uses this to extract value
            }
        }
    }
}

# AI Agent sees user query: "What's the weather in Tokyo?"
# AI thinks: "I should use get_weather tool with city='Tokyo'"
# AI calls: get_weather(city="Tokyo")
```

---

## Tool Anatomy

Every tool has three parts:

### 1. **Declaration** (What the AI sees)

```python
{
    "name": "tool_name",           # Unique identifier
    "description": "What it does",  # AI uses this to decide when to call
    "parameters": {                # Arguments specification (JSON Schema)
        "type": "object",
        "properties": {
            "arg1": {"type": "string", "description": "..."},
            "arg2": {"type": "number", "description": "..."}
        },
        "required": ["arg1"]       # Which args are mandatory
    }
}
```

### 2. **Implementation** (The actual function)

```python
def tool_name(arg1, arg2=None):
    """Actual implementation"""
    try:
        result = do_something(arg1, arg2)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
```

### 3. **Registration** (Connecting declaration to implementation)

```python
tools = {
    "tool_name": tool_name  # Maps name to function
}

def execute_tool(name, args):
    if name in tools:
        return tools[name](**args)
    else:
        return {"error": f"Tool {name} not found"}
```

---

## Creating Database Tools

Let's build a complete set of SQL tools for our agent.

### Tool 1: List Tables

**Purpose**: Show what tables exist in the database

```python
# Declaration for Gemini
list_tables_declaration = {
    "name": "list_tables",
    "description": (
        "List all tables in the database. "
        "Returns table names, row counts, and brief descriptions. "
        "Use this FIRST to understand the database structure."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "schema": {
                "type": "string",
                "description": "Database schema name (optional, default: 'public')"
            },
            "include_row_count": {
                "type": "boolean",
                "description": "Include row count for each table (default: true)"
            }
        }
    }
}

# Implementation
def list_tables(db_connection, schema='public', include_row_count=True):
    """List all tables in schema"""
    try:
        # Get table names
        query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        cursor = db_connection.cursor()
        cursor.execute(query, (schema,))
        tables = [row[0] for row in cursor.fetchall()]

        result = []
        for table in tables:
            table_info = {"name": table}

            # Get row count if requested
            if include_row_count:
                cursor.execute(f"SELECT COUNT(*) FROM {schema}.{table}")
                table_info["row_count"] = cursor.fetchone()[0]

            result.append(table_info)

        return {
            "success": True,
            "tables": result,
            "total": len(result),
            "schema": schema
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to list tables: {str(e)}"
        }
```

### Tool 2: Get Table Schema

**Purpose**: Show columns, types, and constraints for a table

```python
# Declaration
get_schema_declaration = {
    "name": "get_table_schema",
    "description": (
        "Get detailed schema information for a specific table. "
        "Returns column names, data types, nullable status, default values, "
        "and primary/foreign keys. Use this BEFORE writing queries to ensure "
        "you use correct column names and understand the data structure."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "Exact name of the table (case-sensitive)"
            },
            "include_sample_data": {
                "type": "boolean",
                "description": "Include 3 sample rows to see actual data (default: false)"
            },
            "include_indexes": {
                "type": "boolean",
                "description": "Include index information (default: false)"
            },
            "include_foreign_keys": {
                "type": "boolean",
                "description": "Include foreign key relationships (default: true)"
            }
        },
        "required": ["table_name"]
    }
}

# Implementation
def get_table_schema(
    db_connection,
    table_name,
    include_sample_data=False,
    include_indexes=False,
    include_foreign_keys=True
):
    """Get comprehensive table schema"""
    try:
        cursor = db_connection.cursor()

        # Get columns
        columns_query = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
        """
        cursor.execute(columns_query, (table_name,))
        columns = []

        for row in cursor.fetchall():
            col = {
                "name": row[0],
                "type": row[1],
                "nullable": row[2] == 'YES',
                "default": row[3],
                "max_length": row[4]
            }
            columns.append(col)

        if not columns:
            return {
                "success": False,
                "error": f"Table '{table_name}' not found"
            }

        result = {
            "success": True,
            "table": table_name,
            "columns": columns
        }

        # Get primary key
        pk_query = """
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid
                AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = %s::regclass
            AND i.indisprimary
        """
        cursor.execute(pk_query, (table_name,))
        primary_keys = [row[0] for row in cursor.fetchall()]
        if primary_keys:
            result["primary_key"] = primary_keys

        # Get foreign keys if requested
        if include_foreign_keys:
            fk_query = """
                SELECT
                    kcu.column_name,
                    ccu.table_name AS foreign_table,
                    ccu.column_name AS foreign_column
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = %s
            """
            cursor.execute(fk_query, (table_name,))
            foreign_keys = []
            for row in cursor.fetchall():
                fk = {
                    "column": row[0],
                    "references_table": row[1],
                    "references_column": row[2]
                }
                foreign_keys.append(fk)
            if foreign_keys:
                result["foreign_keys"] = foreign_keys

        # Get indexes if requested
        if include_indexes:
            idx_query = """
                SELECT
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE tablename = %s
            """
            cursor.execute(idx_query, (table_name,))
            indexes = [
                {"name": row[0], "definition": row[1]}
                for row in cursor.fetchall()
            ]
            result["indexes"] = indexes

        # Get sample data if requested
        if include_sample_data:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
            sample_data = []
            for row in cursor.fetchall():
                sample_data.append(dict(zip([col.name for col in cursor.description], row)))
            result["sample_data"] = sample_data

        return result

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get schema for '{table_name}': {str(e)}"
        }
```

### Tool 3: Execute Query

**Purpose**: Run SELECT queries and return results

```python
# Declaration
execute_query_declaration = {
    "name": "execute_query",
    "description": (
        "Execute a SQL SELECT query on the database. "
        "IMPORTANT: Only read-only SELECT queries are allowed. "
        "No DML (INSERT/UPDATE/DELETE) or DDL (CREATE/DROP/ALTER) operations. "
        "Always add appropriate WHERE clauses and LIMIT to prevent large result sets. "
        "Returns query results as JSON array of objects."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "SQL SELECT query to execute. Must start with SELECT."
            },
            "limit": {
                "type": "number",
                "description": "Maximum number of rows to return (default: 100, max: 1000)",
                "minimum": 1,
                "maximum": 1000
            },
            "explain_only": {
                "type": "boolean",
                "description": "If true, return query execution plan instead of results (default: false)"
            }
        },
        "required": ["query"]
    }
}

# Implementation
def execute_query(db_connection, query, limit=100, explain_only=False):
    """Execute SQL query with safety checks"""
    try:
        # Validate query starts with SELECT
        query_upper = query.strip().upper()
        if not query_upper.startswith('SELECT'):
            return {
                "success": False,
                "error": "Only SELECT queries are allowed",
                "error_type": "permission_denied"
            }

        # Check for dangerous operations
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE', 'CREATE']
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                return {
                    "success": False,
                    "error": f"Operation {keyword} is not allowed. Only SELECT queries permitted.",
                    "error_type": "permission_denied"
                }

        cursor = db_connection.cursor()

        # If explain only, return execution plan
        if explain_only:
            cursor.execute(f"EXPLAIN {query}")
            plan = [row[0] for row in cursor.fetchall()]
            return {
                "success": True,
                "query": query,
                "execution_plan": plan
            }

        # Add LIMIT if not present
        if 'LIMIT' not in query_upper:
            query = f"{query.rstrip(';')} LIMIT {min(limit, 1000)}"

        # Execute query with timeout
        cursor.execute(f"SET statement_timeout = 30000")  # 30 second timeout
        start_time = time.time()
        cursor.execute(query)
        execution_time = time.time() - start_time

        # Fetch results
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        results = []
        for row in rows:
            result_obj = {}
            for i, column in enumerate(columns):
                value = row[i]
                # Convert special types to JSON-serializable format
                if isinstance(value, (date, datetime)):
                    value = value.isoformat()
                elif isinstance(value, Decimal):
                    value = float(value)
                result_obj[column] = value
            results.append(result_obj)

        return {
            "success": True,
            "query": query,
            "data": results,
            "row_count": len(results),
            "execution_time_ms": round(execution_time * 1000, 2),
            "columns": columns
        }

    except psycopg2.Error as e:
        # Database-specific errors
        return {
            "success": False,
            "error": str(e),
            "error_type": "database_error",
            "suggestion": "Check SQL syntax and table/column names"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": "runtime_error"
        }
```

### Tool 4: Validate SQL

**Purpose**: Check SQL syntax without executing

```python
# Declaration
validate_sql_declaration = {
    "name": "validate_sql",
    "description": (
        "Validate SQL query syntax without executing it. "
        "Returns whether the query is valid and any syntax errors found. "
        "Use this before execute_query to catch errors early."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "SQL query to validate"
            }
        },
        "required": ["query"]
    }
}

# Implementation
def validate_sql(db_connection, query):
    """Validate SQL syntax"""
    try:
        cursor = db_connection.cursor()

        # Use EXPLAIN to validate without executing
        cursor.execute(f"EXPLAIN {query}")

        return {
            "success": True,
            "valid": True,
            "query": query,
            "message": "Query syntax is valid"
        }

    except psycopg2.Error as e:
        error_message = str(e)

        # Extract useful error info
        return {
            "success": True,  # Validation succeeded (found it's invalid)
            "valid": False,
            "query": query,
            "error": error_message,
            "suggestion": "Check table names, column names, and SQL syntax"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Validation failed: {str(e)}"
        }
```

---

## Tool Registration

### Complete Tool Registry

```python
class SQLToolRegistry:
    """Manages all SQL tools for the agent"""

    def __init__(self, db_connection):
        self.db = db_connection

        # Tool declarations (for Gemini)
        self.declarations = [
            list_tables_declaration,
            get_schema_declaration,
            execute_query_declaration,
            validate_sql_declaration
        ]

        # Tool implementations
        self.implementations = {
            'list_tables': lambda **args: list_tables(self.db, **args),
            'get_table_schema': lambda **args: get_table_schema(self.db, **args),
            'execute_query': lambda **args: execute_query(self.db, **args),
            'validate_sql': lambda **args: validate_sql(self.db, **args)
        }

    def get_tool_declarations(self):
        """Get all tool declarations for Gemini"""
        return [{
            "function_declarations": self.declarations
        }]

    def execute(self, tool_name, arguments):
        """Execute a tool by name"""
        if tool_name not in self.implementations:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "available_tools": list(self.implementations.keys())
            }

        try:
            result = self.implementations[tool_name](**arguments)
            return result
        except TypeError as e:
            return {
                "success": False,
                "error": f"Invalid arguments for {tool_name}: {str(e)}",
                "arguments_received": arguments
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}"
            }

    def list_tools(self):
        """List all available tools"""
        return [
            {
                "name": decl["name"],
                "description": decl["description"]
            }
            for decl in self.declarations
        ]

# Usage
registry = SQLToolRegistry(db_connection)

# Get declarations for Gemini
tools = registry.get_tool_declarations()

# Execute a tool
result = registry.execute("list_tables", {"schema": "public"})
```

---

## Error Handling

### Graceful Error Responses

```python
def safe_execute_tool(tool_name, arguments):
    """Execute tool with comprehensive error handling"""

    try:
        # Validate tool exists
        if tool_name not in tools:
            return format_error(
                "unknown_tool",
                f"Tool '{tool_name}' not found",
                f"Available tools: {list(tools.keys())}"
            )

        # Validate arguments
        validation = validate_arguments(tool_name, arguments)
        if not validation["valid"]:
            return format_error(
                "invalid_arguments",
                validation["error"],
                validation["suggestion"]
            )

        # Execute tool
        result = tools[tool_name](**arguments)

        # Ensure result has standard format
        if not isinstance(result, dict):
            result = {"data": result}

        if "success" not in result:
            result["success"] = True

        return result

    except ValueError as e:
        return format_error("validation_error", str(e))
    except PermissionError as e:
        return format_error("permission_denied", str(e))
    except TimeoutError as e:
        return format_error("timeout", str(e), "Query took too long. Try adding filters or LIMIT.")
    except ConnectionError as e:
        return format_error("connection_error", str(e), "Database connection lost. Reconnecting...")
    except Exception as e:
        return format_error("runtime_error", str(e))

def format_error(error_type, message, suggestion=None):
    """Standard error format"""
    error = {
        "success": False,
        "error_type": error_type,
        "error_message": message
    }
    if suggestion:
        error["suggestion"] = suggestion
    return error
```

---

## Testing Tools

### Unit Tests for Tools

```python
import unittest
from unittest.mock import Mock, MagicMock

class TestSQLTools(unittest.TestCase):

    def setUp(self):
        """Set up mock database connection"""
        self.mock_db = Mock()
        self.mock_cursor = MagicMock()
        self.mock_db.cursor.return_value = self.mock_cursor

    def test_list_tables_success(self):
        """Test successful table listing"""
        # Mock database response
        self.mock_cursor.fetchall.return_value = [
            ('users',),
            ('orders',),
            ('products',)
        ]

        result = list_tables(self.mock_db)

        self.assertTrue(result["success"])
        self.assertEqual(len(result["tables"]), 3)
        self.assertIn("users", [t["name"] for t in result["tables"]])

    def test_list_tables_empty(self):
        """Test listing when no tables exist"""
        self.mock_cursor.fetchall.return_value = []

        result = list_tables(self.mock_db)

        self.assertTrue(result["success"])
        self.assertEqual(result["total"], 0)

    def test_execute_query_permission_denied(self):
        """Test that non-SELECT queries are blocked"""
        dangerous_queries = [
            "DELETE FROM users",
            "DROP TABLE users",
            "UPDATE users SET password = '123'"
        ]

        for query in dangerous_queries:
            result = execute_query(self.mock_db, query)

            self.assertFalse(result["success"])
            self.assertEqual(result["error_type"], "permission_denied")

    def test_execute_query_success(self):
        """Test successful query execution"""
        self.mock_cursor.description = [('id',), ('name',)]
        self.mock_cursor.fetchall.return_value = [
            (1, 'Alice'),
            (2, 'Bob')
        ]

        result = execute_query(self.mock_db, "SELECT id, name FROM users")

        self.assertTrue(result["success"])
        self.assertEqual(len(result["data"]), 2)
        self.assertEqual(result["data"][0]["name"], "Alice")

if __name__ == '__main__':
    unittest.main()
```

### Integration Tests

```python
def test_agent_with_real_db():
    """Test agent with actual database"""
    import psycopg2

    # Connect to test database
    conn = psycopg2.connect(
        host="localhost",
        database="test_db",
        user="test_user",
        password="test_pass"
    )

    try:
        # Test list_tables
        result = list_tables(conn)
        assert result["success"], "list_tables failed"
        print(f"✓ Found {result['total']} tables")

        # Test get_schema
        if result["tables"]:
            table_name = result["tables"][0]["name"]
            schema = get_table_schema(conn, table_name)
            assert schema["success"], f"get_schema failed for {table_name}"
            print(f"✓ Got schema for {table_name}: {len(schema['columns'])} columns")

        # Test execute_query
        query_result = execute_query(conn, "SELECT 1 as test")
        assert query_result["success"], "execute_query failed"
        assert query_result["data"][0]["test"] == 1
        print("✓ Query execution works")

        print("\n✅ All integration tests passed!")

    finally:
        conn.close()

# Run tests
test_agent_with_real_db()
```

---

## Advanced Patterns

### Pattern 1: Tool Chaining

```python
def get_table_with_samples(db, table_name):
    """Tool that chains multiple operations"""

    # First, get schema
    schema = get_table_schema(db, table_name, include_foreign_keys=True)

    if not schema["success"]:
        return schema  # Propagate error

    # Then, get sample data
    query = f"SELECT * FROM {table_name} LIMIT 5"
    samples = execute_query(db, query)

    # Combine results
    return {
        "success": True,
        "table": table_name,
        "schema": schema,
        "samples": samples["data"] if samples["success"] else []
    }
```

### Pattern 2: Conditional Tools

```python
def smart_query_tool(db, natural_language_query):
    """Tool that decides strategy based on input"""

    # Simple keyword detection
    if "how many" in natural_language_query.lower():
        # COUNT query
        return suggest_count_query(db, natural_language_query)

    elif "top" in natural_language_query.lower():
        # ORDER BY + LIMIT query
        return suggest_top_query(db, natural_language_query)

    else:
        # General SELECT
        return suggest_general_query(db, natural_language_query)
```

### Pattern 3: Cached Tools

```python
from functools import lru_cache
import time

@lru_cache(maxsize=100)
def cached_get_schema(table_name):
    """Cache schema to avoid repeated DB calls"""
    return get_table_schema(db, table_name)

# Cache expires after 5 minutes
schema_cache = {}

def get_schema_with_ttl(db, table_name, ttl=300):
    """Schema with time-based cache"""
    now = time.time()

    if table_name in schema_cache:
        cached_time, cached_schema = schema_cache[table_name]
        if now - cached_time < ttl:
            return cached_schema

    # Fetch fresh
    schema = get_table_schema(db, table_name)
    schema_cache[table_name] = (now, schema)

    return schema
```

---

## Tool Design Checklist

When creating a tool, ensure it has:

- [ ] **Clear name** - Describes what it does
- [ ] **Detailed description** - Helps AI know when to use it
- [ ] **Well-defined parameters** - Type, description, required/optional
- [ ] **Error handling** - Catches and returns errors gracefully
- [ ] **Consistent return format** - Always returns `{success, ...}`
- [ ] **Safety checks** - Validates inputs, prevents dangerous operations
- [ ] **Good examples** - Test with various inputs
- [ ] **Documentation** - Comments explaining behavior
- [ ] **Logging** - Tracks usage for debugging
- [ ] **Performance** - Executes efficiently

---

## Next Steps

- [Agent Loop Implementation](./AGENT_LOOP_IMPLEMENTATION.md) - Put tools together in agent
- [SQL Agent Example](./SQL_AGENT_EXAMPLE.md) - Complete working example
- [Production Deployment](./PRODUCTION_GUIDE.md) - Deploy to production

---

**Key Insight**: A good tool is like a well-documented API - clear contract, predictable behavior, helpful error messages!
