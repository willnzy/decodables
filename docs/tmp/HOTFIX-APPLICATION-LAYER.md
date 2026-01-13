# 应用层 P0 修复指南

> **修复日期**: 2026-01-13  
> **优先级**: P0 (紧急)  
> **预计时间**: 30 分钟

---

## 📋 修复清单

### ✅ 必须完成 (P0)

- [ ] 删除 Webhook 中的重复奖励调用
- [ ] 验证注册奖励只发放一次
- [ ] 测试并发场景
- [ ] 部署到生产

---

## 🔴 Fix 1: 删除重复的注册奖励调用

### 问题描述

当前代码中，注册奖励被发放了 **两次**：

1. **数据库层** (`create_user_idempotent` RPC):
   ```sql
   INSERT INTO profiles (..., credits_permanent, ...)
   VALUES (..., 50, ...);  -- 第一次
   ```

2. **应用层** (Webhook Handler):
   ```python
   if was_created:
       await self._grant_signup_bonus(user_id)  # 第二次（另外 50）
   ```

**结果**: 每个新用户获得 **100 credits** 而不是 50 ❌

---

### 修复步骤

#### Step 1: 修改 Webhook Handler

**文件**: `decodables/domains/webhooks/clerk_webhook_service.py`

**原代码** (第 147-152 行):
```python
if was_created:
    # Webhook successfully created user (normal case)
    logger.info(f"✅ Webhook created user {user_id}")
    
    # Grant signup bonus (only for newly created users)
    await self._grant_signup_bonus(user_id)  # ❌ 删除这行
    
    status_result = {"status": "processed", "was_created": True}
```

**修改后**:
```python
if was_created:
    # Webhook successfully created user (normal case)
    logger.info(
        f"✅ Webhook created user {user_id}. "
        f"Signup bonus (50 credits) was granted by RPC."
    )
    
    # ✅ 注册奖励已在 create_user_idempotent() RPC 中发放
    # 无需再次调用 _grant_signup_bonus()
    
    status_result = {"status": "processed", "was_created": True}
```

#### Step 2: 添加注释说明

在 `_handle_user_created` 方法顶部添加注释：

```python
async def _handle_user_created(self, data: Dict[str, Any]) -> Dict[str, str]:
    """
    Handle user.created event (Primary Path for User Creation).

    Architecture: Webhook-First Pattern
    - This is the preferred way to create users (95% of cases)
    - Uses idempotent create_or_get() to handle JIT race conditions
    - ✅ Signup bonus (50 credits) is granted by the RPC function
    - ❌ DO NOT call _grant_signup_bonus() here (would duplicate credits)

    Args:
        data: User data from Clerk

    Returns:
        Dict with status ('processed', 'duplicate') and was_created flag
    """
```

---

## 🧪 测试验证

### Test Case 1: 单用户注册

```python
# tests/integration/test_user_creation_hotfix.py
import pytest
from domains.webhooks.clerk_webhook_service import ClerkWebhookService

@pytest.mark.asyncio
async def test_signup_bonus_granted_once():
    """
    验证注册奖励只发放一次（50 credits）
    """
    # 模拟 Clerk webhook 数据
    webhook_data = {
        "id": "test_user_signup_once",
        "email_addresses": [{"email_address": "test@example.com"}],
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "image_url": None
    }
    
    # 处理 webhook
    webhook_service = ClerkWebhookService(user_repo, billing_service, db_client)
    result = await webhook_service._handle_user_created(webhook_data)
    
    assert result["was_created"] is True
    
    # 验证 credits
    user = await user_repo.get_by_id("test_user_signup_once")
    assert user.credits_permanent == 50, "应该只有 50 credits，不是 100"
    
    # 验证交易记录（应该只有 1 条初始奖励记录）
    transactions = await credit_repo.get_transactions(
        user_id="test_user_signup_once",
        transaction_type=TransactionType.REWARD
    )
    
    # ✅ 应该只有 RPC 创建时的初始 50 credits
    # ❌ 不应该有 _grant_signup_bonus 的额外 50 credits
    assert len(transactions) == 0, "不应该有额外的奖励交易记录"
```

### Test Case 2: 并发创建（Webhook vs JIT）

```python
@pytest.mark.asyncio
async def test_concurrent_creation_no_double_bonus():
    """
    验证即使并发创建，奖励也只发放一次
    """
    user_id = "test_concurrent_bonus"
    
    async def webhook_create():
        webhook_data = {
            "id": user_id,
            "email_addresses": [{"email_address": "concurrent@example.com"}],
            "username": "concurrent_user"
        }
        return await webhook_service._handle_user_created(webhook_data)
    
    async def jit_create():
        await asyncio.sleep(0.01)  # 稍微延迟
        user_profile = UserProfile.create_new(
            user_id=user_id,
            email="concurrent@example.com",
            username="concurrent_user"
        )
        return await user_repo.create_or_get(user_profile, source='jit')
    
    # 并发执行
    results = await asyncio.gather(webhook_create(), jit_create())
    
    # 验证：只有一个创建成功
    created_count = sum([
        1 if r.get("was_created") or (isinstance(r, tuple) and r[1]) else 0 
        for r in results
    ])
    assert created_count == 1, "应该只创建一次"
    
    # 验证 credits
    user = await user_repo.get_by_id(user_id)
    assert user.credits_permanent == 50, "即使并发，也应该只有 50 credits"
```

---

## 🚀 部署步骤

### Step 1: 应用数据库修复

```bash
# 在 Supabase Dashboard SQL Editor 中执行
# 或使用 psql
psql "postgresql://your_connection_string" \
  -f migrations/v2/HOTFIX_user_creation_p0.sql
```

