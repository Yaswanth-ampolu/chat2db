"""
SQL Agent TUI Application

A Terminal User Interface for interacting with an AI SQL Agent.
Built with Textual framework.
Features slash commands: /models, /db, /help, /clear
"""

from textual.app import App
from textual.binding import Binding

from tools import PostgreSQLTools
from ui import ChatView


class SQLAgentApp(App):
    """Main TUI Application."""

    TITLE = "SQL Agent TUI"
    SUB_TITLE = "AI-Powered Database Query Interface"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
    ]

    CSS = """
    Screen {
        background: $background;
    }
    """

    def __init__(self):
        super().__init__()
        self.db_tools = PostgreSQLTools()
        # Enable mouse support for text selection and copying
        self.mouse_over_widget = None

    def compose(self):
        """Create the main interface."""
        yield ChatView(self.db_tools)

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()


def main():
    """Entry point."""
    app = SQLAgentApp()
    app.run()


if __name__ == "__main__":
    main()
