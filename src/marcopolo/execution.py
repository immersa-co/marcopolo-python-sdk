"""Execution helpers for running remote MarcoPolo connection commands."""

from __future__ import annotations

import json
import shlex
from dataclasses import dataclass
from typing import Any


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


class ExecutionError(RuntimeError):
    """Raised when remote command execution or result parsing fails."""


def build_connection_query_command(
    connection_name: str,
    query_file: str,
    *,
    params: dict[str, Any] | None = None,
) -> str:
    """Build a `connection query` CLI invocation."""

    command_parts = [
        "connection",
        "query",
        shlex.quote(connection_name),
        "--file",
        shlex.quote(query_file),
        "--json",
        "--sample-rows",
        "-1",
    ]
    if params is not None:
        command_parts.extend(["--params-json", shlex.quote(json.dumps(params))])
    return " ".join(command_parts)


def build_connection_list_command() -> str:
    """Build a `connection list` CLI invocation."""

    return "connection list --json"


def parse_workspace_shell_query_result(
    tool_result: Any,
    *,
    connection_name: str,
    query_file: str,
) -> ExecutionResult:
    """Normalize a `workspace_shell` result for `connection query --json`."""

    command_result = _structured_mapping(tool_result)
    payload = _parse_command_payload(
        command_result,
        empty_output_message=f"Query on connection '{connection_name}' produced no output.",
        failure_message=f"Failed to execute query for connection '{connection_name}'.",
    )
    if payload.get("success") is False:
        raise ExecutionError(
            (
                payload.get("message")
                or payload.get("error")
                or f"Failed to execute query for connection '{connection_name}'."
            )
        )

    rows = _extract_rows(payload.get("data") or payload.get("preview"))
    row_count = (
        payload.get("row_count")
        if isinstance(payload.get("row_count"), int)
        else len(rows)
    )
    resolved_query_file = (
        payload.get("query_file")
        if isinstance(payload.get("query_file"), str)
        else query_file
    )

    return ExecutionResult(
        connection_name=connection_name,
        query_file=resolved_query_file,
        rows=rows,
        row_count=row_count,
        run_id=payload.get("run_id") if isinstance(payload.get("run_id"), str) else None,
        raw_payload=payload,
        raw_command_result=command_result,
    )


def parse_workspace_shell_connection_list_result(tool_result: Any) -> ConnectionListResult:
    """Normalize a `workspace_shell` result for `connection list --json`."""

    command_result = _structured_mapping(tool_result)
    payload = _parse_command_payload(
        command_result,
        empty_output_message="Connection list command produced no output.",
        failure_message="Failed to list connections.",
    )
    if payload.get("success") is False:
        raise ExecutionError(
            (
                payload.get("message")
                or payload.get("error")
                or "Failed to list connections."
            )
        )

    connections: list[ConnectionSummary] = []
    for item in payload.get("connections") or []:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        connection_type = item.get("type")
        if not isinstance(name, str) or not isinstance(connection_type, str):
            continue
        capabilities = [
            capability
            for capability in item.get("capabilities") or []
            if isinstance(capability, str)
        ]
        display_name = (
            item.get("display_name")
            if isinstance(item.get("display_name"), str)
            else None
        )
        workspace_path = (
            item.get("workspace_path")
            if isinstance(item.get("workspace_path"), str)
            else None
        )
        connections.append(
            ConnectionSummary(
                name=name,
                connection_type=connection_type,
                capabilities=capabilities,
                display_name=display_name,
                workspace_path=workspace_path,
            )
        )

    count = payload.get("count") if isinstance(payload.get("count"), int) else len(connections)
    message = payload.get("message") if isinstance(payload.get("message"), str) else None
    next_actions = [
        action for action in payload.get("next_actions") or [] if isinstance(action, str)
    ]

    return ConnectionListResult(
        connections=connections,
        count=count,
        message=message,
        next_actions=next_actions,
        raw_payload=payload,
        raw_command_result=command_result,
    )


def _extract_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    if isinstance(value, str) and value:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [row for row in parsed if isinstance(row, dict)]
    return []


def _structured_mapping(tool_result: Any) -> dict[str, Any]:
    if isinstance(tool_result, dict):
        structured = tool_result.get("structuredContent")
        if isinstance(structured, dict):
            return structured
        return tool_result

    structured = getattr(tool_result, "structuredContent", None)
    if isinstance(structured, dict):
        return structured

    if hasattr(tool_result, "model_dump"):
        dumped = tool_result.model_dump(mode="python")
        if isinstance(dumped, dict):
            structured = dumped.get("structuredContent")
            if isinstance(structured, dict):
                return structured
            return dumped

    raise ExecutionError("Tool returned an unsupported result shape.")


def _parse_command_payload(
    command_result: dict[str, Any],
    *,
    empty_output_message: str,
    failure_message: str,
) -> dict[str, Any]:
    stdout = (command_result.get("stdout") or "").strip()

    if not command_result.get("success"):
        raise ExecutionError(
            _command_error_message(command_result, stdout) or failure_message
        )
    if not stdout:
        raise ExecutionError(empty_output_message)

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ExecutionError("Command returned non-JSON stdout.") from exc

    if not isinstance(payload, dict):
        raise ExecutionError("Command returned a non-object JSON payload.")

    return payload


def _command_error_message(command_result: dict[str, Any], stdout: str) -> str | None:
    if stdout:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            if len(stdout) < 500:
                return stdout
        else:
            if isinstance(payload, dict):
                message = payload.get("message") or payload.get("error")
                if isinstance(message, str) and message:
                    return message
    for key in ("message", "error", "stderr"):
        value = command_result.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
