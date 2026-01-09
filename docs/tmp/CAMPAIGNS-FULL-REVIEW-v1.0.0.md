# Campaigns 模块完整 Review 报告 v1.0.0

**Review Date**: 2026-01-10
**Module**: Campaigns (3 interfaces)
**Reviewer**: Claude Code

---

## 模块概览

**文件清单**:
```
api/user/campaigns.py               (343 lines) - API 层
domains/marketing/service.py        (280 lines) - Domain Service
domains/marketing/repository.py     (135 lines) - Repository Interface
infrastructure/repositories/campaign_repository.py  (169 lines) - Repository 实现
```

**接口清单** (3 个):
1. `GET /api/v2/user/campaigns/active` - 获取活动列表
2. `POST /api/v2/user/campaigns/{id}/claim` - 领取奖励
3. `POST /api/v2/user/campaigns/{id}/dismiss` - 关闭通知

---

## 调用链分析

### 1. GET /active - 获取活动列表

**完整调用链**:
```
API: get_active_campaigns() [campaigns.py:154-229]
  ├─ optional_user (依赖注入)
  ├─ CampaignService (依赖注入)
  └─ CampaignService.get_active_campaigns_for_user() [service.py:74-114]
      ├─ Repository.get_active_campaigns() [campaign_repository.py:32-45]
      │   └─ DB: SELECT * FROM campaigns WHERE status='active' AND is_active=true AND start_at <= now AND end_at > now
      ├─ Repository.get_user_campaign_status() [campaign_repository.py:57-91]
      │   ├─ DB: SELECT campaign_id FROM campaign_claims WHERE user_id=? AND campaign_id IN (?)
      │   └─ DB: SELECT campaign_id, channel FROM campaign_dismissals WHERE user_id=? AND campaign_id IN (?)
      └─ Service._check_target_eligibility() [service.py:215-259]
          └─ 业务逻辑: 根据 target_type 检查用户资格
```

