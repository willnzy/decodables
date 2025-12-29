import os
from supabase import create_client, Client
from datetime import datetime, timezone
import uuid

# 从环境变量获取配置
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# 初始化客户端
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# ==========================================
# 0. 权限校验函数 (Permission Helpers)
# ==========================================

def is_member(user: dict) -> bool:
    """
    检查用户是否为有效会员
    只有 Starter/Pro 且订阅有效才算会员
    """
    if not user:
        return False
    tier = user.get("tier", "free")
    subscription_status = user.get("subscription_status", "inactive")
    
    # 只有 starter/pro 才是会员
    if tier not in ["starter", "pro"]:
        return False
    
    # 订阅必须是有效状态
    if subscription_status not in ["active", "trialing"]:
        return False
    
    return True

def can_access_resource(user: dict, allowed_tiers: list) -> bool:
    """
    检查用户是否有权限访问资源
    
    规则:
    - 若 'free' in allowed_tiers：允许访问（不需要会员）
    - 若 'free' not in allowed_tiers：必须 is_member(user)=true 且 user.tier in allowed_tiers
    """
    if not user or not allowed_tiers:
        return False
    
    user_tier = user.get("tier", "free")
    
    # 如果资源允许 free 用户访问，任何人都可以
    if "free" in allowed_tiers:
        return True
    
    # 否则必须是有效会员且 tier 在允许列表中
    if not is_member(user):
        return False
    
    return user_tier in allowed_tiers

def publish_permission(user: dict, resource_type: str, price_credits: int) -> dict:
    """
    检查用户发布权限（PRD 第7章）
    
    规则:
    - Free：不能发布任何内容
    - Starter：仅允许 resource_type='asset' 且 price_credits=0
    - Pro：允许 resource_type='asset'|'template' 且 price_credits 在 0..500
    
    Returns: { allowed: bool, reason: str }
    """
    if not user:
        return {"allowed": False, "reason": "User not found"}
    
    tier = user.get("tier", "free")
    
    # Free 用户不能发布
    if tier == "free":
        return {"allowed": False, "reason": "Free users cannot publish. Upgrade to Starter or Pro."}
    
    # 价格上限校验
    if price_credits < 0 or price_credits > 500:
        return {"allowed": False, "reason": "Price must be between 0 and 500 credits"}
    
    # Starter 用户限制
    if tier == "starter":
        if resource_type != "asset":
            return {"allowed": False, "reason": "Starter users can only publish Assets. Upgrade to Pro to publish Templates."}
        if price_credits > 0:
            return {"allowed": False, "reason": "Starter users can only publish free assets. Upgrade to Pro to sell."}
    
    # Pro 用户可以发布 asset 或 template
    if tier == "pro":
        if resource_type not in ["asset", "template"]:
            return {"allowed": False, "reason": "Invalid resource type. Must be 'asset' or 'template'."}
    
    return {"allowed": True, "reason": ""}

def validate_allowed_tiers(allowed_tiers: list) -> dict:
    """
    校验 allowed_tiers 白名单（PRD 第7章）
    
    仅允许以下三种之一:
    - ['free']
    - ['starter', 'pro']
    - ['pro']
    
    Returns: { valid: bool, reason: str }
    """
    valid_combinations = [
        ['free'],
        ['starter', 'pro'],
        ['pro']
    ]
    
    # 排序后比较
    sorted_tiers = sorted(allowed_tiers) if allowed_tiers else []
    
    for valid_combo in valid_combinations:
        if sorted_tiers == sorted(valid_combo):
            return {"valid": True, "reason": ""}
    
    return {
        "valid": False, 
        "reason": "allowed_tiers must be one of: ['free'], ['starter', 'pro'], or ['pro']"
    }

def listing_is_public_visible(listing: dict) -> bool:
    """
    检查 listing 是否公开可见（PRD 第8章）
    
    必须同时满足:
    - is_public = true
    - is_deleted = false
    - moderation_status = 'approved'
    """
    if not listing:
        return False
    
    return (
        listing.get("is_public", False) == True and
        listing.get("is_deleted", False) == False and
        listing.get("moderation_status", "draft") == "approved"
    )

def get_total_credits(user: dict) -> int:
    """获取用户总可用积分 (monthly + permanent)"""
    if not user:
        return 0
    return user.get("credits_monthly", 0) + user.get("credits_permanent", 0)

# ==========================================
# 1. 用户档案 (Profiles)
# ==========================================

def get_user_profile(user_id: str):
    """获取用户信息"""
    res = supabase.table("profiles").select("*").eq("id", user_id).execute()
    if res.data:
        user = res.data[0]
        # 计算总积分（兼容前端现有代码）
        user["credits"] = get_total_credits(user)
        return user
    return None

