# db_service.py
import os
from supabase import create_client, Client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def get_user_credits(user_id: str):
    """获取用户积分"""
    response = supabase.table("profiles").select("credits").eq("id", user_id).execute()
    if response.data:
        return response.data[0]['credits']
    # 如果用户不存在，可能需要初始化（视 Clerk webhook 设置而定）
    return 0

def init_project(user_id: str, title: str):
    """创建新项目"""
    data = {
        "user_id": user_id,
        "title": title,
        "canvas_data": {} # 初始为空
    }
    res = supabase.table("projects").insert(data).execute()
    return res.data[0]

def save_project_state(project_id: str, canvas_json: dict):
    """保存画布状态 (Fabric.js JSON)"""
    res = supabase.table("projects").update({
        "canvas_data": canvas_json,
        "updated_at": "now()"
    }).eq("id", project_id).execute()
    return res.data

def deduct_credits(user_id: str, amount: int):
    """扣除积分 (需配合事务或存储过程更安全，这里演示逻辑)"""
    current = get_user_credits(user_id)
    if current < amount:
        raise Exception("Insufficient credits")
    
    new_balance = current - amount
    supabase.table("profiles").update({"credits": new_balance}).eq("id", user_id).execute()
    return new_balance