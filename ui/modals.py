"""Modal dialogs for SQL Agent TUI configuration."""

from textual.screen import ModalScreen
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Input, Label, Static, ListView, ListItem
from textual.app import ComposeResult
from textual.worker import Worker
from rich.syntax import Syntax
from typing import Dict, Optional, List

from api_models import ModelFetcher, get_fallback_models
from tools import PostgreSQLTools
from config import get_config
from .styles import MODAL_STYLES


class DatabaseConfigModal(ModalScreen[bool]):
    """Modal screen for PostgreSQL database configuration."""

    DEFAULT_CSS = MODAL_STYLES

    def __init__(self, db_tools: PostgreSQLTools):
        super().__init__()
        self.db_tools = db_tools

    def compose(self) -> ComposeResult:
        with Container(id="db-dialog"):
            yield Label("🗄️  PostgreSQL Database Configuration", classes="config-title")

            yield Label("Host:", classes="field-label")
            yield Input(
                placeholder="localhost",
                value="localhost",
                id="host-input",
                classes="field-input"
            )

            yield Label("Port:", classes="field-label")
            yield Input(
                placeholder="5432",
                value="5432",
                id="port-input",
                classes="field-input",
                type="integer"
            )

            yield Label("Database Name:", classes="field-label")
            yield Input(
                placeholder="mydb",
                id="database-input",
                classes="field-input"
            )

            yield Label("Username:", classes="field-label")
            yield Input(
                placeholder="postgres",
                id="user-input",
                classes="field-input"
            )

            yield Label("Password:", classes="field-label")
            yield Input(
                placeholder="password",
                password=True,
                id="password-input",
                classes="field-input"
            )

            yield Static("", id="error-msg")
            yield Static("", id="success-msg")

            with Horizontal(id="button-container"):
                yield Button("Test Connection", variant="default", id="test-btn", classes="modal-button")
                yield Button("✓ Connect", variant="success", id="connect-btn", classes="modal-button")
                yield Button("✗ Cancel", variant="error", id="cancel-btn", classes="modal-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(False)
        elif event.button.id == "test-btn":
            self._test_connection()
        elif event.button.id == "connect-btn":
            self._connect()

    def _test_connection(self) -> None:
        """Test database connection."""
        error_msg = self.query_one("#error-msg", Static)
        success_msg = self.query_one("#success-msg", Static)
        error_msg.update("")
        success_msg.update("")

        # Get values
        host = self.query_one("#host-input", Input).value.strip()
        port_str = self.query_one("#port-input", Input).value.strip()
        database = self.query_one("#database-input", Input).value.strip()
        user = self.query_one("#user-input", Input).value.strip()
        password = self.query_one("#password-input", Input).value

        # Validate
        if not all([host, port_str, database, user, password]):
            error_msg.update("❌ All fields are required")
            return

        try:
            port = int(port_str)
        except ValueError:
            error_msg.update("❌ Port must be a number")
            return

        # Test connection
        result = self.db_tools.connect(host, port, database, user, password)

        if result["success"]:
            success_msg.update(f"✓ {result['message']}")
        else:
            error_msg.update(f"❌ {result['error']}")

    def _connect(self) -> None:
        """Connect and close modal."""
        error_msg = self.query_one("#error-msg", Static)
        success_msg = self.query_one("#success-msg", Static)
        error_msg.update("")
        success_msg.update("")

        # Get values
        host = self.query_one("#host-input", Input).value.strip()
        port_str = self.query_one("#port-input", Input).value.strip()
        database = self.query_one("#database-input", Input).value.strip()
        user = self.query_one("#user-input", Input).value.strip()
        password = self.query_one("#password-input", Input).value

        # Validate
        if not all([host, port_str, database, user, password]):
            error_msg.update("❌ All fields are required")
            return

        try:
            port = int(port_str)
        except ValueError:
            error_msg.update("❌ Port must be a number")
            return

        # Connect
        result = self.db_tools.connect(host, port, database, user, password)

        if result["success"]:
            self.dismiss(True)
        else:
            error_msg.update(f"❌ {result['error']}")


class ModelsConfigModal(ModalScreen[Dict[str, str]]):
    """Modal screen for LLM provider configuration."""

    DEFAULT_CSS = MODAL_STYLES

    def __init__(self):
        super().__init__()
        self.config = get_config()
        self.selected_provider = self.config.get_last_provider() or "google"
        self.selected_model = ""
        self.available_models: List[str] = []
        self.fetching_models = False

    def compose(self) -> ComposeResult:
        with Container(id="models-dialog"):
            yield Label("🤖 LLM Provider Configuration", classes="config-title")

            yield Label("Select Provider:", classes="field-label")
            with Horizontal():
                yield Button("Google Gemini", id="provider-google", classes="provider-btn provider-selected")
                yield Button("OpenAI", id="provider-openai", classes="provider-btn")
                yield Button("Anthropic", id="provider-anthropic", classes="provider-btn")

            yield Label("API Key:", classes="field-label")
            yield Input(
                placeholder="Enter your API key...",
                password=True,
                id="api-key-input",
                classes="field-input"
            )

            yield Label("Select Model (click to select):", classes="field-label", id="model-label")
            yield Static("Loading models...", id="model-status")

            # Scrollable list view for models
            yield ListView(id="model-list")

            yield Static("", id="error-msg")

            with Horizontal(id="button-container"):
                yield Button("🔄 Refresh Models", variant="default", id="refresh-btn", classes="modal-button")
                yield Button("✓ Save", variant="success", id="save-btn", classes="modal-button")
                yield Button("✗ Cancel", variant="error", id="cancel-btn", classes="modal-button")

    def on_mount(self) -> None:
        """Initialize model buttons."""
        # Restore last selected provider
        provider_buttons = {
            "google": "#provider-google",
            "openai": "#provider-openai",
            "anthropic": "#provider-anthropic"
        }

        for provider, btn_id in provider_buttons.items():
            btn = self.query_one(btn_id, Button)
            if provider == self.selected_provider:
                btn.add_class("provider-selected")
            else:
                btn.remove_class("provider-selected")

        # Load saved API key if available
        saved_api_key = self.config.get_api_key(self.selected_provider)
        if saved_api_key:
            self.query_one("#api-key-input", Input).value = saved_api_key

        # Fetch models
        self._fetch_models()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id == "cancel-btn":
            self.dismiss(None)

        elif button_id == "save-btn":
            self._save_config()

        elif button_id == "refresh-btn":
            self._fetch_models(force_api=True)

        elif button_id and button_id.startswith("provider-"):
            # Provider selection
            provider = button_id.replace("provider-", "")
            self.selected_provider = provider

            # Update button styles
            for btn in self.query("Button.provider-btn"):
                if btn.id == button_id:
                    btn.add_class("provider-selected")
                else:
                    btn.remove_class("provider-selected")

            # Load saved API key for this provider
            saved_api_key = self.config.get_api_key(self.selected_provider)
            if saved_api_key:
                self.query_one("#api-key-input", Input).value = saved_api_key
            else:
                self.query_one("#api-key-input", Input).value = ""

            # Fetch models for new provider
            self._fetch_models()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle model selection from ListView."""
        # Get the selected index from the ListView
        list_view = event.list_view
        if list_view.index is not None and list_view.index < len(self.available_models):
            self.selected_model = self.available_models[list_view.index]
            # Update status to show selection
            status = self.query_one("#model-status", Static)
            status.update(f"✓ Selected: {self.selected_model}")

    def _fetch_models(self, force_api: bool = False) -> None:
        """Fetch models for selected provider."""
        if self.fetching_models:
            return

        self.fetching_models = True
        status = self.query_one("#model-status", Static)
        status.update(f"⏳ Loading {self.selected_provider} models...")

        # Get API key
        api_key = self.query_one("#api-key-input", Input).value.strip() if force_api else None
        if not api_key:
            api_key = self.config.get_api_key(self.selected_provider)

        # Fetch models in background
        self.run_worker(
            self._fetch_models_async(api_key),
            name="fetch_models",
            exclusive=True
        )

    async def _fetch_models_async(self, api_key: Optional[str]) -> None:
        """Async worker to fetch models."""
        try:
            # Try to fetch from API
            models = await ModelFetcher.fetch_all_models(self.selected_provider, api_key)

            if not models:
                # Use fallback
                models = get_fallback_models(self.selected_provider)

            self.available_models = models

        except Exception as e:
            # Use fallback on error
            self.available_models = get_fallback_models(self.selected_provider)

        finally:
            self.fetching_models = False
            # Update UI - this runs automatically when worker completes
            self._update_model_buttons()

    def _update_model_buttons(self) -> None:
        """Update model list based on fetched models."""
        list_view = self.query_one("#model-list", ListView)
        status = self.query_one("#model-status", Static)

        # Clear existing items
        list_view.clear()

        if not self.available_models:
            status.update("❌ No models available")
            return

        status.update(f"✓ {len(self.available_models)} models available")

        # Get last used model for this provider
        last_model = self.config.get_last_model(self.selected_provider)
        if last_model and last_model in self.available_models:
            self.selected_model = last_model
        else:
            self.selected_model = self.available_models[0] if self.available_models else ""

        # Add model items to ListView
        for i, model in enumerate(self.available_models):
            list_item = ListItem(Label(model))
            list_view.append(list_item)

            # Highlight selected model
            if model == self.selected_model:
                list_view.index = i

    def _save_config(self) -> None:
        """Save configuration."""
        error_msg = self.query_one("#error-msg", Static)
        error_msg.update("")

        # Get API key
        api_key = self.query_one("#api-key-input", Input).value.strip()

        if not api_key:
            error_msg.update("❌ Please enter an API key")
            return

        if not self.selected_model:
            error_msg.update("❌ Please select a model")
            return

        # Save to config
        self.config.set_api_key(self.selected_provider, api_key)
        self.config.set_last_provider(self.selected_provider)
        self.config.set_last_model(self.selected_provider, self.selected_model)

        config = {
            "provider": self.selected_provider,
            "api_key": api_key,
            "model": self.selected_model
        }

        self.dismiss(config)


class QueryApprovalModal(ModalScreen[bool]):
    """Modal for SQL query execution approval."""

    DEFAULT_CSS = MODAL_STYLES

    def __init__(self, sql_query: str):
        super().__init__()
        self.sql_query = sql_query

    def compose(self) -> ComposeResult:
        with Container(id="approval-dialog"):
            yield Label("⚠️  Query Execution Approval", classes="approval-title")
            yield Label("\nThe AI agent wants to execute this SQL query:\n")
            yield Static(
                Syntax(self.sql_query, "sql", theme="monokai", line_numbers=False),
                id="query-display"
            )
            yield Label("\nDo you approve this query?")
            with Horizontal(id="button-container"):
                yield Button("✓ Approve", variant="success", id="approve", classes="approval-btn")
                yield Button("✗ Reject", variant="error", id="reject", classes="approval-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "approve":
            self.dismiss(True)
        else:
            self.dismiss(False)