def create_user_profile(user_id: str, email: str, username: str, avatar_url: str):
    """
    创建新用户并赠送初始积分
    根据 PRD: Free 用户赠送 50 Credits (One-time, Permanent)
    """
    data = {
        "id": user_id,
        "email": email,
        "username": username,
        "avatar_url": avatar_url,
        "credits_monthly": 0,      # 订阅每月赠送
        "credits_permanent": 50,   # 注册赠送 50 Credits (永久)
        "tier": "free",
        "subscription_status": "inactive",
        "role": "user"
    }
    supabase.table("profiles").insert(data).execute()
    # 记录赠送流水
    log_credit_transaction(
        user_id=user_id, 
        amount=50, 
        bucket="permanent",
        balance_monthly_after=0, 
        balance_permanent_after=50, 
        type="signup_bonus", 
        description="Welcome Bonus - 50 Credits"
    )

def update_subscription_tier(user_id: str, tier: str, stripe_customer_id: str = None, subscription_status: str = "active"):
    """
    更新订阅等级
    同时更新 tier、subscription_status 和 stripe_customer_id
    """
    data = {
        "tier": tier,
        "subscription_status": subscription_status
    }
    if stripe_customer_id:
        data["stripe_customer_id"] = stripe_customer_id
    supabase.table("profiles").update(data).eq("id", user_id).execute()

def update_user_profile(user_id: str, avatar_url: str = None, username: str = None):
    """
    更新用户档案（头像、用户名）
    用于处理 Clerk user.updated webhook 事件
    """
    data = {}
    if avatar_url is not None:
        data["avatar_url"] = avatar_url
    if username is not None:
        data["username"] = username
    
    if data:
        supabase.table("profiles").update(data).eq("id", user_id).execute()
        return True
    return False

def refresh_monthly_credits(user_id: str, tier: str):
    """
    刷新月度积分（订阅周期开始时调用）
    - Starter: 500 credits/month
    - Pro: 1000 credits/month
    - 不结转：直接重置为当月额度（permanent credits 不受影响）
    """
    monthly_amounts = {
        "starter": 500,
        "pro": 1000,
        "free": 0
    }
    
    new_monthly = monthly_amounts.get(tier, 0)
    
    profile = get_user_profile(user_id)
    if not profile:
        return False
    
    # 重要：permanent credits 不受影响，保持不变
    permanent = profile.get("credits_permanent", 0)
    
    # 重置月度积分（不结转）- 只重置 monthly，不影响 permanent
    supabase.table("profiles").update({
        "credits_monthly": new_monthly,
        "monthly_credits_cycle_anchor": datetime.now().isoformat()
    }).eq("id", user_id).execute()
    
    # 记录流水
    log_credit_transaction(
        user_id=user_id,
        amount=new_monthly,
        bucket="monthly",
        balance_monthly_after=new_monthly,
        balance_permanent_after=permanent,  # permanent credits 保持不变
        type="sub_grant",
        description=f"Monthly {tier.capitalize()} Credits (Reset - Permanent credits preserved)"
    )
    
    return True

def check_and_reset_monthly_credits_if_needed(user_id: str):
    """
    检查并重置月度积分（如果需要）
    在用户登录或获取用户信息时调用，确保 monthly credits 按时重置
    
    规则：
    - 如果 monthly_credits_cycle_anchor 不存在或超过 30 天，且用户是 Starter/Pro，则重置
    - permanent credits 永远不会被重置
    """
    profile = get_user_profile(user_id)
    if not profile:
        return False
    
    tier = profile.get("tier", "free")
    subscription_status = profile.get("subscription_status", "inactive")
    
    # 只有 Starter/Pro 且订阅有效才需要重置
    if tier not in ["starter", "pro"]:
        return False
    
    if subscription_status not in ["active", "trialing"]:
        return False
    
    cycle_anchor = profile.get("monthly_credits_cycle_anchor")
    
    # 如果没有 cycle_anchor，说明是第一次，需要设置
    if not cycle_anchor:
        refresh_monthly_credits(user_id, tier)
        return True
    
    # 检查是否超过 30 天（一个月）
    try:
        anchor_date = datetime.fromisoformat(cycle_anchor.replace('Z', '+00:00'))
        if anchor_date.tzinfo is None:
            anchor_date = anchor_date.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        days_since_reset = (now - anchor_date).total_seconds() / (24 * 3600)
        
        # 如果超过 30 天，重置 monthly credits
        if days_since_reset >= 30:
            refresh_monthly_credits(user_id, tier)
            return True
    except (ValueError, TypeError) as e:
        # 如果日期解析失败，重置一次
        print(f"Warning: Failed to parse monthly_credits_cycle_anchor for user {user_id}: {e}")
        refresh_monthly_credits(user_id, tier)
        return True
    
    return False

# ==========================================
# 2. 积分与交易 (Credits & Transactions)
# ==========================================

