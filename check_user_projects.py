#!/usr/bin/env python3
"""
查询用户项目数量的工具脚本
用法: python check_user_projects.py <username_or_email>
"""

import sys
import os
from db_service import supabase, count_user_projects

def find_user_by_username_or_email(identifier: str):
    """通过用户名或邮箱查找用户"""
    # 先尝试通过用户名查找
    res = supabase.table("profiles").select("id, username, email").eq("username", identifier).execute()
    if res.data and len(res.data) > 0:
        return res.data[0]
    
    # 再尝试通过邮箱查找
    res = supabase.table("profiles").select("id, username, email").eq("email", identifier).execute()
    if res.data and len(res.data) > 0:
        return res.data[0]
    
    # 尝试部分匹配邮箱
    res = supabase.table("profiles").select("id, username, email").ilike("email", f"%{identifier}%").execute()
    if res.data and len(res.data) > 0:
        return res.data[0]
    
    return None

def get_user_project_count(user_id: str):
    """获取用户项目总数"""
    try:
        count = count_user_projects(user_id)
        return count
    except Exception as e:
        print(f"❌ 查询项目数量时出错: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("用法: python check_user_projects.py <username_or_email>")
        print("示例: python check_user_projects.py user@example.com")
        print("示例: python check_user_projects.py username123")
        sys.exit(1)
    
    identifier = sys.argv[1]
    print(f"🔍 正在查找用户: {identifier}")
    
    # 查找用户
    user = find_user_by_username_or_email(identifier)
    if not user:
        print(f"❌ 未找到用户: {identifier}")
        sys.exit(1)
    
    print(f"✅ 找到用户:")
    print(f"   - ID: {user['id']}")
    print(f"   - 用户名: {user.get('username', 'N/A')}")
    print(f"   - 邮箱: {user.get('email', 'N/A')}")
    print()
    
    # 查询项目数量
    print(f"📊 正在查询项目数量...")
    count = get_user_project_count(user['id'])
    
    if count is not None:
        print(f"✅ 项目总数: {count}")
        
        # 查询项目详情（可选）
        if len(sys.argv) > 2 and sys.argv[2] == "--details":
            from db_service import get_user_projects
            projects = get_user_projects(user['id'], page=1, limit=1000)
            if projects:
                print(f"\n📋 项目列表 (共 {len(projects)} 个):")
                for i, project in enumerate(projects, 1):
                    print(f"   {i}. {project.get('title', 'Untitled')} (ID: {project['id']})")
                    print(f"      创建时间: {project.get('created_at', 'N/A')}")
                    print(f"      更新时间: {project.get('updated_at', 'N/A')}")
    else:
        print(f"❌ 无法获取项目数量")
        sys.exit(1)

if __name__ == "__main__":
    main()

