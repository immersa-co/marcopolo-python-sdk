"""Public package surface for the MarcoPolo Python SDK."""

from marcopolo._version import __version__
from marcopolo.client import MarcoPolo
from marcopolo.errors import ExecutionError, QueryFileAuthoringError, ToolResultError
from marcopolo.mcp_transport import MarcoPoloMCPTransport
from marcopolo.models import (
    AuthoredQueryFile,
    ConnectionListResult,
    ConnectionSetupResult,
    ConnectionSummary,
    DemoConnectionInstallResult,
    ExecutionResult,
    PayloadFormat,
    PreparedQueryFile,
    ResourceTextResult,
    WorkspaceShellResult,
)
from marcopolo.query_files import MarcoPoloQueryFileAuthor

__all__ = [
    "MarcoPolo",
    "ConnectionListResult",
    "ConnectionSummary",
    "ExecutionError",
    "ExecutionResult",
    "MarcoPoloMCPTransport",
    "MarcoPoloQueryFileAuthor",
    "PreparedQueryFile",
    "AuthoredQueryFile",
    "PayloadFormat",
    "ConnectionSetupResult",
    "DemoConnectionInstallResult",
    "ResourceTextResult",
    "ToolResultError",
    "WorkspaceShellResult",
    "QueryFileAuthoringError",
    "__version__",
]
