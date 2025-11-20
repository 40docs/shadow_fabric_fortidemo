# FortiDemo - Security Automation Workflow

Multi-service security automation demo that uses LLM orchestration to:
1. Query FortiCNAPP for hosts with critical CVEs
2. Get AWS instance metadata
3. Onboard vulnerable instances to FortiAppSec
4. Update DNS records as needed

## Architecture

This project uses **MCP (Model Context Protocol) servers** that Claude Desktop can use as tools:

```
Claude Desktop (Orchestrator)
├── FortiCNAPP MCP Server (vulnerability queries)
├── AWS MCP Server (instance metadata)
├── FortiAppSec MCP Server (onboarding)
└── DNS MCP Server (DNS management)
```

Each MCP server is independent and can be:
- Built and tested separately
- Used in other workflows
- Run standalone for debugging

## Project Structure

```
fortidemo/
├── mcp-servers/
│   ├── forticnapp/        ✅ Complete
│   │   ├── server.py
│   │   ├── requirements.txt
│   │   ├── test_cli.py
│   │   └── README.md
│   │
│   ├── aws/               🚧 Next
│   ├── fortiappsec/       📋 Planned
│   └── dns/               📋 Planned
│
└── README.md
```

## Current Status

### ✅ FortiCNAPP MCP Server (Complete)
- [x] Query for CVEs in environment
- [x] List hosts affected by specific CVE
- [x] Filter by severity/CVSS score
- [x] Time range support
- [ ] **Testing needed**

### 🚧 Next Steps
1. Test FortiCNAPP MCP server
2. Build AWS MCP server
3. Build FortiAppSec MCP server
4. Build DNS MCP server

## Quick Start

### 1. Setup Python Environment

```bash
# Create virtual environment (one time)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Linux/macOS
# OR
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r mcp-servers/forticnapp/requirements.txt
```

### 2. Test FortiCNAPP Server

```bash
cd mcp-servers/forticnapp

# Test CLI integration (fast)
python test_cli.py

# Test the MCP server
python test_mcp_server.py
```

### 3. Configure Claude Desktop

Add to your Claude Desktop config file:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%/Claude/claude_desktop_config.json`

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

### 4. Use in Claude Desktop

Restart Claude Desktop and try:

```
"Show me all critical CVEs with CVSS score above 9.0"

"Which AWS hosts are affected by CVE-2024-1234?"

"Get the instance IDs for all hosts with critical vulnerabilities"
```

## Prerequisites

- Python 3.10+
- Lacework CLI (authenticated)
- AWS CLI (for AWS MCP server)
- Claude Desktop

## Development Workflow

For each MCP server:
1. **Build** - Implement the server
2. **Test** - Verify CLI/API integration works
3. **Document** - Update README with usage examples
4. **Integrate** - Add to Claude Desktop config
5. **Validate** - Test full workflow in Claude Desktop

## Documentation

Each MCP server has its own README with:
- Available tools and parameters
- Testing instructions
- Usage examples
- Troubleshooting guide

See individual `mcp-servers/*/README.md` files.
