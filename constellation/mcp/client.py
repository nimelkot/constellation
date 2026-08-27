"""Small MCP registry with pluggable stdio and HTTP JSON-RPC transports."""

from __future__ import annotations

import json
import subprocess
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class MCPServer:
    name: str
    transport: str
    target: str


class MCPClientManager:
    def __init__(self) -> None:
        self.servers: dict[str, MCPServer] = {}
        self.tools: dict[str, dict[str, Any]] = {}

    def bind(self, name: str, transport: str, target: str) -> MCPServer:
        if transport not in {"stdio", "http"}:
            raise ValueError("MCP transport must be 'stdio' or 'http'")
        server = MCPServer(name, transport, target)
        self.servers[name] = server
        return server

    def status(self) -> list[MCPServer]:
        return list(self.servers.values())

    def list_mcp_tools(self, server_name: str) -> list[dict[str, Any]]:
        result = self._request(server_name, "tools/list", {})
        tools = result.get("tools", [])
        for tool in tools:
            self.tools[f"{server_name}:{tool['name']}"] = tool
        return tools

    def execute_mcp_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> Any:
        if f"{server_name}:{tool_name}" not in self.tools:
            self.list_mcp_tools(server_name)
        if f"{server_name}:{tool_name}" not in self.tools:
            raise KeyError(f"MCP tool is not registered: {tool_name}")
        return self._request(server_name, "tools/call", {"name": tool_name, "arguments": arguments})

    def _request(self, server_name: str, method: str, params: dict[str, Any]) -> dict[str, Any]:
        server = self.servers.get(server_name)
        if server is None:
            raise KeyError(f"MCP server is not bound: {server_name}")
        payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        if server.transport == "http":
            request = urllib.request.Request(server.target, payload, {"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - configured by the user
                data = json.loads(response.read())
        else:
            process = subprocess.run([server.target], input=payload + b"\n", capture_output=True, timeout=30, check=True)
            data = json.loads(process.stdout.splitlines()[-1])
        if "error" in data:
            raise RuntimeError(data["error"].get("message", "MCP request failed"))
        return data.get("result", {})