def log_credit_transaction(
    user_id: str, 
    amount: int, 
    bucket: str,  # 'monthly' | 'permanent'
    balance_monthly_after: int, 
    balance_permanent_after: int, 
    type: str, 
    description: str
):
    """[内部调用] 记录流水 - 支持 Credits 分桶"""
    supabase.table("credit_transactions").insert({
        "user_id": user_id,
        "amount": amount,
        "bucket": bucket,
        "balance_monthly_after": balance_monthly_after,
        "balance_permanent_after": balance_permanent_after,
        "type": type,
        "description": description,
        "created_at": datetime.now().isoformat()
    }).execute()

def credit_deduct(user_id: str, amount: int, type: str, description: str) -> dict:
    """
    [核心] 统一扣费函数
    扣费优先级: 优先扣 Monthly Credits，不足部分再扣 Permanent Credits
    
    Returns: { success: bool, balance_monthly: int, balance_permanent: int }
    Raises: Exception if insufficient credits or concurrency conflict
    """
    profile = get_user_profile(user_id)
    if not profile:
        raise Exception("User not found")
    
    monthly = profile.get("credits_monthly", 0)
    permanent = profile.get("credits_permanent", 0)
    total = monthly + permanent
    
    if total < amount:
        raise Exception("CREDITS_INSUFFICIENT")
    
    # 计算扣费分配
    deduct_from_monthly = min(monthly, amount)
    deduct_from_permanent = amount - deduct_from_monthly
    
    new_monthly = monthly - deduct_from_monthly
    new_permanent = permanent - deduct_from_permanent
    
    # 乐观锁更新（检查原始值）
    res = supabase.table("profiles").update({
        "credits_monthly": new_monthly,
        "credits_permanent": new_permanent
    }).eq("id", user_id).eq("credits_monthly", monthly).eq("credits_permanent", permanent).execute()
    
    if not res.data:
        raise Exception("Concurrency conflict, please retry")
    
    # 记录流水（按实际扣减的桶分别记录）
    if deduct_from_monthly > 0:
        log_credit_transaction(
            user_id=user_id,
            amount=-deduct_from_monthly,
            bucket="monthly",
            balance_monthly_after=new_monthly,
            balance_permanent_after=new_permanent,
            type=type,
            description=description
        )
    
    if deduct_from_permanent > 0:
        log_credit_transaction(
            user_id=user_id,
            amount=-deduct_from_permanent,
            bucket="permanent",
            balance_monthly_after=new_monthly,
            balance_permanent_after=new_permanent,
            type=type,
            description=description
        )
    
    return {
        "success": True,
        "balance_monthly": new_monthly,
        "balance_permanent": new_permanent,
        "total": new_monthly + new_permanent
    }

def add_credits_permanent(user_id: str, amount: int, description: str, type: str = "topup_purchase"):
    """
    增加永久积分（用于购买/售卖获得）
    用户购买/售卖获得的 Credits 都是永久的
    """
    profile = get_user_profile(user_id)
    if not profile:
        return None
    
    monthly = profile.get("credits_monthly", 0)
    permanent = profile.get("credits_permanent", 0)
    new_permanent = permanent + amount
    
    supabase.table("profiles").update({
        "credits_permanent": new_permanent
    }).eq("id", user_id).execute()
    
    log_credit_transaction(
        user_id=user_id,
        amount=amount,
        bucket="permanent",
        balance_monthly_after=monthly,
        balance_permanent_after=new_permanent,
        type=type,
        description=description
    )
    
    return {"balance_monthly": monthly, "balance_permanent": new_permanent}

def add_credits_monthly(user_id: str, amount: int, description: str, type: str = "sub_grant"):
    """
    增加月度积分（用于订阅赠送）
    """
    profile = get_user_profile(user_id)
    if not profile:
        return None
    
    monthly = profile.get("credits_monthly", 0)
    permanent = profile.get("credits_permanent", 0)
    new_monthly = monthly + amount
    
    supabase.table("profiles").update({
        "credits_monthly": new_monthly
    }).eq("id", user_id).execute()
    
    log_credit_transaction(
        user_id=user_id,
        amount=amount,
        bucket="monthly",
        balance_monthly_after=new_monthly,
        balance_permanent_after=permanent,
        type=type,
        description=description
    )
    
    return {"balance_monthly": new_monthly, "balance_permanent": permanent}

# 兼容旧接口
def deduct_credits_atomic(user_id: str, amount: int, type: str, description: str):
    """[兼容] 原子扣费 - 内部调用 credit_deduct"""
    result = credit_deduct(user_id, amount, type, description)
    return result["success"]

def add_credits(user_id: str, amount: int, description: str, type: str = "purchase"):
    """[兼容] 增加积分 - 默认增加到 permanent"""
    return add_credits_permanent(user_id, amount, description, type)

def get_credit_history(user_id: str, page: int = 1, limit: int = 20):
    """获取积分历史"""
    start = (page - 1) * limit
    end = start + limit - 1
    res = supabase.table("credit_transactions")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("created_at", desc=True)\
        .range(start, end)\
        .execute()
    return res.data

# ==========================================
# 3. 项目管理 (Projects)
# ==========================================

