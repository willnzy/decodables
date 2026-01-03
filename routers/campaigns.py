"""
Marketing Campaigns Router
Provides public API for campaigns and claim functionality.

@module routers/campaigns
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from dependencies import optional_user, get_current_user
from services.db_service import supabase, add_credits_permanent

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


# ============================================================
# Request/Response Models
# ============================================================

class DismissRequest(BaseModel):
    channel: str  # modal | toast | banner


# ============================================================
# Public API
# ============================================================

@router.get("/active")
async def get_active_campaigns(
    user: Optional[dict] = Depends(optional_user)
) -> Dict[str, Any]:
    """
    Get all active campaigns visible to the current user.
    
    Returns campaigns filtered by:
    1. Active status and within time range
    2. Target audience eligibility
    3. Claim status
    
    Also returns organized notifications by channel (modal, toast, banner).
    
    Returns:
        {
            "campaigns": [...],
            "notifications": {
                "modal": {...} | null,
                "toast": {...} | null,
                "banner": [...]
            }
        }
    """
    now = datetime.utcnow()
    
    # [Why]: Fetch all active campaigns within time range
    result = supabase.table('campaigns').select('*').eq(
        'status', 'active'
    ).eq('is_active', True).lte(
        'start_at', now.isoformat()
    ).gte(
        'end_at', now.isoformat()
    ).execute()
    
    if not result.data:
        return {
            "campaigns": [],
            "notifications": {"modal": None, "toast": None, "banner": []}
        }
    
    campaigns = []
    notifications = {
        "modal": None,
        "toast": None,
        "banner": [],
    }
    
    for campaign in result.data:
        # [Why]: Check if user matches target audience
        if not _check_target_eligibility(campaign, user):
            continue
        
        # [Why]: Check claim and dismissal status for authenticated users
        has_claimed = False
        dismissed_channels = []
        
        if user:
            has_claimed = _check_has_claimed(campaign['id'], user['id'])
            dismissed_channels = _get_dismissed_channels(campaign['id'], user['id'])
        
        # [Why]: Check if user can still claim (usage limits)
        can_claim = not has_claimed and _check_usage_limit(campaign, user)
        
        campaign_data = {
            **campaign,
            'has_claimed': has_claimed,
            'can_claim': can_claim,
        }
        campaigns.append(campaign_data)
        
        # [Why]: Build notifications only for non-dismissed channels
        for channel in campaign.get('notification_channels', []):
            if channel in dismissed_channels:
                continue
            if channel == 'personal_message':
                continue  # Handled separately via notification system
            
            notification = _build_notification(campaign, channel)
            
            if channel == 'banner':
                notifications['banner'].append(notification)
            elif channel == 'modal' and notifications['modal'] is None:
                # [Why]: Only show one modal at a time (highest priority first)
                notifications['modal'] = notification
            elif channel == 'toast' and notifications['toast'] is None:
                notifications['toast'] = notification
    
    return {
        "campaigns": campaigns,
        "notifications": notifications,
    }


@router.post("/{campaign_id}/claim")
async def claim_campaign(
    campaign_id: str,
    user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Claim a campaign reward.
    
    Validates:
    1. Campaign exists and is active
    2. Within time range
    3. User matches target audience
    4. Usage limit not exceeded
    5. User hasn't already claimed
    
    For credits_gift type, immediately grants permanent credits.
    For credits_discount/credits_bonus, records eligibility for future use.
    
    Returns:
        { "success": true, "credits_received": 100, "message": "..." }
    """
    # [Why]: Fetch campaign details
    result = supabase.table('campaigns').select('*').eq(
        'id', campaign_id
    ).execute()
    
    if not result.data:
        raise HTTPException(404, "Campaign not found")
    
    campaign = result.data[0]
    
    # [Why]: Validate campaign is active
    if campaign['status'] != 'active' or not campaign['is_active']:
        raise HTTPException(400, "Campaign is not active")
    
    # [Why]: Validate time range
    now = datetime.utcnow()
    start_at = datetime.fromisoformat(campaign['start_at'].replace('Z', '+00:00'))
    end_at = datetime.fromisoformat(campaign['end_at'].replace('Z', '+00:00'))
    
    if now < start_at.replace(tzinfo=None):
        raise HTTPException(400, "Campaign has not started yet")
    if now > end_at.replace(tzinfo=None):
        raise HTTPException(400, "Campaign has ended")
    
    # [Why]: Validate target audience
    if not _check_target_eligibility(campaign, user):
        raise HTTPException(403, "You are not eligible for this campaign")
    
    # [Why]: Check for duplicate claim
    existing = supabase.table('campaign_claims').select('id').eq(
        'campaign_id', campaign_id
    ).eq('user_id', user['id']).execute()
    
    if existing.data:
        raise HTTPException(400, "You have already claimed this campaign")
    
    # [Why]: Check usage limit
    usage_limit = campaign.get('usage_limit')
    if usage_limit and campaign['usage_count'] >= usage_limit:
        raise HTTPException(400, "Campaign usage limit reached")
    
    # [Why]: Process claim based on campaign type
    credits_received = 0
    config = campaign.get('config', {})
    
    if campaign['type'] == 'credits_gift':
        # [Why]: Direct credit gift - immediately add permanent credits
        credits_received = config.get('amount', 0)
        if credits_received > 0:
            add_credits_permanent(
                user['id'], 
                credits_received, 
                f"Campaign reward: {campaign['name']}",
                "campaign_gift"
            )
    
    elif campaign['type'] == 'credits_discount':
        # [Why]: Discount recorded for future purchase
        # The actual discount is applied during checkout
        pass
    
    elif campaign['type'] == 'credits_bonus':
        # [Why]: Bonus recorded for future purchase
        # The actual bonus is applied during checkout
        pass
    
    # [Why]: Record the claim
    supabase.table('campaign_claims').insert({
        'campaign_id': campaign_id,
        'user_id': user['id'],
        'credits_received': credits_received,
    }).execute()
    
    # [Why]: Increment usage counter
    supabase.table('campaigns').update({
        'usage_count': campaign['usage_count'] + 1
    }).eq('id', campaign_id).execute()
    
    return {
        "success": True,
        "credits_received": credits_received,
        "message": f"You received {credits_received} credits!" if credits_received > 0 else "Offer claimed successfully!"
    }


