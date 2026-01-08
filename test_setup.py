#!/usr/bin/env python3.11
"""
Test script to verify the SQL Agent TUI setup
"""

import sys

print("🔍 Testing SQL Agent TUI Setup...\n")

# Test 1: Check Python version
print("1. Python Version:")
print(f"   ✓ {sys.version}")

# Test 2: Import Textual
try:
    from textual.app import App
    from textual.widgets import RichLog
    print("2. Textual Framework:")
    print("   ✓ Import successful")
except ImportError as e:
    print(f"2. Textual Framework:")
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

# Test 3: Import LangChain
try:
    import langchain
    from langchain_core.messages import HumanMessage
    print("3. LangChain:")
    print("   ✓ Import successful")
except ImportError as e:
    print(f"3. LangChain:")
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

# Test 4: Import PostgreSQL driver
try:
    import psycopg2
    print("4. PostgreSQL Driver (psycopg2):")
    print("   ✓ Import successful")
except ImportError as e:
    print(f"4. PostgreSQL Driver (psycopg2):")
    print(f"   ✗ Import failed: {e}")
    print("   Install with: pip install psycopg2-binary")
    sys.exit(1)

# Test 5: Import our modules
try:
    from tools import PostgreSQLTools
    from agent import SQLAgent, PROVIDER_MODELS
    print("5. Custom Modules:")
    print("   ✓ tools.py import successful")
    print("   ✓ agent.py import successful")
except ImportError as e:
    print(f"5. Custom Modules:")
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

# Test 6: Check provider models
print("6. Available LLM Providers:")
for provider, models in PROVIDER_MODELS.items():
    print(f"   ✓ {provider.title()}: {len(models)} models")

print("\n✅ All tests passed!")
print("\n📖 Next steps:")
print("1. Edit .env file and add your API key")
print("2. Run the application: python app.py")
print("3. Use /models to configure your LLM")
print("4. Use /db to connect to PostgreSQL")
print("\n🚀 Ready to go!")
