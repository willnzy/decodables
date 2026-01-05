"""
Exceptions - Backward Compatibility Layer

This module re-exports all exceptions from the new modular
structure in exceptions/ for backward compatibility.

For new code, prefer importing directly from exceptions package:
    from exceptions import AppException, NotFoundException

@module exceptions
@version 3.24
@deprecated Use exceptions package directly for new code
"""

# Re-export everything from the exceptions package
from exceptions import *
