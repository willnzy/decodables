#!/usr/bin/env python3
"""
简单的查询用户项目数量脚本
需要先设置环境变量或激活虚拟环境
"""

import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

try:
    from db_service import supabase, count_user_projects
    
    def main():
        if len(sys.argv) < 2:
            print("用法: python query_user_projects_simple.py <username_or_email>")
            print("\n示例:")
            print("  python query_user_projects_simple.py user@example.com")
            print("  python query_user_projects_simple.py username123")
            print("\n或者查看所有用户的项目数量:")
            print("  python query_user_projects_simple.py --all")
            sys.exit(1)
        
        identifier = sys.argv[1]
        
        if identifier == "--all":
            # 查询所有用户的项目数量
            print("🔍 正在查询所有用户的项目数量...\n")
            res = supabase.table("profiles").select("id, username, email, tier").execute()
            
            if not res.data:
                print("❌ 未找到任何用户")
                return
            
            results = []
            for user in res.data:
                user_id = user['id']
                count = count_user_projects(user_id)
                results.append({
                    'user': user,
                    'count': count
                })
            
            # 按项目数量排序
            results.sort(key=lambda x: x['count'], reverse=True)
            
            print(f"📊 找到 {len(results)} 个用户:\n")
            print(f"{'用户名':<20} {'邮箱':<30} {'Tier':<10} {'项目数量':<10}")
            print("-" * 80)
            
            for item in results:
                user = item['user']
                count = item['count']
                username = user.get('username', 'N/A')
                email = user.get('email', 'N/A')
                tier = user.get('tier', 'N/A')
                print(f"{username:<20} {email:<30} {tier:<10} {count:<10}")
        else:
            # 查找单个用户
            print(f"🔍 正在查找用户: {identifier}")
            
            # 先尝试通过用户名查找
            res = supabase.table("profiles").select("id, username, email, tier").eq("username", identifier).execute()
            if not res.data or len(res.data) == 0:
                # 再尝试通过邮箱查找
                res = supabase.table("profiles").select("id, username, email, tier").eq("email", identifier).execute()
            
            if not res.data or len(res.data) == 0:
                print(f"❌ 未找到用户: {identifier}")
                sys.exit(1)
            
            user = res.data[0]
            user_id = user['id']
            
            print(f"\n✅ 找到用户:")
            print(f"   - ID: {user_id}")
            print(f"   - 用户名: {user.get('username', 'N/A')}")
            print(f"   - 邮箱: {user.get('email', 'N/A')}")
            print(f"   - Tier: {user.get('tier', 'N/A')}")
            
            # 查询项目数量
            print(f"\n📊 正在查询项目数量...")
            count = count_user_projects(user_id)
            
            print(f"\n✅ 项目总数: {count}")
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("\n请确保:")
    print("1. 已安装所有依赖: pip install -r requirements.txt")
    print("2. 已设置环境变量（.env 文件）")
    print("3. 在 decodables 目录下运行此脚本")
    sys.exit(1)
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