@router.post("/{campaign_id}/dismiss")
async def dismiss_notification(
    campaign_id: str,
    req: DismissRequest,
    user: dict = Depends(get_current_user)
) -> Dict[str, bool]:
    """
    Dismiss a campaign notification for a specific channel.
    
    Records the dismissal so the notification won't show again
    for this user on this channel.
    
    Args:
        campaign_id: The campaign ID
        req.channel: The notification channel (modal, toast, banner)
        
    Returns:
        { "success": true }
    """
    # [Why]: Upsert dismissal record
    supabase.table('campaign_dismissals').upsert({
        'campaign_id': campaign_id,
        'user_id': user['id'],
        'channel': req.channel,
        'dismissed_at': datetime.utcnow().isoformat(),
    }, on_conflict='campaign_id,user_id,channel').execute()
    
    return {"success": True}


# ============================================================
# Helper Functions
# ============================================================

def _check_target_eligibility(campaign: dict, user: Optional[dict]) -> bool:
    """
    Check if user matches the campaign's target audience.
    
    Target types:
    - all: Everyone
    - subscription: Specific subscription tiers
    - users: Specific user IDs
    - new_users: Users registered within N days
    - inactive_users: Users inactive for N days
    """
    target_type = campaign.get('target_type', 'all')
    target_config = campaign.get('target_config', {})
    
    if target_type == 'all':
        return True
    
    if not user:
        return False
    
    if target_type == 'subscription':
        user_tier = user.get('tier', 'free')
        allowed_tiers = target_config.get('tiers', [])
        return user_tier in allowed_tiers
    
    elif target_type == 'users':
        allowed_users = target_config.get('user_ids', [])
        return user['id'] in allowed_users
    
    elif target_type == 'new_users':
        days = target_config.get('days_since_signup', 7)
        created_at = user.get('created_at')
        if not created_at:
            return False
        try:
            signup_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            return (datetime.utcnow() - signup_date.replace(tzinfo=None)).days <= days
        except:
            return False
    
    elif target_type == 'inactive_users':
        days = target_config.get('days_inactive', 30)
        last_login = user.get('last_login_at')
        if not last_login:
            return True  # Never logged in = inactive
        try:
            login_date = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
            return (datetime.utcnow() - login_date.replace(tzinfo=None)).days >= days
        except:
            return False
    
    return False


def _check_has_claimed(campaign_id: str, user_id: str) -> bool:
    """Check if user has already claimed this campaign."""
    result = supabase.table('campaign_claims').select('id').eq(
        'campaign_id', campaign_id
    ).eq('user_id', user_id).execute()
    return len(result.data) > 0


def _get_dismissed_channels(campaign_id: str, user_id: str) -> List[str]:
    """Get list of dismissed notification channels for this user/campaign."""
    result = supabase.table('campaign_dismissals').select('channel').eq(
        'campaign_id', campaign_id
    ).eq('user_id', user_id).execute()
    return [d['channel'] for d in result.data]


def _check_usage_limit(campaign: dict, user: Optional[dict]) -> bool:
    """Check if campaign has remaining usage capacity."""
    usage_limit = campaign.get('usage_limit')
    if usage_limit is None:
        return True  # No limit
    return campaign.get('usage_count', 0) < usage_limit


def _build_notification(campaign: dict, channel: str) -> Dict[str, Any]:
    """Build notification data structure for a channel."""
    config = campaign.get('notification_config', {})
    
    return {
        'campaign_id': campaign['id'],
        'campaign_type': campaign['type'],
        'channel': channel,
        'title': config.get('title', campaign['name']),
        'message': config.get('message', campaign.get('description', '')),
        'cta_text': config.get('cta_text', 'Learn More'),
        'cta_url': config.get('cta_url', '/pricing'),
        'show_once': config.get('show_once', False),
        'can_claim': True,  # Will be updated by caller if needed
    }
