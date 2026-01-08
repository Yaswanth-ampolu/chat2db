#!/bin/bash
# SQL Agent TUI Setup Script
# For Python 3.11+

set -e  # Exit on error

echo "🚀 SQL Agent TUI - Setup Script"
echo "================================"
echo ""

# Check Python version
echo "📌 Checking Python version..."
python_version=$(python3.11 --version 2>&1 | awk '{print $2}')
if [ -z "$python_version" ]; then
    echo "❌ Error: Python 3.11 is not installed"
    echo "Please install Python 3.11 first:"
    echo "  Ubuntu/Debian: sudo apt install python3.11 python3.11-venv"
    echo "  macOS: brew install python@3.11"
    exit 1
fi
echo "✓ Python version: $python_version"
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists. Removing..."
    rm -rf venv
fi
python3.11 -m venv venv
echo "✓ Virtual environment created"
echo ""

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "📥 Upgrading pip..."
pip install --upgrade pip
echo "✓ pip upgraded"
echo ""

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Check if PostgreSQL client libraries are installed
echo "🗄️  Checking PostgreSQL client libraries..."
if ! python -c "import psycopg2" 2>/dev/null; then
    echo "⚠️  psycopg2 installation may need system libraries"
    echo "If you encounter errors, install:"
    echo "  Ubuntu/Debian: sudo apt install libpq-dev"
    echo "  macOS: brew install postgresql"
fi
echo ""

# Create .env template if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env template..."
    cat > .env << 'EOF'
# LLM Provider API Keys
# Uncomment and fill in the API key for your provider

# Google Gemini
# GEMINI_API_KEY=your_gemini_api_key_here

# OpenAI
# OPENAI_API_KEY=your_openai_api_key_here

# Anthropic
# ANTHROPIC_API_KEY=your_anthropic_api_key_here

# PostgreSQL Database (optional - can also configure via /db command)
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=mydb
# DB_USER=postgres
# DB_PASSWORD=password
EOF
    echo "✓ .env template created"
    echo "  Edit .env file to add your API keys"
fi
echo ""

# Make app.py executable
chmod +x app.py
echo "✓ Made app.py executable"
echo ""

echo "✅ Setup complete!"
echo ""
echo "📖 Next steps:"
echo "  1. Edit .env file and add your API key"
echo "  2. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo "  3. Run the application:"
echo "     python app.py"
echo ""
echo "💡 Inside the app:"
echo "  - Type /models to configure your LLM provider"
echo "  - Type /db to connect to PostgreSQL"
echo "  - Type /help to see all commands"
echo ""
echo "Happy querying! 🎉"
