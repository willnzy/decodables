#!/usr/bin/env python3
"""


"""

import sys
import os

# 
sys.path.insert(0, os.path.dirname(__file__))

try:
    from db_service import supabase, count_user_projects
    
    def main():
        if len(sys.argv) < 2:
            print(": python query_user_projects_simple.py <username_or_email>")
            print("\n:")
            print("  python query_user_projects_simple.py user@example.com")
            print("  python query_user_projects_simple.py username123")
            print("\n:")
            print("  python query_user_projects_simple.py --all")
            sys.exit(1)
        
        identifier = sys.argv[1]
        
        if identifier == "--all":
            # 
            print("🔍 ...\n")
            res = supabase.table("profiles").select("id, username, email, tier").execute()
            
            if not res.data:
                print("❌ ")
                return
            
            results = []
            for user in res.data:
                user_id = user['id']
                count = count_user_projects(user_id)
                results.append({
                    'user': user,
                    'count': count
                })
            
            # 
            results.sort(key=lambda x: x['count'], reverse=True)
            
            print(f"📊  {len(results)} :\n")
            print(f"{'':<20} {'':<30} {'Tier':<10} {'':<10}")
            print("-" * 80)
            
            for item in results:
                user = item['user']
                count = item['count']
                username = user.get('username', 'N/A')
                email = user.get('email', 'N/A')
                tier = user.get('tier', 'N/A')
                print(f"{username:<20} {email:<30} {tier:<10} {count:<10}")
        else:
            # 
            print(f"🔍 : {identifier}")
            
            # 
            res = supabase.table("profiles").select("id, username, email, tier").eq("username", identifier).execute()
            if not res.data or len(res.data) == 0:
                # 
                res = supabase.table("profiles").select("id, username, email, tier").eq("email", identifier).execute()
            
            if not res.data or len(res.data) == 0:
                print(f"❌ : {identifier}")
                sys.exit(1)
            
            user = res.data[0]
            user_id = user['id']
            
            print(f"\n✅ :")
            print(f"   - ID: {user_id}")
            print(f"   - : {user.get('username', 'N/A')}")
            print(f"   - : {user.get('email', 'N/A')}")
            print(f"   - Tier: {user.get('tier', 'N/A')}")
            
            # 
            print(f"\n📊 ...")
            count = count_user_projects(user_id)
            
            print(f"\n✅ : {count}")
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"❌ : {e}")
    print("\n:")
    print("1. : pip install -r requirements.txt")
    print("2. （.env ）")
    print("3.  decodables ")
    sys.exit(1)
except Exception as e:
    print(f"❌ : {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

