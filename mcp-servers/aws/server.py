#!/usr/bin/env python3
"""
AWS MCP Server

Provides tools to query AWS EC2 instance metadata and security groups using the AWS CLI.

Tools:
- describe_instance: Get comprehensive metadata for an EC2 instance
- get_security_groups: Get security group rules and configurations
"""

import asyncio
import json
import subprocess
import sys
from typing import Any, Sequence

from mcp.server import Server
from mcp.types import Tool, TextContent


# Initialize MCP server
server = Server("aws")


def run_aws_command(args: list[str], region: str = None) -> dict[str, Any]:
    """
    Execute an AWS CLI command and return the result.

    Args:
        args: Command arguments (without 'aws' prefix)
        region: AWS region (optional, uses default if not provided)

    Returns:
        Parsed JSON output or error dict

    Raises:
        RuntimeError: If command fails
    """
    cmd = ["aws"] + args

    # Add region if specified
    if region:
        cmd.extend(["--region", region])

    # Always use JSON output
    if "--output" not in cmd:
        cmd.extend(["--output", "json"])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )

        return json.loads(result.stdout)

    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"AWS CLI command failed: {e.stderr or e.stdout}"
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("AWS CLI command timed out after 30 seconds")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse JSON output: {e}")
    except FileNotFoundError:
        raise RuntimeError(
            "AWS CLI not found. Please install it: https://aws.amazon.com/cli/"
        )


def extract_instance_summary(instance_data: dict) -> dict:
    """
    Extract key fields from AWS describe-instances output for easier consumption.

    Args:
        instance_data: Raw instance data from AWS API

    Returns:
        Simplified instance metadata
    """
    # AWS returns instances nested in Reservations
    if not instance_data.get("Reservations"):
        return {"error": "No instance data found"}

    instance = instance_data["Reservations"][0]["Instances"][0]

    # Extract tags into a simple dict
    tags = {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])}

    # Extract security group IDs
    security_groups = [sg["GroupId"] for sg in instance.get("SecurityGroups", [])]

    return {
        "instance_id": instance.get("InstanceId"),
        "instance_type": instance.get("InstanceType"),
        "state": instance.get("State", {}).get("Name"),
        "availability_zone": instance.get("Placement", {}).get("AvailabilityZone"),
        "platform": instance.get("Platform", "linux"),  # Windows if set, else linux

        # Network information
        "public_ip": instance.get("PublicIpAddress"),
        "private_ip": instance.get("PrivateIpAddress"),
        "public_dns": instance.get("PublicDnsName"),
        "private_dns": instance.get("PrivateDnsName"),

        # VPC information
        "vpc_id": instance.get("VpcId"),
        "subnet_id": instance.get("SubnetId"),

        # Security
        "security_group_ids": security_groups,
        "iam_instance_profile": instance.get("IamInstanceProfile", {}).get("Arn"),

        # Metadata
        "tags": tags,
        "launch_time": instance.get("LaunchTime"),
        "architecture": instance.get("Architecture"),
        "virtualization_type": instance.get("VirtualizationType"),

        # For reference/debugging
        "raw_security_groups": instance.get("SecurityGroups", [])
    }


