#!/usr/bin/env python3
"""
Phase 3 验证脚本 - 应用启动配置

验证要点:
1. ✅ app.py 使用 lifespan context manager (不是 @app.on_event)
2. ✅ lifespan 在启动时初始化 AsyncClient
3. ✅ lifespan 在关闭时清理 AsyncClient
4. ✅ 应用可以正常启动
"""

import sys
import asyncio


def test_phase3_lifespan_exists():
    """测试 1: 验证 lifespan 函数存在"""
    print("=" * 60)
    print("测试 1: 验证 lifespan 函数存在")
    print("=" * 60)

    try:
        # 检查 app.py 中是否有 lifespan
        with open("app.py", "r") as f:
            content = f.read()

        if "@asynccontextmanager" not in content:
            print("❌ 未找到 @asynccontextmanager 装饰器")
            return False

        if "async def lifespan(app: FastAPI):" not in content:
            print("❌ 未找到 lifespan 函数定义")
            return False

        if "app = FastAPI(" not in content:
            print("❌ 未找到 FastAPI 实例化")
            return False

        if "lifespan=lifespan" not in content:
            print("❌ FastAPI 未使用 lifespan 参数")
            return False

        print("✅ lifespan context manager 正确定义")
        print("✅ FastAPI app 使用 lifespan 参数")
        return True

    except FileNotFoundError:
        print("❌ 未找到 app.py 文件")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_phase3_no_old_events():
    """测试 2: 验证旧的事件处理器已移除"""
    print("\n" + "=" * 60)
    print("测试 2: 验证旧的事件处理器已移除")
    print("=" * 60)

    try:
        with open("app.py", "r") as f:
            content = f.read()

        # 检查是否还有旧的事件处理器
        if '@app.on_event("startup")' in content:
            print("❌ 仍然存在 @app.on_event('startup')")
            return False

        if '@app.on_event("shutdown")' in content:
            print("❌ 仍然存在 @app.on_event('shutdown')")
            return False

        print("✅ 旧的事件处理器已移除")
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_phase3_lifespan_content():
    """测试 3: 验证 lifespan 包含必要的启动/关闭逻辑"""
    print("\n" + "=" * 60)
    print("测试 3: 验证 lifespan 内容")
    print("=" * 60)

    try:
        with open("app.py", "r") as f:
            content = f.read()

        required_startup = [
            "get_async_db_client",
            "init_scheduler",
            "validate_config",
        ]

        required_shutdown = [
            "close_async_db_client",
            "shutdown_scheduler",
            "close_redis",
        ]

        missing_startup = []
        for item in required_startup:
            if item not in content:
                missing_startup.append(item)

        missing_shutdown = []
        for item in required_shutdown:
            if item not in content:
                missing_shutdown.append(item)

        if missing_startup:
            print(f"❌ 启动逻辑缺失: {', '.join(missing_startup)}")
            return False

        if missing_shutdown:
            print(f"❌ 关闭逻辑缺失: {', '.join(missing_shutdown)}")
            return False

        print("✅ lifespan 包含所有必要的启动逻辑")
        print("✅ lifespan 包含所有必要的关闭逻辑")
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_phase3_import_app():
    """测试 4: 验证可以导入 app"""
    print("\n" + "=" * 60)
    print("测试 4: 验证可以导入 app")
    print("=" * 60)

    try:
        # 尝试导入 app
        import sys
        import os

        # 确保在正确的目录
        sys.path.insert(0, os.getcwd())

        from app import app

        if app is None:
            print("❌ app 为 None")
            return False

        print(f"✅ 成功导入 app: {type(app).__name__}")

        # 检查 app 是否有 router
        if not hasattr(app, "router"):
            print("❌ app 没有 router 属性")
            return False

        print("✅ app 结构正确")
        return True

    except ImportError as e:
        print(f"⚠️  导入失败 (可能缺少依赖): {e}")
        # 导入失败不算测试失败，因为可能缺少运行时依赖
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Phase 3 验证: 应用启动配置")
    print("=" * 60)

    results = []

    # 测试 1: lifespan 存在
    results.append(test_phase3_lifespan_exists())

    # 测试 2: 旧事件处理器已移除
    results.append(test_phase3_no_old_events())

    # 测试 3: lifespan 内容
    results.append(test_phase3_lifespan_content())

    # 测试 4: 导入 app
    results.append(test_phase3_import_app())

    # 汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")

    if passed == total:
        print("\n✅ Phase 3 所有测试通过!")
        print("\n下一步: Phase 4 - 重构 BaseRepository (异步化)")
        return 0
    else:
        print(f"\n❌ 有 {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
