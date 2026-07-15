"""Public package surface for the MarcoPolo Python SDK."""

from marcopolo._version import __version__
from marcopolo.client import MarcoPolo
from marcopolo.execution import (
    ConnectionListResult,
    ConnectionSummary,
    ExecutionError,
    ExecutionResult,
)
from marcopolo.mcp_transport import MarcoPoloMCPTransport
from marcopolo.query_files import (
    AuthoredQueryFile,
    MarcoPoloQueryFileAuthor,
    PreparedQueryFile,
)

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
    "__version__",
]