def extract_security_group_summary(sg_data: dict) -> list[dict]:
    """
    Extract and simplify security group information.

    Args:
        sg_data: Raw security group data from AWS API

    Returns:
        List of simplified security group configurations
    """
    security_groups = []

    for sg in sg_data.get("SecurityGroups", []):
        # Parse inbound rules
        inbound_rules = []
        for rule in sg.get("IpPermissions", []):
            inbound_rules.append({
                "protocol": rule.get("IpProtocol", "all"),
                "from_port": rule.get("FromPort"),
                "to_port": rule.get("ToPort"),
                "ip_ranges": [r.get("CidrIp") for r in rule.get("IpRanges", [])],
                "ipv6_ranges": [r.get("CidrIpv6") for r in rule.get("Ipv6Ranges", [])],
                "source_security_groups": [
                    g.get("GroupId") for g in rule.get("UserIdGroupPairs", [])
                ],
                "description": rule.get("IpRanges", [{}])[0].get("Description", "")
            })

        # Parse outbound rules
        outbound_rules = []
        for rule in sg.get("IpPermissionsEgress", []):
            outbound_rules.append({
                "protocol": rule.get("IpProtocol", "all"),
                "from_port": rule.get("FromPort"),
                "to_port": rule.get("ToPort"),
                "ip_ranges": [r.get("CidrIp") for r in rule.get("IpRanges", [])],
                "ipv6_ranges": [r.get("CidrIpv6") for r in rule.get("Ipv6Ranges", [])],
                "destination_security_groups": [
                    g.get("GroupId") for g in rule.get("UserIdGroupPairs", [])
                ],
                "description": rule.get("IpRanges", [{}])[0].get("Description", "")
            })

        security_groups.append({
            "group_id": sg.get("GroupId"),
            "group_name": sg.get("GroupName"),
            "description": sg.get("Description"),
            "vpc_id": sg.get("VpcId"),
            "inbound_rules": inbound_rules,
            "outbound_rules": outbound_rules,
            "tags": {tag["Key"]: tag["Value"] for tag in sg.get("Tags", [])}
        })

    return security_groups


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="describe_instance",
            description=(
                "Get comprehensive metadata for an EC2 instance by instance ID. "
                "Returns instance details including IPs, DNS names, VPC info, security groups, "
                "tags, IAM role, state, and more. Essential for gathering context about "
                "vulnerable instances before onboarding to security tools."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "instance_id": {
                        "type": "string",
                        "description": "EC2 instance ID (e.g., i-1234567890abcdef0)",
                        "pattern": "^i-[a-f0-9]+$"
                    },
                    "region": {
                        "type": "string",
                        "description": "AWS region (e.g., us-east-1). If not specified, uses default AWS CLI region."
                    },
                    "include_raw": {
                        "type": "boolean",
                        "description": "Include raw AWS API response in addition to simplified summary (default: false)",
                        "default": False
                    }
                },
                "required": ["instance_id"]
            }
        ),
        Tool(
            name="get_security_groups",
            description=(
                "Get detailed security group rules and configurations. Can fetch by security group IDs "
                "or automatically extract and fetch from an instance ID. Returns inbound/outbound rules "
                "with ports, protocols, and source/destination IPs. Critical for understanding what "
                "services are exposed and need protection."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "instance_id": {
                        "type": "string",
                        "description": "EC2 instance ID to get security groups from (e.g., i-1234567890abcdef0)",
                        "pattern": "^i-[a-f0-9]+$"
                    },
                    "security_group_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of security group IDs (e.g., ['sg-12345', 'sg-67890'])"
                    },
                    "region": {
                        "type": "string",
                        "description": "AWS region (e.g., us-east-1). If not specified, uses default AWS CLI region."
                    },
                    "include_raw": {
                        "type": "boolean",
                        "description": "Include raw AWS API response in addition to simplified summary (default: false)",
                        "default": False
                    }
                }
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
    """Handle tool execution."""

    try:
        if name == "describe_instance":
            return await handle_describe_instance(arguments)
        elif name == "get_security_groups":
            return await handle_get_security_groups(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def handle_describe_instance(args: dict[str, Any]) -> Sequence[TextContent]:
    """Describe an EC2 instance."""
    instance_id = args["instance_id"]
    region = args.get("region")
    include_raw = args.get("include_raw", False)

    # Execute AWS CLI command
    cmd_args = ["ec2", "describe-instances", "--instance-ids", instance_id]
    result = run_aws_command(cmd_args, region=region)

    # Extract simplified summary
    summary = extract_instance_summary(result)

    # Build response
    response = {
        "instance_id": instance_id,
        "summary": summary
    }

    if include_raw:
        response["raw"] = result

    return [TextContent(
        type="text",
        text=json.dumps(response, indent=2)
    )]


async def handle_get_security_groups(args: dict[str, Any]) -> Sequence[TextContent]:
    """Get security group information."""
    instance_id = args.get("instance_id")
    security_group_ids = args.get("security_group_ids")
    region = args.get("region")
    include_raw = args.get("include_raw", False)

    # If instance_id provided, get its security groups first
    if instance_id and not security_group_ids:
        # Get instance details to extract security group IDs
        instance_result = run_aws_command(
            ["ec2", "describe-instances", "--instance-ids", instance_id],
            region=region
        )

        if instance_result.get("Reservations"):
            instance = instance_result["Reservations"][0]["Instances"][0]
            security_group_ids = [sg["GroupId"] for sg in instance.get("SecurityGroups", [])]
        else:
            raise ValueError(f"Instance {instance_id} not found")

    if not security_group_ids:
        raise ValueError("Must provide either instance_id or security_group_ids")

    # Get security group details
    cmd_args = ["ec2", "describe-security-groups", "--group-ids"] + security_group_ids
    result = run_aws_command(cmd_args, region=region)

    # Extract simplified summary
    summary = extract_security_group_summary(result)

    # Build response
    response = {
        "security_group_count": len(summary),
        "security_groups": summary
    }

    if include_raw:
        response["raw"] = result

    if instance_id:
        response["instance_id"] = instance_id

    return [TextContent(
        type="text",
        text=json.dumps(response, indent=2)
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
