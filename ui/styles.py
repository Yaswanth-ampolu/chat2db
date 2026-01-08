"""CSS styles for the SQL Agent TUI."""

MODAL_STYLES = """
/* Database Configuration Modal */
DatabaseConfigModal {
    align: center middle;
}

#db-dialog {
    width: 70;
    height: auto;
    border: thick $accent 80%;
    background: $surface;
    padding: 1 2;
}

/* Models Configuration Modal */
ModelsConfigModal {
    align: center middle;
}

#models-dialog {
    width: 70;
    height: auto;
    max-height: 90vh;
    border: thick $accent 80%;
    background: $surface;
    padding: 1 2;
}

#model-list {
    width: 100%;
    height: 15;
    border: solid $accent;
    margin: 1 0;
}

#model-status {
    color: $text-muted;
    margin: 0 0 0 0;
    text-align: center;
}

/* Query Approval Modal */
QueryApprovalModal {
    align: center middle;
}

#approval-dialog {
    width: 80;
    height: auto;
    border: thick $warning 80%;
    background: $surface;
    padding: 1 2;
}

#query-display {
    width: 100%;
    height: auto;
    border: solid $accent;
    padding: 1;
    margin: 1 0;
    max-height: 20;
}

/* Common modal styles */
.config-title {
    text-align: center;
    text-style: bold;
    color: $accent;
    margin: 0 0 1 0;
}

.approval-title {
    text-align: center;
    text-style: bold;
    color: $warning;
    margin: 0 0 1 0;
}

.field-label {
    margin: 1 0 0 0;
    color: $text;
}

.field-input {
    margin: 0 0 1 0;
}

#button-container {
    width: 100%;
    height: auto;
    align: center middle;
    margin: 1 0 0 0;
}

.modal-button {
    margin: 0 1;
}

.approval-btn {
    margin: 0 1;
    min-width: 12;
}

#error-msg {
    color: $error;
    margin: 1 0;
    min-height: 1;
}

#success-msg {
    color: $success;
    margin: 1 0;
    min-height: 1;
}

.provider-btn {
    margin: 0 1 1 0;
    min-width: 15;
}

.provider-selected {
    background: $accent;
}

.model-btn {
    margin: 0 1 1 0;
    min-width: 20;
}

.model-selected {
    background: $accent;
}
"""

CHAT_VIEW_STYLES = """
ChatView {
    layout: grid;
    grid-size: 1 3;
    grid-rows: auto 1fr auto;
}

#status-bar {
    height: 3;
    background: $surface;
    padding: 0 1;
    border-bottom: solid $accent;
}

#status-content {
    width: 100%;
    height: 100%;
}

.status-label {
    margin: 0 2 0 0;
    color: $text-muted;
}

#chat-container {
    width: 100%;
    height: 100%;
    overflow: hidden;
}

#messages {
    padding: 1;
    height: 100%;
    background: $background;
    scrollbar-gutter: stable;
}

#input-container {
    height: auto;
    min-height: 3;
    max-height: 10;
    background: $surface;
    padding: 1 2;
    border-top: solid $accent;
}

#user-input {
    width: 100%;
    height: auto;
    min-height: 3;
    max-height: 8;
    border: tall $accent;
}
"""
