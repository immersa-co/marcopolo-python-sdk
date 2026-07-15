"""Top-level client entry point."""

from __future__ import annotations

from typing import Any

from marcopolo.execution import (
    ConnectionListResult,
    ExecutionResult,
    build_connection_list_command,
    build_connection_query_command,
    parse_workspace_shell_connection_list_result,
    parse_workspace_shell_query_result,
)
from marcopolo.mcp_transport import MarcoPoloMCPTransport
from marcopolo.query_files import MarcoPoloQueryFileAuthor, PayloadFormat


class MarcoPolo:
    """MarcoPolo client entry point.

    Callers must pass explicit connection settings. Environment management stays
    outside the library.
    """

    def __init__(
        self,
        api_token: str,
        server_url: str,
    ) -> None:
        """Create a client from explicit settings."""

        self.api_token = api_token
        self.server_url = server_url

    def transport(self) -> MarcoPoloMCPTransport:
        """Create a low-level MCP transport configured for this client."""

        return MarcoPoloMCPTransport(
            api_token=self.api_token,
            server_url=self.server_url,
        )

    def query_file_author(self) -> MarcoPoloQueryFileAuthor:
        """Create the internal remote query-file authoring helper."""

        return MarcoPoloQueryFileAuthor(self.transport())

    async def execute(
        self,
        connection_name: str,
        payload: dict[str, Any] | list[Any] | str,
        *,
        query_name: str,
        context: str,
        payload_format: PayloadFormat | None = None,
        params: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> ExecutionResult:
        """Author a query file remotely and execute it with `connection query`."""

        transport = self.transport()
        authored = await MarcoPoloQueryFileAuthor(transport).author(
            connection_name,
            payload,
            context=context,
            query_name=query_name,
            payload_format=payload_format,
            timeout=timeout,
        )
        return await self.execute_query_file(
            connection_name,
            authored.query_file,
            context=context,
            params=params,
            timeout=timeout,
        )

    async def execute_query_file(
        self,
        connection_name: str,
        query_file: str,
        *,
        context: str,
        params: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> ExecutionResult:
        """Execute an existing remote query file through `connection query`."""

        transport = self.transport()
        command = build_connection_query_command(
            connection_name,
            query_file,
            params=params,
        )
        tool_result = await transport.workspace_shell(
            command=command,
            context=context,
            timeout=timeout,
        )
        return parse_workspace_shell_query_result(
            tool_result,
            connection_name=connection_name,
            query_file=query_file,
        )

    async def list_connections(
        self,
        *,
        context: str,
        timeout: int | None = None,
    ) -> ConnectionListResult:
        """List available MarcoPolo connections through `connection list`."""

        transport = self.transport()
        tool_result = await transport.workspace_shell(
            command=build_connection_list_command(),
            context=context,
            timeout=timeout,
        )
        return parse_workspace_shell_connection_list_result(tool_result)
