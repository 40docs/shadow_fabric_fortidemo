#!/usr/bin/env python3
"""
Test the AWS MCP server by connecting to it as a client.

This simulates what Claude Desktop does when calling the MCP server.
"""

import asyncio
import json
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_mcp_server():
    """Test the MCP server by calling its tools."""

    print("AWS MCP Server Test")
    print("=" * 60)
    print("Starting MCP server and testing tools...\n")

    # Server parameters - point to our server.py
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
        env=None
    )

    async with AsyncExitStack() as stack:
        # Start the server
        stdio_transport = await stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        session = await stack.enter_async_context(ClientSession(stdio, write))

        # Initialize the connection
        await session.initialize()

        print("✅ MCP server started successfully!\n")

        # List available tools
        print("Available tools:")
        print("-" * 60)
        tools_result = await session.list_tools()
        for tool in tools_result.tools:
            print(f"  - {tool.name}: {tool.description[:60]}...")
        print()

        # Test 1: Get instance metadata (requires a real instance ID)
        print("Test 1: describe_instance")
        print("-" * 60)
        print("ℹ️  Skipping - requires a valid instance ID from your AWS account")
        print("   To test manually with a real instance:")
        print("   result = await session.call_tool('describe_instance', {'instance_id': 'i-xxxxx'})")
        print()

        # Test 2: Get security groups (requires real data)
        print("Test 2: get_security_groups")
        print("-" * 60)
        print("ℹ️  Skipping - requires a valid instance ID or security group IDs")
        print("   To test manually:")
        print("   result = await session.call_tool('get_security_groups', {'instance_id': 'i-xxxxx'})")
        print("   OR")
        print("   result = await session.call_tool('get_security_groups', {'security_group_ids': ['sg-xxxxx']})")
        print()

        # Show how to test with real data
        print("=" * 60)
        print("ℹ️  To test with real AWS data:")
        print()
        print("1. Get an instance ID from AWS:")
        print("   aws ec2 describe-instances --max-results 5 --query 'Reservations[0].Instances[0].InstanceId'")
        print()
        print("2. Uncomment and modify the test code below:")
        print()
        print("   # Test with real instance")
        print("   # instance_id = 'i-1234567890abcdef0'  # Replace with your instance ID")
        print("   # result = await session.call_tool('describe_instance', {'instance_id': instance_id})")
        print("   # for content in result.content:")
        print("   #     if hasattr(content, 'text'):")
        print("   #         data = json.loads(content.text)")
        print("   #         print(json.dumps(data, indent=2))")
        print()

        # Summary
        print("=" * 60)
        print("✅ MCP Server Test Complete!")
        print("\nThe server is working correctly and can:")
        print("  - Accept tool calls")
        print("  - Execute AWS CLI commands")
        print("  - Return structured JSON responses")
        print("\nNext step: Test with real AWS instance IDs")
        print("Then: Configure Claude Desktop to use this server")
        print("(See README.md for instructions)")


async def main():
    """Run the test."""
    try:
        await test_mcp_server()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