**预期输出**:
```
NOTICE:  ✅ user_code_seq 序列创建成功
NOTICE:  ✅ create_user_idempotent 函数已更新
NOTICE:  ✅ error_logs 表已创建
NOTICE:  🎉 所有 P0 修复已成功应用！
```

### Step 2: 修改应用代码

```bash
# 1. 修改 clerk_webhook_service.py
vim domains/webhooks/clerk_webhook_service.py

# 2. 删除 _grant_signup_bonus() 调用（第 152 行）

# 3. 添加注释说明
```

### Step 3: 运行测试

```bash
# 运行修复相关的测试
pytest tests/integration/test_user_creation_hotfix.py -v

# 预期输出：
# ✅ test_signup_bonus_granted_once PASSED
# ✅ test_concurrent_creation_no_double_bonus PASSED
```

### Step 4: 部署到生产

```bash
# 1. 提交代码
git add domains/webhooks/clerk_webhook_service.py
git commit -m "hotfix: Remove duplicate signup bonus in webhook handler

- Remove _grant_signup_bonus() call (already done in RPC)
- Update comments to clarify bonus is granted once
- Fixes P0 risk: users getting 100 credits instead of 50

Ref: docs/tmp/IDEMPOTENT-USER-CREATION-RISK-ANALYSIS.md"

# 2. 推送到远程
git push origin main

# 3. 等待部署完成（Railway）
railway logs --follow

# 4. 验证部署
curl https://your-api.com/api/health
```

---

## ✅ 验证清单

### 数据库层验证

```sql
-- 1. 验证序列已创建
SELECT * FROM pg_sequences WHERE sequencename = 'user_code_seq';

-- 2. 验证函数已更新
SELECT 
    proname, 
    prosrc LIKE '%ON CONFLICT%' as uses_upsert 
FROM pg_proc 
WHERE proname = 'create_user_idempotent';
-- 预期: uses_upsert = true

-- 3. 测试创建新用户
SELECT * FROM create_user_idempotent(
    'test_hotfix_user',
    'test@example.com',
    'webhook',
    'testuser',
    'Test',
    'User',
    NULL,
    NULL
);

-- 4. 验证 credits
SELECT id, email, credits_permanent 
FROM profiles 
WHERE id = 'test_hotfix_user';
-- 预期: credits_permanent = 50 (不是 100)
```

### 应用层验证

```bash
# 1. 检查代码是否正确修改
grep -n "_grant_signup_bonus" domains/webhooks/clerk_webhook_service.py
# 预期: 只在方法定义处出现，不在调用处

# 2. 创建测试用户（通过 Clerk）
# 在 Clerk Dashboard 中手动创建一个测试用户

# 3. 检查数据库中的 credits
psql "connection_string" -c "
    SELECT id, email, credits_permanent, created_by 
    FROM profiles 
    WHERE email = 'your_test_email@example.com';
"
# 预期: credits_permanent = 50

# 4. 检查日志
railway logs | grep "Webhook created user"
# 预期: 看到 "Signup bonus was granted by RPC" 消息
```

---

## 🐛 回滚方案

如果修复导致问题，可以快速回滚：

### 代码回滚

```bash
# 回滚到上一个提交
git revert HEAD
git push origin main

# 或使用 Railway 回滚到上一个部署
railway rollback
```

### 数据库回滚

```sql
-- 恢复旧版本的 create_user_idempotent 函数
-- (保留在 git history 中: decodables/migrations/v2/01_core_business.sql)

-- 删除序列（如果需要）
DROP SEQUENCE IF EXISTS user_code_seq CASCADE;
```

---

## 📊 监控指标

### 部署后监控

部署完成后，监控以下指标 24 小时：

```sql
-- 1. 新用户的平均 credits（应该是 50）
SELECT 
    AVG(credits_permanent) as avg_credits,
    COUNT(*) as new_users
FROM profiles
WHERE created_at >= NOW() - INTERVAL '24 hours'
  AND created_by IN ('webhook', 'jit');
-- 预期: avg_credits = 50.00

-- 2. 重复尝试率（应该很低）
SELECT 
    COUNT(*) FILTER (WHERE action = 'duplicate_attempt') as duplicates,
    COUNT(*) FILTER (WHERE action = 'created') as created,
    ROUND(
        COUNT(*) FILTER (WHERE action = 'duplicate_attempt')::NUMERIC 
        / COUNT(*) FILTER (WHERE action = 'created') * 100, 
        2
    ) as duplicate_rate_pct
FROM user_creation_logs
WHERE created_at >= NOW() - INTERVAL '24 hours';
-- 预期: duplicate_rate_pct < 10%

-- 3. 错误率（应该是 0）
SELECT COUNT(*) as error_count
FROM error_logs
WHERE operation = 'create_user_idempotent'
  AND created_at >= NOW() - INTERVAL '24 hours';
-- 预期: error_count = 0
```

---

## 📞 紧急联系

如果遇到问题：

1. **立即回滚** (见上方回滚方案)
2. **检查日志**: `railway logs --follow`
3. **查看错误**: `SELECT * FROM error_logs ORDER BY created_at DESC LIMIT 10;`
4. **联系团队**: 在 Slack #backend-alerts 频道报告

---

## ✅ 完成确认

修复完成后，在下方签名：

- [ ] 数据库 HOTFIX 已应用
- [ ] 应用代码已修改
- [ ] 测试已通过
- [ ] 已部署到生产
- [ ] 监控指标正常

**修复人**: _______________  
**日期**: _______________  
**审核人**: _______________
