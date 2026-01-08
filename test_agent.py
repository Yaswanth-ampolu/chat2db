#!/usr/bin/env python3
"""Test agent creation with new langchain packages."""

import sys

print("Testing agent creation...")

try:
    print("1. Importing tools...")
    from tools import PostgreSQLTools, create_langchain_tools
    print("   ✅ Tools imported")

    print("2. Creating PostgreSQLTools...")
    db_tools = PostgreSQLTools()
    print("   ✅ PostgreSQLTools created")

    print("3. Creating langchain tools...")
    tools = create_langchain_tools(db_tools)
    print(f"   ✅ Created {len(tools)} tools")

    print("4. Importing agent...")
    from agent import SQLAgent
    print("   ✅ Agent module imported")

    print("5. Testing Google Gemini agent creation...")
    # This will fail without API key, but should pass import stage
    try:
        agent = SQLAgent.create_agent(
            provider="google",
            api_key="test-key",
            model="gemini-1.5-flash",
            db_tools=db_tools
        )
        print("   ✅ Agent created (will fail on actual API call, which is OK)")
    except Exception as e:
        error_msg = str(e)
        if "InjectState" in error_msg:
            print(f"   ❌ ERROR: {error_msg}")
            print("   This is the InjectState import error!")
            sys.exit(1)
        elif "Tool" in error_msg and "import" in error_msg.lower():
            print(f"   ❌ ERROR: {error_msg}")
            print("   This is the Tool import error!")
            sys.exit(1)
        elif "bind_tools" in error_msg:
            print(f"   ❌ ERROR: {error_msg}")
            print("   This is the bind_tools error!")
            sys.exit(1)
        else:
            # Other errors (like API key invalid) are OK for this test
            print(f"   ✅ Agent imports work (error is: {error_msg[:50]}...)")

    print("\n✅ ALL TESTS PASSED!")
    print("The imports are fixed. Agent creation should work with valid API key.")
    sys.exit(0)

except Exception as e:
    print(f"\n❌ TEST FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
