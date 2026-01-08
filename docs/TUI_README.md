# SQL Agent TUI - AI-Powered Database Query Interface

A Terminal User Interface (TUI) application that allows you to interact with PostgreSQL databases using natural language through AI agents. Built with Python 3.11, Textual, and LangGraph.

![SQL Agent TUI](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 🌟 Features

- **🤖 AI-Powered Queries**: Use natural language to query your PostgreSQL database
- **🔐 Human-in-the-Loop**: Explicit approval required before executing any SQL query
- **🎨 Beautiful TUI**: Modern terminal interface with modals and real-time updates
- **🔧 Multi-Provider Support**: Works with Google Gemini, OpenAI, and Anthropic
- **⚡ Slash Commands**: Quick configuration with `/models` and `/db` commands
- **🛡️ Safety First**: Only SELECT queries allowed, automatic validation
- **📊 Schema Exploration**: Automatic database schema inspection and understanding
- **🔗 Relationship Discovery**: Understands foreign key relationships between tables

## 📋 Requirements

- Python 3.11 or higher
- PostgreSQL database (local or remote)
- API key for one of:
  - Google Gemini
  - OpenAI
  - Anthropic Claude

## 🚀 Quick Start

### 1. Setup

Run the setup script:

```bash
chmod +x setup.sh
./setup.sh
```

This will:
- Create a Python 3.11 virtual environment
- Install all dependencies
- Create a `.env` template file

### 2. Configure API Key

Edit the `.env` file and add your API key:

```bash
# For Google Gemini
GEMINI_API_KEY=your_api_key_here
```

### 3. Run the Application

```bash
source venv/bin/activate
python app.py
```

## 🎮 Usage

### Initial Setup

When you launch the app, you'll see a welcome screen. Follow these steps:

1. **Configure LLM Provider**
   ```
   /models
   ```
   - Select your provider (Google Gemini, OpenAI, or Anthropic)
   - Enter your API key
   - Choose a model

2. **Connect to Database**
   ```
   /db
   ```
   - Enter host (default: localhost)
   - Enter port (default: 5432)
   - Enter database name
   - Enter username and password
   - Click "Test Connection" to verify
   - Click "Connect" to save

3. **Start Querying!**
   ```
   What tables are in this database?
   ```

### Slash Commands

- `/models` - Configure LLM provider and model
- `/db` - Connect to PostgreSQL database
- `/status` - Show current configuration
- `/clear` - Clear chat history
- `/help` - Show help message

### Example Queries

```
What tables are in the database?

Show me the schema of the users table

How many records are in the orders table?

Find the top 10 customers by revenue

List all orders from the last 30 days

Show me customers who haven't placed orders
```

### Query Approval Flow

When the AI wants to execute a SQL query:

1. The query is displayed in a modal with syntax highlighting
2. You can approve or reject the query
3. If approved, the query executes and results are shown
4. If rejected, the AI will try a different approach

## 🏗️ Architecture

The application follows a clean, modular architecture:

### File Structure

```
chat2sql/
├── app.py                    # Main TUI application
├── agent.py                  # LangGraph agent implementation
├── tools.py                  # PostgreSQL database tools
├── requirements.txt          # Python dependencies
├── setup.sh                  # Setup script
├── README.md                 # This file
└── docs/                     # Additional documentation
    ├── AI_AGENTS_OVERVIEW.md
    ├── GEMINI_SDK_GUIDE.md
    ├── TOOL_CREATION_GUIDE.md
    └── AGENT_LOOP_IMPLEMENTATION.md
```

### Components

#### 1. **TUI (app.py)**
- Built with Textual framework
- Modal screens for configuration
- Slash command handling
- Real-time chat interface

#### 2. **Agent (agent.py)**
- LangGraph-based agent loop
- Multi-provider LLM support
- Tool execution with approval gates
- Conversation state management

#### 3. **Tools (tools.py)**
- PostgreSQL connection management
- Schema inspection
- Query validation and execution
- Safety checks (read-only)

## 🔧 Configuration

### Environment Variables

Create a `.env` file with your API keys:

```env
# Google Gemini
GEMINI_API_KEY=your_key_here

# OpenAI
OPENAI_API_KEY=your_key_here

# Anthropic
ANTHROPIC_API_KEY=your_key_here
```

### Database Connection

You can configure the database in two ways:

1. **Via UI** (Recommended):
   - Use `/db` command in the app
   - Test connection before saving

2. **Via Environment Variables**:
   ```env
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=mydb
   DB_USER=postgres
   DB_PASSWORD=password
   ```

## 🛡️ Security Features

### Read-Only Queries
- Only SELECT statements allowed
- Forbidden operations: DELETE, UPDATE, INSERT, DROP, ALTER, CREATE, GRANT, REVOKE
- Automatic query validation before execution

### Human-in-the-Loop
- Every query requires explicit user approval
- Query displayed with syntax highlighting
- Clear approve/reject interface

### Safety Limits
- 30-second query timeout
- Automatic LIMIT clause addition
- Schema-based validation

## 🎯 Advanced Features

### Schema Intelligence
The AI agent can:
- List all schemas and tables
- Inspect table structures
- Understand primary and foreign keys
- Discover table relationships
- Analyze indexes

### Natural Language Processing
Ask questions like:
- "What's the average order value?"
- "Show me inactive users"
- "Find products that are low in stock"
- "Compare sales between last month and this month"

### Error Recovery
- Handles connection failures gracefully
- Retries with different approaches
- Provides helpful error messages

## 📚 Documentation

Comprehensive guides are available in the `/docs` folder:

1. **[AI Agents Overview](./AI_AGENTS_OVERVIEW.md)** - Understanding AI agents and the ReAct pattern
2. **[Gemini SDK Guide](./GEMINI_SDK_GUIDE.md)** - Using Google's Gemini API for function calling
3. **[Tool Creation Guide](./TOOL_CREATION_GUIDE.md)** - Building custom database tools
4. **[Agent Loop Implementation](./AGENT_LOOP_IMPLEMENTATION.md)** - Understanding the agent execution loop

## 🐛 Troubleshooting

### PostgreSQL Connection Issues

**Error: `psycopg2` module not found**
```bash
# Ubuntu/Debian
sudo apt install libpq-dev python3.11-dev

# macOS
brew install postgresql

# Then reinstall psycopg2
pip install psycopg2-binary
```

**Error: Connection refused**
- Check if PostgreSQL is running
- Verify host and port
- Check firewall settings
- Ensure user has connection permissions

### LLM API Issues

**Error: Invalid API key**
- Verify your API key in `.env` file
- Check for extra spaces or quotes
- Ensure the key is for the correct provider

**Error: Rate limit exceeded**
- Wait a few minutes
- Consider upgrading your API plan
- Switch to a different model

### Application Crashes

**Error: `textual` not found**
```bash
pip install textual==0.47.1
```

**Error: Python version mismatch**
```bash
# Ensure you're using Python 3.11+
python --version

# Recreate virtual environment
rm -rf venv
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- [ ] Support for more databases (MySQL, SQLite, etc.)
- [ ] Query history and favorites
- [ ] Export results to CSV/JSON
- [ ] Visualization of query results
- [ ] Saved database connections
- [ ] Query performance metrics

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

Built with:
- [Textual](https://github.com/Textualize/textual) - TUI framework
- [LangChain](https://github.com/langchain-ai/langchain) - LLM orchestration
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent workflows
- [psycopg2](https://github.com/psycopg/psycopg2) - PostgreSQL adapter

Inspired by:
- [Aider](https://github.com/paul-gauthier/aider) - AI coding assistant
- [vanna.ai](https://github.com/vanna-ai/vanna) - SQL generation
- [Claude Code](https://claude.com/code) - AI development tools

## 📞 Support

Having issues? Check:
1. This README
2. Documentation in `/docs`
3. GitHub issues
4. Stack Overflow with tag `langgraph`

## 🗺️ Roadmap

### v1.0 (Current)
- ✅ PostgreSQL support
- ✅ Multi-provider LLM
- ✅ Slash commands
- ✅ Query approval

### v1.1 (Planned)
- [ ] Query history
- [ ] Result export
- [ ] Connection profiles
- [ ] Advanced table visualization

### v2.0 (Future)
- [ ] Multi-database support
- [ ] Query caching
- [ ] Performance analytics
- [ ] Collaborative features

---

**Made with ❤️ for data analysts and developers who love the terminal**
