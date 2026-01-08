"""
Campaign & Holiday Theme Scheduler (v3.14)

@package application.services.campaigns

模块化重构，拆分为:
- date_utils: 日期计算
- campaigns: 活动管理
- themes: 主题管理
- reporter: 汇总报告
- utils: 工具函数
- scheduler: 调度入口
"""

from .date_utils import calculate_dynamic_date, is_theme_active
from .campaigns import update_campaign_statuses, get_upcoming_campaigns
from .themes import log_current_theme, get_upcoming_themes
from .reporter import generate_summary_report
from .utils import log
from .scheduler import run_full_schedule, run_campaign_only, run_theme_only

__all__ = [
    'calculate_dynamic_date',
    'is_theme_active',
    'update_campaign_statuses',
    'get_upcoming_campaigns',
    'log_current_theme',
    'get_upcoming_themes',
    'generate_summary_report',
    'log',
    'run_full_schedule',
    'run_campaign_only',
    'run_theme_only',
]
