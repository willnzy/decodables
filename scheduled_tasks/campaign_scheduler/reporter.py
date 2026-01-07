"""
汇总报告生成

生成活动和主题的状态汇总。
"""

from datetime import datetime, timezone, date
from typing import Dict, Any

from infrastructure.db_compat import supabase
from .date_utils import is_theme_active
from .themes import get_upcoming_themes
from .utils import log


def generate_summary_report() -> Dict[str, Any]:
    """Generate a summary report of campaigns and themes."""
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "campaigns": {
            "scheduled": 0,
            "active": 0,
            "paused": 0,
            "ended": 0,
            "total": 0
        },
        "themes": {
            "total": 0,
            "current": None,
            "upcoming": []
        }
    }
    
    # Count campaigns by status
    try:
        for status in ['scheduled', 'active', 'paused', 'ended']:
            result = supabase.table('campaigns').select('id', count='exact').eq(
                'status', status
            ).execute()
            report["campaigns"][status] = result.count or 0
        
        report["campaigns"]["total"] = sum([
            report["campaigns"]["scheduled"],
            report["campaigns"]["active"],
            report["campaigns"]["paused"],
            report["campaigns"]["ended"]
        ])
    except Exception as e:
        log(f"❌ Error counting campaigns: {e}", "ERROR")
    
    # Count themes
    try:
        result = supabase.table('holiday_themes').select('id', count='exact').eq(
            'is_active', True
        ).execute()
        report["themes"]["total"] = result.count or 0
    except:
        pass
    
    # Get current theme
    try:
        result = supabase.table('holiday_themes').select('*').eq(
            'is_active', True
        ).order('priority', desc=True).execute()
        
        today = date.today()
        for theme in (result.data or []):
            if is_theme_active(theme['date_rule'], today):
                report["themes"]["current"] = theme['name']
                break
    except:
        pass
    
    # Get upcoming themes
    upcoming = get_upcoming_themes(7)
    report["themes"]["upcoming"] = [
        {"name": t['name'], "in_days": t['starts_in_days']} 
        for t in upcoming[:3]
    ]
    
    return report
