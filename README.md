# MarcoPolo Client

Python client library for executing governed MarcoPolo MCP connection
operations from application code.

The initial public surface is intentionally small:

- one async metadata API: `list_connections()`
- one async top-level API: `execute()`
- one async lower-level helper: `execute_query_file()`
- internal handling for remote query-file authoring under
  `connections/<connection_name>/queries/`

The low-level MCP transport uses the official Python `mcp` SDK.

## Status

This repository implements the approved first cut of the client:

- async connection discovery
- async-only execution
- required `context`
- caller-provided `query_name`
- syntax-agnostic payload handling
- canonical execution through `workspace_shell("connection query ... --json")`

## Install

Install from PyPI:

```bash
python3 -m pip install marcopolo-sdk
```

Install for local development:

```bash
python3 -m pip install -e ".[dev]"
```

## Build Release Artifacts

Build and validate the PyPI release artifacts locally:

```bash
python3 -m pip install -e ".[dev]"
python3 -m build
python3 -m twine check dist/*
```

The built source distribution and wheel are written under `dist/`.

## Publish to PyPI

This repository is set up for GitHub Actions based PyPI trusted publishing.

High-level flow:

1. Configure the one-time trusted publisher on PyPI for this repository.
2. Push a version tag such as `v0.1.1`.
3. Create a GitHub release from that tag.
4. The `publish-pypi.yml` workflow builds the package and uploads it to PyPI.

See [`PYPI_PUBLISHING.md`](PYPI_PUBLISHING.md) for the concrete setup steps.

## Configuration

`MarcoPolo` does not read `.env` files or process environment variables.
Your application owns configuration loading and must pass explicit settings into
the constructor.

## Public API

```python
import os

from marcopolo import MarcoPolo

marcopolo = MarcoPolo(
    api_token=os.environ["MARCOPOLO_API_TOKEN"],
    server_url=os.environ["MARCOPOLO_MCP_SERVER_URL"],
)
```

### `list_connections()`

```python
async def list_connections(
    *,
    context: str,
    timeout: int | None = None,
) -> ConnectionListResult
```

Behavior:

- executes `workspace_shell("connection list --json")`
- parses the returned shell payload and nested JSON `stdout`
- returns normalized connection metadata including capabilities

### `execute()`

```python
async def execute(
    connection_name: str,
    payload: dict | list | str,
    *,
    query_name: str,
    context: str,
    payload_format: Literal["json", "sql", "text"] | None = None,
    params: dict | None = None,
    timeout: int | None = None,
) -> ExecutionResult
```

Behavior:

- writes a durable remote query file under
  `connections/<connection_name>/queries/`
- executes it with `connection query <connection_name> --file <query_file> --json`
- always requests the full result set by passing `--sample-rows -1` internally
- normalizes the result into `ExecutionResult`

### `execute_query_file()`

```python
async def execute_query_file(
    connection_name: str,
    query_file: str,
    *,
    context: str,
    params: dict | None = None,
    timeout: int | None = None,
) -> ExecutionResult
```

Use this when the query file already exists in the MarcoPolo workspace and you
only want execution.

## Payload Rules

The client is syntax-agnostic. It does not read connector `SYNTAX.md` files or
infer connector semantics. The caller is responsible for sending a payload that
is valid for the target connection.

Serialization rules:

- `dict` and `list` payloads are serialized as pretty JSON and written as
  `.json`
- raw `str` payloads require explicit `payload_format`
- supported raw string formats are `json`, `sql`, and `text`
- `query_name` is mandatory and is sanitized into a readable underscore-based
  filename

Examples:

- `query_name="Top 5 Accounts By Revenue"` becomes
  `top_5_accounts_by_revenue.json`
- `query_name="Loki Errors Last 24h"` becomes
  `loki_errors_last_24h.json`

## Usage

The client is async-only by design. A simple application entrypoint can use
`asyncio.run(...)`.

### Jira read

```python
import asyncio
import os

from marcopolo import MarcoPolo


async def main() -> None:
    marcopolo = MarcoPolo(
        api_token=os.environ["MARCOPOLO_API_TOKEN"],
        server_url=os.environ["MARCOPOLO_MCP_SERVER_URL"],
    )
    connections = await marcopolo.list_connections(
        context="List available governed connections before choosing one.",
    )
    print(connections.count)
    print(connections.connections[:2])

    result = await marcopolo.execute(
        "jira-jql-20260710-1527",
        {
            "jql": (
                "assignee = currentUser() "
                "AND statusCategory != Done ORDER BY updated DESC"
            ),
            "fields": [
                "issuekey",
                "summary",
                "status",
                "priority",
                "project",
                "assignee",
                "created",
                "updated",
            ],
        },
        query_name="open_tickets_current_user",
        context="Load current open Jira tickets for the current Jira user.",
    )
    print(result.row_count)
    print(result.rows[:2])


asyncio.run(main())
```

### Google Drive read

Validated live against `google-drive-20260710-1517` and covered by
`tests/test_integration_reads.py::test_execute_google_drive_sheet_read`.
For the current connection scope, the working form is the plain display name
`sales-by-quarter`; a folder-qualified path such as
`some-folder/sales-by-quarter` does not resolve.

```python
result = await marcopolo.execute(
    "google-drive-20260710-1517",
    {
        "file": "sales-by-quarter",
        "sheet": "0",
    },
    query_name="sales_by_quarter_sheet0",
    context="Read the sales-by-quarter spreadsheet from Google Drive.",
)
```

### Loki read

