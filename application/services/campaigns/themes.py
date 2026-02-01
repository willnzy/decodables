"""
节假日主题管理

处理节假日主题的状态检查和日志记录。
"""

import uuid
from datetime import datetime, timezone, date, timedelta
from typing import Optional, Dict, List

from core.database import supabase
from .date_utils import is_theme_active
from .utils import log


def log_current_theme() -> Optional[Dict]:
    """
    Check and log the current active holiday theme.
    Useful for analytics and debugging.
    """
    today = date.today()
    
    try:
        result = supabase.table('daily_themes').select('*').eq(
            'is_active', True
        ).eq('is_deleted', False).order('priority', desc=True).execute()

        if not result.data:
            log("📅 No daily themes configured")
            return None

        for theme in result.data:
            date_rule = theme.get('date_rule')
            if date_rule and is_theme_active(date_rule, today):
                log(f"🎉 Active daily theme: {theme['name']} (ID: {theme['id']}, Priority: {theme.get('priority', 0)})")

                # Log to analytics table (optional)
                try:
                    supabase.table('analytics_events').insert({
                        'event_type': 'daily_theme_active',
                        'event_id': str(uuid.uuid4()),
                        'properties': {
                            'theme_id': theme['id'],
                            'theme_name': theme['name'],
                            'date': today.isoformat()
                        },
                        'created_at': datetime.now(timezone.utc).isoformat()
                    }).execute()
                except Exception:
                    pass  # Analytics logging is optional, non-blocking

                return theme

        log("📅 No active daily theme for today")
        return None
        
    except Exception as e:
        log(f"❌ Error checking daily theme: {e}", "ERROR")
        return None


def get_upcoming_themes(days: int = 7) -> List[Dict]:
    """
    Get themes that will be active within the next N days.
    Useful for preview and preparation.
    """
    today = date.today()
    
    try:
        result = supabase.table('daily_themes').select('*').eq(
            'is_active', True
        ).eq('is_deleted', False).order('priority', desc=True).execute()

        if not result.data:
            return []

        upcoming = []
        for day_offset in range(1, days + 1):
            check_date = today + timedelta(days=day_offset)
            for theme in result.data:
                date_rule = theme.get('date_rule')
                if date_rule and is_theme_active(date_rule, check_date):
                    if theme['id'] not in [t['id'] for t in upcoming]:
                        upcoming.append({
                            **theme,
                            'starts_in_days': day_offset
                        })

        return upcoming

    except Exception as e:
        log(f"❌ Error checking upcoming daily themes: {e}", "ERROR")
        return []
