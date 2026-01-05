"""
活动状态管理

处理活动的生命周期状态转换。
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List

from services.db_service import supabase
from .utils import log


def update_campaign_statuses() -> Dict[str, int]:
    """
    Update campaign statuses based on current time.
    
    State transitions:
    - scheduled -> active: when current time >= start_at
    - active -> ended: when current time >= end_at
    - paused campaigns are not auto-transitioned
    
    Returns:
        Dict with counts of activated and ended campaigns
    """
    now = datetime.now(timezone.utc)
    results = {"activated": 0, "ended": 0, "errors": 0}
    
    log("Checking campaign statuses...")
    
    # 1. Activate scheduled campaigns that have started
    try:
        scheduled = supabase.table('campaigns').select('id, name, start_at').eq(
            'status', 'scheduled'
        ).eq('is_active', True).execute()
        
        for campaign in (scheduled.data or []):
            try:
                start_at = datetime.fromisoformat(
                    campaign['start_at'].replace('Z', '+00:00')
                )
                
                if now >= start_at:
                    supabase.table('campaigns').update({
                        'status': 'active',
                        'updated_at': now.isoformat()
                    }).eq('id', campaign['id']).execute()
                    
                    log(f"✅ Activated campaign: {campaign['name']} (ID: {campaign['id']})")
                    results["activated"] += 1
                    
            except Exception as e:
                log(f"❌ Error activating campaign {campaign['id']}: {e}", "ERROR")
                results["errors"] += 1
                
    except Exception as e:
        log(f"❌ Error fetching scheduled campaigns: {e}", "ERROR")
        results["errors"] += 1
    
    # 2. End active campaigns that have passed end_at
    try:
        active = supabase.table('campaigns').select('id, name, end_at').eq(
            'status', 'active'
        ).execute()
        
        for campaign in (active.data or []):
            try:
                end_at = datetime.fromisoformat(
                    campaign['end_at'].replace('Z', '+00:00')
                )
                
                if now >= end_at:
                    supabase.table('campaigns').update({
                        'status': 'ended',
                        'is_active': False,
                        'updated_at': now.isoformat()
                    }).eq('id', campaign['id']).execute()
                    
                    log(f"🏁 Ended campaign: {campaign['name']} (ID: {campaign['id']})")
                    results["ended"] += 1
                    
            except Exception as e:
                log(f"❌ Error ending campaign {campaign['id']}: {e}", "ERROR")
                results["errors"] += 1
                
    except Exception as e:
        log(f"❌ Error fetching active campaigns: {e}", "ERROR")
        results["errors"] += 1
    
    return results


def get_upcoming_campaigns(hours: int = 24) -> List[Dict]:
    """
    Get campaigns starting within the next N hours.
    Useful for sending advance notifications.
    """
    now = datetime.now(timezone.utc)
    future = now + timedelta(hours=hours)
    
    try:
        result = supabase.table('campaigns').select('*').eq(
            'status', 'scheduled'
        ).gte('start_at', now.isoformat()).lte(
            'start_at', future.isoformat()
        ).execute()
        
        return result.data or []
    except Exception as e:
        log(f"❌ Error fetching upcoming campaigns: {e}", "ERROR")
        return []
