import pytest

from marcopolo import MarcoPolo
from tests.live_support import (
    build_query_file_path,
    print_connection_list_details,
    print_execution_details,
    resolve_first_connection_name_by_type,
)

pytestmark = pytest.mark.live

@pytest.mark.asyncio
async def test_list_connections(live_client: MarcoPolo) -> None:
    result = await live_client.list_connections(
        context=(
            "Running a live connection list integration test "
            "through the MarcoPolo client library."
        ),
        timeout=180,
    )
    print_connection_list_details(
        test_name="test_list_connections",
        result=result,
    )

    assert result.count >= 1
    assert result.connections
    assert len(result.connections) == result.count
    assert any(connection.name == "local_files" for connection in result.connections)
    assert any("query" in connection.capabilities for connection in result.connections)


@pytest.mark.asyncio
async def test_execute_jira_open_tickets_read(live_client: MarcoPolo) -> None:
    connection_name = await resolve_first_connection_name_by_type(
        live_client,
        "jira",
    )
    payload = {
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
    }
    result = await live_client.execute(
        connection_name,
        payload,
        query_name="integration_jira_open_tickets_current_user",
        context="Running a live Jira read integration test through the MarcoPolo client library.",
        timeout=180,
    )
    print_execution_details(
        test_name="test_execute_jira_open_tickets_read",
        connection_name=connection_name,
        payload=payload,
        result=result,
    )

    assert result.connection_name == connection_name
    assert result.query_file.endswith("integration_jira_open_tickets_current_user.json")
    if result.rows:
        assert "key" in result.rows[0]
        assert "summary" in result.rows[0]


@pytest.mark.asyncio
async def test_execute_salesforce_top_accounts_read(live_client: MarcoPolo) -> None:
    connection_name = await resolve_first_connection_name_by_type(
        live_client,
        "salesforce",
    )

    payload = {
        "soql": (
            "SELECT Id, Name, AnnualRevenue, Industry "
            "FROM Account WHERE AnnualRevenue != NULL "
            "ORDER BY AnnualRevenue DESC LIMIT 5"
        ),
    }
    result = await live_client.execute(
        connection_name,
        payload,
        query_name="integration_salesforce_top_5_accounts_by_revenue",
        context=(
            "Running a live Salesforce read integration test "
            "through the MarcoPolo client library."
        ),
        timeout=180,
    )
    print_execution_details(
        test_name="test_execute_salesforce_top_accounts_read",
        connection_name=connection_name,
        payload=payload,
        result=result,
    )

    assert result.connection_name == connection_name
    assert result.query_file.endswith("integration_salesforce_top_5_accounts_by_revenue.json")
    assert result.row_count >= 1
    assert result.rows
    assert {"Id", "Name", "AnnualRevenue", "Industry"} <= set(result.rows[0])

@pytest.mark.asyncio
async def test_execute_google_drive_sheet_read(live_client: MarcoPolo) -> None:
    connection_name = await resolve_first_connection_name_by_type(
        live_client,
        "google_drive",
    )
    payload = {
        "file": "sales-by-quarter",
        "sheet": "0",
    }
    result = await live_client.execute(
        connection_name,
        payload,
        query_name="integration_google_drive_sales_by_quarter",
        context=(
            "Running a live Google Drive sheet read integration test "
            "through the MarcoPolo client library."
        ),
        timeout=180,
    )
    print_execution_details(
        test_name="test_execute_google_drive_sheet_read",
        connection_name=connection_name,
        payload=payload,
        result=result,
    )

    assert result.connection_name == connection_name
    assert result.query_file.endswith("integration_google_drive_sales_by_quarter.json")
    assert result.row_count >= 1
    assert result.rows
    assert {"customer_id", "quarter_end_dt", "billing_amount_usd"} <= set(result.rows[0])

@pytest.mark.asyncio
async def test_execute_loki_error_read(live_client: MarcoPolo) -> None:
    connection_name = await resolve_first_connection_name_by_type(
        live_client,
        "grafana_loki",
    )
    payload = {
        "operation": "query_range",
        "query": '{job=~".+"} |~ "(?i)error"',
        "start": "now-24h",
        "end": "now",
        "limit": 200,
        "direction": "backward",
    }
    result = await live_client.execute(
        connection_name,
        payload,
        query_name="integration_loki_errors_last_24h",
        context="Running a live Loki read integration test through the MarcoPolo client library.",
        timeout=180,
    )
    print_execution_details(
        test_name="test_execute_loki_error_read",
        connection_name=connection_name,
        payload=payload,
        result=result,
    )

    assert result.connection_name == connection_name
    assert result.query_file.endswith("integration_loki_errors_last_24h.json")
    if result.rows:
        assert "timestamp" in result.rows[0]
        assert "line" in result.rows[0]


@pytest.mark.asyncio
async def test_execute_existing_query_file(live_client: MarcoPolo) -> None:
    connection_name = await resolve_first_connection_name_by_type(
        live_client,
        "google_drive",
    )
    query_file = build_query_file_path(
        connection_name,
        "clientlib/sales_by_quarter_sheet0.json",
    )
    result = await live_client.execute_query_file(
        connection_name,
        query_file,
        context=(
            "Running a live execute_query_file integration test "
            "through the MarcoPolo client library."
        ),
        timeout=180,
    )
    print_execution_details(
        test_name="test_execute_existing_query_file",
        connection_name=connection_name,
        payload=None,
        result=result,
    )

    assert result.connection_name == connection_name
    assert result.query_file.endswith("clientlib/sales_by_quarter_sheet0.json")
    assert result.row_count >= 1
    assert result.rows
