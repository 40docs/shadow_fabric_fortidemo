#!/usr/bin/env python3
"""
Quick script to query an instance using the AWS MCP server.
"""

import asyncio
import json
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def query_instance(instance_id: str):
    """Query an instance via the MCP server."""

    print(f"Querying instance: {instance_id}")
    print("=" * 60)

    import os

    # Server parameters - pass through current environment for AWS credentials
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
        env=os.environ.copy()  # Pass AWS credentials from current shell
    )

    async with AsyncExitStack() as stack:
        # Start the server
        stdio_transport = await stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        session = await stack.enter_async_context(ClientSession(stdio, write))

        # Initialize
        await session.initialize()

        # Call describe_instance
        print("\n1. Getting instance metadata...")
        print("-" * 60)
        result = await session.call_tool(
            "describe_instance",
            arguments={"instance_id": instance_id}
        )

        instance_data = None
        for content in result.content:
            if hasattr(content, 'text'):
                # Check if it's an error message or JSON
                text = content.text
                if text.startswith("Error:"):
                    print(f"❌ {text}")
                    return
                try:
                    instance_data = json.loads(text)
                    print(json.dumps(instance_data, indent=2))
                except json.JSONDecodeError:
                    print(f"Response: {text}")

        # Get security groups if we have the instance data
        if instance_data and instance_data.get('summary', {}).get('security_group_ids'):
            print("\n2. Getting security group details...")
            print("-" * 60)

            result = await session.call_tool(
                "get_security_groups",
                arguments={"instance_id": instance_id}
            )

            for content in result.content:
                if hasattr(content, 'text'):
                    sg_data = json.loads(content.text)
                    print(json.dumps(sg_data, indent=2))


async def main():
    """Run the query."""
    if len(sys.argv) < 2:
        print("Usage: python query_instance.py <instance-id>")
        return 1

    instance_id = sys.argv[1]

    try:
        await query_instance(instance_id)
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
