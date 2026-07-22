"""Builders for shell commands executed inside the MarcoPolo workspace."""

from __future__ import annotations

import base64
import json
import shlex

from marcopolo.models import PreparedQueryFile


def build_connection_query_command(
    connection_name: str,
    query_file: str,
    *,
    params: dict[str, object] | None = None,
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


def build_remote_write_command(prepared: PreparedQueryFile) -> str:
    """Build a shell-safe command that writes content in `/workspace`."""

    encoded = base64.b64encode(prepared.content.encode("utf-8")).decode("ascii")
    return "\n".join(
        [
            "python3 - <<'PY'",
            "from pathlib import Path",
            "import base64",
            f"path = Path('/workspace/{prepared.query_file}')",
            f"content = base64.b64decode('{encoded}')",
            "path.parent.mkdir(parents=True, exist_ok=True)",
            "path.write_bytes(content)",
            "print(path.as_posix())",
            "PY",
        ]
    )
