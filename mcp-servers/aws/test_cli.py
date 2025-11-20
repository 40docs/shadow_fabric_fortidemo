#!/usr/bin/env python3
"""
Test script to verify AWS CLI integration before running MCP server.

This script tests the underlying CLI commands to ensure they work properly.
"""

import json
import subprocess
import sys


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and report results."""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )

        # Try to parse as JSON if output looks like JSON
        if result.stdout.strip().startswith('{') or result.stdout.strip().startswith('['):
            try:
                data = json.loads(result.stdout)
                print("✅ Success! JSON output:")
                print(json.dumps(data, indent=2)[:500])  # First 500 chars
                if len(json.dumps(data)) > 500:
                    print("... (output truncated)")
                return True
            except json.JSONDecodeError:
                print("⚠️  Command succeeded but output is not valid JSON")
                print(result.stdout[:500])
                return False
        else:
            print("✅ Success!")
            print(result.stdout[:500])
            return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed with exit code {e.returncode}")
        print(f"Error: {e.stderr or e.stdout}")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Command timed out after 30 seconds")
        return False
    except FileNotFoundError:
        print("❌ Command not found. Is 'aws' CLI installed and in PATH?")
        return False


def main():
    """Run all tests."""
    print("AWS CLI Integration Tests")
    print("==========================================\n")

    tests = [
        {
            "cmd": ["aws", "--version"],
            "description": "Check AWS CLI version"
        },
        {
            "cmd": ["aws", "sts", "get-caller-identity"],
            "description": "Check AWS authentication"
        },
        {
            "cmd": ["aws", "ec2", "describe-instances", "--max-results", "5", "--output", "json"],
            "description": "Quick EC2 test - list up to 5 instances (verifies permissions)"
        }
    ]

    print("Note: These tests verify AWS CLI is installed and authenticated.")
    print("They don't test specific instances to keep tests generic.\n")

    results = []
    for test in tests:
        success = run_command(test["cmd"], test["description"])
        results.append((test["description"], success))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    all_passed = True
    for description, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {description}")
        if not success:
            all_passed = False

    print("\n" + "="*60)

    if all_passed:
        print("✅ All tests passed! The MCP server should work correctly.")
        print("\nNext steps:")
        print("1. Install MCP dependencies: pip install -r requirements.txt")
        print("2. Test the MCP server: python test_mcp_server.py")
        print("3. Configure Claude Desktop (see README.md)")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        print("\nCommon issues:")
        print("- AWS CLI not installed: https://aws.amazon.com/cli/")
        print("- Not authenticated: Run 'aws configure'")
        print("- Insufficient permissions: Ensure EC2 read permissions")
        return 1


if __name__ == "__main__":
    sys.exit(main())
