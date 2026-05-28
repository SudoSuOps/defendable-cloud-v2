"""CLI errors — surfaced to the user without a Python traceback."""
from __future__ import annotations


class CLIError(Exception):
    """A user-facing CLI failure (bad input, API rejected the call, etc.).

    main.py catches this, prints the message, and exits non-zero. Never use
    raise X without a message — operator deserves to know what's wrong.
    """

    def __init__(self, message: str, *, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


class AuthError(CLIError):
    """No credentials, or credentials rejected by the API. exit_code = 2."""

    def __init__(self, message: str = "not signed in — run `defendable auth login`"):
        super().__init__(message, exit_code=2)
