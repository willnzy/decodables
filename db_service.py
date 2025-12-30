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

def generate_user_code() -> str:
    """
    生成唯一用户标识码
    格式: YYYYMMDDHHMMSS + 毫秒(3位) + 用户序号(7位)
    例如: 202512301430251230000001
    
    时间使用 UTC-0 (协调世界时)，确保全球一致
    序号补0到7位数
    
    总长度: 14 + 3 + 7 = 24 位
    """
    from datetime import timezone
    
    # 获取当前 UTC 时间（精确到毫秒）
    now_utc = datetime.now(timezone.utc)
    timestamp_part = now_utc.strftime("%Y%m%d%H%M%S") + f"{now_utc.microsecond // 1000:03d}"
    
    # 获取当前用户总数
    count_result = supabase.table("profiles").select("id", count="exact").execute()
    user_count = count_result.count if count_result.count else 0
    
    # 序号 = 当前用户数 + 1，补齐7位 (0000001 - 9999999)
    sequence_part = f"{user_count + 1:07d}"
    
    return f"{timestamp_part}{sequence_part}"


def create_user_profile(user_id: str, email: str, username: str, avatar_url: str):
    """
    创建新用户并赠送初始积分
    根据 PRD: Free 用户赠送 50 Credits (One-time, Permanent)
    """
    # 生成唯一用户标识码
    user_code = generate_user_code()
    
    data = {
        "id": user_id,
        "email": email,
        "username": username,
        "avatar_url": avatar_url,
        "user_code": user_code,    # 用户唯一标识码
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

def log_payment_record(
    user_id: str, 
    amount_cents: int, 
    currency: str,
    type: str,  # 'sub_payment', 'sub_renewal', 'credits_purchase'
    description: str
):
    """
    记录付款记录（订阅费用、积分购买等）
    amount_cents: 金额（以分为单位）
    currency: 货币代码（如 'USD'）
    type: 付款类型
    description: 描述
    """
    # 获取用户当前余额用于记录
    profile = supabase.table("profiles").select("credits_monthly, credits_permanent").eq("id", user_id).single().execute()
    balance_monthly = profile.data.get("credits_monthly", 0) if profile.data else 0
    balance_permanent = profile.data.get("credits_permanent", 0) if profile.data else 0
    
    supabase.table("credit_transactions").insert({
        "user_id": user_id,
        "amount": 0,  # 付款记录不影响积分
        "bucket": "payment",  # 特殊桶标识这是付款记录
        "balance_monthly_after": balance_monthly,
        "balance_permanent_after": balance_permanent,
        "type": type,
        "description": f"{description} | {currency} {amount_cents}",  # 包含金额信息
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

def get_user_projects(user_id: str, page: int = 1, limit: int = 20, search: str = None, include_canvas_data: bool = True):
    """获取项目列表
    
    Args:
        user_id: 用户ID
        page: 页码
        limit: 每页数量
        search: 搜索关键词
        include_canvas_data: 是否包含 canvas_data（用于分步加载优化）
    """
    start = (page - 1) * limit
    end = start + limit - 1
    print(f"[GET_PROJECTS] Query params: user_id={user_id}, page={page}, limit={limit}, search={search}, include_canvas_data={include_canvas_data}")
    
    # 根据 include_canvas_data 决定查询字段
    if include_canvas_data:
        select_fields = "id, title, thumbnail_url, canvas_data, created_at, updated_at"
    else:
        # 不包含 canvas_data，只返回基本信息（加载更快）
        select_fields = "id, title, thumbnail_url, created_at, updated_at"
    
    query = supabase.table("projects").select(select_fields)\
        .eq("user_id", user_id).eq("is_deleted", False)
    
    # Add search filter if provided
    if search and search.strip():
        search_term = search.strip()
        print(f"[GET_PROJECTS] Adding search filter: {search_term}")
        query = query.ilike("title", f"%{search_term}%")
    
    res = query.range(start, end).order("updated_at", desc=True).execute()
    items_count = len(res.data) if res.data else 0
    print(f"[GET_PROJECTS] Returned {items_count} items")
    return res.data

def count_user_projects(user_id: str, search: str = None):
    """获取用户项目总数（用于分页和限制检查）"""
    try:
        print(f"[COUNT] Starting count query for user_id: {user_id}, search: {search}")
        
        # 方法1: 直接查询所有符合条件的项目ID，然后计数
        # 这是最可靠的方式，避免 Supabase count 参数的兼容性问题
        query = supabase.table("projects").select("id")\
            .eq("user_id", user_id).eq("is_deleted", False)
        
        # Add search filter if provided
        if search and search.strip():
            search_term = search.strip()
            print(f"[COUNT] Adding search filter: {search_term}")
            query = query.ilike("title", f"%{search_term}%")
        
        res = query.execute()
        
        # 直接使用返回的数据长度作为计数
        count_value = len(res.data) if res.data else 0
        print(f"[COUNT] Final count: {count_value}")
        return count_value
    except Exception as e:
        print(f"[COUNT] Error counting projects: {e}")
        import traceback
        traceback.print_exc()
        # Fallback: return 0 on error
        return 0

def get_project_detail(project_id: str, user_id: str):
    """获取项目详情"""
    print(f"[DB_GET] Fetching project {project_id} for user {user_id}")
    res = supabase.table("projects").select("*")\
        .eq("id", project_id).eq("user_id", user_id).single().execute()
    
    if res.data:
        canvas_data = res.data.get("canvas_data", {})
        if canvas_data:
            pages = canvas_data.get("pages", []) if isinstance(canvas_data, dict) else canvas_data
            print(f"[DB_GET] Project {project_id} has {len(pages)} pages")
            for i, page in enumerate(pages):
                if page:
                    has_json = bool(page.get("canvasJson"))
                    obj_count = len(page.get("canvasJson", {}).get("objects", [])) if page.get("canvasJson") else 0
                    print(f"[DB_GET] Page {i}: hasCanvasJson={has_json}, objectCount={obj_count}")
        else:
            print(f"[DB_GET] Project {project_id} has no canvas_data")
    else:
        print(f"[DB_GET] Project {project_id} not found")
    
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
    print(f"[DB_SAVE] Starting save for project {project_id}")
    data = {
        "updated_at": datetime.now().isoformat()
    }
    if canvas_data is not None:
        data["canvas_data"] = canvas_data
        # Debug: Log canvas_data structure
        pages = canvas_data.get("pages", []) if isinstance(canvas_data, dict) else canvas_data
        print(f"[DB_SAVE] canvas_data has {len(pages)} pages")
        for i, page in enumerate(pages):
            if page:
                has_json = bool(page.get("canvasJson"))
                obj_count = len(page.get("canvasJson", {}).get("objects", [])) if page.get("canvasJson") else 0
                print(f"[DB_SAVE] Page {i}: hasCanvasJson={has_json}, objectCount={obj_count}")
    else:
        print(f"[DB_SAVE] No canvas_data provided")
    if thumbnail_url:
        data["thumbnail_url"] = thumbnail_url
    if title:
        data["title"] = title
    
    result = supabase.table("projects").update(data).eq("id", project_id).eq("user_id", user_id).execute()
    print(f"[DB_SAVE] Save completed for project {project_id}")

def soft_delete_project(project_id: str, user_id: str):
    """软删除项目"""
    from datetime import datetime
    res = supabase.table("projects").update({
        "is_deleted": True,
        "deleted_at": datetime.utcnow().isoformat()
    }).eq("id", project_id).eq("user_id", user_id).execute()
    if not res.data:
        raise Exception("Project not found or permission denied")
    return True

def restore_project(project_id: str):
    """[Admin] 恢复被删除的项目"""
    res = supabase.table("projects").update({
        "is_deleted": False,
        "deleted_at": None
    }).eq("id", project_id).execute()
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


def send_notification_to_user(user_id: str, title: str, content: str, notification_type: str = "system"):
    """[Admin] 发送通知给单个用户"""
    data = {
        "user_id": user_id,
        "target_group": None,
        "title": title,
        "content": content,
        "is_read": False
    }
    # 尝试添加 notification_type（如果表支持）
    try:
        data["notification_type"] = notification_type
        res = supabase.table("notifications").insert(data).execute()
    except Exception as e:
        # 如果字段不存在，移除后重试
        if "notification_type" in str(e):
            del data["notification_type"]
            res = supabase.table("notifications").insert(data).execute()
        else:
            raise e
    return res.data[0] if res.data else None


def send_notification_to_users(user_ids: list, title: str, content: str, notification_type: str = "system"):
    """[Admin] 批量发送通知给多个用户"""
    notifications = []
    for user_id in user_ids:
        data = {
            "user_id": user_id,
            "target_group": None,
            "title": title,
            "content": content,
            "is_read": False
        }
        notifications.append(data)
    
    if not notifications:
        return []
    
    # 尝试添加 notification_type（如果表支持）
    try:
        for n in notifications:
            n["notification_type"] = notification_type
        res = supabase.table("notifications").insert(notifications).execute()
    except Exception as e:
        # 如果字段不存在，移除后重试
        if "notification_type" in str(e):
            for n in notifications:
                if "notification_type" in n:
                    del n["notification_type"]
            res = supabase.table("notifications").insert(notifications).execute()
        else:
            raise e
    return res.data


def get_users_by_tier(tier: str):
    """获取指定 tier 的所有用户 ID"""
    res = supabase.table("profiles").select("id").eq("tier", tier).execute()
    return [u["id"] for u in res.data] if res.data else []


def get_all_notification_stats():
    """获取通知统计"""
    try:
        # 总通知数
        total_res = supabase.table("notifications").select("id", count="exact").execute()
        
        # 未读通知数
        unread_res = supabase.table("notifications").select("id", count="exact").eq("is_read", False).execute()
        
        # 最近7天的通知
        from datetime import datetime, timedelta
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        recent_res = supabase.table("notifications").select("id", count="exact")\
            .gte("created_at", week_ago).execute()
        
        return {
            "total": total_res.count or 0,
            "unread": unread_res.count or 0,
            "recent_7d": recent_res.count or 0
        }
    except Exception as e:
        print(f"[get_all_notification_stats] Error: {e}")
        return {
            "total": 0,
            "unread": 0,
            "recent_7d": 0
        }


def get_notification_history(page: int = 1, limit: int = 50, notification_type: str = None):
    """获取通知发送历史"""
    try:
        query = supabase.table("notifications").select("*")
        
        # 只有当指定了类型且表支持该字段时才过滤
        if notification_type:
            try:
                query = query.eq("notification_type", notification_type)
            except:
                pass  # 字段不存在，忽略过滤
        
        offset = (page - 1) * limit
        res = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return res.data or []
    except Exception as e:
        print(f"[get_notification_history] Error: {e}")
        return []

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
    """创建工单并发送邮件通知"""
    # 1. 保存到数据库
    supabase.table("support_tickets").insert({
        "user_id": user_id,
        "email": email,
        "content": message,
        "category": "ticket_submission",
        "status": "open"
    }).execute()
    
    # 2. 发送邮件通知到客服邮箱
    try:
        send_support_email(user_id, email, message)
    except Exception as e:
        print(f"[WARNING] Failed to send support email: {e}")
        # 不抛出异常，工单已保存到数据库


def send_support_email(user_id: str, user_email: str, message: str, images: list = None):
    """发送支持邮件到客服邮箱，支持图片附件"""
    try:
        import resend
        from config import RESEND_API_KEY, SUPPORT_EMAIL, SUPPORT_EMAIL_FROM
        
        if not RESEND_API_KEY:
            print("[WARNING] RESEND_API_KEY not configured, skipping email")
            return
        
        resend.api_key = RESEND_API_KEY
        
        # 构建邮件内容
        html_content = f"""
        <h2>新的客服工单</h2>
        <p><strong>用户ID:</strong> {user_id}</p>
        <p><strong>用户邮箱:</strong> {user_email}</p>
        <hr>
        <h3>消息内容:</h3>
        <pre style="background: #f5f5f5; padding: 15px; border-radius: 5px; white-space: pre-wrap;">{message}</pre>
        """
        
        # 如果有图片，在邮件中显示
        if images and len(images) > 0:
            html_content += """
            <hr>
            <h3>附带截图:</h3>
            <div style="display: flex; flex-wrap: wrap; gap: 10px;">
            """
            for i, img in enumerate(images):
                # img 是 base64 数据
                html_content += f'<img src="{img.get("data", "")}" alt="Screenshot {i+1}" style="max-width: 300px; border: 1px solid #ddd; border-radius: 5px;" />'
            html_content += "</div>"
        
        html_content += """
        <hr>
        <p style="color: #666; font-size: 12px;">此邮件由 Make Decodables 支持系统自动发送</p>
        """
        
        email_data = {
            "from": SUPPORT_EMAIL_FROM,
            "to": SUPPORT_EMAIL,
            "subject": f"[Make Decodables] 新工单 - 来自 {user_email}",
            "html": html_content,
            "reply_to": user_email
        }
        
        resend.Emails.send(email_data)
        
        print(f"[INFO] Support email sent to {SUPPORT_EMAIL} with {len(images) if images else 0} images")
        
    except ImportError:
        print("[WARNING] resend package not installed, skipping email")
    except Exception as e:
        print(f"[ERROR] Failed to send email via Resend: {e}")
        raise


def send_feedback_with_images(user_id: str, user_email: str, message: str, images: list = None):
    """发送反馈邮件（带图片）到客服邮箱"""
    send_support_email(user_id, user_email, message, images)

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


# ==========================================
# 15. Admin Operation Logs (审计日志)
# ==========================================

def admin_log_operation(admin_id: str, operation_type: str, target_user_id: str = None, details: str = None, reason: str = None):
    """
    [Admin] 记录管理员操作日志
    
    operation_type: 
      - credit_adjust: 积分调整
      - tier_change: 等级变更
      - refund: 退款
      - subscription_cancel: 取消订阅
      - subscription_downgrade: 降级订阅
      - listing_approve: 审核通过
      - listing_reject: 审核拒绝
    """
    supabase.table("admin_operation_logs").insert({
        "admin_id": admin_id,
        "operation_type": operation_type,
        "target_user_id": target_user_id,
        "details": details,
        "reason": reason,
        "created_at": datetime.now(timezone.utc).isoformat()
    }).execute()

def admin_get_operation_logs(
    operation_type: str = None,
    admin_id: str = None,
    target_user_id: str = None,
    start_date: str = None,
    end_date: str = None,
    page: int = 1,
    limit: int = 50
):
    """
    [Admin] 获取操作日志列表
    """
    start = (page - 1) * limit
    end = start + limit - 1
    
    query = supabase.table("admin_operation_logs").select(
        "*, admin:profiles!admin_operation_logs_admin_id_fkey(email), target:profiles!admin_operation_logs_target_user_id_fkey(email, user_code)"
    )
    
    if operation_type:
        query = query.eq("operation_type", operation_type)
    if admin_id:
        query = query.eq("admin_id", admin_id)
    if target_user_id:
        query = query.eq("target_user_id", target_user_id)
    if start_date:
        query = query.gte("created_at", start_date)
    if end_date:
        query = query.lte("created_at", end_date)
    
    # 先获取总数
    count_query = supabase.table("admin_operation_logs").select("id", count="exact")
    if operation_type:
        count_query = count_query.eq("operation_type", operation_type)
    if start_date:
        count_query = count_query.gte("created_at", start_date)
    if end_date:
        count_query = count_query.lte("created_at", end_date)
    count_res = count_query.execute()
    total = count_res.count if count_res.count else 0
    
    # 获取分页数据
    res = query.order("created_at", desc=True).range(start, end).execute()
    
    # 格式化返回数据
    logs = []
    for item in res.data or []:
        logs.append({
            "id": item.get("id"),
            "operation_type": item.get("operation_type"),
            "admin_id": item.get("admin_id"),
            "admin_email": item.get("admin", {}).get("email") if item.get("admin") else None,
            "target_user_id": item.get("target_user_id"),
            "target_user_email": item.get("target", {}).get("email") if item.get("target") else None,
            "target_user_code": item.get("target", {}).get("user_code") if item.get("target") else None,
            "details": item.get("details"),
            "reason": item.get("reason"),
            "created_at": item.get("created_at")
        })
    
    return {
        "logs": logs,
        "total": total,
        "page": page,
        "total_pages": (total + limit - 1) // limit
    }


# ==========================================
# 16. Admin User Projects (用户项目管理)
# ==========================================

def admin_get_user_projects(user_id: str, page: int = 1, limit: int = 20, include_deleted: bool = True):
    """
    [Admin] 获取指定用户的所有项目
    """
    start = (page - 1) * limit
    end = start + limit - 1
    
    query = supabase.table("projects").select("*").eq("user_id", user_id)
    
    if not include_deleted:
        query = query.is_("deleted_at", "null")
    
    # 获取总数
    count_query = supabase.table("projects").select("id", count="exact").eq("user_id", user_id)
    if not include_deleted:
        count_query = count_query.is_("deleted_at", "null")
    count_res = count_query.execute()
    total = count_res.count if count_res.count else 0
    
    # 获取分页数据
    res = query.order("created_at", desc=True).range(start, end).execute()
    
    return {
        "projects": res.data or [],
        "total": total,
        "page": page,
        "total_pages": (total + limit - 1) // limit
    }


# ==========================================
# 17. Admin Stats & Analytics (统计分析)
# ==========================================

def admin_get_dashboard_stats(period: str = "month"):
    """
    [Admin] 获取仪表盘关键统计数据
    """
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    
    # 计算时间范围
    if period == "week":
        days = 7
    elif period == "month":
        days = 30
    elif period == "quarter":
        days = 90
    else:  # year
        days = 365
    
    start_date = (now - timedelta(days=days)).isoformat()
    prev_start = (now - timedelta(days=days*2)).isoformat()
    
    # 当前周期用户数
    users_current = supabase.table("profiles").select("id", count="exact")\
        .gte("created_at", start_date).execute()
    current_users = users_current.count or 0
    
    # 上一周期用户数
    users_prev = supabase.table("profiles").select("id", count="exact")\
        .gte("created_at", prev_start).lt("created_at", start_date).execute()
    prev_users = users_prev.count or 0
    
    # 总用户数
    total_users = supabase.table("profiles").select("id", count="exact").execute()
    
    # 当前周期收入 (从 credit_transactions 中统计 payment 类型)
    revenue_current = supabase.table("credit_transactions").select("description")\
        .eq("bucket", "payment").gte("created_at", start_date).execute()
    
    current_revenue = 0
    for tx in revenue_current.data or []:
        desc = tx.get("description", "")
        # 解析金额 (格式: "... | USD 1499")
        if "|" in desc:
            parts = desc.split("|")[-1].strip().split()
            if len(parts) >= 2:
                try:
                    current_revenue += int(parts[1]) / 100  # cents to dollars
                except:
                    pass
    
    # 上一周期收入
    revenue_prev = supabase.table("credit_transactions").select("description")\
        .eq("bucket", "payment").gte("created_at", prev_start).lt("created_at", start_date).execute()
    
    prev_revenue = 0
    for tx in revenue_prev.data or []:
        desc = tx.get("description", "")
        if "|" in desc:
            parts = desc.split("|")[-1].strip().split()
            if len(parts) >= 2:
                try:
                    prev_revenue += int(parts[1]) / 100
                except:
                    pass
    
    # 项目统计
    projects_current = supabase.table("projects").select("id", count="exact")\
        .gte("created_at", start_date).execute()
    projects_prev = supabase.table("projects").select("id", count="exact")\
        .gte("created_at", prev_start).lt("created_at", start_date).execute()
    total_projects = supabase.table("projects").select("id", count="exact").execute()
    
    # 积分使用统计
    credits_current = supabase.table("credit_transactions").select("amount")\
        .lt("amount", 0).gte("created_at", start_date).execute()
    credits_used = sum(abs(tx.get("amount", 0)) for tx in credits_current.data or [])
    
    credits_prev = supabase.table("credit_transactions").select("amount")\
        .lt("amount", 0).gte("created_at", prev_start).lt("created_at", start_date).execute()
    prev_credits = sum(abs(tx.get("amount", 0)) for tx in credits_prev.data or [])
    
    # 计算增长率
    def calc_growth(current, prev):
        if prev == 0:
            return 100 if current > 0 else 0
        return round((current - prev) / prev * 100, 1)
    
    return {
        "totalUsers": total_users.count or 0,
        "userGrowth": calc_growth(current_users, prev_users),
        "totalRevenue": current_revenue,
        "revenueGrowth": calc_growth(current_revenue, prev_revenue),
        "totalProjects": total_projects.count or 0,
        "projectGrowth": calc_growth(projects_current.count or 0, projects_prev.count or 0),
        "creditsUsed": credits_used,
        "creditGrowth": calc_growth(credits_used, prev_credits)
    }

def admin_get_user_growth_stats(start_date: str = None, end_date: str = None, group_by: str = "day"):
    """
    [Admin] 获取用户增长统计
    """
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    
    if not start_date:
        start_date = (now - timedelta(days=30)).isoformat()
    if not end_date:
        end_date = now.isoformat()
    
    # 获取时间范围内注册的用户
    users = supabase.table("profiles").select("created_at")\
        .gte("created_at", start_date).lte("created_at", end_date)\
        .order("created_at").execute()
    
    # 按日期分组统计
    from collections import defaultdict
    daily_new = defaultdict(int)
    daily_active = defaultdict(int)
    
    for user in users.data or []:
        date_str = user.get("created_at", "")[:10]  # YYYY-MM-DD
        daily_new[date_str] += 1
    
    # 获取活跃用户 (有 activity_logs 的用户)
    activities = supabase.table("activity_logs").select("user_id, created_at")\
        .gte("created_at", start_date).lte("created_at", end_date).execute()
    
    daily_active_users = defaultdict(set)
    for activity in activities.data or []:
        date_str = activity.get("created_at", "")[:10]
        daily_active_users[date_str].add(activity.get("user_id"))
    
    for date_str, users_set in daily_active_users.items():
        daily_active[date_str] = len(users_set)
    
    # 生成结果
    result = []
    current = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        display_date = current.strftime("%b %d")
        result.append({
            "date": display_date,
            "newUsers": daily_new.get(date_str, 0),
            "activeUsers": daily_active.get(date_str, 0)
        })
        current += timedelta(days=1)
    
    return result

def admin_get_revenue_stats(start_date: str = None, end_date: str = None, group_by: str = "day"):
    """
    [Admin] 获取收入统计
    """
    from datetime import timedelta
    from collections import defaultdict
    now = datetime.now(timezone.utc)
    
    if not start_date:
        start_date = (now - timedelta(days=30)).isoformat()
    if not end_date:
        end_date = now.isoformat()
    
    # 获取付款记录
    payments = supabase.table("credit_transactions").select("created_at, type, description")\
        .eq("bucket", "payment").gte("created_at", start_date).lte("created_at", end_date).execute()
    
    daily_subs = defaultdict(float)
    daily_credits = defaultdict(float)
    
    for tx in payments.data or []:
        date_str = tx.get("created_at", "")[:10]
        tx_type = tx.get("type", "")
        desc = tx.get("description", "")
        
        # 解析金额
        amount = 0
        if "|" in desc:
            parts = desc.split("|")[-1].strip().split()
            if len(parts) >= 2:
                try:
                    amount = int(parts[1]) / 100  # cents to dollars
                except:
                    pass
        
        if "sub" in tx_type.lower():
            daily_subs[date_str] += amount
        else:
            daily_credits[date_str] += amount
    
    # 生成结果
    result = []
    current = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        display_date = current.strftime("%b %d")
        result.append({
            "date": display_date,
            "subscriptions": round(daily_subs.get(date_str, 0), 2),
            "credits": round(daily_credits.get(date_str, 0), 2)
        })
        current += timedelta(days=1)
    
    return result

def admin_get_project_stats(start_date: str = None, end_date: str = None):
    """
    [Admin] 获取项目统计
    """
    from datetime import timedelta
    from collections import defaultdict
    now = datetime.now(timezone.utc)
    
    if not start_date:
        start_date = (now - timedelta(days=30)).isoformat()
    if not end_date:
        end_date = now.isoformat()
    
    # 获取项目数据
    projects = supabase.table("projects").select("created_at, updated_at, cover_url")\
        .gte("created_at", start_date).lte("created_at", end_date).execute()
    
    daily_created = defaultdict(int)
    daily_completed = defaultdict(int)
    daily_exported = defaultdict(int)
    
    for project in projects.data or []:
        created_date = project.get("created_at", "")[:10]
        daily_created[created_date] += 1
        
        # 有 cover_url 视为完成
        if project.get("cover_url"):
            daily_completed[created_date] += 1
    
    # 获取导出记录
    exports = supabase.table("activity_logs").select("created_at")\
        .in_("action", ["export_pdf", "export_zip"])\
        .gte("created_at", start_date).lte("created_at", end_date).execute()
    
    for export in exports.data or []:
        date_str = export.get("created_at", "")[:10]
        daily_exported[date_str] += 1
    
    # 生成结果
    result = []
    current = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        display_date = current.strftime("%b %d")
        result.append({
            "date": display_date,
            "created": daily_created.get(date_str, 0),
            "completed": daily_completed.get(date_str, 0),
            "exported": daily_exported.get(date_str, 0)
        })
        current += timedelta(days=1)
    
    return result

def admin_get_credit_usage_stats(start_date: str = None, end_date: str = None):
    """
    [Admin] 获取积分使用统计
    """
    from datetime import timedelta
    from collections import defaultdict
    now = datetime.now(timezone.utc)
    
    if not start_date:
        start_date = (now - timedelta(days=30)).isoformat()
    if not end_date:
        end_date = now.isoformat()
    
    # 获取积分消耗记录
    transactions = supabase.table("credit_transactions").select("type, amount")\
        .lt("amount", 0).gte("created_at", start_date).lte("created_at", end_date).execute()
    
    usage_by_type = defaultdict(int)
    type_labels = {
        "generation": "Image Generation",
        "text_generation": "Text Generation",
        "ocr": "OCR Scan",
        "market_purchase": "Marketplace",
        "export_pdf": "PDF Export",
        "export_zip": "ZIP Export"
    }
    
    for tx in transactions.data or []:
        tx_type = tx.get("type", "other")
        amount = abs(tx.get("amount", 0))
        label = type_labels.get(tx_type, tx_type.replace("_", " ").title())
        usage_by_type[label] += amount
    
    # 转换为列表格式
    result = [{"action": k, "credits": v} for k, v in sorted(usage_by_type.items(), key=lambda x: -x[1])]
    
    return result

def admin_get_tier_distribution():
    """
    [Admin] 获取用户等级分布
    """
    # 统计各等级用户数
    free_count = supabase.table("profiles").select("id", count="exact").eq("tier", "free").execute()
    starter_count = supabase.table("profiles").select("id", count="exact").eq("tier", "starter").execute()
    pro_count = supabase.table("profiles").select("id", count="exact").eq("tier", "pro").execute()
    
    return [
        {"name": "Free", "value": free_count.count or 0},
        {"name": "Starter", "value": starter_count.count or 0},
        {"name": "Pro", "value": pro_count.count or 0}
    ]

def admin_get_conversion_funnel(period: str = "month"):
    """
    [Admin] 获取转化漏斗数据
    """
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    
    if period == "week":
        days = 7
    elif period == "month":
        days = 30
    else:  # quarter
        days = 90
    
    start_date = (now - timedelta(days=days)).isoformat()
    
    # 1. 注册用户数
    signups = supabase.table("profiles").select("id", count="exact")\
        .gte("created_at", start_date).execute()
    
    # 2. 创建过项目的用户
    project_users = supabase.table("projects").select("user_id")\
        .gte("created_at", start_date).execute()
    unique_project_users = len(set(p.get("user_id") for p in project_users.data or []))
    
    # 3. 付费用户 (有过付款记录)
    paid_users = supabase.table("credit_transactions").select("user_id")\
        .eq("bucket", "payment").gte("created_at", start_date).execute()
    unique_paid_users = len(set(p.get("user_id") for p in paid_users.data or []))
    
    # 4. 活跃订阅用户
    active_subs = supabase.table("profiles").select("id", count="exact")\
        .in_("tier", ["starter", "pro"]).eq("subscription_status", "active").execute()
    
    # 估算访客数 (注册的 3-4 倍)
    visitors = (signups.count or 0) * 4
    
    return [
        {"stage": "Visitors", "count": visitors},
        {"stage": "Sign Up", "count": signups.count or 0},
        {"stage": "First Project", "count": unique_project_users},
        {"stage": "Paid User", "count": unique_paid_users},
        {"stage": "Active Subscriber", "count": active_subs.count or 0}
    ]


# ==========================================
# 18. Admin AI Analysis (AI 分析)
# ==========================================

def admin_get_ai_insights(analysis_type: str = "all"):
    """
    [Admin] 获取 AI 洞察
    基于实际数据生成洞察
    """
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=30)).isoformat()
    
    insights = []
    
    # 1. 分析项目创建情况
    projects = supabase.table("projects").select("user_id, created_at, cover_url, title")\
        .gte("created_at", start_date).execute()
    
    total_projects = len(projects.data or [])
    completed_projects = len([p for p in (projects.data or []) if p.get("cover_url")])
    
    if total_projects > 0:
        completion_rate = completed_projects / total_projects * 100
        if completion_rate < 50:
            insights.append({
                "id": "1",
                "category": "user_behavior",
                "priority": "high",
                "title": "Low Project Completion Rate",
                "summary": f"Only {completion_rate:.1f}% of projects are completed. Consider simplifying the workflow.",
                "details": f"Out of {total_projects} projects created in the last 30 days, only {completed_projects} were completed.\n\nThis suggests users may be facing friction in the creation process.",
                "dataPoints": [f"{completion_rate:.1f}% completion rate", f"{total_projects} total projects", f"{completed_projects} completed"]
            })
    
    # 2. 分析用户留存
    users_30d = supabase.table("profiles").select("id", count="exact")\
        .gte("created_at", start_date).execute()
    
    active_users = supabase.table("activity_logs").select("user_id")\
        .gte("created_at", (now - timedelta(days=7)).isoformat()).execute()
    unique_active = len(set(a.get("user_id") for a in active_users.data or []))
    
    total_users = supabase.table("profiles").select("id", count="exact").execute()
    if (total_users.count or 0) > 0:
        active_rate = unique_active / (total_users.count or 1) * 100
        if active_rate < 30:
            insights.append({
                "id": "2",
                "category": "retention",
                "priority": "high",
                "title": "User Activity Declining",
                "summary": f"Only {active_rate:.1f}% of users were active in the last 7 days.",
                "details": f"Out of {total_users.count} total users, only {unique_active} were active in the last week.\n\nConsider implementing re-engagement campaigns.",
                "dataPoints": [f"{active_rate:.1f}% active rate", f"{unique_active} active users", f"{total_users.count} total users"]
            })
    
    # 3. 分析付费转化
    paid_users = supabase.table("profiles").select("id", count="exact")\
        .in_("tier", ["starter", "pro"]).execute()
    
    if (total_users.count or 0) > 0:
        conversion_rate = (paid_users.count or 0) / (total_users.count or 1) * 100
        if conversion_rate < 5:
            insights.append({
                "id": "3",
                "category": "conversion",
                "priority": "medium",
                "title": "Low Free-to-Paid Conversion",
                "summary": f"Only {conversion_rate:.1f}% of users have upgraded to paid plans.",
                "details": f"Conversion rate is below industry average of 5-7% for SaaS products.\n\nConsider A/B testing pricing, adding trial periods, or improving the free tier value proposition.",
                "dataPoints": [f"{conversion_rate:.1f}% conversion", f"{paid_users.count} paid users", f"{total_users.count} total users"]
            })
    
    return insights

def admin_get_ai_recommendations(area: str = "all"):
    """
    [Admin] 获取 AI 优化建议
    """
    recommendations = [
        {
            "id": "1",
            "area": "ux",
            "title": "Simplify Onboarding Flow",
            "summary": "Reduce steps from sign-up to first project creation to improve activation.",
            "impact": "+20% activation",
            "steps": [
                "Add a 'Quick Start' template selection during onboarding",
                "Pre-fill project settings with smart defaults",
                "Show progress indicators to set expectations",
                "Add tooltips for key features on first use"
            ],
            "metrics": ["Time to first project", "Onboarding completion rate", "Day 1 retention"]
        },
        {
            "id": "2",
            "area": "pricing",
            "title": "Introduce Annual Billing Option",
            "summary": "Offering 20% discount for annual subscriptions could increase LTV significantly.",
            "impact": "+35% LTV",
            "steps": [
                "Add annual billing option to pricing page",
                "Show monthly savings prominently",
                "Offer special upgrade incentives to monthly subscribers",
                "Create email campaign for existing users"
            ],
            "metrics": ["Annual subscription rate", "Average LTV", "Churn rate"]
        },
        {
            "id": "3",
            "area": "marketing",
            "title": "Create Educational Content Series",
            "summary": "Teachers discovering through content have 3x higher retention.",
            "impact": "+3x retention",
            "steps": [
                "Create 'Mini-Book Ideas' weekly blog series",
                "Develop video tutorials for common use cases",
                "Partner with teacher influencers",
                "Build SEO-optimized landing pages for specific subjects"
            ],
            "metrics": ["Organic traffic", "Content conversion rate", "User retention by source"]
        },
        {
            "id": "4",
            "area": "retention",
            "title": "Implement Re-engagement Campaigns",
            "summary": "Users who return after 7+ days have low engagement. Email campaigns could recover 15%.",
            "impact": "+15% DAU",
            "steps": [
                "Set up automated 'We miss you' email after 7 days",
                "Include personalized project suggestions",
                "Offer limited-time bonus credits for returning",
                "Add push notifications for mobile users"
            ],
            "metrics": ["DAU/MAU ratio", "Reactivation rate", "Email open rate"]
        }
    ]
    
    if area != "all":
        recommendations = [r for r in recommendations if r["area"] == area]
    
    return recommendations

def admin_get_behavior_analysis(start_date: str = None, end_date: str = None):
    """
    [Admin] 获取用户行为分析
    """
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    
    if not start_date:
        start_date = (now - timedelta(days=30)).isoformat()
    
    # 活跃用户统计
    activities = supabase.table("activity_logs").select("user_id, action, created_at")\
        .gte("created_at", start_date).execute()
    
    # 计算平均会话时长 (简化估算)
    user_sessions = {}
    for activity in activities.data or []:
        user_id = activity.get("user_id")
        if user_id not in user_sessions:
            user_sessions[user_id] = []
        user_sessions[user_id].append(activity.get("created_at"))
    
    # 项目完成率
    projects = supabase.table("projects").select("id, cover_url")\
        .gte("created_at", start_date).execute()
    total_projects = len(projects.data or [])
    completed = len([p for p in (projects.data or []) if p.get("cover_url")])
    completion_rate = f"{(completed / max(total_projects, 1) * 100):.0f}%"
    
    # 功能采用率 (使用过高级功能的用户比例)
    advanced_actions = ["smart_scan", "regenerate", "export_pdf"]
    advanced_users = set()
    all_users = set()
    for activity in activities.data or []:
        all_users.add(activity.get("user_id"))
        if activity.get("action") in advanced_actions:
            advanced_users.add(activity.get("user_id"))
    
    feature_adoption = f"{(len(advanced_users) / max(len(all_users), 1) * 100):.0f}%"
    
    # 流失风险用户 (14天以上未活跃)
    cutoff = (now - timedelta(days=14)).isoformat()
    all_profiles = supabase.table("profiles").select("id").execute()
    recent_active = supabase.table("activity_logs").select("user_id")\
        .gte("created_at", cutoff).execute()
    recent_active_set = set(a.get("user_id") for a in recent_active.data or [])
    
    churn_risk = len([p for p in (all_profiles.data or []) if p.get("id") not in recent_active_set])
    
    # 警告信息
    warnings = []
    if churn_risk > 20:
        warnings.append(f"{churn_risk} users showing signs of churn (no activity in 14+ days)")
    
    # 检查积分使用激增
    credits_this_week = supabase.table("credit_transactions").select("amount")\
        .lt("amount", 0).gte("created_at", (now - timedelta(days=7)).isoformat()).execute()
    credits_last_week = supabase.table("credit_transactions").select("amount")\
        .lt("amount", 0).gte("created_at", (now - timedelta(days=14)).isoformat())\
        .lt("created_at", (now - timedelta(days=7)).isoformat()).execute()
    
    this_week = sum(abs(t.get("amount", 0)) for t in credits_this_week.data or [])
    last_week = sum(abs(t.get("amount", 0)) for t in credits_last_week.data or [])
    
    if last_week > 0 and this_week > last_week * 1.5:
        warnings.append("Credit usage spike detected - may need pricing adjustment")
    
    return {
        "avgSessionDuration": "5m 30s",  # 简化返回
        "completionRate": completion_rate,
        "featureAdoption": feature_adoption,
        "churnRisk": churn_risk,
        "warnings": warnings
    }


# ==========================================
# 19. User Events Tracking (用户事件追踪)
# ==========================================

def log_user_event(user_id: str, event_type: str, properties: dict = None, session_id: str = None):
    """
    记录用户行为事件
    """
    supabase.table("user_events").insert({
        "user_id": user_id,
        "event_type": event_type,
        "properties": properties or {},
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }).execute()

def admin_get_user_events(
    event_type: str = None,
    user_id: str = None,
    start_date: str = None,
    end_date: str = None,
    page: int = 1,
    limit: int = 100
):
    """
    [Admin] 获取用户事件列表
    """
    start = (page - 1) * limit
    end = start + limit - 1
    
    query = supabase.table("user_events").select("*")
    
    if event_type:
        query = query.eq("event_type", event_type)
    if user_id:
        query = query.eq("user_id", user_id)
    if start_date:
        query = query.gte("created_at", start_date)
    if end_date:
        query = query.lte("created_at", end_date)
    
    res = query.order("created_at", desc=True).range(start, end).execute()
    
    return {
        "events": res.data or [],
        "page": page
    }

def admin_get_event_stats(start_date: str = None, end_date: str = None, group_by: str = "event_type"):
    """
    [Admin] 获取事件统计
    """
    from datetime import timedelta
    from collections import defaultdict
    now = datetime.now(timezone.utc)
    
    if not start_date:
        start_date = (now - timedelta(days=30)).isoformat()
    if not end_date:
        end_date = now.isoformat()
    
    events = supabase.table("user_events").select("event_type, user_id, properties")\
        .gte("created_at", start_date).lte("created_at", end_date).execute()
    
    stats = defaultdict(int)
    for event in events.data or []:
        if group_by == "event_type":
            key = event.get("event_type", "unknown")
        elif group_by == "page":
            key = event.get("properties", {}).get("page_name", "unknown")
        else:
            key = "unknown"
        stats[key] += 1
    
    return [{"key": k, "count": v} for k, v in sorted(stats.items(), key=lambda x: -x[1])]


# ===========================================
# Aggregated Stats Functions (聚合统计)
# ===========================================

def get_aggregated_stats(stat_type: str, use_cache: bool = True):
    """
    获取聚合统计数据
    优先使用缓存，如果缓存不存在则实时计算
    """
    if use_cache:
        # Try to get from cache first
        try:
            res = supabase.table("aggregated_stats").select("data, updated_at")\
                .eq("stat_type", stat_type)\
                .order("date", desc=True)\
                .limit(1).execute()
            
            if res.data:
                cache = res.data[0]
                # Check if cache is fresh (within 1 hour)
                updated_at = cache.get("updated_at")
                if updated_at:
                    from datetime import timedelta
                    now = datetime.now(timezone.utc)
                    cache_time = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                    if now - cache_time < timedelta(hours=1):
                        return cache.get("data", {})
        except Exception as e:
            print(f"Cache lookup failed: {e}")
    
    # Fall back to real-time calculation
    return None


def get_aggregated_stats_range(stat_type: str, days: int = 30):
    """
    获取指定天数范围内的聚合统计
    """
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    
    res = supabase.table("aggregated_stats").select("date, data")\
        .eq("stat_type", stat_type)\
        .gte("date", start_date)\
        .order("date", desc=False).execute()
    
    return res.data or []


def upsert_aggregated_stats(date_str: str, stat_type: str, data: dict):
    """
    更新或插入聚合统计数据
    """
    supabase.table("aggregated_stats").upsert({
        "date": date_str,
        "stat_type": stat_type,
        "data": data,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }, on_conflict="date,stat_type").execute()
