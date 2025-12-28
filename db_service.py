import os
from supabase import create_client, Client
from datetime import datetime
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
    - 不结转：直接重置为当月额度
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
    
    permanent = profile.get("credits_permanent", 0)
    
    # 重置月度积分（不结转）
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
        balance_permanent_after=permanent,
        type="sub_grant",
        description=f"Monthly {tier.capitalize()} Credits (Reset)"
    )
    
    return True

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
    res = supabase.table("projects").select("id, title, thumbnail_url, canvas_data, updated_at")\
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
    limit: int = 20
):
    """获取市场商品列表"""
    start = (page - 1) * limit
    end = start + limit - 1
    
    query = supabase.table("marketplace_listings").select("*, profiles(username, avatar_url)")\
        .eq("is_public", True).eq("is_deleted", False)
    
    if resource_type:
        query = query.eq("resource_type", resource_type)
    
    if featured:
        query = query.order("sales_count", desc=True)
    else:
        query = query.order("created_at", desc=True)
    
    res = query.range(start, end).execute()
    return res.data

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
    allowed_tiers: list = None
):
    """上架商品"""
    data = {
        "seller_id": seller_id,
        "title": title,
        "description": description,
        "thumbnail_url": thumbnail_url,
        "resource_url": resource_url,
        "resource_type": resource_type,
        "price_credits": price_credits,
        "allowed_tiers": allowed_tiers or ["free", "starter", "pro"],
        "is_public": True,
        "sales_count": 0
    }
    res = supabase.table("marketplace_listings").insert(data).execute()
    return res.data[0]

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
    执行购买逻辑
    
    规则:
    1) 校验 listing.allowed_tiers 与用户权限
    2) 去重：若已购买则直接返回成功
    3) 事务扣费：买家扣 price（优先 monthly）
    4) 卖家入账：price × 90%（计入 permanent）
    5) 平台抽成 10%
    6) 写入 user_purchases
    
    Returns: { success: bool, message: str }
    """
    # 1. 获取商品信息
    listing_res = supabase.table("marketplace_listings").select("*")\
        .eq("id", listing_id).eq("is_public", True).eq("is_deleted", False).single().execute()
    
    if not listing_res.data:
        return {"success": False, "message": "Listing not found"}
    
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
    """获取卖家统计数据"""
    # 获取所有商品
    listings = supabase.table("marketplace_listings").select("id, sales_count, price_credits")\
        .eq("seller_id", seller_id).eq("is_deleted", False).execute().data
    
    total_sales = sum(l.get("sales_count", 0) for l in listings)
    
    # 计算总收入（90% 分成）
    total_earned = 0
    for listing in listings:
        total_earned += int(listing.get("price_credits", 0) * listing.get("sales_count", 0) * 0.9)
    
    return {
        "total_listings": len(listings),
        "total_sales": total_sales,
        "total_earned_credits": total_earned
    }

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
