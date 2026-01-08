#!/usr/bin/env python3
"""Test script to verify Input widget works."""

from textual.app import App
from textual.widgets import Input, Static
from textual.containers import Container


class TestInputApp(App):
    """Simple app to test input."""

    CSS = """
    Screen {
        align: center middle;
    }

    Container {
        width: 60;
        height: auto;
        border: solid green;
        padding: 1;
    }

    Input {
        margin: 1 0;
    }
    """

    def compose(self):
        with Container():
            yield Static("Type something and press Enter:")
            yield Input(placeholder="Type here...", id="test-input")
            yield Static("Output will appear here", id="output")

    def on_mount(self):
        """Focus the input when app starts."""
        self.query_one("#test-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted):
        """Handle input submission."""
        output = self.query_one("#output", Static)
        output.update(f"You typed: {event.value}")
        event.input.value = ""


if __name__ == "__main__":
    TestInputApp().run()
