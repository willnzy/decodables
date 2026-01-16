"""
调度器工具函数

@version 1.1.0 (Log Hygiene)

Changes:
- v1.1.0: Replaced print-based log function with proper logging
- v1.0.0: Initial implementation
"""

import logging

logger = logging.getLogger(__name__)


def log(message: str, level: str = "INFO"):
    """Log with appropriate level using standard logging."""
    level_upper = level.upper()
    if level_upper == "ERROR":
        logger.error(message)
    elif level_upper == "WARNING":
        logger.warning(message)
    elif level_upper == "DEBUG":
        logger.debug(message)
    else:
        logger.info(message)
