# Tier 降级处理

> **版本**: v2.1
> **日期**: 2026-02-04
> **状态**: 产品确认
> **实现状态**: 🔴 部分待实现

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [README.md](./README.md) | 文档导航索引 |
| [11-trial-expiration.md](./11-trial-expiration.md) | t1 试用期过期处理 |
| [15-credits-lifecycle.md](./15-credits-lifecycle.md) | 积分完整生命周期 |

---

## 一、降级触发条件

### 1.1 主动降级

| 触发方式 | 说明 | 生效时间 |
|----------|------|----------|
| 用户取消订阅 | 在账户设置中取消自动续费 | 当前周期结束 |
| 用户主动降级 | t3 → t2 或 t2 → t1 | 当前周期结束 |

### 1.2 被动降级

| 触发方式 | 说明 | 生效时间 |
|----------|------|----------|
| 付款失败 | 3 次重试均失败 | 宽限期结束后立即 |
| 订阅过期 | 未续费 | 过期后立即 |

---

## 二、Graceful Degradation 策略

> **核心原则**: 保护用户数据，给予充足缓冲期

### 2.1 宽限期设计 (Grace Period)

```
付款失败 → 宽限期 (7天) → 降级生效

时间线:
Day 0: 付款失败，发送提醒
Day 3: 第二次提醒
Day 5: 最后警告
Day 7: 宽限期结束，执行降级
```

**宽限期内**:
- 保持当前 Tier 所有权限
- 顶部 Banner 提示 "付款失败，请更新支付方式"
- 倒计时显示剩余宽限期天数

### 2.2 数据保护策略

| 资源类型 | 超限处理 | 说明 |
|----------|----------|------|
| Workspace | 只读模式 | 保留数据，禁止编辑 |
| 项目 | 只读模式 | 保留数据，禁止新建 |
| 自定义素材 | 只读模式 | 保留数据，禁止上传 |
| 文件夹 | 只读模式 | 保留数据，禁止新建 |

**绝不删除用户数据**，只限制新增和编辑。

### 2.3 超限资源处理

当 t3 → t2 且项目数从 unlimited 变为 10 时:

```
if user.project_count > new_tier.max_projects:
    # 方案 1: 用户自选保留 (推荐)
    show_selection_modal(
        message: "您当前有 25 个项目，Starter Plan 最多支持 10 个",
        action: "请选择要保留的 10 个项目，其余将变为只读"
    )

    # 方案 2: 按时间自动选择
    # 保留最近修改的 10 个，其余只读
```

---

## 三、降级执行流程

### 3.1 执行步骤

```
1. 记录降级原因和时间
2. 更新用户 Tier (profiles.tier)
3. 重新计算资源配额
4. 标记超限资源为只读
5. 发送降级通知邮件
6. 记录审计日志
```

### 3.2 权限同步

```python
async def execute_downgrade(user_id: str, new_tier: str):
    # 1. 更新 Tier
    await update_user_tier(user_id, new_tier)

    # 2. 获取新配额
    new_quotas = TIER_CONFIGS[new_tier]['quotas']

    # 3. 处理超限资源
    await handle_over_quota_resources(user_id, new_quotas)

    # 4. 清除权限缓存
    await clear_permission_cache(user_id)

    # 5. 发送通知
    await send_downgrade_notification(user_id, new_tier)
```

---

## 四、用户通知策略

### 4.1 邮件通知

| 时间点 | 邮件主题 | 内容 |
|--------|----------|------|
| 降级前 7 天 | 订阅即将变更 | 提醒用户即将降级，说明影响 |
| 降级前 1 天 | 最后提醒 | 最后机会恢复订阅 |
| 降级当天 | 订阅已变更 | 确认降级，说明如何升级 |

### 4.2 应用内通知

