# AWS MCP Server

MCP server that provides tools to query AWS EC2 instance metadata and security groups using the AWS CLI.

## Prerequisites

1. **AWS CLI installed and authenticated**
   ```bash
   # Verify CLI is installed
   aws --version

   # Verify authentication
   aws sts get-caller-identity
   ```

2. **AWS IAM Permissions**
   Required permissions:
   - `ec2:DescribeInstances`
   - `ec2:DescribeSecurityGroups`

3. **Python 3.10+**

4. **MCP Python SDK**
   ```bash
   pip install -r requirements.txt
   ```

## Available Tools

### 1. `describe_instance`
Get comprehensive metadata for an EC2 instance by instance ID.

**Purpose**: Gather complete context about vulnerable instances before onboarding to security tools like FortiAppSec.

**Parameters:**
- `instance_id` (required): EC2 instance ID (e.g., i-1234567890abcdef0)
- `region` (optional): AWS region (e.g., us-east-1). Uses default if not specified.
- `include_raw` (optional): Include raw AWS API response (default: false)

**Returns:**
- Instance ID, type, state, availability zone, platform
- Public/private IP addresses
- Public/private DNS names
- VPC ID and subnet ID
- Security group IDs
- IAM instance profile ARN
- Tags (Name, Environment, Application, etc.)
- Launch time, architecture, virtualization type

**Example:**
```json
{
  "instance_id": "i-1234567890abcdef0"
}
```

**Response:**
```json
{
  "instance_id": "i-1234567890abcdef0",
  "summary": {
    "instance_id": "i-1234567890abcdef0",
    "instance_type": "t3.medium",
    "state": "running",
    "availability_zone": "us-east-1a",
    "platform": "linux",
    "public_ip": "54.123.45.67",
    "private_ip": "10.0.1.100",
    "public_dns": "ec2-54-123-45-67.compute-1.amazonaws.com",
    "private_dns": "ip-10-0-1-100.ec2.internal",
    "vpc_id": "vpc-12345678",
    "subnet_id": "subnet-87654321",
    "security_group_ids": ["sg-11111111", "sg-22222222"],
    "iam_instance_profile": "arn:aws:iam::123456789012:instance-profile/MyRole",
    "tags": {
      "Name": "web-server-01",
      "Environment": "production",
      "Application": "api"
    },
    "launch_time": "2024-01-15T10:30:00.000Z",
    "architecture": "x86_64",
    "virtualization_type": "hvm"
  }
}
```

### 2. `get_security_groups`
Get detailed security group rules and configurations.

**Purpose**: Understand what ports and services are exposed on instances. Critical for determining what needs protection in FortiAppSec.

**Parameters:**
- `instance_id` (optional): EC2 instance ID to get security groups from
- `security_group_ids` (optional): List of security group IDs
- `region` (optional): AWS region
- `include_raw` (optional): Include raw AWS API response (default: false)

**Note**: Must provide either `instance_id` OR `security_group_ids`.

**Returns:**
- Security group ID, name, description
- VPC ID
- Inbound rules (ingress): protocol, ports, source IPs/security groups
- Outbound rules (egress): protocol, ports, destination IPs/security groups
- Tags

**Example 1 - By instance ID:**
```json
{
  "instance_id": "i-1234567890abcdef0"
}
```

**Example 2 - By security group IDs:**
```json
{
  "security_group_ids": ["sg-11111111", "sg-22222222"]
}
```

**Response:**
```json
{
  "security_group_count": 2,
  "security_groups": [
    {
      "group_id": "sg-11111111",
      "group_name": "web-server-sg",
      "description": "Security group for web servers",
      "vpc_id": "vpc-12345678",
      "inbound_rules": [
        {
          "protocol": "tcp",
          "from_port": 443,
          "to_port": 443,
          "ip_ranges": ["0.0.0.0/0"],
          "ipv6_ranges": [],
          "source_security_groups": [],
          "description": "HTTPS from anywhere"
        },
        {
          "protocol": "tcp",
          "from_port": 80,
          "to_port": 80,
          "ip_ranges": ["0.0.0.0/0"],
          "ipv6_ranges": [],
          "source_security_groups": [],
          "description": "HTTP from anywhere"
        }
      ],
      "outbound_rules": [
        {
          "protocol": "-1",
          "from_port": null,
          "to_port": null,
          "ip_ranges": ["0.0.0.0/0"],
          "ipv6_ranges": [],
          "destination_security_groups": [],
          "description": "Allow all outbound"
        }
      ],
      "tags": {
        "Name": "web-server-security-group",
        "Environment": "production"
      }
    }
  ]
}
```

