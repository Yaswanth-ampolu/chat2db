# SQL Agent TUI - Quick Start Guide

## 🚀 Installation & Setup

### 1. Navigate to Directory
```bash
cd /home/yaswanth/programming/PinnacleAi/python/chat2sql
```

### 2. Run Setup Script
```bash
./setup.sh
```

This will:
- Create a Python 3.11 virtual environment
- Install all required packages
- Create a `.env` template

### 3. Configure API Key

Edit `.env` file:
```bash
nano .env
```

Add your Gemini API key:
```env
GEMINI_API_KEY=your_actual_api_key_here
```

### 4. Activate Virtual Environment
```bash
source venv/bin/activate
```

### 5. Run the Application
```bash
python app.py
```

## 🎮 First-Time Usage

### Step 1: Configure LLM Provider
In the application, type:
```
/models
```

- Select "Google Gemini"
- Enter your API key
- Select "gemini-pro" model
- Click "Save"

### Step 2: Connect to PostgreSQL Database
Type:
```
/db
```

Fill in your PostgreSQL details:
- Host: `localhost` (or your server)
- Port: `5432`
- Database: `your_database_name`
- Username: `postgres` (or your username)
- Password: `your_password`

Click "Test Connection" to verify, then "Connect"

### Step 3: Start Asking Questions!

```
What tables are in the database?
```

```
Show me the schema of the users table
```

```
How many records are in each table?
```

## 📋 Available Commands

| Command | Description |
|---------|-------------|
| `/models` | Configure LLM provider (Google, OpenAI, Anthropic) |
| `/db` | Connect to PostgreSQL database |
| `/status` | Show current configuration |
| `/clear` | Clear chat history |
| `/help` | Show help message |

## 🔐 Query Approval

When the AI wants to run a SQL query:
1. A modal appears showing the SQL
2. You can **Approve** ✓ or **Reject** ✗
3. Only approved queries execute

## 🛠️ Troubleshooting

### Issue: psycopg2 not found
```bash
# Ubuntu/Debian
sudo apt install libpq-dev
pip install psycopg2-binary

# macOS
brew install postgresql
pip install psycopg2-binary
```

### Issue: Can't connect to database
- Verify PostgreSQL is running
- Check host, port, username, password
- Ensure database exists
- Check firewall/network settings

### Issue: Invalid API key
- Double-check `.env` file
- Remove quotes around the API key
- Ensure no extra spaces

## 📚 Example Queries

```
Find customers who spent more than $1000

Show orders from the last 7 days

What's the average product price?

List employees hired in 2024

Which products are out of stock?
```

## 🔒 Safety Features

- **Read-Only**: Only SELECT queries allowed
- **Human Approval**: Every query needs your OK
- **Timeout Protection**: Queries timeout after 30 seconds
- **Auto-Limit**: Automatically adds LIMIT to prevent huge result sets

## 📖 Full Documentation

See `TUI_README.md` for complete documentation.

See `/docs` folder for:
- AI Agents Overview
- Gemini SDK Guide
- Tool Creation Guide
- Agent Loop Implementation

---

**Need Help?** Type `/help` in the app or read `TUI_README.md`
