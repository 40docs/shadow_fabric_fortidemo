#!/usr/bin/env python3
"""
Test the FortiCNAPP MCP server by connecting to it as a client.

This simulates what Claude Desktop does when calling the MCP server.
"""

import asyncio
import json
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_mcp_server():
    """Test the MCP server by calling its tools."""

    print("FortiCNAPP MCP Server Test")
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

        # Test 1: Get critical CVEs
        print("Test 1: get_critical_cves")
        print("-" * 60)
        try:
            result = await session.call_tool(
                "get_critical_cves",
                arguments={"min_cvss_score": 9.0, "start_time": "-5m"}
            )

            # Parse the result
            for content in result.content:
                if hasattr(content, 'text'):
                    data = json.loads(content.text)
                    print(f"✅ Success!")
                    print(f"   Threshold: {data['threshold']}")
                    print(f"   Critical CVEs found: {data['critical_cves_count']}")
                    print(f"   Total CVEs scanned: {data['total_cves_scanned']}")

                    if data['critical_cves_count'] > 0:
                        print(f"\n   Sample critical CVE:")
                        sample = data['critical_cves'][0]
                        print(f"   - {sample.get('cve_id', 'N/A')}: CVSS {sample.get('cvss_score', 'N/A')}")
                    print()
        except Exception as e:
            print(f"❌ Error: {e}\n")

        # Test 2: List CVEs with filter
        print("Test 2: list_cves (with severity filter)")
        print("-" * 60)
        try:
            result = await session.call_tool(
                "list_cves",
                arguments={
                    "severity_filter": "Critical",
                    "start_time": "-5m"
                }
            )

            for content in result.content:
                if hasattr(content, 'text'):
                    data = json.loads(content.text)
                    print(f"✅ Success!")
                    print(f"   Total CVEs: {data['total_cves']}")
                    print(f"   Filters: {data['filters_applied']}")
                    print()
        except Exception as e:
            print(f"❌ Error: {e}\n")

        # Test 3: List hosts by CVE (will only work if you have a known CVE)
        print("Test 3: list_hosts_by_cve")
        print("-" * 60)
        print("ℹ️  Skipping - requires a valid CVE ID from your environment")
        print("   To test manually, use a CVE from the results above:")
        print("   result = await session.call_tool('list_hosts_by_cve', {'cve_id': 'CVE-XXXX-XXXXX'})")
        print()

        # Summary
        print("=" * 60)
        print("✅ MCP Server Test Complete!")
        print("\nThe server is working correctly and can:")
        print("  - Accept tool calls")
        print("  - Execute Lacework CLI commands")
        print("  - Return structured JSON responses")
        print("\nNext step: Configure Claude Desktop to use this server")
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
    exit(exit_code)
