"""Main chat view for SQL Agent TUI with ReAct pattern."""

from textual.widgets import Input, RichLog, Label
from textual.containers import Container, Horizontal
from textual.app import ComposeResult
from textual.widget import Widget
from typing import Optional, Dict
import json

from agent import SQLAgent, AgentEvent
from tools import PostgreSQLTools
from intent_detector import IntentDetector
from .modals import DatabaseConfigModal, ModelsConfigModal, QueryApprovalModal
from .styles import CHAT_VIEW_STYLES


class ChatView(Widget):
    """Main chat interface with ReAct agent support."""

    DEFAULT_CSS = CHAT_VIEW_STYLES

    def __init__(self, db_tools: PostgreSQLTools):
        super().__init__()
        self.db_tools = db_tools
        self.agent: Optional[SQLAgent] = None
        self.agent_state: Optional[Dict] = None
        self.config: Optional[Dict[str, str]] = None
        self.intent_detector = IntentDetector(db_tools)

    def compose(self) -> ComposeResult:
        with Container(id="status-bar"):
            with Horizontal(id="status-content"):
                yield Label("Provider: Not configured", id="provider-status", classes="status-label")
                yield Label("Model: Not configured", id="model-status", classes="status-label")
                yield Label("DB: Not connected", id="db-status", classes="status-label")

        with Container(id="chat-container"):
            rich_log = RichLog(
                id="messages",
                highlight=True,
                markup=True,
                wrap=True,
                auto_scroll=True,
                max_lines=10000
            )
            rich_log.can_focus = False
            yield rich_log

        with Container(id="input-container"):
            yield Input(
                placeholder="Type your message or /help for commands...",
                id="user-input"
            )

    def on_mount(self) -> None:
        """Initialize chat and focus input."""
        messages = self.query_one("#messages", RichLog)
        messages.write("[bold cyan]🤖 SQL Agent TUI[/bold cyan]\n")
        messages.write("[dim]Welcome! Use slash commands to get started:[/dim]")
        messages.write("[dim]  /models - Configure LLM provider and API key[/dim]")
        messages.write("[dim]  /db - Connect to PostgreSQL database[/dim]")
        messages.write("[dim]  /help - Show all commands[/dim]")
        messages.write("")
        messages.write("[bold yellow]💡 How to copy text:[/bold yellow]")
        messages.write("[dim]  Linux/Windows: Hold SHIFT while selecting, then CTRL+SHIFT+C[/dim]")
        messages.write("[dim]  Mac: Hold OPTION while selecting, then CMD+C[/dim]\n")

        input_widget = self.query_one("#user-input", Input)
        input_widget.can_focus = True
        self.set_timer(0.05, lambda: input_widget.focus())
        self.set_timer(0.2, lambda: input_widget.focus())

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input."""
        user_input = event.value.strip()
        if not user_input:
            return

        event.input.value = ""
        messages = self.query_one("#messages", RichLog)
        messages.write(f"\n[bold green]You:[/bold green] {user_input}")

        if user_input.startswith("/"):
            self.run_worker(
                self.handle_command(user_input),
                name="command_handler",
                exclusive=True
            )
            return

        if not self.agent:
            messages.write("[bold red]Error:[/bold red] Please configure LLM provider first using /models")
            return

        if not self.db_tools.connection_params:
            messages.write("[bold yellow]Warning:[/bold yellow] No database connected. Use /db to connect.")
            return

        # Try intent detection for simple queries
        intent_response = self.intent_detector.process_message(user_input)
        if intent_response:
            messages.write(f"\n[bold cyan]⚡ Quick Response:[/bold cyan]\n{intent_response}")
            return

        # Use full agent with ReAct pattern
        self.run_worker(
            self._process_agent_streaming(user_input),
            name="agent_processing",
            exclusive=True
        )

    async def _process_agent_streaming(self, user_input: str) -> None:
        """Process with ReAct pattern - continuous reasoning and tool usage."""
        messages = self.query_one("#messages", RichLog)
        messages.write("\n[dim]🤔 Thinking...[/dim]")

        try:
            async for event in self.agent.process_message_streaming(user_input, self.agent_state):
                await self._handle_agent_event(event, messages)

        except Exception as e:
            messages.write(f"\n[bold red]Error:[/bold red] {str(e)}")

        finally:
            self.query_one("#user-input", Input).focus()

    async def _handle_agent_event(self, event: AgentEvent, messages: RichLog) -> None:
        """Handle a single agent event."""

        if event.type == AgentEvent.THINKING:
            iteration = event.data.get("iteration", 1)
            if iteration > 1:
                messages.write(f"[dim]🤔 Thinking (step {iteration})...[/dim]")

        elif event.type == AgentEvent.TOOL_CALL:
            tool_name = event.data.get("tool", "unknown")
            tool_args = event.data.get("args", {})
            args_str = ", ".join(f"{k}={repr(v)[:30]}" for k, v in tool_args.items()) if tool_args else ""
            messages.write(f"[bold magenta]🔧 Calling:[/bold magenta] [cyan]{tool_name}[/cyan]({args_str})")

        elif event.type == AgentEvent.TOOL_RESULT:
            tool_name = event.data.get("tool", "unknown")
            result = event.data.get("result", "")
            result_preview = self._format_tool_result(tool_name, result)
            messages.write(f"[dim]   ↳ {result_preview}[/dim]")

        elif event.type == AgentEvent.APPROVAL_NEEDED:
            sql = event.data.get("sql", "")

            messages.write(f"\n[bold yellow]📋 SQL Query Requires Approval:[/bold yellow]")
            messages.write(f"```sql\n{sql}\n```")

            # Show approval modal
            approved = await self.app.push_screen_wait(
                QueryApprovalModal(sql)
            )

            if approved:
                messages.write("\n[green]✓ Query approved - executing...[/green]")
            else:
                messages.write("\n[red]✗ Query rejected[/red]")

            # Continue after approval
            async for post_event in self.agent.continue_after_approval(
                approved=approved,
                sql=sql,
                tool_call_id=event.data.get("tool_call_id", ""),
                state=event.data
            ):
                await self._handle_agent_event(post_event, messages)

        elif event.type == AgentEvent.RESPONSE:
            content = event.data.get("content", "")
            messages.write(f"\n[bold yellow]Agent:[/bold yellow]\n{content}")
            self.agent_state = event.data.get("state", self.agent_state)

        elif event.type == AgentEvent.ERROR:
            error = event.data.get("error", "Unknown error")
            messages.write(f"\n[bold red]Error:[/bold red] {error}")

    def _format_tool_result(self, tool_name: str, result) -> str:
        """Format tool result for display."""
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except:
                return result[:150] + "..." if len(result) > 150 else result

        if isinstance(result, dict):
            if "error" in result:
                return f"❌ {result['error']}"

            if tool_name == "list_schemas":
                schemas = result.get("schemas", [])
                return f"Found {len(schemas)} schemas: {', '.join(schemas[:5])}"

            elif tool_name == "list_tables":
                tables = result.get("tables", [])
                names = [t.get("name", t) if isinstance(t, dict) else t for t in tables[:5]]
                more = f"... (+{len(tables) - 5} more)" if len(tables) > 5 else ""
                return f"Found {len(tables)} tables: {', '.join(names)}{more}"

            elif tool_name == "inspect_schema":
                columns = result.get("columns", [])
                col_names = [c.get("name", c) if isinstance(c, dict) else c for c in columns[:3]]
                return f"Found {len(columns)} columns: {', '.join(col_names)}..."

            elif tool_name == "get_table_relationships":
                fks = result.get("foreign_keys", [])
                refs = result.get("referenced_by", [])
                return f"Found {len(fks)} foreign keys, {len(refs)} references"

            elif tool_name == "validate_sql":
                return "✓ SQL is valid" if result.get("valid") else f"❌ {result.get('error', 'Invalid')}"

            elif tool_name == "execute_query":
                rows = result.get("rows", [])
                if rows:
                    # Show preview of first row
                    first_row = rows[0]
                    preview = str(first_row)[:80] + "..." if len(str(first_row)) > 80 else str(first_row)
                    return f"Query returned {len(rows)} rows. First: {preview}"
                return f"Query returned {len(rows)} rows"

        return str(result)[:150]

    async def handle_command(self, command: str) -> None:
        """Handle slash commands."""
        messages = self.query_one("#messages", RichLog)
        cmd = command.split(maxsplit=1)[0].lower()

        if cmd == "/help":
            self._show_help()
        elif cmd == "/models":
            await self._configure_models()
        elif cmd == "/db":
            await self._configure_database()
        elif cmd == "/status":
            self._show_status()
        elif cmd == "/clear":
            messages.clear()
            self.agent_state = None
            messages.write("[green]✓ Chat cleared[/green]")
        else:
            messages.write(f"[red]Unknown command: {cmd}[/red]")
            messages.write("[dim]Type /help for available commands[/dim]")

    def _show_help(self) -> None:
        """Show help message."""
        messages = self.query_one("#messages", RichLog)
        messages.write("\n[bold]Available Commands:[/bold]")
        messages.write("  [cyan]/models[/cyan] - Configure LLM provider")
        messages.write("  [cyan]/db[/cyan] - Connect to PostgreSQL database")
        messages.write("  [cyan]/status[/cyan] - Show current status")
        messages.write("  [cyan]/clear[/cyan] - Clear chat history")
        messages.write("  [cyan]/help[/cyan] - Show this help")
        messages.write("\n[bold]How It Works:[/bold]")
        messages.write("  The agent thinks step-by-step and uses tools dynamically.")
        messages.write("  It will explore the database, run queries, and adapt based on results.")
        messages.write("  SQL queries require your approval before execution.")
        messages.write("\n[bold]Example Queries:[/bold]")
        messages.write("  - What tables are in the database?")
        messages.write("  - How many users are there?")
        messages.write("  - Show me 5 messages from the messages table")
        messages.write("  - What are the relationships between tables?")

    async def _configure_models(self) -> None:
        """Configure LLM provider."""
        messages = self.query_one("#messages", RichLog)

        config = await self.app.push_screen_wait(ModelsConfigModal())

        if config:
            try:
                self.config = config
                self.agent = SQLAgent.create_agent(
                    provider=config["provider"],
                    api_key=config["api_key"],
                    model=config["model"],
                    db_tools=self.db_tools
                )

                self.query_one("#provider-status", Label).update(f"Provider: {config['provider'].title()}")
                self.query_one("#model-status", Label).update(f"Model: {config['model']}")

                messages.write(f"\n[green]✓ LLM configured: {config['provider']} / {config['model']}[/green]")
                messages.write("[dim]Use /db to connect to a database.[/dim]")

            except Exception as e:
                messages.write(f"\n[red]❌ Error: {str(e)}[/red]")
        else:
            messages.write("\n[dim]Configuration cancelled[/dim]")

        self.query_one("#user-input", Input).focus()

    async def _configure_database(self) -> None:
        """Configure database connection."""
        messages = self.query_one("#messages", RichLog)

        connected = await self.app.push_screen_wait(DatabaseConfigModal(self.db_tools))

        if connected:
            db_name = self.db_tools.connection_params.get("database", "Unknown")
            self.query_one("#db-status", Label).update(f"DB: {db_name}")
            messages.write(f"\n[green]✓ Connected to: {db_name}[/green]")
        else:
            messages.write("\n[dim]Configuration cancelled[/dim]")

        self.query_one("#user-input", Input).focus()

    def _show_status(self) -> None:
        """Show current status."""
        messages = self.query_one("#messages", RichLog)
        messages.write("\n[bold]Current Status:[/bold]")

        if self.agent and self.config:
            messages.write(f"  [green]✓[/green] LLM: {self.config['provider']} / {self.config['model']}")
        else:
            messages.write("  [red]✗[/red] LLM: Not configured (use /models)")

        if self.db_tools.connection_params:
            db_name = self.db_tools.connection_params.get("database", "Unknown")
            db_host = self.db_tools.connection_params.get("host", "Unknown")
            messages.write(f"  [green]✓[/green] Database: {db_name} @ {db_host}")
        else:
            messages.write("  [red]✗[/red] Database: Not connected (use /db)")
