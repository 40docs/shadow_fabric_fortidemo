#!/usr/bin/env python3
"""
FortiCNAPP MCP Server

Provides tools to query Lacework/FortiCNAPP for vulnerability data using the CLI.

Tools:
- list_cves: List all CVEs found in your environment
- list_hosts_by_cve: List hosts that contain a specific CVE
- get_critical_cves: Get CVEs above a severity threshold
"""

import asyncio
import json
import subprocess
import sys
from typing import Any, Sequence

from mcp.server import Server
from mcp.types import Tool, TextContent


# Initialize MCP server
server = Server("forticnapp")


def run_lacework_command(args: list[str], json_output: bool = True) -> dict[str, Any]:
    """
    Execute a lacework CLI command and return the result.

    Args:
        args: Command arguments (without 'lacework' prefix)
        json_output: Whether to add --json flag

    Returns:
        Parsed JSON output or error dict

    Raises:
        RuntimeError: If command fails
    """
    cmd = ["lacework"] + args
    if json_output and "--json" not in args:
        cmd.append("--json")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=60
        )

        if json_output:
            return json.loads(result.stdout)
        return {"output": result.stdout}

    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Lacework command failed: {e.stderr or e.stdout}"
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Lacework command timed out after 60 seconds")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse JSON output: {e}")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="list_cves",
            description=(
                "List all CVEs found in hosts in your environment. "
                "Returns CVE ID, severity, CVSS scores, affected packages, and host count. "
                "Optionally filter by severity level (Critical, High, Medium, Low) or CVSS threshold."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "severity_filter": {
                        "type": "string",
                        "description": "Filter by severity (Critical, High, Medium, Low)",
                        "enum": ["Critical", "High", "Medium", "Low"]
                    },
                    "min_cvss_score": {
                        "type": "number",
                        "description": "Minimum CVSS score (0.0-10.0)",
                        "minimum": 0.0,
                        "maximum": 10.0
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start of time range (default: -24h). Examples: -7d, -1w, 2024-01-01T00:00:00Z"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End of time range (default: now). Examples: now, 2024-01-31T23:59:59Z"
                    }
                }
            }
        ),
        Tool(
            name="list_hosts_by_cve",
            description=(
                "List all hosts that contain a specific CVE ID. "
                "Returns machine ID, hostname, IP addresses, OS, cloud provider, instance ID, and status. "
                "Useful for identifying which instances need patching or remediation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "cve_id": {
                        "type": "string",
                        "description": "CVE identifier (e.g., CVE-2024-1234)",
                        "pattern": "^CVE-\\d{4}-\\d+$"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start of time range (default: -24h)"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End of time range (default: now)"
                    }
                },
                "required": ["cve_id"]
            }
        ),
        Tool(
            name="get_critical_cves",
            description=(
                "Get high-priority CVEs that need immediate attention. "
                "Returns CVEs with CVSS score >= 9.0 (Critical) or as specified. "
                "Includes host count and severity details for prioritization."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "min_cvss_score": {
                        "type": "number",
                        "description": "Minimum CVSS score threshold (default: 9.0 for Critical)",
                        "minimum": 0.0,
                        "maximum": 10.0,
                        "default": 9.0
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start of time range (default: -24h)"
                    }
                }
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
    """Handle tool execution."""

    try:
        if name == "list_cves":
            return await handle_list_cves(arguments)
        elif name == "list_hosts_by_cve":
            return await handle_list_hosts_by_cve(arguments)
        elif name == "get_critical_cves":
            return await handle_get_critical_cves(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def handle_list_cves(args: dict[str, Any]) -> Sequence[TextContent]:
    """List all CVEs in the environment."""
    cmd_args = ["vulnerability", "host", "list-cves"]

    # Add time range if specified
    if args.get("start_time"):
        cmd_args.extend(["--start", args["start_time"]])
    if args.get("end_time"):
        cmd_args.extend(["--end", args["end_time"]])

    # Execute command
    result = run_lacework_command(cmd_args)

    # Parse and filter results
    cves = result.get("data", [])

    # Apply severity filter
    if args.get("severity_filter"):
        severity = args["severity_filter"]
        cves = [cve for cve in cves if cve.get("severity", "").lower() == severity.lower()]

    # Apply CVSS score filter
    if args.get("min_cvss_score"):
        min_score = args["min_cvss_score"]
        cves = [
            cve for cve in cves
            if float(cve.get("cvss_score", 0) or 0) >= min_score
        ]

    # Format response
    summary = {
        "total_cves": len(cves),
        "filters_applied": {
            k: v for k, v in args.items() if v is not None
        },
        "cves": cves
    }

    return [TextContent(
        type="text",
        text=json.dumps(summary, indent=2)
    )]


async def handle_list_hosts_by_cve(args: dict[str, Any]) -> Sequence[TextContent]:
    """List hosts affected by a specific CVE."""
    cve_id = args["cve_id"]

    cmd_args = ["vulnerability", "host", "list-hosts", cve_id]

    # Add time range if specified
    if args.get("start_time"):
        cmd_args.extend(["--start", args["start_time"]])
    if args.get("end_time"):
        cmd_args.extend(["--end", args["end_time"]])

    # Execute command
    result = run_lacework_command(cmd_args)

    hosts = result.get("data", [])

    # Format response
    summary = {
        "cve_id": cve_id,
        "affected_hosts_count": len(hosts),
        "hosts": hosts
    }

    return [TextContent(
        type="text",
        text=json.dumps(summary, indent=2)
    )]


async def handle_get_critical_cves(args: dict[str, Any]) -> Sequence[TextContent]:
    """Get critical CVEs above severity threshold."""
    min_score = args.get("min_cvss_score", 9.0)

    cmd_args = ["vulnerability", "host", "list-cves"]

    if args.get("start_time"):
        cmd_args.extend(["--start", args["start_time"]])

    # Execute command
    result = run_lacework_command(cmd_args)

    # Filter for critical CVEs
    all_cves = result.get("data", [])
    critical_cves = [
        cve for cve in all_cves
        if float(cve.get("cvss_score", 0) or 0) >= min_score
    ]

    # Sort by CVSS score (highest first)
    critical_cves.sort(
        key=lambda x: float(x.get("cvss_score", 0) or 0),
        reverse=True
    )

    # Format response
    summary = {
        "threshold": min_score,
        "critical_cves_count": len(critical_cves),
        "total_cves_scanned": len(all_cves),
        "critical_cves": critical_cves
    }

    return [TextContent(
        type="text",
        text=json.dumps(summary, indent=2)
    )]


async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