def get_user_projects(user_id: str, page: int = 1, limit: int = 20):
    """获取项目列表（包含 canvas_data 用于缩略图预览）"""
    start = (page - 1) * limit
    end = start + limit - 1
    # Include created_at for project limit check (PRD v3.2)
    res = supabase.table("projects").select("id, title, thumbnail_url, canvas_data, created_at, updated_at")\
        .eq("user_id", user_id).eq("is_deleted", False)\
        .range(start, end).order("updated_at", desc=True).execute()
    return res.data

def get_project_detail(project_id: str, user_id: str):
    """获取项目详情"""
    res = supabase.table("projects").select("*")\
        .eq("id", project_id).eq("user_id", user_id).single().execute()
    return res.data

def create_project(user_id: str, title: str = None, canvas_data: dict = None):
    """创建项目（可选带初始数据）"""
    data = {
        "user_id": user_id,
        "title": title or "My Magic Story",
        "canvas_data": canvas_data or {},
        "last_downloaded_hash": ""
    }
    res = supabase.table("projects").insert(data).execute()
    return res.data[0]

def save_project(project_id: str, user_id: str, canvas_data: dict = None, thumbnail_url: str = None, title: str = None):
    """保存项目"""
    data = {
        "updated_at": datetime.now().isoformat()
    }
    if canvas_data is not None:
        data["canvas_data"] = canvas_data
    if thumbnail_url:
        data["thumbnail_url"] = thumbnail_url
    if title:
        data["title"] = title
    supabase.table("projects").update(data).eq("id", project_id).eq("user_id", user_id).execute()

def soft_delete_project(project_id: str, user_id: str):
    """软删除项目"""
    res = supabase.table("projects").update({"is_deleted": True})\
        .eq("id", project_id).eq("user_id", user_id).execute()
    if not res.data:
        raise Exception("Project not found or permission denied")
    return True

def restore_project(project_id: str):
    """[Admin] 恢复被删除的项目"""
    res = supabase.table("projects").update({"is_deleted": False})\
        .eq("id", project_id).execute()
    return res.data[0] if res.data else None

def update_project_hash(project_id: str, new_hash: str):
    """仅更新 Hash 值（用于缓存/去重，不参与扣费）"""
    supabase.table("projects").update({"last_downloaded_hash": new_hash})\
        .eq("id", project_id).execute()

def get_all_projects_feed(page: int = 1, limit: int = 50):
    """[Admin] 获取全站项目流"""
    start = (page - 1) * limit
    end = start + limit - 1
    res = supabase.table("projects").select("*, profiles(email, username)")\
        .eq("is_deleted", False)\
        .order("updated_at", desc=True)\
        .range(start, end).execute()
    return res.data

# ==========================================
# 4. 素材与资源 (Assets & Resources)
# ==========================================

def save_asset(user_id: str, url: str, type: str, project_id: str = None, prompt: str = None):
    """保存素材"""
    data = {
        "user_id": user_id,
        "url": url,
        "type": type,
        "project_id": project_id,
        "prompt": prompt
    }
    supabase.table("assets").insert(data).execute()

def get_assets(user_id: str, project_id: str = None):
    """获取用户素材"""
    query = supabase.table("assets").select("*").eq("user_id", user_id).eq("is_deleted", False)
    if project_id:
        query = query.eq("project_id", project_id)
    res = query.order("created_at", desc=True).execute()
    return res.data

def get_system_resources(resource_type: str = "sticker", user_tier: str = "free"):
    """
    获取系统公共资源 (贴纸等)
    根据用户 tier 过滤可访问的资源
    """
    res = supabase.table("system_resources").select("*").eq("type", resource_type).execute()
    
    # 过滤用户有权访问的资源
    accessible = []
    for resource in res.data or []:
        allowed_tiers = resource.get("allowed_tiers", ["free", "starter", "pro"])
        if user_tier in allowed_tiers or "free" in allowed_tiers:
            resource["is_accessible"] = True
        else:
            resource["is_accessible"] = False
        accessible.append(resource)
    
    return accessible

# ==========================================
# 5. Marketplace (市场)
# ==========================================

