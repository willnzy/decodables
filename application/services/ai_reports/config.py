"""
AI Reports Configuration

Centralized configuration for AI report generation service.

@module services.ai_reports.config
@version 1.0
"""

# OpenAI Configuration
OPENAI_MODEL = "gpt-4o"
OPENAI_TEMPERATURE = 0.3
OPENAI_MAX_TOKENS = 2000
OPENAI_TIMEOUT = 30  # seconds

# Report Type Mappings
REPORT_TYPE_ANALYSIS_DEPTH = {
    "quick": "quick",
    "comprehensive": "deep",
    "growth": "standard",
    "engagement": "standard",
    "revenue": "standard"
}

# Insight Detection Thresholds
LOW_CONVERSION_RATE_THRESHOLD = 3.0  # percentage
ANOMALY_THRESHOLD = 0.2  # 20% change threshold

# Data Collection Limits
MAX_USER_EVENTS_BEHAVIOR_ANALYSIS = 50000  # Prevent OOM
MAX_PROJECTS_FOR_RETENTION = 100000  # Limit for unique creator count

# Time Windows
DEFAULT_INSIGHT_DAYS = 7  # Days of data for insights
DEFAULT_BEHAVIOR_ANALYSIS_DAYS = 30  # Default analysis period

# Recommendation Thresholds
GROWTH_WARNING_THRESHOLD = 0.8  # 80% of average
LOW_CREATION_RATE_THRESHOLD = 50.0  # percentage
LOW_MONETIZATION_THRESHOLD = 5.0  # percentage
