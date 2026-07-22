"""Public SDK exception types."""

from __future__ import annotations


class MarcoPoloSDKError(RuntimeError):
    """Base exception for SDK-level normalization and orchestration failures."""


class ExecutionError(MarcoPoloSDKError):
    """Raised when remote command execution or result parsing fails."""


class ToolResultError(MarcoPoloSDKError):
    """Raised when a MarcoPolo MCP tool/resource result cannot be normalized."""


class QueryFileAuthoringError(ValueError, MarcoPoloSDKError):
    """Raised when payload serialization choices are ambiguous or invalid."""
