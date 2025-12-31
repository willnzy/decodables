#!/usr/bin/env python3
"""

: python check_user_projects.py <username_or_email>
"""

import sys
import os
from db_service import supabase, count_user_projects

def find_user_by_username_or_email(identifier: str):
    """"""
    # 
    res = supabase.table("profiles").select("id, username, email").eq("username", identifier).execute()
    if res.data and len(res.data) > 0:
        return res.data[0]
    
    # 
    res = supabase.table("profiles").select("id, username, email").eq("email", identifier).execute()
    if res.data and len(res.data) > 0:
        return res.data[0]
    
    # 
    res = supabase.table("profiles").select("id, username, email").ilike("email", f"%{identifier}%").execute()
    if res.data and len(res.data) > 0:
        return res.data[0]
    
    return None

def get_user_project_count(user_id: str):
    """"""
    try:
        count = count_user_projects(user_id)
        return count
    except Exception as e:
        print(f"❌ : {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print(": python check_user_projects.py <username_or_email>")
        print(": python check_user_projects.py user@example.com")
        print(": python check_user_projects.py username123")
        sys.exit(1)
    
    identifier = sys.argv[1]
    print(f"🔍 : {identifier}")
    
    # 
    user = find_user_by_username_or_email(identifier)
    if not user:
        print(f"❌ : {identifier}")
        sys.exit(1)
    
    print(f"✅ :")
    print(f"   - ID: {user['id']}")
    print(f"   - : {user.get('username', 'N/A')}")
    print(f"   - : {user.get('email', 'N/A')}")
    print()
    
    # 
    print(f"📊 ...")
    count = get_user_project_count(user['id'])
    
    if count is not None:
        print(f"✅ : {count}")
        
        # （）
        if len(sys.argv) > 2 and sys.argv[2] == "--details":
            from db_service import get_user_projects
            projects = get_user_projects(user['id'], page=1, limit=1000)
            if projects:
                print(f"\n📋  ( {len(projects)} ):")
                for i, project in enumerate(projects, 1):
                    print(f"   {i}. {project.get('title', 'Untitled')} (ID: {project['id']})")
                    print(f"      : {project.get('created_at', 'N/A')}")
                    print(f"      : {project.get('updated_at', 'N/A')}")
    else:
        print(f"❌ ")
        sys.exit(1)

if __name__ == "__main__":
    main()