```
Banner (持续显示):
"您的订阅已变更为 Free Plan，部分功能受限"
[立即升级] [了解详情]

Modal (首次登录):
"您好！您的订阅已变更"
- 当前 Plan: Free Plan
- 受影响的项目: 15 个已变为只读
- 受影响的素材: 40 个已变为只读
[查看详情] [立即升级]
```

---

## 五、恢复升级

### 5.1 快速恢复

宽限期内恢复订阅:
- 自动恢复所有权限
- 无需重新选择资源
- 只读资源自动解锁

### 5.2 降级后重新升级

```
1. 用户选择新 Plan
2. 完成支付
3. 立即生效
4. 超限资源自动解锁
5. 发送确认邮件
```

---

## 六、特殊情况处理

### 6.1 连续降级

t3 → t2 → t1 连续降级时，采用渐进处理:
- 每次降级独立处理
- 每次都有完整的通知流程
- 累积的只读资源标记保留

### 6.2 降级期间的数据变更

降级执行期间，禁止:
- 新建资源
- 删除资源
- 转移资源所有权

确保降级过程中数据一致性。

---

## 七、监控与告警

### 7.1 关键指标

| 指标 | 告警阈值 | 说明 |
|------|----------|------|
| 日降级用户数 | > 100 | 可能存在系统问题 |
| 宽限期恢复率 | < 30% | 需要优化恢复流程 |
| 降级后流失率 | > 50% | 需要优化保留策略 |

### 7.2 审计日志

```json
{
  "event_type": "tier_downgrade",
  "user_id": "user_xxx",
  "old_tier": "t3",
  "new_tier": "t2",
  "reason": "subscription_cancelled",
  "over_quota_projects": 15,
  "over_quota_assets": 40,
  "timestamp": "2026-02-04T10:00:00Z"
}
```

---

## 八、各资源降级处理规则

### 8.1 Workspace 降级

| 原 Tier | 新 Tier | 原配额 | 新配额 | 处理方式 |
|:-------:|:-------:|:-----:|:-----:|---------|
| t3 | t2 | unlimited | 1 | 保留所有，超额的标记为 "只读" |
| t3 | t1 | unlimited | 1 | 保留所有，超额的标记为 "只读" |
| t2 | t1 | 1 | 1 | 无变化 |

**处理逻辑**:
```typescript
// 降级时处理 Workspace
async function handleWorkspaceDowngrade(userId: string, newTier: string) {
  const maxWorkspaces = TIER_QUOTAS[newTier].maxWorkspaces;
  if (maxWorkspaces === -1) return; // unlimited

  const workspaces = await db.fetch(`
    SELECT id, name, created_at FROM workspaces
    WHERE owner_id = $1
    ORDER BY created_at ASC
  `, userId);

  // 超额的 Workspace 标记为只读
  for (let i = maxWorkspaces; i < workspaces.length; i++) {
    await db.execute(`
      UPDATE workspaces
      SET is_read_only = true,
          read_only_reason = 'tier_downgrade',
          read_only_at = NOW()
      WHERE id = $1
    `, workspaces[i].id);
  }
}
```

### 8.2 Project 降级

| 原 Tier | 新 Tier | 原配额 | 新配额 | 处理方式 |
|:-------:|:-------:|:-----:|:-----:|---------|
| t3 | t2 | unlimited | 10 | 保留所有，超额的标记为 "只读" |
| t3 | t1 | unlimited | 1 | 保留所有，超额的标记为 "只读" |
| t2 | t1 | 10 | 1 | 保留所有，超额的标记为 "只读" |

**UI 显示**:
- 只读项目卡片显示 🔒 图标
- 点击只读项目 → 提示 "升级后可编辑"
- 可以查看、导出 PDF，但不能编辑

### 8.3 Folder 降级

| 原 Tier | 新 Tier | 原配额 | 新配额 | 处理方式 |
|:-------:|:-------:|:-----:|:-----:|---------|
| t3 | t2 | 200 | 20 | 超额文件夹只读，内部项目只读 |
| t3 | t1 | 200 | 1 | 超额文件夹只读，内部项目只读 |
| t2 | t1 | 20 | 1 | 超额文件夹只读，内部项目只读 |

