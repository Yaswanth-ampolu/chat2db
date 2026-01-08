#!/bin/bash
# Fix all issues and clean cached files

echo "🧹 Cleaning Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null

echo "🔄 Reinstalling packages to fix version conflicts..."
source venv/bin/activate

# Remove conflicting packages
pip uninstall -y langgraph-prebuilt langgraph langchain langchain-core 2>/dev/null

# Reinstall in correct order
pip install langchain-core==1.2.6
pip install langgraph==1.0.5
pip install langchain==1.2.1

echo "✅ Done! Now run: python app.py"
