from __future__ import annotations


class SwingleError(ValueError):
    """Base class for deterministic domain errors exposed by the CLI."""

    code = "swingle_error"

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


class LedgerValidationError(SwingleError):
    code = "ledger_invalid_event"


class LedgerEventTooLarge(LedgerValidationError):
    code = "ledger_event_too_large"


class LedgerLifecycleError(LedgerValidationError):
    code = "ledger_invalid_lifecycle"


class WorkspaceError(SwingleError):
    """Raised for a workspace-command domain failure with a stable code.

    The message always starts with the code, followed by the operation and
    the exact path or identity that caused the failure.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}", code)
