# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**FortiDemo** is a security automation workflow that uses MCP (Model Context Protocol) servers to chain multiple security services together. The architecture allows an LLM (like Claude) to orchestrate complex security workflows by calling individual MCP servers as tools.

**Workflow**: FortiCNAPP CVE discovery → AWS instance metadata → FortiAppSec onboarding → DNS updates

## Architecture

### MCP Server Pattern
Each integration is built as an **independent MCP server** that:
- Exposes tools via the Model Context Protocol
- Wraps CLI tools or APIs (e.g., Lacework CLI, AWS CLI)
- Returns structured JSON responses
- Runs as a subprocess when called by Claude Desktop

**Key principle**: MCP servers are stateless. The LLM (Claude) maintains context and orchestrates the workflow during a conversation session.

### Directory Structure
```
fortidemo/
├── mcp-servers/           # Each subdirectory is an independent MCP server
│   ├── forticnapp/        # ✅ Lacework CLI wrapper for CVE queries
│   ├── aws/               # ✅ AWS CLI wrapper for instance metadata
│   ├── fortiappsec/       # 🚧 FortiAppSec API integration
│   └── dns/               # 📋 DNS registrar integration
├── venv/                  # Python virtual environment (gitignored)
└── CLAUDE.md              # This file
```

## Development Commands

### Environment Setup
```bash
# One-time setup
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# OR: venv\Scripts\activate  # Windows

# Install all dependencies
pip install -r mcp-servers/*/requirements.txt
```

### Testing MCP Servers

Each MCP server has its own test scripts:

```bash
# Example: Testing FortiCNAPP server
cd mcp-servers/forticnapp
python test_cli.py         # Test underlying CLI integration
python test_mcp_server.py  # Test MCP server itself
```

**Test pattern**: All MCP servers follow this structure:
- `test_cli.py` or similar - Tests the underlying CLI/API
- `test_mcp_server.py` - Tests the MCP server by connecting as a client
- `server.py` - The actual MCP server implementation

### Running Individual MCP Servers

MCP servers are designed to be run by Claude Desktop, not manually. But for debugging:

```bash
# This will start the server and wait for stdio communication
python mcp-servers/forticnapp/server.py
```

To actually test, use `test_mcp_server.py` which simulates a client connection.

## Building New MCP Servers

When adding a new MCP server to this project:

### 1. Create Directory Structure
```bash
mkdir -p mcp-servers/<service-name>
cd mcp-servers/<service-name>
```

### 2. Required Files
- `server.py` - MCP server implementation
- `requirements.txt` - Python dependencies (must include `mcp>=0.9.0`)
- `README.md` - Tool documentation, parameters, examples
- `test_*.py` - Test scripts for CLI/API and MCP server

### 3. Server Implementation Pattern

All servers follow this pattern:

```python
from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("service-name")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """Define available tools"""
    return [Tool(name="...", description="...", inputSchema={...})]

@server.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
    """Execute tool calls"""
    # Implementation here
    return [TextContent(type="text", text=json.dumps(result))]

async def main():
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream,
                        server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

### 4. CLI Wrapper Best Practices

When wrapping CLI tools (like Lacework, AWS CLI):

- Use `subprocess.run()` with `capture_output=True, text=True`
- Set reasonable timeouts (30-60 seconds)
- Add `--json` flag to CLI commands for structured output
- Parse JSON responses and re-format for consistency
- Handle errors gracefully with try/except

Example from `forticnapp/server.py`:
```python
def run_lacework_command(args: list[str], json_output: bool = True):
    cmd = ["lacework"] + args
    if json_output:
        cmd.append("--json")

    result = subprocess.run(cmd, capture_output=True, text=True,
                          check=True, timeout=60)
    return json.loads(result.stdout)