```python
result = await marcopolo.execute(
    "grafana-loki-20260519-2152",
    {
        "operation": "query_range",
        "query": '{job=~".+"} |~ "(?i)error"',
        "start": "now-24h",
        "end": "now",
        "limit": 200,
        "direction": "backward",
    },
    query_name="errors_last_24h",
    context="Read recent error logs from Loki.",
)
```

### Salesforce update

```python
result = await marcopolo.execute(
    "salesforce-demo-3841cee8-20260709-2149",
    {
        "endpoint": "/services/data/v47.0/sobjects/Account/001gK00000DFg5tQAD",
        "method": "PATCH",
        "body": {
            "Description": "Customer since 2024-01-24. Tier: enterprise",
        },
    },
    query_name="update_existing_account_description",
    context="Apply a non-destructive Salesforce account update.",
)
```

### Salesforce insert

```python
result = await marcopolo.execute(
    "salesforce-demo-3841cee8-20260709-2149",
    {
        "endpoint": "/services/data/v47.0/sobjects/Opportunity",
        "method": "POST",
        "body": {
            "Name": "MarcoPolo Client Example Opportunity",
            "StageName": "Prospecting",
            "CloseDate": "2026-07-31",
            "Description": "Created from the MarcoPolo client README example",
        },
    },
    query_name="create_example_opportunity",
    context="Create a Salesforce opportunity through the MarcoPolo client.",
)
```

### Execute an existing remote query file

```python
result = await marcopolo.execute_query_file(
    "google-drive-20260710-1517",
    "connections/google-drive-20260710-1517/queries/sales_by_quarter_sheet0.json",
    context="Execute a pre-authored Google Drive query file.",
)
```

## Result Model

`execute()` and `execute_query_file()` return `ExecutionResult`:

```python
ExecutionResult(
    connection_name: str,
    query_file: str,
    rows: list[dict[str, Any]],
    row_count: int,
    run_id: str | None,
    raw_payload: dict[str, Any],
    raw_command_result: dict[str, Any],
)
```

Notes:

- `rows` is extracted from `data` or `preview`
- `row_count` uses the command payload value when present, otherwise `len(rows)`
- write operations may still return useful rows, such as Salesforce create
  responses with inserted record IDs
- `raw_payload` and `raw_command_result` are preserved for debugging

`list_connections()` returns `ConnectionListResult`:

```python
ConnectionListResult(
    connections: list[ConnectionSummary],
    count: int,
    message: str | None,
    next_actions: list[str],
    raw_payload: dict[str, Any],
    raw_command_result: dict[str, Any],
)
```

Where each `ConnectionSummary` includes:

```python
ConnectionSummary(
    name: str,
    connection_type: str,
    capabilities: list[str],
    display_name: str | None,
    workspace_path: str | None,
)
```

## Observed Result Shapes

The exact row schema is connector-specific. The client does not reshape rows
beyond extracting them from the command response. These are representative
live-observed examples from the validated connectors.

### Jira rows

```python
[
    {
        "key": "IMMERSA-455",
        "summary": "Example issue title",
        "created": "2026-05-11T18:28:05.844+0000",
        "project_key": "IMMERSA",
        "project_name": "Immersa",
        "assignee": "{\"displayName\": \"Example User\", ...}",
        "priority_name": "Medium",
        "updated": "2026-05-11T18:28:07.126+0000",
        "status_name": "To Do",
    },
    ...,
]
```

### Google Drive rows

```python
[
    {
        "customer_id": 1,
        "quarter_end_dt": "03/31/2025",
        "billing_amount_usd": 100,
    },
    ...,
]
```

### Loki rows

```python
[
    {
        "timestamp": "2026-07-10T17:42:31.123456Z",
        "line": "ERROR request failed for job=api",
        "labels": "{\"job\": \"duploservices-prod01/mproxy\", ...}",
    },
    ...,
]
```

### Salesforce insert rows

```python
[
    {
        "id": "006gK00000KlbtRQAR",
        "success": True,
        "errors": "[]",
    },
    ...,
]
```

### Salesforce update and delete rows

For successful update and delete operations, the command payload may report
`row_count = 1` while `rows` is empty because the connector returned no tabular
data:

```python
result.row_count == 1
result.rows == []
```

### Raw command payload

`ExecutionResult.raw_payload` is the parsed JSON body returned by
`connection query --json`. Representative shape:

```python
{
    "success": True,
    "data": "[{\"id\":\"006gK00000KlbtRQAR\",\"success\":true,\"errors\":\"[]\"}]",
    "preview": "[{\"id\":\"006gK00000KlbtRQAR\",\"success\":true,\"errors\":\"[]\"}]",
    "row_count": 1,
    "run_id": "run_123",
    "query_file": (
        "connections/salesforce-demo-3841cee8-20260709-2149/"
        "queries/create_example_opportunity.json"
    ),
}
```

## Development

Run lint:

```bash
ruff check .
```

Run tests:

```bash
pytest -q
```

The test suite is live-only. Before running it, load these variables into your
shell by whatever mechanism your environment uses:

```bash
export MARCOPOLO_API_TOKEN=...
export MARCOPOLO_MCP_SERVER_URL=...
pytest -q -s
```

## Current Limitations

- The client does not inspect connection `SYNTAX.md` files. Payload formation
  is fully caller-owned.
- The first version exposes execution only. Higher-level `query()` helpers and
  connector-specific convenience wrappers are deferred.
- Jira create/update is not documented by the currently validated Jira
  connection surface, so the examples stay read-only.
- The Google Drive spec example using `test1` / `test` is environment-dependent
  and not currently available in the active validated connection scope.
- For the validated Google Drive spreadsheet example, use the authorized file
  display name `sales-by-quarter` or a file ID/URL. Folder-qualified display
  paths such as `some-folder/sales-by-quarter` are not currently resolved by
  the active connection.