### 8.4 自定义素材降级

| 原 Tier | 新 Tier | 原配额 | 新配额 | 处理方式 |
|:-------:|:-------:|:-----:|:-----:|---------|
| t3 | t2 | unlimited | 0 | 所有自定义素材只读 (t2 不支持上传) |
| t3 | t1 | unlimited | 0 | 所有自定义素材只读 |
| t2 | t1 | 0 | 0 | 无变化 (t2 已经不支持自定义素材) |

**注意**: t1 试用期过期后 `max_custom_assets = 0`，但已上传的素材仍可在项目中使用

### 8.5 Workspace 成员降级 (邀请的用户)

| 原 Tier | 新 Tier | 能力变化 | 处理方式 |
|:-------:|:-------:|---------|---------|
| t3 | t2/t1 | 失去邀请能力 | 已邀请的成员**保留**，但无法再邀请新成员 |

**业界参考 (Notion, Figma)**:
- 已邀请的成员不会被踢出
- 成员可以继续访问和编辑 (如果项目未被锁定)
- Owner 无法再邀请新成员
- 成员数量不设上限锁定 (仅锁定邀请入口)

### 8.6 商城相关降级

| 功能 | t3 | t2 | t1 | 降级处理 |
|------|:--:|:--:|:--:|---------|
| 浏览商城 | ✅ | ✅ | ❌ | t2→t1: 入口锁定 |
| 购买商城 | ✅ | ✅ | ❌ | t2→t1: 入口锁定，已购买的项目保留 |
| 发布免费 | ✅ | ✅ | ❌ | t2→t1: 入口锁定，已发布的**保留上架** |
| 发布付费 | ✅ | ❌ | ❌ | t3→t2: 入口锁定，已发布的**保留上架** |

**已发布商品处理**:
- 降级后已发布的商品**继续保持上架**
- 用户仍可获得销售收入
- 但无法发布新商品或修改已发布商品的价格
- 可以下架已发布的商品

---

## 九、宽限期配置

```sql
-- 宽限期配置
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
('downgrade.grace_period_days', '7', 'integer', 'downgrade', '降级宽限期天数'),
('downgrade.lock_after_grace', 'true', 'boolean', 'downgrade', '宽限期后是否锁定超额资源');
```

**宽限期流程**:

```
Day 0: 降级生效
├── 发送邮件通知
├── 应用内 Banner 提醒
├── 超额资源标记为 "即将锁定"
└── 用户可正常使用所有资源

Day 1-6: 宽限期
├── 每天发送提醒邮件 (可配置)
├── Banner 显示剩余天数
└── 用户可正常使用，建议整理资源

Day 7: 宽限期结束
├── 超额资源正式锁定为 "只读"
├── 发送最终通知邮件
└── 锁定资源显示 🔒 图标
```

---

## 十、降级通知邮件模板

