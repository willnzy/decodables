# Campaigns P0/P1 问题修复报告 v1.0.0

**Fix Date**: 2026-01-10
**Module**: Campaigns
**Previous Version**: v1.0.0 (repository), v1.0.0 (service)
**New Version**: v1.0.1 (repository), v1.0.1 (service)

---

## 修复概述

修复了 Campaigns 模块 Review 中发现的 **4 个 P0/P1 关键问题**。

**问题来源**: `CAMPAIGNS-FULL-REVIEW-v1.0.0.md`

---

## 修复清单

### ✅ #C-HIGH-2: 表名不一致 - campaign_claims vs campaign_participations (P0)

**问题描述**:
- 代码中使用: `campaign_claims` 表 (不存在)
- 数据库实际: `campaign_participations` 表
- 导致所有 claim/status 查询失败 (表不存在)

**受影响代码**:
```python
# infrastructure/repositories/campaign_repository.py:69, 103, 116
self.client.table("campaign_claims").select(...)    # ← 表不存在
self.client.table("campaign_claims").insert(...)    # ← 表不存在
self.client.table("campaign_claims").delete(...)    # ← 表不存在
```

**修复方案**:
全局替换 `campaign_claims` → `campaign_participations` (3 处)

**修复后**:
```python
# L69
claims_result = self.client.table("campaign_participations").select(...)

# L103
self.client.table("campaign_participations").insert(...)

# L116
self.client.table("campaign_participations").delete(...)
```

**影响**: 🔴 极高 → ✅ 已解决
**变更**: `campaign_repository.py` (+3/-3)

---

### ✅ #C-HIGH-1: campaign.type 枚举值不匹配 (P0)

**问题描述**:
- 数据库 CHECK 约束: `('credits_reward', 'discount', 'trial_extension', 'bonus')`
- 代码中校验: `{'credits_gift', 'credits_discount', 'credits_bonus'}`
- **完全不匹配**, 导致所有活动无法领取 (type 校验失败)

**受影响代码**:
```python
# domains/marketing/service.py:29
VALID_CAMPAIGN_TYPES = {"credits_gift", "credits_discount", "credits_bonus"}  # ← 错误

# service.py:164
if campaign.type == "credits_gift":  # ← 数据库中是 'credits_reward'
    credits_received = ...
```

**修复方案**:
修改代码匹配数据库枚举值

**修复后**:
```python
# L28-30
# Valid campaign types (must match database CHECK constraint)
# Database: CHECK (type IN ('credits_reward', 'discount', 'trial_extension', 'bonus'))
VALID_CAMPAIGN_TYPES = {"credits_reward", "discount", "trial_extension", "bonus"}

# L165
if campaign.type == "credits_reward":  # C-HIGH-1 FIX: Match database enum value
    credits_received = self._validate_credit_amount(campaign.config.get("amount", 0))
```

**影响**: 🔴 极高 → ✅ 已解决
**变更**: `service.py` (+4/-2)

---

### ✅ #C-MEDIUM-2: RPC 返回值结构假设错误 (P1)

**问题描述**:
- RPC 函数 `increment_campaign_usage()` 返回 `RETURNS BOOLEAN`
- Supabase 返回 `result.data = True/False` (直接布尔值)
- 代码假设返回 `[{"success": true/false}]` (list[dict])
- 导致 `len(result.data)` 抛出 `TypeError`

**受影响代码**:
```python
# campaign_repository.py:132-134
if result.data and len(result.data) > 0:  # ← TypeError: bool has no len()
    return result.data[0].get("success", False)
return False
```

**修复方案**:
直接返回布尔值

**修复后**:
```python
# L132-134
# C-MEDIUM-2 FIX: RPC returns BOOLEAN directly, not list[dict]
# result.data is True/False, not [{"success": true/false}]
return bool(result.data)
```

**影响**: 🟠 高 → ✅ 已解决
**变更**: `campaign_repository.py` (+3/-3)

---

### ✅ #C-MEDIUM-1: target_type 枚举值部分不匹配 (P1)

**问题描述**:
- 数据库 CHECK: `('all', 'tier', 'cohort', 'user_list')`
- 代码实现: `all`, `subscription`, `users`, `new_users`, `inactive_users`
- **部分不匹配**:
  - ❌ `subscription` (代码) vs `tier` (DB)
  - ❌ `users` (代码) vs `user_list` (DB)
  - ❌ `new_users`, `inactive_users` (代码) - DB 不允许
  - ❌ `cohort` (DB) - 代码未实现

