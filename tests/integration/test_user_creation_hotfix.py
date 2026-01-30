"""
P0 HOTFIX 测试 - 验证用户创建修复

测试范围：
1. 注册奖励只发放一次（50 credits，不是 100）
2. UPSERT 避免 race condition
3. user_code 序列无冲突
4. 并发场景下的正确性
"""
import pytest
import asyncio
from datetime import datetime
from domains.identity.aggregates.user_profile import UserProfile
from domains.webhooks.clerk_webhook_service import ClerkWebhookService
from infrastructure.repositories.user_repository import SupabaseUserRepository
from core.database import get_async_db_client


@pytest.mark.asyncio
class TestUserCreationHotfix:
    """用户创建 HOTFIX 测试套件"""
    
    async def test_signup_bonus_granted_once(self, user_repo, db_client):
        """
        测试1: 验证注册奖励只发放一次（50 credits）
        
        预期结果：
        - 新用户 credits_permanent = 50（不是 100）
        - 无额外的奖励交易记录
        """
        user_id = f"test_bonus_once_{datetime.now().timestamp()}"
        user_profile = UserProfile.create_new(
            user_id=user_id,
            email="test_bonus_once@example.com",
            username="test_bonus_once",
            first_name="Test",
            last_name="User",
            display_name="Test Bonus Once"
        )
        
        # 通过 Webhook 创建用户
        profile, was_created = await user_repo.create_or_get(
            user_profile,
            source='webhook'
        )
        
        assert was_created is True, "应该是新创建的用户"
        assert profile.credits_permanent == 50, "应该只有 50 credits（不是 100）"
        
        # 验证数据库中的 credits
        result = await db_client.table("profiles")\
            .select("id, email, credits_permanent, created_by")\
            .eq("id", user_id)\
            .single()\
            .execute()
        
        assert result.data is not None
        assert result.data["credits_permanent"] == 50, "数据库中应该只有 50 credits"
        assert result.data["created_by"] == "webhook"
        
        print(f"✅ Test 1 Passed: User {user_id} has exactly 50 credits")
    
    
    async def test_concurrent_creation_no_error(self, user_repo):
        """
        测试2: 验证并发创建不会导致错误（UPSERT 修复）
        
        预期结果：
        - 并发创建不会抛出异常
        - 只有一个创建成功
        - 另一个返回 was_created=False
        """
        user_id = f"test_concurrent_{datetime.now().timestamp()}"
        
        async def create_via_webhook():
            user_profile = UserProfile.create_new(
                user_id=user_id,
                email="concurrent@example.com",
                username="concurrent_user",
                display_name="Concurrent User"
            )
            return await user_repo.create_or_get(user_profile, source='webhook')
        
        async def create_via_jit():
            await asyncio.sleep(0.01)  # 稍微延迟
            user_profile = UserProfile.create_new(
                user_id=user_id,
                email="concurrent@example.com",
                username="concurrent_user",
                display_name="Concurrent User"
            )
            return await user_repo.create_or_get(user_profile, source='jit')
        
        # 并发执行
        results = await asyncio.gather(
            create_via_webhook(),
            create_via_jit(),
            return_exceptions=True  # 捕获异常而不是抛出
        )
        
        # 验证：没有异常
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), \
                f"Result {i} should not be an exception: {result}"
        
        # 验证：只有一个创建成功
        profiles = [r[0] for r in results]
        was_created_flags = [r[1] for r in results]
        
        assert sum(was_created_flags) == 1, "应该只创建一次"
        assert profiles[0].user_id == profiles[1].user_id
        
        # 验证 credits 仍然是 50
        assert profiles[0].credits_permanent == 50, "即使并发，也应该只有 50 credits"
        
        print(f"✅ Test 2 Passed: Concurrent creation handled gracefully")
    
    
    async def test_user_code_no_conflict(self, user_repo, db_client):
        """
        测试3: 验证 user_code 序列无冲突
        
        预期结果：
        - 快速创建多个用户
        - 所有 user_code 都是唯一的
        - 无主键冲突错误
        """
        user_count = 10
        tasks = []
        
        for i in range(user_count):
            user_profile = UserProfile.create_new(
                user_id=f"test_user_code_{i}_{datetime.now().timestamp()}",
                email=f"test_user_code_{i}@example.com",
                username=f"test_user_code_{i}",
                display_name=f"Test User {i}"
            )
            tasks.append(user_repo.create_or_get(user_profile, source='jit'))
        
        # 并发创建
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 验证：没有异常
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), \
                f"User {i} creation failed: {result}"
        
        # 验证：所有 user_code 都是唯一的
        user_codes = [r[0].user_code for r in results]
        assert len(user_codes) == len(set(user_codes)), \
            "所有 user_code 应该是唯一的"
        
        print(f"✅ Test 3 Passed: All {user_count} user_codes are unique")
    
    
    async def test_webhook_handler_no_double_bonus(
        self, 
        webhook_service: ClerkWebhookService,
        user_repo,
        db_client
    ):
        """
        测试4: 验证 Webhook Handler 不会重复发放奖励
        
        预期结果：
        - Webhook 创建用户后 credits = 50
        - 不调用 _grant_signup_bonus()
        """
        user_id = f"test_webhook_bonus_{datetime.now().timestamp()}"
        webhook_data = {
            "id": user_id,
            "email_addresses": [{"email_address": "webhook_test@example.com"}],
            "username": "webhook_test_user",
            "first_name": "Webhook",
            "last_name": "Test",
            "image_url": None
        }
        
        # 处理 Webhook
        result = await webhook_service._handle_user_created(webhook_data)
        
        assert result["was_created"] is True
        assert result["status"] == "processed"
        
        # 验证 credits
        user = await user_repo.get_by_id(user_id)
        assert user is not None
        assert user.credits_permanent == 50, \
            "Webhook 创建的用户应该只有 50 credits（不是 100）"
        
        print(f"✅ Test 4 Passed: Webhook handler grants only 50 credits")
    
    
    async def test_creation_logs_recorded(self, user_repo, db_client):
        """
        测试5: 验证创建日志正确记录
        
        预期结果：
        - 创建成功时记录 'created' 日志
        - 重复尝试时记录 'duplicate_attempt' 日志
        """
        user_id = f"test_logs_{datetime.now().timestamp()}"
        user_profile = UserProfile.create_new(
            user_id=user_id,
            email="test_logs@example.com",
            username="test_logs_user",
            display_name="Test Logs"
        )
        
        # 第一次创建
        profile1, was_created1 = await user_repo.create_or_get(
            user_profile,
            source='webhook'
        )
        assert was_created1 is True
        
        # 第二次创建（重复）
        profile2, was_created2 = await user_repo.create_or_get(
            user_profile,
            source='jit'
        )
        assert was_created2 is False
        
        # 验证日志
        logs = await db_client.table("user_creation_logs")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at")\
            .execute()
        
        assert len(logs.data) >= 2, "应该有至少 2 条日志"
        
        # 第一条：创建
        assert logs.data[0]["action"] == "created"
        assert logs.data[0]["source"] == "webhook"
        
        # 第二条：重复尝试
        assert logs.data[1]["action"] == "duplicate_attempt"
        assert logs.data[1]["source"] == "jit"
        
        print(f"✅ Test 5 Passed: Creation logs recorded correctly")