## Testing

### Step 1: Test AWS CLI Integration
Verify the AWS CLI works before testing the MCP server:

```bash
# Quick CLI test
python test_cli.py
```

### Step 2: Test the MCP Server
Test the actual MCP server and its tools:

```bash
# Install dependencies (if not already installed)
pip install -r requirements.txt

# Test the MCP server (generic test)
python test_mcp_server.py
```

### Step 3: Query Real Instance (Optional)
Quick utility to query a specific instance via the MCP server:

```bash
# Query a real instance by ID
python query_instance.py i-1234567890abcdef0
```

This script:
- Calls the MCP server's `describe_instance` tool
- Automatically fetches security groups
- Shows exactly what Claude Desktop would see
- Useful for quick testing and debugging

### Manual CLI Testing

Test the CLI commands directly with your instance:

```bash
# Get an instance ID (optional - just to have one for testing)
aws ec2 describe-instances --max-results 5 \
  --query 'Reservations[0].Instances[0].InstanceId' --output text

# Describe instance
aws ec2 describe-instances --instance-ids i-1234567890abcdef0 --output json

# Describe security groups
aws ec2 describe-security-groups --group-ids sg-11111111 --output json
```

## Running the MCP Server

### Standalone (for testing)
```bash
python server.py
```

### With Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or
`%APPDATA%/Claude/claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "aws": {
      "command": "python",
      "args": ["/absolute/path/to/fortidemo/mcp-servers/aws/server.py"]
    }
  }
}
```

Restart Claude Desktop and you should see the AWS tools available.

## Example Usage in Claude Desktop

### Scenario 1: Investigate a vulnerable instance from FortiCNAPP

```
You: "I found instance i-1234567890abcdef0 has a critical CVE. Get me its details."

Claude: [calls describe_instance]

Response shows:
- Public IP: 54.123.45.67
- Private IP: 10.0.1.100
- Security groups: sg-11111111, sg-22222222
- Tags: Name=web-server-01, Environment=production

You: "What ports are exposed on this instance?"

Claude: [calls get_security_groups with instance_id]

Response shows:
- Port 443 (HTTPS) open to 0.0.0.0/0
- Port 80 (HTTP) open to 0.0.0.0/0
- All outbound traffic allowed
```

### Scenario 2: Prepare data for FortiAppSec onboarding

```
You: "Get all the information needed to onboard instance i-1234567890abcdef0 to FortiAppSec"

Claude:
1. [calls describe_instance] - Gets IPs, DNS, VPC info, tags
2. [calls get_security_groups] - Gets exposed ports and services
3. Formats response with all relevant data for FortiAppSec API
```

## Integration with FortiDemo Workflow

This MCP server is part of the larger FortiDemo security automation workflow:

**Step 1**: FortiCNAPP MCP → Find instances with critical CVEs → Returns instance IDs
**Step 2**: **AWS MCP** → Get instance metadata and security context
**Step 3**: FortiAppSec MCP → Onboard instance with metadata
**Step 4**: DNS MCP → Update DNS records if needed

## Troubleshooting

### "aws: command not found"
- Install the AWS CLI: https://aws.amazon.com/cli/
- Ensure it's in your PATH

### "Unable to locate credentials"
- Run `aws configure` to set up credentials
- Verify with `aws sts get-caller-identity`

### "An error occurred (UnauthorizedOperation)"
- Ensure your IAM user/role has `ec2:DescribeInstances` and `ec2:DescribeSecurityGroups` permissions
- Check if you're using the correct AWS profile: `aws configure list`

### "InvalidInstanceID.NotFound"
- Verify the instance ID is correct
- Ensure you're querying the correct region (add `--region` parameter)
- The instance may have been terminated

### "JSON parsing error"
- Ensure you're using AWS CLI v2 (recommended)
- Check that `--output json` is working: `aws ec2 describe-instances --max-results 1 --output json`

## Security Notes

- This MCP server uses your existing AWS CLI authentication
- No credentials are stored in the MCP server
- All authentication is handled by the AWS CLI
- The server runs locally and doesn't expose any ports
- Read-only operations (no modifications to AWS resources)

## Output Format

All tools return JSON with consistent structure:

```json
{
  "instance_id": "i-xxxxx",
  "summary": { ... },
  "raw": { ... }  // Only if include_raw=true
}
```

The `summary` field contains simplified, easy-to-consume data.
The `raw` field (if requested) contains the complete AWS API response for debugging.
