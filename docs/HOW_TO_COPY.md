# 📋 How to Copy Text from the TUI

## The Limitation

**Textual TUI apps don't support direct text selection like web browsers.**

This is a limitation of terminal applications - they capture all mouse/keyboard input for the UI, so standard terminal text selection doesn't work.

## ✅ How to Copy Text (3 Methods)

### Method 1: Terminal's Native Copy (Best)

Most terminals allow you to copy even when an app is running:

**Linux (gnome-terminal, konsole, xterm):**
```
1. Hold SHIFT while selecting text with mouse
2. Press CTRL+SHIFT+C to copy
3. Press CTRL+SHIFT+V to paste
```

**Mac (Terminal.app, iTerm2):**
```
1. Hold Option (⌥) while selecting text
2. Press Cmd+C to copy
3. Press Cmd+V to paste
```

**Windows Terminal:**
```
1. Hold Shift while selecting text
2. Press Ctrl+Shift+C to copy
3. Press Ctrl+Shift+V to paste
```

### Method 2: Terminal Scrollback

1. Scroll up in your terminal (Shift+PageUp)
2. Select and copy text normally
3. Return to app (Shift+PageDown)

### Method 3: Output to File (For Long Outputs)

We can add a `/export` command to save conversation to a file:

```
/export output.txt
```

This will save the entire chat to a text file you can copy from.

## 🔧 Let's Add Export Feature

I'll add a `/export` command that saves the conversation to a file!

Would you like me to add this feature?

## 📝 Quick Workaround

For now, you can:

1. **Use your terminal's native copy** (Shift+Select)
2. **Redirect output:**
   ```bash
   python app.py 2>&1 | tee session.log
   ```
   This logs everything to `session.log`

3. **Take screenshots** for visual reference

## 🎯 Best Practice

**Use tmux or screen with logging enabled:**

```bash
# Start tmux with logging
tmux

# Inside tmux, enable logging
Ctrl+b :
set -g history-file ~/chat2sql-session.log

# Run the app
python app.py

# Everything is now logged!
```

## Why Can't TUI Apps Support Direct Copy?

Terminal applications work differently than GUI apps:

1. **Full Control:** TUI apps take over the entire terminal
2. **Raw Input:** They receive raw keyboard/mouse events
3. **No Selection API:** No standard "select text" API like browsers
4. **Terminal Emulation:** Text is rendered, not stored as HTML

**But** your terminal emulator (the window itself) still supports selection - you just need to bypass the app using Shift or Option keys.

## 💡 Recommended Solution

Use your terminal's **Shift+Select** method:

```
1. Start app: python app.py
2. Ask question: "What tables are in my database?"
3. See response
4. Hold SHIFT
5. Click and drag to select response text
6. Press CTRL+SHIFT+C (Linux) or Cmd+C (Mac)
7. Paste anywhere with CTRL+V (Linux) or Cmd+V (Mac)
```

This works in **all terminal emulators** and is the standard way to copy from TUI apps!