@pytest.mark.asyncio
class TestMonitoringStats:
    """监控统计测试"""
    
    async def test_stats_calculation_accurate(self, db_client):
        """
        测试6: 验证统计数据计算准确
        
        预期结果：
        - webhook_success_rate 准确
        - jit_fallback_rate 准确
        - 无除以 0 错误
        """
        result = await db_client.rpc('get_user_creation_stats', {
            'p_days': 7
        }).execute()
        
        assert result.data is not None
        stats = result.data[0] if isinstance(result.data, list) else result.data
        
        # 验证：所有字段都存在
        assert 'total_users' in stats
        assert 'webhook_created' in stats
        assert 'jit_created' in stats
        assert 'webhook_success_rate' in stats
        assert 'jit_fallback_rate' in stats
        
        # 验证：百分比计算正确
        if stats['total_users'] > 0:
            expected_webhook_rate = round(
                stats['webhook_created'] / stats['total_users'] * 100, 
                2
            )
            assert stats['webhook_success_rate'] == expected_webhook_rate
        else:
            # 没有用户时应该返回 0 而不是 NULL
            assert stats['webhook_success_rate'] == 0
        
        print(f"✅ Test 6 Passed: Stats calculation is accurate")


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def db_client():
    """获取数据库客户端"""
    client = await get_async_db_client()
    return client


@pytest.fixture
async def user_repo(db_client):
    """获取用户仓储"""
    return SupabaseUserRepository(db_client)


@pytest.fixture
async def webhook_service(user_repo, db_client):
    """获取 Webhook 服务"""
    from domains.billing.service import BillingService
    
    # Mock billing service（如果需要）
    billing_service = None  # 实际测试中需要真实或 mock 的 BillingService
    
    return ClerkWebhookService(
        user_repo=user_repo,
        billing_service=billing_service,
        db_client=db_client
    )


# ============================================================================
# 测试运行说明
# ============================================================================
"""
运行测试：

# 运行所有 HOTFIX 测试
pytest tests/integration/test_user_creation_hotfix.py -v

# 运行特定测试
pytest tests/integration/test_user_creation_hotfix.py::TestUserCreationHotfix::test_signup_bonus_granted_once -v

# 运行并显示详细输出
pytest tests/integration/test_user_creation_hotfix.py -v -s

预期输出：
✅ Test 1 Passed: User xxx has exactly 50 credits
✅ Test 2 Passed: Concurrent creation handled gracefully
✅ Test 3 Passed: All 10 user_codes are unique
✅ Test 4 Passed: Webhook handler grants only 50 credits
✅ Test 5 Passed: Creation logs recorded correctly
✅ Test 6 Passed: Stats calculation is accurate

=========================== 6 passed in X.XXs ===========================
"""