**受影响代码**:
```python
# service.py:226-257
if target_type == "subscription":  # ← DB 中是 'tier'
    ...
elif target_type == "users":  # ← DB 中是 'user_list'
    ...
elif target_type == "new_users":  # ← DB 不允许此值
    ...
elif target_type == "inactive_users":  # ← DB 不允许此值
    ...
```

**修复方案**:
修改代码匹配数据库枚举值, 移除不支持的类型

**修复后**:
```python
# L216-251
def _check_target_eligibility(self, campaign: CampaignData, user: Optional[dict]) -> bool:
    """
    Check if user matches the campaign's target audience.

    C-MEDIUM-1 FIX: Match database CHECK constraint
    Database: CHECK (target_type IN ('all', 'tier', 'cohort', 'user_list'))
    """
    target_type = campaign.target_type
    target_config = campaign.target_config

    if target_type == "all":
        return True

    if not user:
        return False

    # C-MEDIUM-1 FIX: 'tier' matches database enum (was 'subscription')
    if target_type == "tier":
        user_tier = user.get("tier", "free")
        allowed_tiers = target_config.get("tiers", [])
        return user_tier in allowed_tiers

    # C-MEDIUM-1 FIX: 'user_list' matches database enum (was 'users')
    elif target_type == "user_list":
        allowed_users = target_config.get("user_ids", [])
        return user["id"] in allowed_users

    # C-MEDIUM-1 FIX: 'cohort' for grouped user targeting
    elif target_type == "cohort":
        cohort_name = target_config.get("cohort_name")
        user_cohort = user.get("cohort")
        if not cohort_name or not user_cohort:
            return False
        return user_cohort == cohort_name

    return False
```

**影响**: 🟠 高 → ✅ 已解决
**变更**: `service.py` (+15/-28)

**说明**:
- 移除了 `new_users`, `inactive_users` 类型 (数据库不支持)
- 如果需要这些功能, 应该:
  1. 修改数据库 schema 添加枚举值
  2. 或者在 `cohort` 类型中实现 (通过 cohort 筛选)

---

## 代码变更统计

| 文件 | 行数变化 | 说明 |
|------|----------|------|
| `campaign_repository.py` | +9 / -9 | 表名修正 + RPC 返回值修正 |
| `service.py` | +19 / -30 | type/target_type 枚举值修正 |

**总变更**: +28 / -39 (净减少 11 行, 代码更简洁)

---

## 向后兼容性

### ⚠️ Breaking Changes

1. **#C-HIGH-2 修复 (表名)**:
   - ✅ **无 Breaking Change**
   - 修正了代码错误, 匹配数据库表名
   - 之前的代码无法运行, 修复后才能正常工作

2. **#C-HIGH-1 修复 (campaign.type)**:
   - ⚠️ **可能影响旧数据**
   - 如果数据库中有使用旧值 (`credits_gift` 等) 的活动:
     - 需要数据迁移: `UPDATE campaigns SET type='credits_reward' WHERE type='credits_gift'`
   - 但根据 schema, 旧值应该无法插入 (CHECK 约束)

3. **#C-MEDIUM-1 修复 (target_type)**:
   - ⚠️ **Breaking Change**
   - 移除了 `new_users`, `inactive_users` 支持
   - 如果有使用这些类型的活动 (不应该有, CHECK 约束不允许), 将被忽略
   - `subscription` → `tier`, `users` → `user_list` 重命名
   - **需要文档更新**: 告知管理员使用新的类型名称

---

## 测试验证

### 需要添加的测试

**文件**: `tests/api/user/test_campaigns.py`

#### 1. Test #C-HIGH-2: 表名修正

```python
async def test_claim_campaign_success():
    """
    Test: Campaign claim creates record in campaign_participations

    Given: Valid campaign and authenticated user
    When: POST /campaigns/{id}/claim
    Then: Record inserted into campaign_participations table
    """
    # Create test campaign
    campaign = await create_test_campaign(type="credits_reward")

    # Claim campaign
    response = client.post(
        f"/api/v2/user/campaigns/{campaign['id']}/claim",
        headers={"Authorization": f"Bearer {user_token}"}
    )

    assert response.status_code == 200
    assert response.json()["success"] is True

    # Verify record in database
    result = supabase.table("campaign_participations").select("*").eq(
        "campaign_id", campaign["id"]
    ).eq("user_id", user_id).execute()

    assert len(result.data) == 1
    assert result.data[0]["credits_received"] > 0
```

#### 2. Test #C-HIGH-1: type 枚举值匹配

