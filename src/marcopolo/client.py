"""Top-level client entry point."""

from __future__ import annotations

from typing import Any

from marcopolo.commands import (
    build_connection_list_command,
    build_connection_query_command,
    build_remote_write_command,
)
from marcopolo.mcp_transport import MarcoPoloMCPTransport
from marcopolo.models import (
    ConnectionListResult,
    ConnectionSetupResult,
    DemoConnectionInstallResult,
    ExecutionResult,
    PayloadFormat,
    ResourceTextResult,
    WorkspaceShellResult,
)
from marcopolo.parsers import (
    parse_connection_setup_result,
    parse_install_demo_connection_result,
    parse_resource_text_result,
    parse_workspace_shell_connection_list_result,
    parse_workspace_shell_query_result,
    parse_workspace_shell_result,
)
from marcopolo.query_files import MarcoPoloQueryFileAuthor


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
        """Author a query file remotely and execute it with `connection query`.

        The caller requested one logical operation, so this method keeps both
        sub-steps on the same MCP session:

        1. write the query file into the remote workspace
        2. execute `connection query ... --file ... --json`

        Reopening a fresh MCP session between those two steps proved fragile in
        live MarcoPolo environments using developer API tokens.
        """

        transport = self.transport()
        author = MarcoPoloQueryFileAuthor(transport)
        prepared = author.prepare(
            connection_name,
            payload,
            query_name=query_name,
            payload_format=payload_format,
        )

        async with transport.session() as session:
            write_arguments: dict[str, Any] = {
                "command": build_remote_write_command(prepared),
                "context": context,
            }
            if timeout is not None:
                write_arguments["timeout"] = timeout
            await session.call_tool("workspace_shell", write_arguments)

            query_arguments: dict[str, Any] = {
                "command": build_connection_query_command(
                    connection_name,
                    prepared.query_file,
                    params=params,
                ),
                "context": context,
            }
            if timeout is not None:
                query_arguments["timeout"] = timeout
            tool_result = await session.call_tool("workspace_shell", query_arguments)

        return parse_workspace_shell_query_result(
            tool_result,
            connection_name=connection_name,
            query_file=prepared.query_file,
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

    async def install_demo_connection(
        self,
        demo_connection: str,
        *,
        intent_text: str | None = None,
    ) -> DemoConnectionInstallResult:
        """Install a hosted MarcoPolo demo connection."""

        normalized_demo_connection = demo_connection.strip()
        if not normalized_demo_connection:
            raise ValueError("demo_connection must not be empty.")

        tool_result = await self.transport().call_tool(
            "install_demo_connection",
            {
                "demo_connection": normalized_demo_connection,
                "intent_text": intent_text
                or (
                    "Install the hosted demo connection requested by the caller: "
                    f"{normalized_demo_connection}"
                ),
            },
        )
        return parse_install_demo_connection_result(tool_result)

    async def start_connection_setup(
        self,
        connection_type: str,
        *,
        context: str,
    ) -> ConnectionSetupResult:
        """Start an embedded MarcoPolo connection setup workflow."""

        tool_result = await self.transport().call_tool(
            "connection_setup",
            {
                "type": connection_type,
                "context": context,
            },
        )
        return parse_connection_setup_result(tool_result)

    async def workspace_shell(
        self,
        command: str,
        *,
        context: str,
        timeout: int | None = None,
    ) -> WorkspaceShellResult:
        """Run an arbitrary workspace shell command and normalize the result."""

        tool_result = await self.transport().workspace_shell(
            command=command,
            context=context,
            timeout=timeout,
        )
        return parse_workspace_shell_result(tool_result)

    async def read_resource_text(self, uri: str) -> ResourceTextResult:
        """Read a text resource exposed by the MarcoPolo MCP server."""

        resource_result = await self.transport().read_resource(uri)
        return parse_resource_text_result(resource_result, uri=uri)
