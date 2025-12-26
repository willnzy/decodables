import os
from supabase import create_client, Client
from datetime import datetime
import uuid

# 初始化 Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# --- 用户相关 ---

def get_user_profile(user_id: str):
    """获取用户信息"""
    res = supabase.table("profiles").select("*").eq("id", user_id).execute()
    return res.data[0] if res.data else None

def create_user_profile(user_id: str, email: str, username: str, avatar_url: str):
    """创建新用户"""
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
    """更新会员等级"""
    data = {"tier": tier}
    if stripe_customer_id:
        data["stripe_customer_id"] = stripe_customer_id
    supabase.table("profiles").update(data).eq("id", user_id).execute()

# --- 积分与交易 (核心) ---

def log_credit_transaction(user_id: str, amount: int, balance_after: int, type: str, description: str):
    """记录积分流水"""
    supabase.table("credit_transactions").insert({
        "user_id": user_id,
        "amount": amount,
        "balance_after": balance_after,
        "type": type,
        "description": description,
        "created_at": datetime.now().isoformat()
    }).execute()

def deduct_credits_atomic(user_id: str, amount: int, type: str, description: str):
    """
    [原子扣费] 
    注意: 严格的行级锁需要 Postgres Function (RPC)。
    此处为 Python 侧模拟乐观锁逻辑，生产环境建议在 Supabase 创建 RPC 函数。
    """
    # 1. 获取当前积分
    profile = get_user_profile(user_id)
    if not profile:
        raise Exception("User not found")
    
    current_credits = profile.get("credits", 0)
    
    # 2. 检查余额
    if current_credits < amount:
        raise Exception("CREDITS_INSUFFICIENT")
        
    # 3. 计算新余额
    new_credits = current_credits - amount
    
    # 4. 执行更新 (带条件更新以防止并发冲突)
    # update profiles set credits = new where id = uid and credits = old
    res = supabase.table("profiles").update({"credits": new_credits})\
        .eq("id", user_id).eq("credits", current_credits).execute()
        
    if not res.data:
        raise Exception("Concurrency conflict, please retry")
        
    # 5. 记流水
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

# --- 项目与素材 ---

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

def create_project(user_id: str):
    """创建空项目"""
    data = {
        "user_id": user_id,
        "title": "My Magic Story",
        "canvas_data": {}, # 初始为空 JSON
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

def save_asset(user_id: str, url: str, type: str, project_id: str = None, prompt: str = None):
    """保存素材到库"""
    data = {
        "user_id": user_id,
        "url": url,
        "type": type,
        "project_id": project_id,
        "prompt": prompt
    }
    supabase.table("assets").insert(data).execute()

def get_assets(user_id: str, project_id: str = None):
    """获取素材"""
    query = supabase.table("assets").select("*").eq("user_id", user_id).eq("is_deleted", False)
    if project_id:
        query = query.eq("project_id", project_id)
    
    res = query.order("created_at", desc=True).execute()
    return res.data

# --- 运营与日志 ---

def log_activity(user_id: str, action: str, metadata: dict = None):
    """记录用户行为"""
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
    """[Admin] 搜索用户"""
    # 简单实现：匹配 ID 或 Email
    res = supabase.table("profiles").select("*").or_(f"id.eq.{query},email.eq.{query}").execute()
    return res.data