```python
@pytest.mark.parametrize("campaign_type", ["credits_reward", "discount", "trial_extension", "bonus"])
async def test_campaign_type_validation(campaign_type):
    """
    Test: All valid campaign types are recognized

    Given: Campaign with valid type from database enum
    When: Claim campaign
    Then: Type validation passes
    """
    campaign = await create_test_campaign(type=campaign_type)
    response = client.post(f"/api/v2/user/campaigns/{campaign['id']}/claim")

    # Should not get CONFIG_ERROR for valid types
    assert response.status_code != 500
    assert "Campaign configuration error" not in response.json().get("message", "")
```

#### 3. Test #C-MEDIUM-2: RPC 返回值处理

```python
async def test_increment_usage_count_success():
    """
    Test: increment_usage_count correctly handles RPC boolean return

    Given: Campaign with usage_limit > usage_count
    When: Claim campaign
    Then: usage_count incremented successfully
    """
    campaign = await create_test_campaign(usage_limit=10, usage_count=5)

    # Claim campaign
    response = client.post(f"/api/v2/user/campaigns/{campaign['id']}/claim")
    assert response.status_code == 200

    # Verify usage_count incremented
    result = supabase.table("campaigns").select("usage_count").eq(
        "id", campaign["id"]
    ).execute()

    assert result.data[0]["usage_count"] == 6
```

#### 4. Test #C-MEDIUM-1: target_type 匹配

```python
@pytest.mark.parametrize("target_type,config,eligible", [
    ("all", {}, True),
    ("tier", {"tiers": ["pro"]}, True),  # User is pro
    ("tier", {"tiers": ["free"]}, False),  # User is pro, not free
    ("user_list", {"user_ids": ["user123"]}, True),  # User ID matches
    ("user_list", {"user_ids": ["other"]}, False),
    ("cohort", {"cohort_name": "early_adopters"}, True),  # User cohort matches
    ("cohort", {"cohort_name": "beta"}, False),
])
async def test_target_eligibility(target_type, config, eligible):
    """
    Test: Target eligibility check with database-valid types
    """
    campaign = await create_test_campaign(
        target_type=target_type,
        target_config=config
    )

    response = client.get("/api/v2/user/campaigns/active")
    campaigns = response.json()["campaigns"]

    if eligible:
        assert any(c["id"] == campaign["id"] for c in campaigns)
    else:
        assert not any(c["id"] == campaign["id"] for c in campaigns)
```

---

## 文档更新

### 需要更新的文档

1. **API 文档** (`API_REFERENCE.md`):
   - 更新 campaign type 枚举值文档
   - 更新 target_type 枚举值文档
   - 说明 `cohort` 类型的使用方法

2. **管理员手册**:
   - 告知 `subscription` → `tier`, `users` → `user_list` 重命名
   - 说明不再支持 `new_users`, `inactive_users` (改用 `cohort`)

3. **数据库 Schema 文档**:
   - 确保 `campaign_participations` 表有文档说明
   - 确保枚举值文档与数据库一致

---

## 下一步行动

1. ✅ **修复完成** (4 个 P0/P1 问题)
2. ⏳ **添加测试用例** (4 个测试场景)
3. ⏳ **更新文档** (API 文档 + 管理员手册)
4. ⏳ **检查是否需要数据迁移** (旧 campaign 数据)
5. ✅ **继续 Review Config 模块**

---

## Git Commit 建议

```bash
# Commit message
fix(campaigns): align code with database schema - P0/P1 fixes

- #C-HIGH-2: Fix table name mismatch (campaign_claims → campaign_participations)
  All campaign claim/status queries now use correct table name from database

- #C-HIGH-1: Fix campaign.type enum mismatch with database CHECK constraint
  Use database values: credits_reward, discount, trial_extension, bonus
  Removed invalid values: credits_gift, credits_discount, credits_bonus

- #C-MEDIUM-2: Fix RPC return value handling in increment_usage_count
  RPC returns BOOLEAN directly, not list[dict] with "success" key

- #C-MEDIUM-1: Fix target_type enum mismatch with database CHECK constraint
  Align with database: all, tier, cohort, user_list
  Removed unsupported types: new_users, inactive_users (use cohort instead)
  Renamed: subscription → tier, users → user_list

BREAKING CHANGE:
- target_type values changed to match database schema
- new_users/inactive_users no longer supported, use cohort type instead

Related: CAMPAIGNS-FULL-REVIEW-v1.0.0.md
```

---

**Status**: ✅ **修复完成** (4/4 P0/P1 问题已修复)
**Next**: 添加测试用例 + 继续 Review Config 模块