def get_marketplace_listings(
    featured: bool = False, 
    resource_type: str = None, 
    page: int = 1, 
    limit: int = 20,
    sort: str = "latest",  # 'latest' | 'popular' | 'best_selling'
    tier_filter: str = None,  # 'all' | 'free' | 'starter' | 'pro'
    price_filter: str = None,  # 'all' | 'free' | 'paid'
    mine: bool = False,
    user_id: str = None
):
    """
    获取市场商品列表（PRD 第13章）
    
    公共列表默认返回: moderation_status='approved' AND is_public=true AND is_deleted=false
    mine=true 时返回本人全状态（包括 draft/pending/rejected/approved）
    """
    start = (page - 1) * limit
    end = start + limit - 1
    
    # 明确指定使用 seller_id 关系（因为 moderated_by 关系也存在）
    # 使用 profiles!marketplace_listings_seller_id_fkey 明确指定卖家关系
    query = supabase.table("marketplace_listings").select("*, profiles!marketplace_listings_seller_id_fkey(username, avatar_url)")
    
    if mine and user_id:
        # 卖家查看自己的 listing（全状态）
        query = query.eq("seller_id", user_id).eq("is_deleted", False)
    else:
        # 公共列表：必须 approved + public + not deleted（PRD 强制规则）
        query = query.eq("is_public", True)\
            .eq("is_deleted", False)\
            .eq("moderation_status", "approved")
    
    # 资源类型过滤
    if resource_type:
        query = query.eq("resource_type", resource_type)
    
    # Tier 过滤
    if tier_filter and tier_filter != "all":
        # 使用 contains 查询 allowed_tiers 数组
        query = query.contains("allowed_tiers", [tier_filter])
    
    # 价格过滤
    if price_filter == "free":
        query = query.eq("price_credits", 0)
    elif price_filter == "paid":
        query = query.gt("price_credits", 0)
    
    # 排序
    if featured or sort == "best_selling":
        query = query.order("sales_count", desc=True)
    elif sort == "popular":
        query = query.order("usage_count", desc=True)
    else:  # latest
        query = query.order("created_at", desc=True)
    
    res = query.range(start, end).execute()
    return res.data

def get_marketplace_item(listing_id: str, user_id: str = None):
    """
    获取单个 listing 详情（PRD 第13章）
    
    公共访问: 仅允许 approved + public + not deleted
    卖家本人: 可看自己的任意状态
    """
    # 明确指定使用 seller_id 关系
    res = supabase.table("marketplace_listings").select("*, profiles!marketplace_listings_seller_id_fkey(username, avatar_url)")\
        .eq("id", listing_id).single().execute()
    
    if not res.data:
        return None
    
    listing = res.data
    
    # 检查访问权限
    is_seller = user_id and listing.get("seller_id") == user_id
    is_visible = listing_is_public_visible(listing)
    
    if not is_seller and not is_visible:
        return None
    
    return listing

def get_seller_listings(seller_id: str, page: int = 1, limit: int = 20):
    """获取卖家自己的商品"""
    start = (page - 1) * limit
    end = start + limit - 1
    
    res = supabase.table("marketplace_listings").select("*")\
        .eq("seller_id", seller_id).eq("is_deleted", False)\
        .order("created_at", desc=True).range(start, end).execute()
    return res.data

def create_listing(
    seller_id: str,
    title: str,
    description: str,
    thumbnail_url: str,
    resource_url: str,
    resource_type: str,
    price_credits: int,
    allowed_tiers: list = None,
    submit_for_review: bool = True
):
    """
    创建商品 listing（PRD 第7/8章）
    
    提交后 moderation_status='pending'，必须管理员审核通过后才能上架
    """
    data = {
        "seller_id": seller_id,
        "title": title,
        "description": description,
        "thumbnail_url": thumbnail_url,
        "resource_url": resource_url,
        "resource_type": resource_type,
        "price_credits": price_credits,
        "allowed_tiers": allowed_tiers or ["free"],
        "is_public": True,  # 用户希望公开，但仍不可见直到 approved
        "is_deleted": False,
        "sales_count": 0,
        "usage_count": 0,
        "moderation_status": "pending" if submit_for_review else "draft",
        "moderation_note": None,
        "moderated_by": None,
        "moderated_at": None
    }
    res = supabase.table("marketplace_listings").insert(data).execute()
    return res.data[0]

def submit_listing_for_review(listing_id: str, seller_id: str):
    """
    提交 listing 审核（PRD 第8章）
    
    draft -> pending
    rejected -> pending（允许修改后再次提交）
    """
    # 获取 listing 并验证所有权
    res = supabase.table("marketplace_listings").select("*")\
        .eq("id", listing_id).eq("seller_id", seller_id).single().execute()
    
    if not res.data:
        return None
    
    listing = res.data
    current_status = listing.get("moderation_status", "draft")
    
    # 只有 draft 或 rejected 可以提交
    if current_status not in ["draft", "rejected"]:
        return {"error": f"Cannot submit listing with status '{current_status}'"}
    
    # 更新状态
    update_res = supabase.table("marketplace_listings").update({
        "moderation_status": "pending",
        "is_public": True
    }).eq("id", listing_id).execute()
    
    return update_res.data[0] if update_res.data else None

def unpublish_listing(listing_id: str, seller_id: str):
    """
    下架 listing（PRD 第13章）
    
    设置 is_public=false，不改变历史 purchases 与 usage_count
    """
    res = supabase.table("marketplace_listings").update({
        "is_public": False
    }).eq("id", listing_id).eq("seller_id", seller_id).execute()
    
    return res.data[0] if res.data else None

def update_listing(listing_id: str, seller_id: str, updates: dict):
    """更新商品（只能修改自己的）"""
    allowed_fields = ["title", "description", "price_credits", "is_public", "allowed_tiers"]
    data = {k: v for k, v in updates.items() if k in allowed_fields}
    
    res = supabase.table("marketplace_listings").update(data)\
        .eq("id", listing_id).eq("seller_id", seller_id).execute()
    return res.data[0] if res.data else None