**上游依赖**:
- ✅ `dependencies.optional_user` - 已在 Analytics Review 中修复 (#A1)
- ✅ Rate Limiter - 未使用 (匿名可访问)
- ✅ Database schema - `campaigns`, `campaign_claims`, `campaign_dismissals` 表

**下游影响**:
- ✅ 返回 `ActiveCampaignsResponse` - 包含 campaigns 列表 + notifications 分组
- ✅ 前端消费: 渲染 banner/modal/toast 通知

---

### 2. POST /{id}/claim - 领取奖励

**完整调用链**:
```
API: claim_campaign() [campaigns.py:232-282]
  ├─ Rate Limiter: 10/minute
  ├─ get_current_user (依赖注入)
  ├─ UUID_PATTERN.match(campaign_id) - 输入验证
  └─ CampaignService.claim_campaign() [service.py:116-196]
      ├─ Repository.get_by_id() [campaign_repository.py:47-55]
      │   └─ DB: SELECT * FROM campaigns WHERE id=?
      ├─ Service._check_target_eligibility() [service.py:215-259]
      ├─ Service._check_usage_limit() [service.py:261-265]
      ├─ Service._validate_credit_amount() [service.py:267-275]
      ├─ Repository.record_claim() [campaign_repository.py:93-112]
      │   └─ DB: INSERT INTO campaign_claims (campaign_id, user_id, credits_received)
      │       UNIQUE constraint: (campaign_id, user_id)
      ├─ grant_credits_fn() [campaigns.py:78-90]
      │   └─ CreditRepository.add_credits_permanent() [credit_repository.py:247-276]
      │       └─ RPC: add_credits_atomic() - 原子积分增加
      ├─ Repository.delete_claim() [campaign_repository.py:114-118] (失败时回滚)
      └─ Repository.increment_usage_count() [campaign_repository.py:120-137]
          └─ RPC: increment_campaign_usage() - 原子计数器
```

**上游依赖**:
- ✅ `dependencies.get_current_user` - JWT 认证
- ✅ Rate Limiter - 10/minute (防止滥用)
- ✅ UUID validation - Regex 验证

**下游影响**:
- ✅ 积分系统 - 调用 Billing Domain (已 Review)
- ✅ 数据库事务 - campaign_claims + credits 原子性

---

### 3. POST /{id}/dismiss - 关闭通知

**完整调用链**:
```
API: dismiss_notification() [campaigns.py:285-309]
  ├─ Rate Limiter: 30/minute
  ├─ get_current_user (依赖注入)
  ├─ UUID_PATTERN.match(campaign_id) - 输入验证
  ├─ DismissRequest.channel validation (Pydantic pattern)
  └─ CampaignService.dismiss_notification() [service.py:198-213]
      └─ Repository.record_dismissal() [campaign_repository.py:139-148]
          └─ DB: UPSERT INTO campaign_dismissals (campaign_id, user_id, channel)
              ON CONFLICT (campaign_id, user_id, channel) DO UPDATE
```

**上游依赖**:
- ✅ `dependencies.get_current_user` - JWT 认证
- ✅ Rate Limiter - 30/minute
- ✅ Pydantic validation - `^(modal|toast|banner)$` pattern

**下游影响**:
- ✅ 用户偏好存储 - campaign_dismissals 表
- ✅ 幂等性 - UPSERT 保证安全

---

## 数据库验证

### Schema 检查

**campaigns 表** (✅ 存在):
```sql
CREATE TABLE campaigns (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL CHECK (type IN ('credits_reward', 'discount', 'trial_extension', 'bonus')),
    config JSONB NOT NULL DEFAULT '{}',
    target_type TEXT NOT NULL DEFAULT 'all' CHECK (target_type IN ('all', 'tier', 'cohort', 'user_list')),
    target_config JSONB DEFAULT '{}',
    notification_channels TEXT[] DEFAULT ARRAY['banner'],
    notification_config JSONB DEFAULT '{}',
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ NOT NULL,
    usage_limit INTEGER,
    usage_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'paused', 'completed')),
    is_active BOOLEAN DEFAULT TRUE,
    ...
);
```

**⚠️ 发现问题 #C-HIGH-1**: **type CHECK 约束不匹配**

**数据库定义**:
```sql
CHECK (type IN ('credits_reward', 'discount', 'trial_extension', 'bonus'))
```

**代码中使用**:
```python
# domains/marketing/service.py:29
VALID_CAMPAIGN_TYPES = {"credits_gift", "credits_discount", "credits_bonus"}

# service.py:158
if campaign.type not in VALID_CAMPAIGN_TYPES:
    return ClaimResult(False, error_code="CONFIG_ERROR", ...)

# service.py:164
if campaign.type == "credits_gift":
    credits_received = ...
```

**冲突分析**:
- 数据库允许: `credits_reward`, `discount`, `trial_extension`, `bonus`
- 代码校验: `credits_gift`, `credits_discount`, `credits_bonus`
- **完全不匹配!**

**影响**:
- 🔴 **P0 严重 Bug**: 所有数据库中的活动都无法领取 (因为 type 不匹配)
- 代码会返回 `CONFIG_ERROR`
- 用户无法领取任何奖励

**修复方案**: 统一命名规范 (见后续修复建议)

---

**campaign_participations 表** (✅ 存在):
```sql
CREATE TABLE campaign_participations (
    id UUID PRIMARY KEY,
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    credits_received INTEGER,
    claimed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(campaign_id, user_id)
);
```

**⚠️ 发现问题 #C-HIGH-2**: **表名不一致**

**代码中使用**: `campaign_claims` (repository.py:69, 103)
**数据库中实际**: `campaign_participations`

**影响**:
- 🔴 **P0 严重 Bug**: 所有 claim/status 查询会失败 (表不存在)
- Repository 方法会抛出数据库错误

---

**campaign_dismissals 表** (✅ 存在且匹配):
```sql
CREATE TABLE campaign_dismissals (
    id UUID PRIMARY KEY,
    campaign_id UUID NOT NULL REFERENCES campaigns(id),
    user_id TEXT NOT NULL REFERENCES profiles(id),
    channel TEXT NOT NULL,
    dismissed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(campaign_id, user_id, channel)
);
```

✅ 代码和数据库一致

---

**increment_campaign_usage RPC** (✅ 存在且正确):
```sql
CREATE OR REPLACE FUNCTION increment_campaign_usage(p_campaign_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_usage_limit INT;
    v_usage_count INT;
BEGIN
    SELECT usage_limit, usage_count INTO v_usage_limit, v_usage_count
    FROM campaigns WHERE id = p_campaign_id FOR UPDATE;

    IF NOT FOUND THEN RETURN FALSE; END IF;

    IF v_usage_limit IS NOT NULL AND v_usage_count >= v_usage_limit THEN
        RETURN FALSE;
    END IF;

    UPDATE campaigns SET usage_count = usage_count + 1 WHERE id = p_campaign_id;
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;
```

✅ 返回类型正确 (BOOLEAN)
✅ 使用 FOR UPDATE 锁
✅ Repository 正确解析返回值 (L132-133)

---

## 发现的问题汇总

### 🔴 P0 - 关键 Bug (阻塞功能)

#### #C-HIGH-1: campaign.type 枚举值不匹配 (P0)

**位置**: `domains/marketing/service.py:29` + `migrations/v2/refactored_schema_v2.sql`

**问题描述**:
- 数据库 CHECK 约束: `('credits_reward', 'discount', 'trial_extension', 'bonus')`
- 代码中校验: `{"credits_gift", "credits_discount", "credits_bonus"}`
- **完全不匹配**, 导致所有活动无法领取

**受影响代码**:
```python
# service.py:158-160
if campaign.type not in VALID_CAMPAIGN_TYPES:
    logger.error(f"[CampaignService] Unknown campaign type: {campaign.type}")
    return ClaimResult(False, error_code="CONFIG_ERROR", message="Campaign configuration error")

# service.py:164-168
if campaign.type == "credits_gift":  # 数据库中是 'credits_reward'
    credits_received = self._validate_credit_amount(campaign.config.get("amount", 0))
    if credits_received is None:
        return ClaimResult(False, error_code="CONFIG_ERROR", ...)
```

**修复建议**: 统一使用数据库中的命名 (修改代码匹配数据库)

---

#### #C-HIGH-2: 表名不一致 - campaign_claims vs campaign_participations (P0)

**位置**: `infrastructure/repositories/campaign_repository.py:69, 103`

**问题描述**:
- 代码使用: `campaign_claims` 表
- 数据库实际: `campaign_participations` 表
- 导致所有 claim/status 查询失败

**受影响代码**:
```python
# Line 69-71
claims_result = self.client.table("campaign_claims").select(
    "campaign_id"
).eq("user_id", user_id).in_("campaign_id", campaign_ids).execute()

# Line 103-107
self.client.table("campaign_claims").insert({
    "campaign_id": campaign_id,
    "user_id": user_id,
    "credits_received": credits_received,
}).execute()

# Line 116-118
self.client.table("campaign_claims").delete().eq(
    "campaign_id", campaign_id
).eq("user_id", user_id).execute()
```

**修复建议**: 全局替换 `campaign_claims` → `campaign_participations`

---

### 🟠 P1 - 高优先级 (功能风险)

#### #C-MEDIUM-1: target_type 枚举值部分不匹配 (P1)

**位置**: `domains/marketing/service.py:215-259`

**问题描述**:
- 数据库 CHECK: `('all', 'tier', 'cohort', 'user_list')`
- 代码实现: `all`, `subscription`, `users`, `new_users`, `inactive_users`
- **部分不匹配**:
  - ✅ `all` - 匹配
  - ❌ `tier` (DB) vs `subscription` (代码)
  - ❌ `cohort` (DB) vs 无实现
  - ❌ `user_list` (DB) vs `users` (代码)
  - ❌ `new_users`, `inactive_users` (代码) - 数据库不允许

**受影响代码**:
```python
# service.py:226-233
if target_type == "subscription":  # DB 中是 'tier'
    user_tier = user.get("tier", "free")
    allowed_tiers = target_config.get("tiers", [])
    return user_tier in allowed_tiers

elif target_type == "users":  # DB 中是 'user_list'
    allowed_users = target_config.get("user_ids", [])
    return user["id"] in allowed_users

elif target_type == "new_users":  # DB 中不允许此值
    ...
elif target_type == "inactive_users":  # DB 中不允许此值
    ...
```

**影响**:
- 数据库中插入 `tier` / `user_list` 类型的活动后, 代码无法识别
- 代码中使用 `new_users` / `inactive_users` 无法插入数据库

**修复建议**: 统一命名规范

---

#### #C-MEDIUM-2: RPC 返回值结构假设 (P1)

**位置**: `campaign_repository.py:128-134`

**问题描述**:
```python
result = self.client.rpc("increment_campaign_usage", {
    "p_campaign_id": campaign_id,
}).execute()

if result.data and len(result.data) > 0:
    return result.data[0].get("success", False)  # ← 假设返回 dict
return False
```

**实际情况**:
- RPC 函数返回 `RETURNS BOOLEAN`
- Supabase 会返回 `result.data = True` (直接布尔值, **不是** list[dict])

**影响**:
- `result.data` 是 `True/False`, 不是列表
- `len(result.data)` 会抛出 `TypeError: object of type 'bool' has no len()`
- 导致 `increment_usage_count()` 始终失败

**修复建议**: 修改为 `return bool(result.data)`

---

### 🟡 P2 - 中等优先级 (代码质量)

#### #C-LOW-1: Service 缺少对 CreditOperationFailedException 的处理 (P2)

**位置**: `service.py:183-187`

**问题描述**:
```python
try:
    if credits_received > 0:
        await grant_credits_fn(user["id"], credits_received, ...)
except Exception as e:  # ← 捕获太宽泛
    logger.error(f"[CampaignService] Credit grant failed: {e}")
    await self._repo.delete_claim(campaign_id, user["id"])
    return ClaimResult(False, error_code="CREDIT_FAILED", ...)
```

**问题**:
- 未区分预期异常 (InsufficientCreditsException) vs 意外异常
- 与 Billing Review 中发现的问题类似 (#B-NEW-1)

**修复建议**: 参考 Billing 修复, 区分异常类型

---

#### #C-LOW-2: Repository 吞噬异常导致数据不一致风险 (P2)

**位置**: `campaign_repository.py:75, 89`

**问题描述**:
```python
# Line 68-75
try:
    claims_result = self.client.table("campaign_claims").select(...)
    claimed_campaigns = {c["campaign_id"] for c in claims_result.data}
except Exception as e:
    logger.warning(f"[CampaignRepo] Failed to batch fetch claims: {e}")
    # ← 吞噬异常, 返回空集合

# Line 78-89 (同样问题)
try:
    dismissals_result = ...
except Exception as e:
    logger.warning(f"[CampaignRepo] Failed to batch fetch dismissals: {e}")
    # ← 吞噬异常, 返回空字典
```

**影响**:
- 数据库错误时, 返回空结果
- 导致 `has_claimed=False`, `can_claim=True` (错误状态)
- 用户可能重复领取

**修复建议**: 抛出异常而不是吞噬, 或返回错误标识

---

#### #C-LOW-3: API 层缺少日志记录 (P2)

**位置**: `campaigns.py:154-309`

**问题描述**:
- 只有一处 warning 日志 (L211)
- 缺少关键操作的审计日志:
  - 活动列表查询 (用户 ID, 返回数量)
  - 领取成功/失败 (已由 Service 记录, 但 API 层应有独立日志)
  - 关闭通知 (用户行为追踪)

**修复建议**: 添加结构化日志

---

### 🟢 P3 - 低优先级 (优化建议)

#### #C-OPT-1: _build_notification_from_data 可以优化默认值 (P3)

**位置**: `campaigns.py:324-342`

**问题描述**:
```python
notification = NotificationData(
    campaign_id=campaign.id,
    campaign_type=campaign.type,
    channel=channel,
    title=config.get("title", campaign.name),
    message=config.get("message", campaign.description or ""),  # ← 可能返回 None
    cta_text=config.get("cta_text", "Learn More"),
    cta_url=config.get("cta_url", "/pricing"),
    show_once=config.get("show_once", False),
    can_claim=can_claim,
)
```

**潜在问题**:
- `campaign.description or ""` - 如果 description 是 None, 返回空字符串
- 但如果是空字符串, 仍返回空字符串 (符合预期)
- 建议明确处理: `config.get("message") or campaign.description or ""`

**修复建议**: 代码审查时明确默认值链

---

#### #C-OPT-2: Repository 可以使用连接池优化 (P3)

**位置**: `campaign_repository.py:20-30`

**问题描述**:
- 每次调用创建新的 Repository 实例 (campaigns.py:67-75)
- Supabase client 可以共享

**修复建议**: 使用单例模式或连接池 (低优先级, 不影响功能)

---

## 优先级统计

| 优先级 | 数量 | 问题 ID |
|--------|------|---------|
| 🔴 P0 | 2 | C-HIGH-1, C-HIGH-2 |
| 🟠 P1 | 2 | C-MEDIUM-1, C-MEDIUM-2 |
| 🟡 P2 | 3 | C-LOW-1, C-LOW-2, C-LOW-3 |
| 🟢 P3 | 2 | C-OPT-1, C-OPT-2 |
| **Total** | **9** | |

---

## 测试覆盖验证

**测试文件位置**: `tests/api/user/test_campaigns.py` (待检查)

**需要覆盖的场景**:
1. ✅ GET /active - 匿名用户 + 已登录用户
2. ✅ POST /claim - 成功领取 + 重复领取 + 额度用完 + 不符合条件
3. ✅ POST /dismiss - 成功关闭 + 重复关闭
4. ❌ target_type 各种类型的资格校验
5. ❌ RPC 函数返回值边界情况
6. ❌ 数据库错误时的异常处理

**测试覆盖率评估**: 待补充测试代码后分析

---

## 向后兼容性分析

### Breaking Changes 风险

1. **#C-HIGH-1 修复 (type 枚举值)**:
   - ⚠️ 如果数据库中已有使用旧值的活动, 需要数据迁移
   - 建议: 保持数据库命名, 修改代码

2. **#C-HIGH-2 修复 (表名)**:
   - ⚠️ 代码修改后, 旧版本会读取空数据
   - 建议: 立即修复, 表名是数据库标准

3. **#C-MEDIUM-1 修复 (target_type)**:
   - ⚠️ 需要数据库迁移或代码适配

---

## 修复建议优先级

**立即修复 (P0)**:
1. ✅ #C-HIGH-2: 表名不一致 → 1 行代码 (全局替换)
2. ✅ #C-HIGH-1: type 枚举值 → 修改 service.py 常量

**短期修复 (P1)**:
3. ✅ #C-MEDIUM-2: RPC 返回值假设 → 1 行代码
4. ✅ #C-MEDIUM-1: target_type 枚举值 → 需要迁移策略

**中期优化 (P2)**:
5. ⏳ #C-LOW-1, C-LOW-2, C-LOW-3 → 异常处理 + 日志优化

**长期优化 (P3)**:
6. ⏳ #C-OPT-1, C-OPT-2 → 代码重构

---

## 下一步行动

1. ✅ **立即修复 P0 问题** (阻塞功能)
2. ✅ **修复 P1 问题** (功能风险)
3. ⏳ 添加测试用例覆盖边界情况
4. ⏳ 数据迁移脚本 (统一枚举值)
5. ✅ 继续 Review Config 模块

---

**Review Status**: ✅ **完成** (发现 9 个问题, 需修复 4 个 P0/P1)
