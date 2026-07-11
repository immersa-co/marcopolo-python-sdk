"""Low-level MCP transport for MarcoPolo."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client
from mcp.types import CallToolResult, ListToolsResult


class BearerTokenAuth(httpx.Auth):
    """Attach a bearer token to outgoing HTTP requests."""

    def __init__(self, token: str) -> None:
        self._token = token

    def auth_flow(
        self, request: httpx.Request
    ) -> Any:
        request.headers["Authorization"] = f"Bearer {self._token}"
        yield request


@dataclass(slots=True)
class MarcoPoloMCPTransport:
    """Thin wrapper around the official Python MCP SDK."""

    api_token: str
    server_url: str
    timeout_seconds: float = 30.0
    sse_read_timeout_seconds: float = 300.0
    extra_headers: Mapping[str, str] = field(default_factory=dict)
    session_factory: Callable[..., ClientSession] = ClientSession
    http_client_factory: Callable[..., httpx.AsyncClient] = create_mcp_http_client
    streamable_http_factory: Callable[..., Any] = streamable_http_client

    @asynccontextmanager
    async def session(self) -> AsyncIterator[ClientSession]:
        """Open an initialized MCP client session."""

        headers = dict(self.extra_headers) or None
        auth = BearerTokenAuth(self.api_token)
        timeout = httpx.Timeout(
            self.timeout_seconds,
            read=self.sse_read_timeout_seconds,
        )
        async with self.http_client_factory(
            headers=headers,
            timeout=timeout,
            auth=auth,
        ) as http_client:
            async with self.streamable_http_factory(
                self.server_url,
                http_client=http_client,
            ) as (read_stream, write_stream, _get_session_id):
                async with self.session_factory(read_stream, write_stream) as session:
                    await session.initialize()
                    yield session

    async def list_tools(self) -> ListToolsResult:
        """List tools exposed by the configured MarcoPolo MCP server."""

        async with self.session() as session:
            return await session.list_tools()

    async def call_tool(
        self, name: str, arguments: dict[str, Any] | None = None
    ) -> CallToolResult:
        """Call a named MCP tool with optional arguments."""

        async with self.session() as session:
            return await session.call_tool(name, arguments)

    async def workspace_shell(
        self, command: str, context: str, timeout: int | None = None
    ) -> CallToolResult:
        """Call MarcoPolo's `workspace_shell` tool."""

        arguments: dict[str, Any] = {"command": command, "context": context}
        if timeout is not None:
            arguments["timeout"] = timeout
        return await self.call_tool("workspace_shell", arguments)

    async def data_query(
        self,
        connection_name: str,
        query_file: str,
        context: str,
        max_rows: int | None = None,
        params: dict[str, Any] | None = None,
    ) -> CallToolResult:
        """Call MarcoPolo's `data_query` tool."""

        arguments: dict[str, Any] = {
            "connection_name": connection_name,
            "query_file": query_file,
            "context": context,
        }
        if max_rows is not None:
            arguments["max_rows"] = max_rows
        if params is not None:
            arguments["params"] = params
        return await self.call_tool("data_query", arguments)