def check_user_purchase(user_id: str, listing_id: str) -> bool:
    """检查用户是否已购买某商品"""
    res = supabase.table("user_purchases").select("id")\
        .eq("user_id", user_id).eq("listing_id", listing_id).execute()
    return len(res.data) > 0

def execute_purchase(buyer_id: str, listing_id: str) -> dict:
    """
    执行购买逻辑（PRD 第13章）
    
    规则:
    0) 校验 listing: moderation_status='approved' AND is_public=true AND is_deleted=false
    1) 校验 listing.allowed_tiers 与用户权限
    2) 去重：若已购买则直接返回成功
    3) 事务扣费：买家扣 price（优先 monthly）
    4) 卖家入账：price × 90%（计入 permanent）
    5) 平台抽成 10%
    6) 写入 user_purchases
    
    Returns: { success: bool, message: str }
    """
    # 0. 获取商品信息（必须 approved + public + not deleted）
    listing_res = supabase.table("marketplace_listings").select("*")\
        .eq("id", listing_id)\
        .eq("is_public", True)\
        .eq("is_deleted", False)\
        .eq("moderation_status", "approved")\
        .single().execute()
    
    if not listing_res.data:
        return {"success": False, "message": "Listing not found or not available for purchase"}
    
    listing = listing_res.data
    price = listing.get("price_credits", 0)
    seller_id = listing.get("seller_id")
    allowed_tiers = listing.get("allowed_tiers", ["free", "starter", "pro"])
    
    # 2. 获取买家信息
    buyer = get_user_profile(buyer_id)
    if not buyer:
        return {"success": False, "message": "Buyer not found"}
    
    # 3. 权限校验
    if not can_access_resource(buyer, allowed_tiers):
        return {"success": False, "message": "Upgrade required to purchase this item"}
    
    # 4. 去重检查
    if check_user_purchase(buyer_id, listing_id):
        return {"success": True, "message": "Already purchased", "already_owned": True}
    
    # 5. 免费商品处理
    if price == 0:
        supabase.table("user_purchases").insert({
            "user_id": buyer_id,
            "listing_id": listing_id,
            "price_paid": 0
        }).execute()
        return {"success": True, "message": "Free item claimed"}
    
    # 6. 扣除买家积分
    try:
        credit_deduct(buyer_id, price, "market_purchase", f"Purchase: {listing.get('title', 'Item')}")
    except Exception as e:
        if "INSUFFICIENT" in str(e):
            return {"success": False, "message": "Insufficient credits"}
        raise e
    
    # 7. 卖家入账（90%）
    if seller_id:
        seller_amount = int(price * 0.9)
        add_credits_permanent(
            seller_id, 
            seller_amount, 
            f"Sale: {listing.get('title', 'Item')}", 
            type="market_sale"
        )
    
    # 8. 记录购买
    supabase.table("user_purchases").insert({
        "user_id": buyer_id,
        "listing_id": listing_id,
        "price_paid": price
    }).execute()
    
    # 9. 更新销量
    supabase.table("marketplace_listings").update({
        "sales_count": listing.get("sales_count", 0) + 1
    }).eq("id", listing_id).execute()
    
    return {"success": True, "message": "Purchase successful"}

def get_user_purchases(user_id: str, page: int = 1, limit: int = 50):
    """获取用户已购买的商品"""
    start = (page - 1) * limit
    end = start + limit - 1
    
    res = supabase.table("user_purchases").select("*, marketplace_listings(*)")\
        .eq("user_id", user_id)\
        .order("purchased_at", desc=True).range(start, end).execute()
    return res.data

def get_seller_stats(seller_id: str) -> dict:
    """获取卖家统计数据（PRD 第13章）"""
    # 获取所有商品
    listings = supabase.table("marketplace_listings").select("id, sales_count, usage_count, price_credits, moderation_status")\
        .eq("seller_id", seller_id).eq("is_deleted", False).execute().data
    
    total_sales = sum(l.get("sales_count", 0) for l in listings)
    total_usage = sum(l.get("usage_count", 0) for l in listings)
    
    # 计算总收入（90% 分成）
    total_earned = 0
    for listing in listings:
        total_earned += int(listing.get("price_credits", 0) * listing.get("sales_count", 0) * 0.9)
    
    # 按审核状态统计
    status_counts = {}
    for listing in listings:
        status = listing.get("moderation_status", "draft")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    return {
        "total_listings": len(listings),
        "total_sales": total_sales,
        "total_usage": total_usage,
        "total_earned_credits": total_earned,
        "status_counts": status_counts
    }

# ==========================================
# 5.1 Listing Usage（使用次数统计）
# ==========================================

