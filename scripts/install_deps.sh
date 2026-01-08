#!/bin/bash
# Quick installation script

echo "🔧 Installing updated dependencies..."
echo ""

pip install --upgrade pip

echo "Installing core packages..."
pip install --upgrade textual rich

echo "Installing AI/LLM packages..."
pip install --upgrade langchain langchain-core langgraph
pip install --upgrade langchain-google-genai langchain-openai langchain-anthropic

echo "Installing database packages..."
pip install --upgrade psycopg2-binary

echo "Installing utilities..."
pip install --upgrade python-dotenv pydantic httpx google-generativeai

echo ""
echo "✅ All packages installed!"
echo ""
echo "Now run: python app.py"
