from __future__ import annotations

import json
import os
from typing import Any

import pytest

from marcopolo import ExecutionResult, MarcoPolo


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise RuntimeError(
            f"Missing required environment variable {name}. "
            "Load your environment before running the live test suite."
        )
    return value.strip()


@pytest.fixture
def live_client() -> MarcoPolo:
    return MarcoPolo(
        api_token=_require_env("MARCOPOLO_API_TOKEN"),
        server_url=_require_env("MARCOPOLO_MCP_SERVER_URL"),
    )


def print_execution_details(
    *,
    test_name: str,
    connection_name: str,
    payload: dict[str, Any] | list[Any] | str | None,
    result: ExecutionResult,
) -> None:
    print(f"\n=== {test_name} request ===", flush=True)
    print(f"connection_name={connection_name}", flush=True)
    if payload is None:
        print("payload=<query file execution>", flush=True)
    elif isinstance(payload, str):
        print(payload, flush=True)
    else:
        print(json.dumps(payload, indent=2, sort_keys=True), flush=True)

    print(f"=== {test_name} response ===", flush=True)
    print(json.dumps(result.raw_payload, indent=2, sort_keys=True, default=str), flush=True)