def record_listing_usage(listing_id: str, used_by_user_id: str, project_id: str) -> bool:
    """
    记录 listing 使用（PRD 第9章）
    
    去重规则: (listing_id, used_by_user_id, project_id) unique
    同一用户对同一 listing 在同一项目内重复 Apply，不重复计数
    
    Returns: True if new usage recorded, False if already exists
    """
    # 检查是否已存在
    existing = supabase.table("listing_usage").select("id")\
        .eq("listing_id", listing_id)\
        .eq("used_by_user_id", used_by_user_id)\
        .eq("project_id", project_id).execute()
    
    if existing.data:
        return False  # 已存在，不重复计数
    
    try:
        # 插入使用记录
        supabase.table("listing_usage").insert({
            "listing_id": listing_id,
            "used_by_user_id": used_by_user_id,
            "project_id": project_id
        }).execute()
        
        # 增加 usage_count
        listing = supabase.table("marketplace_listings").select("usage_count")\
            .eq("id", listing_id).single().execute()
        
        if listing.data:
            current_count = listing.data.get("usage_count", 0)
            supabase.table("marketplace_listings").update({
                "usage_count": current_count + 1
            }).eq("id", listing_id).execute()
        
        return True
    except Exception as e:
        print(f"Failed to record listing usage: {e}")
        return False

def get_leaderboard(period: str = "monthly", board_type: str = "all", limit: int = 10):
    """
    获取排行榜（PRD 第9章）
    
    period: 'monthly' | 'all_time'
    board_type: 'all' | 'template' | 'asset'
    
    Returns: Top 10 listings with usage_count and rank
    """
    # 明确指定使用 seller_id 关系
    query = supabase.table("marketplace_listings").select("id, title, thumbnail_url, usage_count, resource_type, seller_id, profiles!marketplace_listings_seller_id_fkey(username, avatar_url)")\
        .eq("is_public", True)\
        .eq("is_deleted", False)\
        .eq("moderation_status", "approved")
    
    if board_type != "all":
        query = query.eq("resource_type", board_type)
    
    query = query.order("usage_count", desc=True).limit(limit)
    
    res = query.execute()
    
    # 添加排名
    leaderboard = []
    for idx, item in enumerate(res.data or []):
        item["rank"] = idx + 1
        leaderboard.append(item)
    
    return leaderboard

# ==========================================
# 6. 通知系统 (Notifications)
# ==========================================

def get_user_notifications(user_id: str, unread_only: bool = False, limit: int = 20):
    """获取用户通知"""
    query = supabase.table("notifications").select("*")
    
    # 个人通知 + 广播通知
    query = query.or_(f"user_id.eq.{user_id},user_id.is.null")
    
    if unread_only:
        query = query.eq("is_read", False)
    
    res = query.order("created_at", desc=True).limit(limit).execute()
    return res.data

def mark_notification_read(notification_id: str, user_id: str):
    """标记通知为已读"""
    supabase.table("notifications").update({"is_read": True})\
        .eq("id", notification_id).execute()

def create_broadcast(title: str, content: str, target_group: str = "all"):
    """[Admin] 创建广播通知"""
    data = {
        "user_id": None,  # NULL = 广播
        "target_group": target_group,
        "title": title,
        "content": content,
        "is_read": False
    }
    res = supabase.table("notifications").insert(data).execute()
    return res.data[0]

# ==========================================
# 7. 折扣系统 (Discounts)
# ==========================================

def get_user_discount(user_id: str, target_plan: str = None):
    """获取用户有效折扣"""
    query = supabase.table("user_discounts").select("*")\
        .eq("user_id", user_id)\
        .gte("valid_until", datetime.now().isoformat())
    
    if target_plan:
        query = query.eq("target_plan", target_plan)
    
    res = query.order("discount_percent", desc=True).limit(1).execute()
    return res.data[0] if res.data else None

def create_user_discount(user_id: str, discount_percent: int, valid_days: int, target_plan: str = None):
    """[Admin] 创建用户折扣"""
    from datetime import timedelta
    valid_until = datetime.now() + timedelta(days=valid_days)
    
    data = {
        "user_id": user_id,
        "discount_percent": discount_percent,
        "valid_until": valid_until.isoformat(),
        "target_plan": target_plan
    }
    res = supabase.table("user_discounts").insert(data).execute()
    return res.data[0]

# ==========================================
# 8. 运营与后台 (Admin & Ops)
# ==========================================

def log_activity(user_id: str, action: str, metadata: dict = None):
    """记录用户行为日志"""
    supabase.table("activity_logs").insert({
        "user_id": user_id,
        "action": action,
        "metadata": metadata
    }).execute()

def create_support_ticket(user_id: str, email: str, message: str):
    """创建工单"""
    supabase.table("support_tickets").insert({
        "user_id": user_id,
        "email": email,
        "content": message,
        "category": "ticket_submission",
        "status": "open"
    }).execute()

def search_users(query: str):
    """[Admin] 搜索用户 (支持 ID 或 Email 模糊搜索)"""
    res = supabase.table("profiles").select("*")\
        .or_(f"id.eq.{query},email.ilike.%{query}%")\
        .execute()
    return res.data

