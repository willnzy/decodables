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
# 1. 用户档案 (Profiles)
# ==========================================

def get_user_profile(user_id: str):
    """获取用户信息"""
    res = supabase.table("profiles").select("*").eq("id", user_id).execute()
    return res.data[0] if res.data else None

def create_user_profile(user_id: str, email: str, username: str, avatar_url: str):
    """创建新用户并赠送初始积分"""
    data = {
        "id": user_id,
        "email": email,
        "username": username,
        "avatar_url": avatar_url,
        "credits": 100, # 注册赠送
        "tier": "free"
    }
    supabase.table("profiles").insert(data).execute()
    # 记录赠送流水
    log_credit_transaction(user_id, 100, 100, "signup_bonus", "Welcome Bonus")

def update_subscription_tier(user_id: str, tier: str, stripe_customer_id: str = None):
    """更新订阅等级"""
    data = {"tier": tier}
    if stripe_customer_id:
        data["stripe_customer_id"] = stripe_customer_id
    supabase.table("profiles").update(data).eq("id", user_id).execute()

# ==========================================
# 2. 积分与交易 (Credits & Transactions)
# ==========================================

def log_credit_transaction(user_id: str, amount: int, balance_after: int, type: str, description: str):
    """[内部调用] 记录流水"""
    supabase.table("credit_transactions").insert({
        "user_id": user_id,
        "amount": amount,
        "balance_after": balance_after,
        "type": type,
        "description": description,
        "created_at": datetime.now().isoformat()
    }).execute()

def deduct_credits_atomic(user_id: str, amount: int, type: str, description: str):
    """[核心] 乐观锁原子扣费"""
    profile = get_user_profile(user_id)
    if not profile:
        raise Exception("User not found")
    
    current_credits = profile.get("credits", 0)
    
    if current_credits < amount:
        raise Exception("CREDITS_INSUFFICIENT")
        
    new_credits = current_credits - amount
    
    # 带条件更新 (Where credits = old_credits)
    res = supabase.table("profiles").update({"credits": new_credits})\
        .eq("id", user_id).eq("credits", current_credits).execute()
        
    if not res.data:
        raise Exception("Concurrency conflict, please retry")
        
    log_credit_transaction(user_id, -amount, new_credits, type, description)
    return True

def add_credits(user_id: str, amount: int, description: str, type="purchase"):
    """增加积分"""
    profile = get_user_profile(user_id)
    if not profile: return
    
    current = profile.get("credits", 0)
    new_credits = current + amount
    
    supabase.table("profiles").update({"credits": new_credits}).eq("id", user_id).execute()
    log_credit_transaction(user_id, amount, new_credits, type, description)

def get_credit_history(user_id: str, page: int = 1, limit: int = 20):
    """[补丁功能] 获取积分历史"""
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
    """获取项目列表"""
    start = (page - 1) * limit
    end = start + limit - 1
    res = supabase.table("projects").select("id, title, thumbnail_url, updated_at")\
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

def save_project(project_id: str, user_id: str, canvas_data: dict, thumbnail_url: str = None):
    """保存项目"""
    data = {
        "canvas_data": canvas_data,
        "updated_at": datetime.now().isoformat()
    }
    if thumbnail_url:
        data["thumbnail_url"] = thumbnail_url
    supabase.table("projects").update(data).eq("id", project_id).eq("user_id", user_id).execute()

def soft_delete_project(project_id: str, user_id: str):
    """[补丁功能] 软删除项目"""
    res = supabase.table("projects").update({"is_deleted": True})\
        .eq("id", project_id).eq("user_id", user_id).execute()
    if not res.data:
        raise Exception("Project not found or permission denied")
    return True

def update_project_hash(project_id: str, new_hash: str):
    """[漏掉的函数] 仅更新 Hash 值"""
    # 这里的 user_id 校验通常由上层逻辑保证，或者也可以加进去
    supabase.table("projects").update({"last_downloaded_hash": new_hash})\
        .eq("id", project_id).execute()

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

def get_system_resources(resource_type: str = "sticker", is_pro: bool = False):
    """获取系统公共资源 (贴纸)"""
    query = supabase.table("system_resources").select("*").eq("type", resource_type)
    if not is_pro:
        # 非 Pro 用户只返回免费资源
        query = query.eq("is_pro_only", False)
    res = query.execute()
    return res.data

# ==========================================
# 5. 运营与后台 (Admin & Ops)
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

# [新增] Admin 聚合查询 (替换 app.py 中的直接调用)
def get_full_user_audit(user_id: str):
    """
    [Admin] 获取用户全方位视图：档案、流水、日志、工单
    """
    # 1. 档案
    profile = get_user_profile(user_id)
    
    # 2. 积分流水
    txs = supabase.table("credit_transactions").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data
    
    # 3. 行为日志
    logs = supabase.table("activity_logs").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(50).execute().data
    
    # 4. 工单记录
    tickets = supabase.table("support_tickets").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data
    
    return {
        "profile": profile,
        "transactions": txs,
        "logs": logs,
        "tickets": tickets
    }