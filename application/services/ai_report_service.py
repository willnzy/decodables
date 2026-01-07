"""
AI Report Service - Backward Compatibility Layer

This module re-exports all AI report operations from the new modular
structure in services/ai_reports/ for backward compatibility.

For new code, prefer importing directly from application.services.ai_reports:
    from application.services.ai_reports import generate_ai_business_report

@module services.ai_report_service
@version 3.24
@deprecated Use services.ai_reports directly for new code
"""

# Re-export everything from the ai_reports package
from .ai_reports import *