```typescript
// 降级通知邮件
const downgradeEmailTemplate = {
  subject: '您的 Make Decodables 订阅已变更',
  body: `
    亲爱的 {{userName}}，

    您的订阅已从 {{oldTier}} 变更为 {{newTier}}。

    以下是受影响的内容：
    {{#if exceededWorkspaces}}
    • Workspace: {{exceededWorkspaces}} 个将在 {{gracePeriodDays}} 天后变为只读
    {{/if}}
    {{#if exceededProjects}}
    • 项目: {{exceededProjects}} 个将在 {{gracePeriodDays}} 天后变为只读
    {{/if}}
    {{#if exceededFolders}}
    • 文件夹: {{exceededFolders}} 个将在 {{gracePeriodDays}} 天后变为只读
    {{/if}}

    在宽限期内，您可以：
    • 导出项目数据
    • 删除不需要的项目
    • 重新订阅以保留所有访问权限

    如有任何问题，请联系我们的客服团队。

    Make Decodables 团队
  `
};
```

---

## 十一、降级处理服务

```python
# domains/entitlement/services/downgrade_service.py

from datetime import datetime, timedelta
from typing import List, Dict

class DowngradeService:
    """Tier 降级处理服务"""

    async def process_downgrade(
        self,
        user_id: str,
        old_tier: str,
        new_tier: str,
        reason: str  # 'subscription_expired' | 'cancelled' | 'payment_failed' | 'refund' | 'admin'
    ) -> Dict:
        """处理 Tier 降级"""

        # 1. 获取配额变化
        old_quotas = TIER_QUOTAS[old_tier]
        new_quotas = TIER_QUOTAS[new_tier]

        # 2. 检查超额资源
        exceeded = await self._check_exceeded_resources(user_id, new_quotas)

        # 3. 获取宽限期配置
        grace_days = await get_config('downgrade.grace_period_days') or 7
        grace_end = datetime.now() + timedelta(days=grace_days)

        # 4. 标记超额资源 (宽限期内)
        await self._mark_resources_pending_lock(user_id, exceeded, grace_end)

        # 5. 记录降级事件
        await self._log_downgrade_event(user_id, old_tier, new_tier, reason, exceeded)

        # 6. 发送通知
        await self._send_downgrade_notification(user_id, old_tier, new_tier, exceeded, grace_end)

        # 7. 调度宽限期结束任务
        await self._schedule_grace_period_end(user_id, grace_end)

        return {
            'old_tier': old_tier,
            'new_tier': new_tier,
            'exceeded_resources': exceeded,
            'grace_period_end': grace_end
        }

    async def _check_exceeded_resources(self, user_id: str, new_quotas: Dict) -> Dict:
        """检查超额资源"""
        exceeded = {
            'workspaces': [],
            'projects': [],
            'folders': [],
            'custom_assets': []
        }

        # 检查 Workspace
        if new_quotas['max_workspaces'] != -1:
            workspaces = await db.fetch_all("""
                SELECT id, name FROM workspaces
                WHERE owner_id = $1
                ORDER BY created_at ASC
            """, user_id)

            if len(workspaces) > new_quotas['max_workspaces']:
                exceeded['workspaces'] = [
                    w['id'] for w in workspaces[new_quotas['max_workspaces']:]
                ]

        # 检查 Projects
        if new_quotas['max_projects'] != -1:
            projects = await db.fetch_all("""
                SELECT id, name FROM projects
                WHERE owner_id = $1
                ORDER BY created_at ASC
            """, user_id)

            if len(projects) > new_quotas['max_projects']:
                exceeded['projects'] = [
                    p['id'] for p in projects[new_quotas['max_projects']:]
                ]

        # 检查 Folders
        if new_quotas['max_folders'] != -1:
            folders = await db.fetch_all("""
                SELECT id, name FROM folders
                WHERE owner_id = $1
                ORDER BY created_at ASC
            """, user_id)

            if len(folders) > new_quotas['max_folders']:
                exceeded['folders'] = [
                    f['id'] for f in folders[new_quotas['max_folders']:]
                ]

        # 检查自定义素材
        if new_quotas['max_custom_assets'] != -1:
            assets = await db.fetch_all("""
                SELECT id FROM custom_assets
                WHERE owner_id = $1
                ORDER BY created_at ASC
            """, user_id)

            if len(assets) > new_quotas['max_custom_assets']:
                exceeded['custom_assets'] = [
                    a['id'] for a in assets[new_quotas['max_custom_assets']:]
                ]

        return exceeded

    async def _mark_resources_pending_lock(
        self,
        user_id: str,
        exceeded: Dict,
        grace_end: datetime
    ):
        """标记资源为待锁定状态"""
        for ws_id in exceeded['workspaces']:
            await db.execute("""
                UPDATE workspaces SET
                    pending_lock = true,
                    pending_lock_at = $1,
                    lock_reason = 'tier_downgrade'
                WHERE id = $2
            """, grace_end, ws_id)

        for proj_id in exceeded['projects']:
            await db.execute("""
                UPDATE projects SET
                    pending_lock = true,
                    pending_lock_at = $1,
                    lock_reason = 'tier_downgrade'
                WHERE id = $2
            """, grace_end, proj_id)

        # ... 类似处理 folders 和 custom_assets

    async def execute_grace_period_end(self, user_id: str):
        """宽限期结束，正式锁定资源"""
        await db.execute("""
            UPDATE workspaces SET
                is_read_only = true,
                read_only_at = NOW(),
                pending_lock = false
            WHERE owner_id = $1 AND pending_lock = true
        """, user_id)

        await db.execute("""
            UPDATE projects SET
                is_read_only = true,
                read_only_at = NOW(),
                pending_lock = false
            WHERE owner_id = $1 AND pending_lock = true
        """, user_id)

        # ... 类似处理其他资源

        # 发送锁定完成通知
        await self._send_lock_completed_notification(user_id)
```

---

## 十二、其他业界常见边界场景

### 12.1 升级场景 (Upgrade)

| 场景 | 处理方式 |
|------|---------|
| t1→t2 | 立即解锁 t2 功能，只读项目恢复可编辑 |
| t1→t3 | 立即解锁 t3 功能，只读项目恢复可编辑 |
| t2→t3 | 立即解锁 t3 功能 |
| 试用期内升级 | 试用期状态取消，进入正式订阅 |

**升级处理**:
```typescript
async function handleUpgrade(userId: string, newTier: string) {
  // 1. 解锁所有只读资源
  await db.execute(`
    UPDATE workspaces SET is_read_only = false, read_only_at = NULL
    WHERE owner_id = $1 AND read_only_reason = 'tier_downgrade'
  `, userId);

  await db.execute(`
    UPDATE projects SET is_read_only = false, read_only_at = NULL
    WHERE owner_id = $1 AND read_only_reason = 'tier_downgrade'
  `, userId);

  // 2. 取消待锁定状态
  await db.execute(`
    UPDATE workspaces SET pending_lock = false, pending_lock_at = NULL
    WHERE owner_id = $1
  `, userId);

  // 3. 发送升级成功通知
  await sendUpgradeNotification(userId, newTier);
}
```

### 12.2 支付失败重试

| 重试次数 | 间隔 | 操作 |
|:-------:|:----:|------|
| 第 1 次 | 立即 | 自动重试 |
| 第 2 次 | 3 天后 | 自动重试 + 邮件通知 |
| 第 3 次 | 7 天后 | 自动重试 + 邮件警告 |
| 第 4 次 | 14 天后 | 最终重试 + 降级预警 |
| 全部失败 | - | 自动降级 + 宽限期开始 |

### 12.3 账户删除 / 数据导出

| 场景 | 处理方式 |
|------|---------|
| **数据导出** | 任何 Tier 都可以导出自己的项目数据 (PDF/JSON) |
| **账户删除请求** | 发起后 30 天内可取消，30 天后永久删除 |
| **删除后数据** | 所有数据永久删除，商城已发布商品下架 |

### 12.4 并发订阅冲突

| 场景 | 处理方式 |
|------|---------|
| 重复订阅同一 Plan | 拒绝，提示已订阅 |
| 订阅更低 Tier | 确认降级意图，当前周期结束后生效 |
| 订阅更高 Tier | 立即升级，按比例退还原订阅余额 |
| 订阅不同周期 | 当前周期结束后切换 |

### 12.5 家庭/团队共享 (未来)

| 场景 | 处理方式 |
|------|---------|
| Owner 降级 | 所有成员权限跟随降级 |
| Owner 升级 | 所有成员权限跟随升级 |
| 成员自己有订阅 | 取较高的 Tier |
| 成员离开团队 | 回退到自己的订阅 Tier |

### 12.6 促销码 / 优惠

| 场景 | 处理方式 |
|------|---------|
| 限时免费 Pro | 创建 `user_feature_overrides` 带过期时间 |
| 教育优惠 | 用户组 `edu_discount`，长期有效 |
| 推荐奖励 | 延长订阅时长 或 积分奖励 |
| 黑五折扣 | 通过 Stripe Coupon 处理 |

### 12.7 异常场景处理

| 场景 | 处理方式 |
|------|---------|
| Stripe Webhook 延迟 | 本地缓存 Tier，Webhook 到达后同步 |
| 数据库不一致 | 定时任务检查 Stripe 状态同步 |
| 时区问题 | 所有时间使用 UTC，前端转换显示 |
| 试用期中途升级又取消 | 恢复试用期剩余天数 (可配置) |

---

## 十三、场景支持矩阵汇总

| 场景 | 支持情况 | 说明 |
|------|:--------:|------|
| t1 试用期过期 - 项目只读 | ✅ | 进入编辑器时检测 |
| t1 试用期过期 - 禁止新建/复制 | ✅ | 按钮带锁 |
| t1 试用期过期 - 允许删除 | ✅ | 减少资源占用 |
| t1 试用期过期 - 状态提醒 | ✅ | Banner + Modal |
| Tier 降级 - 数据保留 | ✅ | 只锁定不删除 |
| Tier 降级 - 宽限期 | ✅ | 可配置天数 |
| Tier 降级 - 超额锁定 | ✅ | 最旧优先 |
| Tier 降级 - 成员保留 | ✅ | 已邀请的不踢出 |
| Tier 降级 - 商城商品保留 | ✅ | 继续上架 |
| Tier 升级 - 立即生效 | ✅ | 解锁所有资源 |
| 支付失败重试 | ✅ | 4 次重试机制 |
| 数据导出 | ✅ | 任何 Tier 可导出 |

---

## 十四、待实现清单

> ⚠️ **审计发现** (2026-02-04): 以下内容已设计但尚未在数据库/后端实现

### 14.1 数据库层 (🔴 P0)

| # | 待实现项 | 说明 | 优先级 |
|---|---------|------|--------|
| 1 | **添加 `profiles` 宽限期字段** | `grace_period_start`, `grace_period_end` | 🔴 P0 |
| 2 | **添加 `payment_records` 宽限期字段** | `grace_period_start`, `grace_period_end` | 🔴 P0 |
| 3 | **添加资源只读标记字段** | `is_read_only`, `read_only_reason`, `pending_lock`, `pending_lock_at` (projects/workspaces/folders/custom_assets) | 🔴 P0 |

### 14.2 后端逻辑层 (🔴 P0)

| # | 待实现项 | 说明 |
|---|---------|------|
| 1 | `DowngradeService` 实现 | 降级处理服务 (参见 §11) |
| 2 | `_check_exceeded_resources()` | 检查超额资源 |
| 3 | `_mark_resources_pending_lock()` | 标记待锁定资源 |
| 4 | `execute_grace_period_end()` | 宽限期结束执行锁定 |
| 5 | 宽限期定时任务 | 自动降级调度 |

### 14.3 前端组件 (🟡 P1)

| # | 待实现项 | 说明 |
|---|---------|------|
| 1 | `GracePeriodBanner` | 宽限期提醒 Banner |
| 2 | `LockedProjectCard` | 只读项目卡片 (带 🔒 图标) |
| 3 | `DowngradeConfirmModal` | 降级确认弹窗 |
| 4 | 资源选择 Modal | 超额时用户选择保留的资源 |

### 14.4 通知系统 (🟡 P1)

| # | 待实现项 | 说明 |
|---|---------|------|
| 1 | 降级通知邮件 | 降级前 7 天/1 天/当天 |
| 2 | 宽限期结束邮件 | 资源锁定通知 |

---

**END OF DOCUMENT**
