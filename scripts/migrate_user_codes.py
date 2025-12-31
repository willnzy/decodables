"""
： user_code

User Code : YYYYMMDDHHMMSS + (3) + (6)
: 20251230143025123000001

:
python scripts/migrate_user_codes.py
"""
import os
import sys
from datetime import datetime

#  path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client

#  Supabase 
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_KEY environment variables required")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def generate_user_code_for_existing_user(user_index: int, created_at: str) -> str:
    """
     user_code
     created_at 
    
     UTC-0
    07
    """
    from datetime import timezone
    
    try:
        #  created_at 
        if 'T' in created_at:
            # ISO : 2024-01-15T10:30:45.123456+00:00
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(created_at)
        
        #  UTC
        if dt.tzinfo is None:
            # ， UTC
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            #  UTC
            dt = dt.astimezone(timezone.utc)
        
        #  (, UTC )
        timestamp_part = dt.strftime("%Y%m%d%H%M%S") + f"{dt.microsecond // 1000:03d}"
        
        #  (7, 0)
        sequence_part = f"{user_index:07d}"
        
        return f"{timestamp_part}{sequence_part}"
    except Exception as e:
        print(f"  ⚠️ Error parsing date '{created_at}': {e}")
        #  UTC  fallback
        now_utc = datetime.now(timezone.utc)
        timestamp_part = now_utc.strftime("%Y%m%d%H%M%S") + f"{now_utc.microsecond // 1000:03d}"
        sequence_part = f"{user_index:07d}"
        return f"{timestamp_part}{sequence_part}"


def migrate_user_codes():
    """ user_code  user_code"""
    
    print("🔄  user_code...")
    print()
    
    #  user_code ， created_at 
    result = supabase.table("profiles")\
        .select("id, email, created_at, user_code")\
        .is_("user_code", "null")\
        .order("created_at")\
        .execute()
    
    users_without_code = result.data
    
    if not users_without_code:
        print("✅  user_code，")
        return
    
    print(f"📊  {len(users_without_code)}  user_code")
    print()
    
    #  user_code （）
    existing_count_result = supabase.table("profiles")\
        .select("id", count="exact")\
        .not_.is_("user_code", "null")\
        .execute()
    
    start_index = existing_count_result.count or 0
    
    #  user_code
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
    print(f"✅ : {success_count}")
    print(f"❌ : {error_count}")
    print("=" * 50)


if __name__ == "__main__":
    migrate_user_codes()

