# Copyright 2026-present Gabby Contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Optional MCP client and server adapters."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

from .config import _validate_output_schema
from .tools import Tool, ToolRegistry


def _client_type() -> Any:
    try:
        from mcp import Client
    except ImportError as exc:
        raise RuntimeError("MCP support requires gabby-agent-runtime[mcp]") from exc
    return Client


async def load_mcp_tools(
    configuration: Mapping[str, Any], *, client_factory: Callable[[str], Any] | None = None
) -> ToolRegistry:
    """Discover explicitly allowed remote tools and adapt them to Gabby's tool contracts.

    A fresh client session is used for discovery and each invocation. This avoids retaining
    subprocesses or network sessions across runs and works with Gabby's explicit async lifecycle.
    """
    if client_factory is None:
        Client = _client_type()
        client_factory = Client
    registry = ToolRegistry()
    servers = configuration.get("servers", {})
    for server_name, server in servers.items():
        url = server["url"]
        allowed_names = set(server["allow_tools"])
        async with client_factory(url) as client:
            response = await client.list_tools()
        remote_tools = {item.name: item for item in response.tools}
        missing = allowed_names - remote_tools.keys()
        if missing:
            raise ValueError(
                f"MCP server {server_name!r} did not provide allowlisted tool(s): "
                + ", ".join(sorted(missing))
            )
        for remote_name in sorted(allowed_names):
            remote = remote_tools[remote_name]
            name = f"{server_name}_{remote_name}"
            if len(name) > 64:
                raise ValueError(f"MCP tool name {name!r} exceeds Gabby's 64-character limit")
            parameters = remote.inputSchema
            if not isinstance(parameters, dict):
                raise ValueError(f"MCP tool {name!r} did not provide a JSON Schema object")
            if len(json.dumps(parameters, ensure_ascii=False).encode("utf-8")) > 256 * 1024:
                raise ValueError(f"MCP tool {name!r} schema exceeds 256 KiB")
            _validate_output_schema(parameters, field_name=f"MCP tool {name!r} input schema")
            description = remote.description or remote_name
            if not isinstance(description, str) or len(description.encode("utf-8")) > 8192:
                raise ValueError(f"MCP tool {name!r} description exceeds 8 KiB")

            async def invoke(
                _server_url: str = url, _remote_name: str = remote_name, **arguments: Any
            ) -> Any:
                async with client_factory(_server_url) as active_client:
                    result = await active_client.call_tool(_remote_name, arguments)
                if getattr(result, "isError", False):
                    raise RuntimeError("MCP tool server reported a tool error")
                structured = getattr(result, "structuredContent", None)
                if structured is not None:
                    return structured
                blocks = getattr(result, "content", [])
                return {
                    "content": [
                        block.model_dump(mode="json")
                        if callable(getattr(block, "model_dump", None))
                        else {
                            "type": getattr(block, "type", "unknown"),
                            "text": getattr(block, "text", ""),
                        }
                        for block in blocks
                    ]
                }

            registry.register(
                Tool(
                    name=name,
                    description=f"MCP tool from {server_name}: {description}",
                    parameters=parameters,
                    handler=invoke,
                    output_schema={},
                )
            )
    return registry


def create_mcp_server(
    agent: Any,
    *,
    auth: Any = None,
    token_verifier: Any = None,
    trusted_transport: bool = False,
) -> Any:
    """Expose one configured Gabby agent as an MCP ``run_agent`` tool.

    The tool delegates to ``Agent.arun``; agent tool policies, approvals, sandboxing,
    output checks, and persona verification therefore remain in Gabby's runtime.
    """
    if not agent.definition.mcp.get("expose", False):
        raise ValueError(
            "Set mcp.expose: true in the agent definition before creating an MCP server"
        )
    if auth is None and token_verifier is None and not trusted_transport:
        raise ValueError(
            "Provide MCP auth/token_verifier or set trusted_transport=True only when an external "
            "authenticated boundary protects this server"
        )
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("MCP support requires gabby-agent-runtime[mcp]") from exc

    server = FastMCP(
        agent.definition.name,
        auth=auth,
        token_verifier=token_verifier,
    )

    @server.tool()  # type: ignore[untyped-decorator]
    async def run_agent(task: str) -> dict[str, Any]:
        """Run this governed agent once for the supplied task."""
        result = await agent.arun(task)
        return {"output": result.output, "trace_id": result.trace.trace_id}

    return server
