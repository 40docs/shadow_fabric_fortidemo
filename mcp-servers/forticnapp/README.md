# FortiCNAPP MCP Server

MCP server that provides tools to query Lacework FortiCNAPP for vulnerability data using the Lacework CLI.

## Prerequisites

1. **Lacework CLI installed and authenticated**
   ```bash
   # Verify CLI is installed
   lacework version

   # Verify authentication
   lacework configure list
   ```

2. **Python 3.10+**

3. **MCP Python SDK**
   ```bash
   pip install -r requirements.txt
   ```

## Available Tools

### 1. `list_cves`
List all CVEs found in hosts in your environment.

**Parameters:**
- `severity_filter` (optional): Filter by severity (Critical, High, Medium, Low)
- `min_cvss_score` (optional): Minimum CVSS score (0.0-10.0)
- `start_time` (optional): Start of time range (default: -24h)
- `end_time` (optional): End of time range (default: now)

**Example:**
```json
{
  "severity_filter": "Critical",
  "min_cvss_score": 9.0
}
```

### 2. `list_hosts_by_cve`
List all hosts that contain a specific CVE ID.

**Parameters:**
- `cve_id` (required): CVE identifier (e.g., CVE-2024-1234)
- `start_time` (optional): Start of time range (default: -24h)
- `end_time` (optional): End of time range (default: now)

**Example:**
```json
{
  "cve_id": "CVE-2024-1234"
}
```

### 3. `get_critical_cves`
Get high-priority CVEs that need immediate attention.

**Parameters:**
- `min_cvss_score` (optional): Minimum CVSS score threshold (default: 9.0)
- `start_time` (optional): Start of time range (default: -24h)

**Example:**
```json
{
  "min_cvss_score": 9.0
}
```

## Testing

### Step 1: Test Lacework CLI Integration
Verify the Lacework CLI works before testing the MCP server:

```bash
# Quick CLI test (fast)
python test_cli.py
```

### Step 2: Test the MCP Server
Test the actual MCP server and its tools:

```bash
# Install dependencies (if not already installed)
pip install -r requirements.txt

# Test the MCP server
python test_mcp_server.py
```

This will:
- ✅ Start the MCP server
- ✅ List available tools
- ✅ Call `get_critical_cves` with test parameters
- ✅ Call `list_cves` with filters
- ✅ Verify JSON responses are correct

### Manual CLI Testing (Optional)
Test the CLI commands directly:

```bash
# List CVEs from last 5 minutes (fast)
lacework vulnerability host list-cves --start -5m --json

# List hosts for a specific CVE
lacework vulnerability host list-hosts CVE-2024-1234 --json

# Note: Full CVE list can take several minutes
lacework vulnerability host list-cves --json
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
    "forticnapp": {
      "command": "python",
      "args": ["/absolute/path/to/fortidemo/mcp-servers/forticnapp/server.py"]
    }
  }
}
```

Restart Claude Desktop and you should see the FortiCNAPP tools available.

## Example Usage in Claude Desktop

```
You: "Show me all critical CVEs with CVSS score above 9.0"

Claude: [calls get_critical_cves with min_cvss_score: 9.0]

You: "Which hosts have CVE-2024-1234?"

Claude: [calls list_hosts_by_cve with cve_id: CVE-2024-1234]

You: "Show me the instance IDs for hosts with that CVE in AWS"

Claude: [parses previous result, filters for AWS provider, returns instance IDs]
```

## Troubleshooting

### "lacework: command not found"
- Install the Lacework CLI: https://docs.lacework.net/cli/
- Ensure it's in your PATH

### "Authentication failed"
- Run `lacework configure` to set up credentials
- Verify with `lacework configure list`

### "No data returned"
- Check time range parameters
- Verify you have hosts reporting to FortiCNAPP
- Run the CLI command directly to debug

### "JSON parsing error"
- Ensure you're using a recent version of the Lacework CLI
- The `--json` flag should be supported

## Security Notes

- This MCP server uses your existing Lacework CLI authentication
- No credentials are stored in the MCP server
- All authentication is handled by the CLI tool
- The server runs locally and doesn't expose any ports

## Output Format

All tools return JSON with consistent structure:

```json
{
  "total_cves": 10,
  "filters_applied": {...},
  "cves": [
    {
      "cve_id": "CVE-2023-12345",
      "severity": "Critical",
      "cvss_score": 9.8,
      "package": "example-package",
      "version": "1.2.3",
      "os": "ubuntu:20.04",
      "host_count": 5,
      "status": "Active"
    }
  ]
}
```

For `list_hosts_by_cve`:

```json
{
  "cve_id": "CVE-2024-1234",
  "affected_hosts_count": 2,
  "hosts": [
    {
      "machine_id": "1234567890123456789",
      "hostname": "web-server-01",
      "external_ip": "203.0.113.10",
      "internal_ip": "10.0.1.100",
      "os": "ubuntu:22.04",
      "provider": "AWS",
      "instance_id": "i-1234567890abcdef0",
      "status": "Active"
    }
  ]
}
```
