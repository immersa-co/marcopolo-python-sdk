"""Normalization helpers for MarcoPolo MCP tool and command results."""

from __future__ import annotations

import json
from typing import Any

from marcopolo.errors import ExecutionError, ToolResultError
from marcopolo.models import (
    ConnectionListResult,
    ConnectionSetupResult,
    ConnectionSummary,
    DemoConnectionInstallResult,
    ExecutionResult,
    ResourceTextResult,
    WorkspaceShellResult,
)


def parse_workspace_shell_query_result(
    tool_result: Any,
    *,
    connection_name: str,
    query_file: str,
) -> ExecutionResult:
    """Normalize a `workspace_shell` result for `connection query --json`."""

    command_result = structured_mapping(tool_result, error_type=ExecutionError)
    payload = _parse_command_payload(
        command_result,
        empty_output_message=f"Query on connection '{connection_name}' produced no output.",
        failure_message=f"Failed to execute query for connection '{connection_name}'.",
    )
    if payload.get("success") is False:
        raise ExecutionError(
            payload.get("message")
            or payload.get("error")
            or f"Failed to execute query for connection '{connection_name}'."
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

    command_result = structured_mapping(tool_result, error_type=ExecutionError)
    payload = _parse_command_payload(
        command_result,
        empty_output_message="Connection list command produced no output.",
        failure_message="Failed to list connections.",
    )
    if payload.get("success") is False:
        raise ExecutionError(
            payload.get("message")
            or payload.get("error")
            or "Failed to list connections."
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

    count = (
        payload.get("count")
        if isinstance(payload.get("count"), int)
        else len(connections)
    )
    message = payload.get("message") if isinstance(payload.get("message"), str) else None
    next_actions = [
        action
        for action in payload.get("next_actions") or []
        if isinstance(action, str)
    ]

    return ConnectionListResult(
        connections=connections,
        count=count,
        message=message,
        next_actions=next_actions,
        raw_payload=payload,
        raw_command_result=command_result,
    )


def parse_install_demo_connection_result(tool_result: Any) -> DemoConnectionInstallResult:
    """Normalize `install_demo_connection` output into a typed result."""

    raw_tool_result = mapping(tool_result, error_type=ToolResultError)
    payload = parse_tool_payload(raw_tool_result)
    if not payload:
        raise ToolResultError("MarcoPolo install_demo_connection did not return a usable payload.")

    if payload.get("success") is False:
        raise ToolResultError(_describe_demo_install_failure(payload))

    return DemoConnectionInstallResult(
        message=_required_string(payload, "message"),
        connection_name=_required_string(payload, "connection_name"),
        display_name=_required_string(payload, "display_name"),
        connection_type=_required_string(payload, "type"),
        demo_connection_id=_optional_string(payload, "demo_connection_id"),
        raw_payload=payload,
        raw_tool_result=raw_tool_result,
    )


def parse_connection_setup_result(tool_result: Any) -> ConnectionSetupResult:
    """Normalize `connection_setup` output into a typed result."""

    raw_tool_result = mapping(tool_result, error_type=ToolResultError)
    payload = parse_tool_payload(raw_tool_result)
    if not payload:
        raise ToolResultError("MarcoPolo connection_setup did not return a usable payload.")

    next_actions = [
        action
        for action in payload.get("next_actions", [])
        if isinstance(action, str) and action
    ]
    return ConnectionSetupResult(
        url=_required_string(payload, "url"),
        workflow_type=_optional_string(payload, "workflow_type"),
        message=_optional_string(payload, "message"),
        setup_session_id=_optional_string(payload, "setup_session_id"),
        status=_optional_string(payload, "status"),
        status_url=_optional_string(payload, "status_url"),
        next_actions=next_actions,
        raw_payload=payload,
        raw_tool_result=raw_tool_result,
    )


def parse_workspace_shell_result(tool_result: Any) -> WorkspaceShellResult:
    """Normalize direct `workspace_shell` structured content."""

    raw_tool_result = mapping(tool_result, error_type=ToolResultError)
    payload = structured_mapping(raw_tool_result, error_type=ToolResultError)
    if not payload:
        raise ToolResultError("MarcoPolo workspace_shell did not return structured content.")

    execution_time = payload.get("execution_time")
    if not isinstance(execution_time, (int, float)):
        execution_time = None

    return WorkspaceShellResult(
        success=bool(payload.get("success", False)),
        exit_code=payload.get("exit_code") if isinstance(payload.get("exit_code"), int) else None,
        stdout=payload.get("stdout") if isinstance(payload.get("stdout"), str) else "",
        stderr=payload.get("stderr") if isinstance(payload.get("stderr"), str) else "",
        execution_time=execution_time,
        raw_tool_result=raw_tool_result,
    )


def parse_resource_text_result(resource_result: Any, *, uri: str) -> ResourceTextResult:
    """Normalize the first text content returned from `resources/read`."""

    raw_resource_result = mapping(resource_result, error_type=ToolResultError)
    contents = raw_resource_result.get("contents")
    if not isinstance(contents, list):
        raise ToolResultError(f"Resource read for {uri} did not return contents.")

    for item in contents:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if isinstance(text, str):
            mime_type = item.get("mimeType") if isinstance(item.get("mimeType"), str) else None
            return ResourceTextResult(
                uri=uri,
                text=text,
                mime_type=mime_type,
                raw_resource_result=raw_resource_result,
            )

    raise ToolResultError(f"Resource read for {uri} did not include text content.")


def mapping(value: Any, *, error_type: type[Exception] = ToolResultError) -> dict[str, Any]:
    """Normalize a pydantic/MCP result object into a plain mapping."""

    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="python")
        if isinstance(dumped, dict):
            return dumped
    raise error_type("Tool returned an unsupported result shape.")


def structured_mapping(
    tool_result: Any, *, error_type: type[Exception] = ToolResultError
) -> dict[str, Any]:
    """Return the best structured mapping view of a tool result."""

    raw = mapping(tool_result, error_type=error_type)
    structured = raw.get("structuredContent")
    if isinstance(structured, dict):
        return structured
    structured = raw.get("structured_content")
    if isinstance(structured, dict):
        return structured
    return raw if raw else {}


def parse_tool_payload(tool_result: dict[str, Any]) -> dict[str, Any]:
    """Extract the most useful payload object from a generic MCP tool result."""

    structured = tool_result.get("structuredContent") or tool_result.get("structured_content")
    if isinstance(structured, dict):
        return structured

    result_payload = tool_result.get("result")
    if isinstance(result_payload, dict):
        return result_payload

    for block in tool_result.get("content", []):
        if not isinstance(block, dict):
            continue
        block_structured = block.get("structuredContent")
        if isinstance(block_structured, dict):
            return block_structured
        block_json = block.get("json")
        if isinstance(block_json, dict):
            return block_json
        text = block.get("text")
        if isinstance(text, str):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed

    return {}


def _extract_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    if isinstance(value, str) and value:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [row for row in parsed if isinstance(row, dict)]
    return []


def _parse_command_payload(
    command_result: dict[str, Any],
    *,
    empty_output_message: str,
    failure_message: str,
) -> dict[str, Any]:
    stdout = (command_result.get("stdout") or "").strip()

    if not command_result.get("success"):
        raise ExecutionError(_command_error_message(command_result, stdout) or failure_message)
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


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if isinstance(value, str) and value:
        return value
    raise ToolResultError(f"MarcoPolo response was missing required field '{key}'.")


def _optional_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) and value else None


def _describe_demo_install_failure(payload: dict[str, Any]) -> str:
    message = payload.get("message")
    error = payload.get("error")
    available = payload.get("available_demo_connections")

    detail = message if isinstance(message, str) and message else None
    if not detail and isinstance(error, str) and error:
        detail = error
    if not detail:
        detail = "MarcoPolo could not install the requested demo connection."

    if isinstance(available, list) and available:
        option_ids = [
            item.get("id")
            for item in available
            if isinstance(item, dict) and isinstance(item.get("id"), str) and item.get("id")
        ]
        if option_ids:
            detail = f"{detail} Available demo connections: {', '.join(option_ids)}."

    return detail
