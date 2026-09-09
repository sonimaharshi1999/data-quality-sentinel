# Data Quality Sentinel - Automated Data Validation Framework
# Author: Maharshi Soni | License: MIT
"""
Check registry: maps CheckType enum values to check executor functions.
All built-in checks are registered here.
"""

from __future__ import annotations

from typing import Callable

import pandas as pd

from sentinel.models import CheckResult, CheckType, ExpectationCheck


# Type alias for check executor functions
CheckExecutor = Callable[[pd.DataFrame, ExpectationCheck], CheckResult]


class CheckRegistry:
    """Registry mapping check types to their executor functions."""

    def __init__(self) -> None:
        self._checks: dict[CheckType, CheckExecutor] = {}

    def register(self, check_type: CheckType) -> Callable[[CheckExecutor], CheckExecutor]:
        """Decorator to register a check executor for a given check type.

        Args:
            check_type: The CheckType this executor handles.

        Returns:
            Decorator that registers the function.
        """
        def decorator(func: CheckExecutor) -> CheckExecutor:
            self._checks[check_type] = func
            return func
        return decorator

    def get_executor(self, check_type: CheckType) -> CheckExecutor:
        """Get the executor function for a check type.

        Args:
            check_type: The check type to look up.

        Returns:
            The registered executor function.

        Raises:
            KeyError: If no executor is registered for the check type.
        """
        if check_type not in self._checks:
            raise KeyError(f"No executor registered for check type: {check_type.value}")
        return self._checks[check_type]

    def has_executor(self, check_type: CheckType) -> bool:
        """Check if an executor is registered for a check type.

        Args:
            check_type: The check type to look up.

        Returns:
            True if an executor is registered.
        """
        return check_type in self._checks

    @property
    def registered_types(self) -> list[CheckType]:
        """List all registered check types."""
        return list(self._checks.keys())


# Global registry instance
_registry = CheckRegistry()


def get_registry() -> CheckRegistry:
    """Get the global check registry (lazily loads built-in checks).

    Returns:
        The global CheckRegistry instance with all built-in checks loaded.
    """
    if not _registry.registered_types:
        # Import to trigger registration decorators
        import sentinel.checks.builtin  # noqa: F401
    return _registry