def get_full_user_audit(user_id: str):
    """
    [Admin] 获取用户全方位视图：档案、流水、日志、工单
    """
    # 1. 档案
    profile = get_user_profile(user_id)
    
    # 2. 积分流水
    txs = supabase.table("credit_transactions").select("*")\
        .eq("user_id", user_id).order("created_at", desc=True).execute().data
    
    # 3. 行为日志
    logs = supabase.table("activity_logs").select("*")\
        .eq("user_id", user_id).order("created_at", desc=True).limit(50).execute().data
    
    # 4. 工单记录
    tickets = supabase.table("support_tickets").select("*")\
        .eq("user_id", user_id).order("created_at", desc=True).execute().data
    
    # 5. 购买记录
    purchases = get_user_purchases(user_id)
    
    return {
        "profile": profile,
        "transactions": txs,
        "logs": logs,
        "tickets": tickets,
        "purchases": purchases
    }

def admin_adjust_credits(user_id: str, amount: int, bucket: str, reason: str):
    """
    [Admin] 手动调整积分
    bucket: 'monthly' | 'permanent'
    """
    profile = get_user_profile(user_id)
    if not profile:
        raise Exception("User not found")
    
    monthly = profile.get("credits_monthly", 0)
    permanent = profile.get("credits_permanent", 0)
    
    if bucket == "monthly":
        new_monthly = max(0, monthly + amount)
        supabase.table("profiles").update({"credits_monthly": new_monthly}).eq("id", user_id).execute()
        log_credit_transaction(
            user_id, amount, "monthly", new_monthly, permanent, "admin_adj", reason
        )
    else:
        new_permanent = max(0, permanent + amount)
        supabase.table("profiles").update({"credits_permanent": new_permanent}).eq("id", user_id).execute()
        log_credit_transaction(
            user_id, amount, "permanent", monthly, new_permanent, "admin_adj", reason
        )
    
    return True

# ==========================================
# 8.1 Admin 审核功能（Marketplace Moderation）
# ==========================================

def admin_get_moderation_list(
    status: str = None,  # 'pending' | 'approved' | 'rejected' | 'all'
    resource_type: str = None,  # 'template' | 'asset'
    page: int = 1,
    limit: int = 20
):
    """
    [Admin] 获取审核列表（PRD 第16章）
    """
    start = (page - 1) * limit
    end = start + limit - 1
    
    # 明确指定使用 seller_id 关系（卖家信息）
    query = supabase.table("marketplace_listings").select("*, profiles!marketplace_listings_seller_id_fkey(username, email, avatar_url)")\
        .eq("is_deleted", False)
    
    if status and status != "all":
        query = query.eq("moderation_status", status)
    
    if resource_type:
        query = query.eq("resource_type", resource_type)
    
    query = query.order("created_at", desc=True).range(start, end)
    
    res = query.execute()
    return res.data

def admin_get_moderation_detail(listing_id: str):
    """
    [Admin] 获取审核详情（PRD 第16章）
    """
    # 明确指定使用 seller_id 关系（卖家信息）
    res = supabase.table("marketplace_listings").select("*, profiles!marketplace_listings_seller_id_fkey(username, email, avatar_url)")\
        .eq("id", listing_id).single().execute()
    
    return res.data

def admin_approve_listing(listing_id: str, admin_id: str):
    """
    [Admin] 批准 listing（PRD 第16章）
    
    pending -> approved
    """
    from datetime import datetime
    
    res = supabase.table("marketplace_listings").update({
        "moderation_status": "approved",
        "moderated_by": admin_id,
        "moderated_at": datetime.now().isoformat()
    }).eq("id", listing_id).execute()
    
    return res.data[0] if res.data else None

def admin_reject_listing(listing_id: str, admin_id: str, reason: str):
    """
    [Admin] 拒绝 listing（PRD 第16章）
    
    pending -> rejected（必须附原因）
    """
    from datetime import datetime
    
    if not reason or not reason.strip():
        raise Exception("Rejection reason is required")
    
    res = supabase.table("marketplace_listings").update({
        "moderation_status": "rejected",
        "moderation_note": reason,
        "moderated_by": admin_id,
        "moderated_at": datetime.now().isoformat()
    }).eq("id", listing_id).execute()
    
    return res.data[0] if res.data else None

def admin_delete_listing(listing_id: str):
    """
    [Admin] 软删除 listing（PRD 第16章）
    """
    res = supabase.table("marketplace_listings").update({
        "is_deleted": True
    }).eq("id", listing_id).execute()
    
    return res.data[0] if res.data else None

def admin_unpublish_listing(listing_id: str):
    """
    [Admin] 强制下架 listing（PRD 第16章）
    
    设置 is_public=false
    """
    res = supabase.table("marketplace_listings").update({
        "is_public": False
    }).eq("id", listing_id).execute()
    
    return res.data[0] if res.data else None
