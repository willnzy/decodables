# db_service.py
import os
from supabase import create_client, Client
from datetime import datetime

# 初始化 Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

def get_user_profile(user_id: str):
    """获取用户信息（含积分）"""
    res = supabase.table("profiles").select("*").eq("id", user_id).execute()
    if res.data:
        return res.data[0]
    return None

def add_credits(user_id: str, amount: int, description: str, type="purchase"):
    """
    核心功能：给用户加积分，并记录流水
    """
    if not supabase: return None

    # 1. 获取当前积分
    profile = get_user_profile(user_id)
    if not profile:
        # 如果用户不存在（比如刚注册），先创建
        supabase.table("profiles").insert({"id": user_id, "credits": 50}).execute() # 默认送50
        current_credits = 50
    else:
        current_credits = profile.get("credits", 0)

    # 2. 更新总积分
    new_credits = current_credits + amount
    supabase.table("profiles").update({"credits": new_credits}).eq("id", user_id).execute()

    # 3. 写入交易记录 (Log)
    supabase.table("credit_transactions").insert({
        "user_id": user_id,
        "amount": amount,
        "type": type,
        "description": description,
        "created_at": datetime.now().isoformat()
    }).execute()
    
    print(f"💰 [Credits] User {user_id} +{amount} | Total: {new_credits}")
    return new_credits

def update_subscription_tier(user_id: str, tier: str, stripe_customer_id: str = None):
    """更新会员等级"""
    data = {"tier": tier}
    if stripe_customer_id:
        data["stripe_customer_id"] = stripe_customer_id
    
    supabase.table("profiles").update(data).eq("id", user_id).execute()