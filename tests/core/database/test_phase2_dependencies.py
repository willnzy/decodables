#!/usr/bin/env python3
"""
Phase 2 验证脚本 - FastAPI 依赖注入模块

验证要点:
1. ✅ get_async_db() 可以正确导入
2. ✅ require_async_db() 可以正确导入
3. ✅ 依赖函数可以正常调用 (返回 AsyncGenerator)
4. ✅ require_async_db() 在无配置时抛出异常
5. ✅ 向后兼容别名 (get_db, require_db)
"""

import asyncio
import sys
from typing import AsyncGenerator


async def test_phase2_imports():
    """测试 1: 验证依赖函数可以正确导入"""
    print("=" * 60)
    print("测试 1: 验证依赖函数导入")
    print("=" * 60)

    try:
        from core.database import (
            get_async_db,
            require_async_db,
            get_db,
            require_db,
        )
        print("✅ get_async_db 导入成功")
        print("✅ require_async_db 导入成功")
        print("✅ get_db (别名) 导入成功")
        print("✅ require_db (别名) 导入成功")
        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False


async def test_phase2_get_async_db():
    """测试 2: 验证 get_async_db() 正常工作"""
    print("\n" + "=" * 60)
    print("测试 2: 验证 get_async_db() 函数")
    print("=" * 60)

    try:
        from core.database import get_async_db

        # 调用依赖函数
        print("调用 get_async_db()...")
        gen = get_async_db()

        # 验证是 AsyncGenerator
        if not isinstance(gen, AsyncGenerator):
            print(f"❌ 返回类型错误: {type(gen)}")
            return False

        print("✅ 返回类型正确: AsyncGenerator")

        # 获取客户端
        print("获取客户端实例...")
        client = await gen.__anext__()

        if client is None:
            print("⚠️  客户端为 None (环境变量未设置，这是预期的)")
        else:
            client_type = f"{type(client).__module__}.{type(client).__name__}"
            print(f"✅ 获取到客户端: {client_type}")

        # 清理
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            print("✅ Generator 正确结束")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_phase2_require_async_db():
    """测试 3: 验证 require_async_db() 在无配置时抛出异常"""
    print("\n" + "=" * 60)
    print("测试 3: 验证 require_async_db() 异常处理")
    print("=" * 60)

    try:
        from core.database import require_async_db

        # 调用依赖函数
        print("调用 require_async_db()...")
        gen = require_async_db()

        # 验证是 AsyncGenerator
        if not isinstance(gen, AsyncGenerator):
            print(f"❌ 返回类型错误: {type(gen)}")
            return False

        print("✅ 返回类型正确: AsyncGenerator")

        # 尝试获取客户端 (应该抛出异常，因为环境变量未设置)
        print("尝试获取客户端 (应该抛出异常)...")
        try:
            client = await gen.__anext__()

            # 如果成功获取到客户端，说明环境变量已设置
            if client is not None:
                print("⚠️  环境变量已设置，获取到客户端 (跳过异常测试)")
                try:
                    await gen.__anext__()
                except StopAsyncIteration:
                    pass
                return True

            # 如果返回 None，但没有抛出异常，这是错误的
            print("❌ 应该抛出 RuntimeError，但返回了 None")
            return False

        except RuntimeError as e:
            print(f"✅ 正确抛出 RuntimeError: {e}")
            return True
        except Exception as e:
            print(f"❌ 抛出了错误的异常类型: {type(e).__name__}: {e}")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_phase2_backward_compatibility():
    """测试 4: 验证向后兼容别名"""
    print("\n" + "=" * 60)
    print("测试 4: 验证向后兼容别名")
    print("=" * 60)

    try:
        from core.database import get_db, require_db, get_async_db, require_async_db

        # 验证别名指向正确的函数
        if get_db is get_async_db:
            print("✅ get_db 别名正确")
        else:
            print("❌ get_db 别名错误")
            return False

        if require_db is require_async_db:
            print("✅ require_db 别名正确")
        else:
            print("❌ require_db 别名错误")
            return False

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


async def test_phase2_fastapi_usage_simulation():
    """测试 5: 模拟 FastAPI 路由使用场景"""
    print("\n" + "=" * 60)
    print("测试 5: 模拟 FastAPI 路由使用")
    print("=" * 60)

    try:
        from core.database import get_async_db

        # 模拟 FastAPI 依赖注入流程
        print("模拟路由调用...")

        async def mock_route_handler():
            """模拟路由处理函数"""
            # FastAPI 会自动调用依赖并传入结果
            async for db in get_async_db():
                # 在路由处理函数中使用 db
                if db is None:
                    print("   路由: 数据库未配置")
                else:
                    print(f"   路由: 获取到数据库客户端 - {type(db).__name__}")
                break  # 模拟只使用一次

        await mock_route_handler()
        print("✅ FastAPI 使用模式验证成功")
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Phase 2 验证: FastAPI 依赖注入模块")
    print("=" * 60)

    results = []

    # 测试 1: 导入
    results.append(await test_phase2_imports())

    # 测试 2: get_async_db
    results.append(await test_phase2_get_async_db())

    # 测试 3: require_async_db
    results.append(await test_phase2_require_async_db())

    # 测试 4: 向后兼容
    results.append(await test_phase2_backward_compatibility())

    # 测试 5: FastAPI 使用模式
    results.append(await test_phase2_fastapi_usage_simulation())

    # 汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")

    if passed == total:
        print("\n✅ Phase 2 所有测试通过!")
        print("\n下一步: Phase 3 - 修改应用启动配置")
        return 0
    else:
        print(f"\n❌ 有 {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
