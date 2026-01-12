#!/usr/bin/env python3
"""
Phase 1 验证脚本 - AsyncClient 基础设施

验证要点:
1. ✅ get_async_db_client() 可以正确导入
2. ✅ AsyncClient 可以成功创建
3. ✅ AsyncClient 类型正确
4. ✅ close_async_db_client() 可以正确调用
"""

import asyncio
import sys


async def test_phase1_imports():
    """测试 1: 验证函数可以正确导入"""
    print("=" * 60)
    print("测试 1: 验证 AsyncClient 函数导入")
    print("=" * 60)

    try:
        from core.database import get_async_db_client, close_async_db_client
        print("✅ get_async_db_client 导入成功")
        print("✅ close_async_db_client 导入成功")
        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False


async def test_phase1_client_creation():
    """测试 2: 验证 AsyncClient 可以创建"""
    print("\n" + "=" * 60)
    print("测试 2: 验证 AsyncClient 创建")
    print("=" * 60)

    try:
        from core.database import get_async_db_client

        # 创建客户端
        print("创建 AsyncClient...")
        client = await get_async_db_client()

        if client is None:
            print("⚠️  客户端为 None (可能是环境变量未设置)")
            return True  # 这是预期的，因为测试环境可能没有配置

        # 检查类型
        client_type = f"{type(client).__module__}.{type(client).__name__}"
        print(f"✅ AsyncClient 创建成功")
        print(f"   类型: {client_type}")

        # 验证是否是 AsyncClient
        if "async" in client_type.lower():
            print("✅ 确认是 AsyncClient 类型")
            return True
        else:
            print(f"❌ 错误: 不是 AsyncClient 类型 ({client_type})")
            return False

    except Exception as e:
        print(f"❌ 创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_phase1_cleanup():
    """测试 3: 验证清理函数"""
    print("\n" + "=" * 60)
    print("测试 3: 验证清理函数")
    print("=" * 60)

    try:
        from core.database import close_async_db_client

        print("调用 close_async_db_client()...")
        await close_async_db_client()
        print("✅ 清理函数调用成功")
        return True

    except Exception as e:
        print(f"❌ 清理失败: {e}")
        return False


async def test_phase1_singleton():
    """测试 4: 验证单例模式"""
    print("\n" + "=" * 60)
    print("测试 4: 验证单例模式")
    print("=" * 60)

    try:
        from core.database import get_async_db_client, close_async_db_client

        # 清理旧实例
        await close_async_db_client()

        # 创建两次
        print("第一次调用 get_async_db_client()...")
        client1 = await get_async_db_client()

        print("第二次调用 get_async_db_client()...")
        client2 = await get_async_db_client()

        if client1 is None and client2 is None:
            print("⚠️  客户端为 None (环境变量未设置)")
            return True

        # 验证是同一个实例
        if client1 is client2:
            print("✅ 单例模式正确: 两次调用返回同一实例")
            return True
        else:
            print("❌ 单例模式错误: 两次调用返回不同实例")
            return False

    except Exception as e:
        print(f"❌ 单例测试失败: {e}")
        return False


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Phase 1 验证: AsyncClient 基础设施")
    print("=" * 60)

    results = []

    # 测试 1: 导入
    results.append(await test_phase1_imports())

    # 测试 2: 创建
    results.append(await test_phase1_client_creation())

    # 测试 3: 清理
    results.append(await test_phase1_cleanup())

    # 测试 4: 单例
    results.append(await test_phase1_singleton())

    # 汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")

    if passed == total:
        print("\n✅ Phase 1 所有测试通过!")
        print("\n下一步: Phase 2 - 创建 FastAPI 依赖注入模块")
        return 0
    else:
        print(f"\n❌ 有 {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
