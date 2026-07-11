"""Execution helpers for running remote MarcoPolo query files."""

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


def parse_workspace_shell_query_result(
    tool_result: Any,
    *,
    connection_name: str,
    query_file: str,
) -> ExecutionResult:
    """Normalize a `workspace_shell` result for `connection query --json`."""

    command_result = _structured_mapping(tool_result)
    stdout = (command_result.get("stdout") or "").strip()

    if not command_result.get("success"):
        raise ExecutionError(
            _command_error_message(command_result, stdout)
            or f"Failed to execute query for connection '{connection_name}'."
        )
    if not stdout:
        raise ExecutionError(
            f"Query on connection '{connection_name}' produced no output."
        )

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ExecutionError("Command returned non-JSON stdout.") from exc

    if not isinstance(payload, dict):
        raise ExecutionError("Command returned a non-object JSON payload.")
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
