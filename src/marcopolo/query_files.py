"""Query-file preparation and authoring helpers."""

from __future__ import annotations

import json
import re
from pathlib import PurePosixPath
from typing import Any, Protocol

from marcopolo.commands import build_remote_write_command
from marcopolo.errors import QueryFileAuthoringError
from marcopolo.models import AuthoredQueryFile, PayloadFormat, PreparedQueryFile

_VALID_PAYLOAD_FORMATS = {"json", "sql", "text"}


class SupportsWorkspaceShell(Protocol):
    """Minimal protocol required for remote query-file authoring."""

    async def workspace_shell(
        self, command: str, context: str, timeout: int | None = None
    ) -> Any:
        """Run a command in the MarcoPolo workspace."""


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
            command=build_remote_write_command(prepared),
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
