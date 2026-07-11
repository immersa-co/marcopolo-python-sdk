from __future__ import annotations

from datetime import UTC, datetime

import pytest

from marcopolo import MarcoPolo
from tests.live_support import print_execution_details


@pytest.mark.asyncio
async def test_execute_salesforce_account_update(live_client: MarcoPolo) -> None:
    payload = {
        "endpoint": "/services/data/v47.0/sobjects/Account/001gK00000DFg5tQAD",
        "method": "PATCH",
        "body": {
            "Description": "Customer since 2024-01-24. Tier: enterprise",
        },
    }
    result = await live_client.execute(
        "salesforce-demo-3841cee8-20260709-2149",
        payload,
        query_name="integration_salesforce_update_account_description",
        context=(
            "Running a live Salesforce update integration test "
            "through the MarcoPolo client library."
        ),
        timeout=180,
    )
    print_execution_details(
        test_name="test_execute_salesforce_account_update",
        connection_name="salesforce-demo-3841cee8-20260709-2149",
        payload=payload,
        result=result,
    )

    assert result.connection_name == "salesforce-demo-3841cee8-20260709-2149"
    assert result.query_file.endswith("integration_salesforce_update_account_description.json")
    assert result.row_count >= 0


@pytest.mark.asyncio
async def test_execute_salesforce_opportunity_insert_with_cleanup(
    live_client: MarcoPolo,
) -> None:
    suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    payload = {
        "endpoint": "/services/data/v47.0/sobjects/Opportunity",
        "method": "POST",
        "body": {
            "Name": f"MarcoPolo Integration Test Opportunity {suffix}",
            "StageName": "Prospecting",
            "CloseDate": "2026-07-31",
            "Description": "Created during TASK-127 integration coverage",
        },
    }
    create_result = await live_client.execute(
        "salesforce-demo-3841cee8-20260709-2149",
        payload,
        query_name="integration_salesforce_create_test_opportunity",
        context=(
            "Running a live Salesforce insert integration test "
            "through the MarcoPolo client library."
        ),
        timeout=180,
    )
    print_execution_details(
        test_name="test_execute_salesforce_opportunity_insert_with_cleanup",
        connection_name="salesforce-demo-3841cee8-20260709-2149",
        payload=payload,
        result=create_result,
    )

    assert create_result.rows
    created_id = create_result.rows[0]["id"]
    assert create_result.rows[0]["success"] is True

    try:
        assert create_result.connection_name == "salesforce-demo-3841cee8-20260709-2149"
        assert created_id.startswith("006")
        assert create_result.query_file.endswith(
            "integration_salesforce_create_test_opportunity.json"
        )
    finally:
        cleanup_payload = {
            "endpoint": f"/services/data/v47.0/sobjects/Opportunity/{created_id}",
            "method": "DELETE",
        }
        cleanup_result = await live_client.execute(
            "salesforce-demo-3841cee8-20260709-2149",
            cleanup_payload,
            query_name="integration_salesforce_delete_test_opportunity",
            context=(
                "Cleaning up the Salesforce integration test opportunity "
                "created during live validation."
            ),
            timeout=180,
        )
        print_execution_details(
            test_name="test_execute_salesforce_opportunity_insert_with_cleanup.cleanup",
            connection_name="salesforce-demo-3841cee8-20260709-2149",
            payload=cleanup_payload,
            result=cleanup_result,
        )
