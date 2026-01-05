"""
调度器工具函数
"""

from datetime import datetime


def log(message: str, level: str = "INFO"):
    """Log with timestamp and level"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")
