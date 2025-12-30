"""
迁移脚本：为现有用户生成 user_code

User Code 格式: YYYYMMDDHHMMSS + 毫秒(3位) + 用户序号(6位)
例如: 20251230143025123000001

运行方式:
python scripts/migrate_user_codes.py
"""
import os
import sys
from datetime import datetime

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client

# 初始化 Supabase 客户端
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_KEY environment variables required")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def generate_user_code_for_existing_user(user_index: int, created_at: str) -> str:
    """
    为现有用户生成 user_code
    使用用户的 created_at 时间作为时间戳部分
    
    时间统一转换为 UTC-0
    序号补0到7位数
    """
    from datetime import timezone
    
    try:
        # 解析 created_at 时间
        if 'T' in created_at:
            # ISO 格式: 2024-01-15T10:30:45.123456+00:00
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(created_at)
        
        # 确保时间是 UTC
        if dt.tzinfo is None:
            # 如果没有时区信息，假设是 UTC
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            # 转换为 UTC
            dt = dt.astimezone(timezone.utc)
        
        # 生成时间戳部分 (精确到毫秒, UTC 时间)
        timestamp_part = dt.strftime("%Y%m%d%H%M%S") + f"{dt.microsecond // 1000:03d}"
        
        # 序号部分 (7位, 补0)
        sequence_part = f"{user_index:07d}"
        
        return f"{timestamp_part}{sequence_part}"
    except Exception as e:
        print(f"  ⚠️ Error parsing date '{created_at}': {e}")
        # 使用当前 UTC 时间作为 fallback
        now_utc = datetime.now(timezone.utc)
        timestamp_part = now_utc.strftime("%Y%m%d%H%M%S") + f"{now_utc.microsecond // 1000:03d}"
        sequence_part = f"{user_index:07d}"
        return f"{timestamp_part}{sequence_part}"


def migrate_user_codes():
    """为所有没有 user_code 的用户生成 user_code"""
    
    print("🔄 开始迁移 user_code...")
    print()
    
    # 获取所有没有 user_code 的用户，按 created_at 排序
    result = supabase.table("profiles")\
        .select("id, email, created_at, user_code")\
        .is_("user_code", "null")\
        .order("created_at")\
        .execute()
    
    users_without_code = result.data
    
    if not users_without_code:
        print("✅ 所有用户都已有 user_code，无需迁移")
        return
    
    print(f"📊 发现 {len(users_without_code)} 个用户需要生成 user_code")
    print()
    
    # 获取已有 user_code 的用户数量（作为起始序号）
    existing_count_result = supabase.table("profiles")\
        .select("id", count="exact")\
        .not_.is_("user_code", "null")\
        .execute()
    
    start_index = existing_count_result.count or 0
    
    # 为每个用户生成 user_code
    success_count = 0
    error_count = 0
    
    for i, user in enumerate(users_without_code):
        user_index = start_index + i + 1
        user_code = generate_user_code_for_existing_user(user_index, user['created_at'])
        
        try:
            supabase.table("profiles")\
                .update({"user_code": user_code})\
                .eq("id", user['id'])\
                .execute()
            
            print(f"  ✅ [{user_index}] {user['email'][:30]}... -> {user_code}")
            success_count += 1
        except Exception as e:
            print(f"  ❌ [{user_index}] {user['email'][:30]}... -> Error: {e}")
            error_count += 1
    
    print()
    print("=" * 50)
    print(f"✅ 成功: {success_count}")
    print(f"❌ 失败: {error_count}")
    print("=" * 50)


if __name__ == "__main__":
    migrate_user_codes()

