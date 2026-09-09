# Data Quality Sentinel - Automated Data Validation Framework
# Author: Maharshi Soni | License: MIT
"""
Built-in validation checks package.
"""

from sentinel.checks.registry import CheckRegistry, get_registry

__all__ = ["CheckRegistry", "get_registry"]
