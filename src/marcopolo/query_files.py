"""Internal remote query-file authoring utilities."""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Literal, Protocol

PayloadFormat = Literal["json", "sql", "text"]
_VALID_PAYLOAD_FORMATS = {"json", "sql", "text"}


class SupportsWorkspaceShell(Protocol):
    """Minimal protocol required for remote query-file authoring."""

    async def workspace_shell(
        self, command: str, context: str, timeout: int | None = None
    ) -> Any:
        """Run a command in the MarcoPolo workspace."""


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


class QueryFileAuthoringError(ValueError):
    """Raised when payload serialization choices are ambiguous or invalid."""


class MarcoPoloQueryFileAuthor:
    """Prepare and persist query files in the remote MarcoPolo workspace."""

    def __init__(self, transport: SupportsWorkspaceShell) -> None:
        self._transport = transport

    def prepare(
        self,
        connection_name: str,
        payload: dict[str, Any] | list[Any] | str,
        *,
        query_name: str,
        payload_format: PayloadFormat | None = None,
    ) -> PreparedQueryFile:
        """Prepare content and a workspace-relative query-file path."""

        slug = _slugify(query_name)
        if isinstance(payload, (dict, list)):
            if payload_format not in (None, "json"):
                raise QueryFileAuthoringError(
                    "Structured payloads support only the 'json' payload_format."
                )
            content = json.dumps(payload, indent=2) + "\n"
            resolved_format: PayloadFormat = "json"
        elif isinstance(payload, str):
            if payload_format is None:
                raise QueryFileAuthoringError(
                    "Raw string payloads require an explicit payload_format of "
                    "'json', 'sql', or 'text'."
                )
            if payload_format not in _VALID_PAYLOAD_FORMATS:
                raise QueryFileAuthoringError(
                    "Unsupported payload_format. Use 'json', 'sql', or 'text'."
                )
            content = payload
            resolved_format = payload_format
        else:
            raise QueryFileAuthoringError(
                "Unsupported payload type. Use dict, list, or str."
            )

        query_file = (
            PurePosixPath("connections")
            / connection_name
            / "queries"
            / f"{slug}.{_extension_for(resolved_format)}"
        ).as_posix()
        return PreparedQueryFile(
            connection_name=connection_name,
            query_file=query_file,
            payload_format=resolved_format,
            content=content,
        )

    async def author(
        self,
        connection_name: str,
        payload: dict[str, Any] | list[Any] | str,
        *,
        context: str,
        query_name: str,
        payload_format: PayloadFormat | None = None,
        timeout: int | None = None,
    ) -> AuthoredQueryFile:
        """Write the prepared query file into the remote MarcoPolo workspace."""

        prepared = self.prepare(
            connection_name,
            payload,
            query_name=query_name,
            payload_format=payload_format,
        )
        await self._transport.workspace_shell(
            command=_build_remote_write_command(prepared),
            context=context,
            timeout=timeout,
        )
        return AuthoredQueryFile(
            connection_name=prepared.connection_name,
            query_file=prepared.query_file,
            payload_format=prepared.payload_format,
        )


def _slugify(value: str) -> str:
    """Create a readable underscore-based slug."""

    slug = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    if not slug:
        raise QueryFileAuthoringError(
            "query_name must contain at least one alphanumeric character."
        )
    return slug


def _extension_for(payload_format: PayloadFormat) -> str:
    """Map payload formats to file extensions."""

    return {
        "json": "json",
        "sql": "sql",
        "text": "txt",
    }[payload_format]


def _build_remote_write_command(prepared: PreparedQueryFile) -> str:
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
