#!/usr/bin/env python3
"""
Test script to verify Lacework CLI integration before running MCP server.

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
            timeout=60  # Increased timeout for slower queries
        )

        # Try to parse as JSON if --json flag is present
        if "--json" in cmd:
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
        print("❌ Command timed out after 60 seconds")
        return False
    except FileNotFoundError:
        print("❌ Command not found. Is 'lacework' CLI installed and in PATH?")
        return False


def main():
    """Run all tests."""
    print("FortiCNAPP/Lacework CLI Integration Tests")
    print("==========================================\n")

    tests = [
        {
            "cmd": ["lacework", "version"],
            "description": "Check Lacework CLI version"
        },
        {
            "cmd": ["lacework", "configure", "list"],
            "description": "Check Lacework authentication"
        },
        {
            "cmd": ["lacework", "vulnerability", "host", "list-cves", "--start", "-5m", "--json"],
            "description": "Quick CVE test - last 5 minutes (JSON format)"
        }
    ]

    print("Note: The CVE query uses a 5-minute window to keep the test fast.")
    print("If this still takes too long, you can skip it - the important tests are version and auth.\n")

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
        print("2. Test the MCP server: python server.py")
        print("3. Configure Claude Desktop (see README.md)")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        print("\nCommon issues:")
        print("- Lacework CLI not installed: https://docs.lacework.net/cli/")
        print("- Not authenticated: Run 'lacework configure'")
        print("- No data available: Ensure hosts are reporting to FortiCNAPP")
        return 1


if __name__ == "__main__":
    sys.exit(main())