```

### 5. Testing Strategy

**Step 1**: Test CLI/API integration independently
```python
# test_cli.py
subprocess.run(["lacework", "version"])  # Verify installed
subprocess.run(["lacework", "configure", "list"])  # Verify auth
# Test actual commands with small time windows for speed
```

**Step 2**: Test MCP server with simulated client
```python
# test_mcp_server.py
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Start server as subprocess, call tools, verify responses
```

## Integration with Claude Desktop

### Configuration File Location
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

### Adding MCP Servers
```json
{
  "mcpServers": {
    "forticnapp": {
      "command": "python",
      "args": ["/absolute/path/to/fortidemo/mcp-servers/forticnapp/server.py"]
    },
    "aws": {
      "command": "python",
      "args": ["/absolute/path/to/fortidemo/mcp-servers/aws/server.py"]
    }
  }
}
```

**Important**:
- Use absolute paths (not relative)
- Restart Claude Desktop after config changes
- Ensure virtual environment's Python interpreter is used if needed

## Workflow Orchestration

The demo workflow is orchestrated by Claude during a conversation:

1. **User**: "Find AWS instances with critical CVEs and onboard to FortiAppSec"
2. **Claude** (uses forticnapp): `get_critical_cves` → returns list of CVE IDs
3. **Claude** (uses forticnapp): `list_hosts_by_cve` for each CVE → gets instance IDs
4. **Claude** (uses aws): `get_instance_metadata` for each instance → gets details
5. **Claude** (uses fortiappsec): `onboard_instance` with metadata
6. **Claude** (uses dns): Updates DNS records if needed
7. **Claude**: Reports results to user

**No external orchestrator needed** - Claude maintains state across tool calls within the conversation.

## Authentication & Credentials

### FortiCNAPP (Lacework)
- Uses existing Lacework CLI authentication
- Configure once: `lacework configure`
- Credentials stored in `~/.lacework.toml`
- No credentials needed in MCP server code

### AWS
- Uses AWS CLI credentials
- Configure once: `aws configure`
- Credentials stored in `~/.aws/credentials`
- No credentials needed in MCP server code

### FortiAppSec
- TBD - will use API keys via environment variables

### DNS
- TBD - depends on DNS provider (Route53, Cloudflare, etc.)

**Security principle**: MCP servers should use existing CLI authentication or environment variables. Never hardcode credentials.

## Common Issues & Solutions

### "externally-managed-environment" pip error
**Solution**: Always use virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### MCP server hangs when run directly
**Expected behavior**: MCP servers communicate via stdio and wait for input. Use test scripts instead.

### Claude Desktop doesn't show MCP tools
**Checklist**:
1. Config file has correct JSON syntax
2. Paths are absolute (not relative)
3. Claude Desktop was restarted after config change
4. Server script is executable and has no syntax errors
5. Dependencies are installed in accessible Python environment

### CLI commands take too long in tests
**Solution**: Use time range filters
```bash
# Slow
lacework vulnerability host list-cves --json

# Fast
lacework vulnerability host list-cves --start -5m --json
```

## Project Status

- ✅ **FortiCNAPP MCP Server**: Complete and tested
- ✅ **AWS MCP Server**: Complete and tested
- 🚧 **FortiAppSec MCP Server**: Next to build
- 📋 **DNS MCP Server**: Planned

## Additional Notes

### Why MCP over traditional APIs?
- **Reusability**: MCP servers work with any MCP client (Claude Desktop, custom apps)
- **LLM-native**: Designed for LLM tool use with structured schemas
- **Standardization**: MCP is a protocol, not a custom integration
- **Composability**: Easy to combine multiple MCP servers in workflows

### Performance Considerations
- MCP servers start as subprocesses (small overhead ~100-200ms)
- CLI tools may have their own latency (Lacework queries: 5s-2min depending on scope)
- Use time range filters to keep queries fast during development
- For production, consider caching strategies or direct API calls instead of CLI

### Future Enhancements
- Add state persistence layer (SQLite) for workflow tracking
- Build orchestrator script for automated/scheduled runs
- Add retry logic and error recovery
- Implement rate limiting for API calls
- Add comprehensive logging and audit trails
