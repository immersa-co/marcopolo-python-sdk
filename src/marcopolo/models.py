"""Public SDK value objects and result models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

PayloadFormat = Literal["json", "sql", "text"]


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Normalized result from a MarcoPolo `connection query` execution."""

    connection_name: str
    query_file: str
    rows: list[dict[str, Any]]
    row_count: int
    run_id: str | None
    raw_payload: dict[str, Any]
    raw_command_result: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ConnectionSummary:
    """Normalized metadata for one MarcoPolo connection."""

    name: str
    connection_type: str
    capabilities: list[str]
    display_name: str | None
    workspace_path: str | None


@dataclass(frozen=True, slots=True)
class ConnectionListResult:
    """Normalized result from a MarcoPolo `connection list` execution."""

    connections: list[ConnectionSummary]
    count: int
    message: str | None
    next_actions: list[str]
    raw_payload: dict[str, Any]
    raw_command_result: dict[str, Any]


@dataclass(frozen=True, slots=True)
class DemoConnectionInstallResult:
    """Normalized result from MarcoPolo's `install_demo_connection` tool."""

    message: str
    connection_name: str
    display_name: str
    connection_type: str
    demo_connection_id: str | None
    raw_payload: dict[str, Any]
    raw_tool_result: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ConnectionSetupResult:
    """Embedded MCP app payload from MarcoPolo's `connection_setup` tool."""

    resource_uri: str
    tool_result: dict[str, Any]
    tool_output: dict[str, Any]
    widget_meta: dict[str, Any]
    status_url: str | None


@dataclass(frozen=True, slots=True)
class WorkspaceShellResult:
    """Normalized result from MarcoPolo's `workspace_shell` tool."""

    success: bool
    exit_code: int | None
    stdout: str
    stderr: str
    execution_time: float | int | None
    raw_tool_result: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ResourceTextResult:
    """First text payload returned from an MCP `resources/read` call."""

    uri: str
    text: str
    mime_type: str | None
    raw_resource_result: dict[str, Any]


@dataclass(frozen=True, slots=True)
class PreparedQueryFile:
    """Locally prepared query-file metadata before remote write."""

    connection_name: str
    query_file: str
    payload_format: PayloadFormat
    content: str


@dataclass(frozen=True, slots=True)
class AuthoredQueryFile:
    """Remote query-file metadata after workspace persistence."""

    connection_name: str
    query_file: str
    payload_format: PayloadFormat
