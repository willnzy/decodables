# Phase 3.3 软删除功能完善实施计划

**创建时间**: 2026-01-10
**版本**: v1.0
**状态**: 📋 规划阶段

---

## 📋 目标概述

基于 Phase 3.2 完成的恢复期过期追踪功能，进一步完善软删除系统：

1. **Service 层适配** - 使用新的 `list_deleted_recoverable()` 方法
2. **API 层增强** - 添加恢复倒计时展示
3. **定期清理任务** - 自动清理过期记录
4. **扩展软删除支持** - 为剩余 38 张表添加软删除

---

## 🎯 任务分解

### Task 1: Service 层调整 (优先级: P1)

#### 目标
修改现有的删除历史查询方法，使用 `list_deleted_recoverable()` 替代旧的查询逻辑。

#### 涉及模块

通过代码搜索，找到所有使用删除历史查询的 Service:

1. **Projects Service** - `domains/creation/service.py`
2. **Assets Service** - `domains/assets/assets_service.py`
3. **其他可能的 Service** - 需要全面搜索

#### 实施步骤

**Step 1.1: 搜索现有删除历史查询**

```bash
# 搜索所有 Service 层的删除查询
grep -r "is_deleted.*True" decodables/domains/*/service.py
grep -r "eq.*is_deleted" decodables/domains/*/service.py
grep -r "deleted_at" decodables/domains/*/service.py
```

**Step 1.2: 修改 Service 方法**

以 Projects Service 为例:

```python
# ❌ 旧方法 (假设存在)
async def get_user_deleted_projects(
    self,
    user_id: str,
    offset: int = 0,
    limit: int = 20
) -> tuple[List[ProjectDTO], int]:
    """获取用户删除的项目 (旧实现)"""
    # 手动查询已删除记录
    projects, total = await self.repository.list(
        filters={"user_id": user_id, "is_deleted": True},
        offset=offset,
        limit=limit,
        order_by=("deleted_at", "desc")
    )
    return [self._to_dto(p) for p in projects], total

# ✅ 新方法
async def get_user_deleted_projects(
    self,
    user_id: str,
    offset: int = 0,
    limit: int = 20
) -> tuple[List[ProjectDTO], int]:
    """获取用户删除的项目 (可恢复期内)"""
    # 使用 BaseRepository 的新方法
    projects, total = await self.repository.list_deleted_recoverable(
        user_id=user_id,
        offset=offset,
        limit=limit
    )
    return [self._to_dto(p) for p in projects], total
```

**Step 1.3: 更新测试**

```python
# tests/domains/creation/test_service.py
@pytest.mark.asyncio
async def test_get_user_deleted_projects_only_recoverable():
    """只返回恢复期内的删除项目"""
    # Mock repository
    mock_repo = AsyncMock()

    # 模拟 3 个项目: 2 个可恢复, 1 个已过期
    future = datetime.now(timezone.utc) + timedelta(days=15)
    past = datetime.now(timezone.utc) - timedelta(days=1)

    mock_repo.list_deleted_recoverable.return_value = (
        [
            Project(id="p1", recovery_expires_at=future),
            Project(id="p2", recovery_expires_at=future),
        ],
        2  # Total count (不包括已过期)
    )

    service = ProjectService(repository=mock_repo)
    projects, total = await service.get_user_deleted_projects("user_123")

    assert len(projects) == 2
    assert total == 2
    mock_repo.list_deleted_recoverable.assert_called_once()
```

#### 预期成果

- ✅ 所有 Service 层删除历史查询使用统一方法
- ✅ 自动过滤已过期记录
- ✅ 测试覆盖率 ≥ 80%

---

### Task 2: API 层增强 (优先级: P1)

#### 目标
在 DTO 和 API 响应中添加恢复倒计时信息，方便前端展示。

#### 实施步骤

**Step 2.1: 更新 DTO**

```python
# domains/creation/dto.py
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, computed_field

class ProjectDTO(BaseModel):
    """项目 DTO"""
    id: str
    title: str
    user_id: str

    # 软删除字段
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    recovery_expires_at: Optional[datetime] = None

    # 🆕 计算属性: 距离永久删除的天数
    @computed_field
    @property
    def days_until_permanent_delete(self) -> Optional[int]:
        """
        计算距离永久删除还有多少天.

        Returns:
            - None: 未删除或已永久删除
            - int: 剩余天数 (≥ 0)
        """
        if not self.is_deleted or not self.recovery_expires_at:
            return None

        now = datetime.now(timezone.utc)
        if self.recovery_expires_at <= now:
            # 已过期
            return None

        delta = self.recovery_expires_at - now
        return delta.days

    # 🆕 计算属性: 恢复期剩余小时数
    @computed_field
    @property
    def hours_until_permanent_delete(self) -> Optional[int]:
        """计算距离永久删除还有多少小时"""
        if not self.is_deleted or not self.recovery_expires_at:
            return None

        now = datetime.now(timezone.utc)
        if self.recovery_expires_at <= now:
            return None

        delta = self.recovery_expires_at - now
        return int(delta.total_seconds() / 3600)

    # 🆕 计算属性: 是否即将过期 (≤ 3 天)
    @computed_field
    @property
    def is_expiring_soon(self) -> bool:
        """恢复期是否即将过期 (剩余 ≤ 3 天)"""
        days = self.days_until_permanent_delete
        return days is not None and days <= 3

    class Config:
        from_attributes = True
```

**Step 2.2: 更新 API 响应示例**

```python
# api/routers/projects.py
@router.get("/deleted", response_model=PaginatedResponse[ProjectDTO])
async def list_deleted_projects(
    offset: int = 0,
    limit: int = 20,
    user_id: str = Depends(get_current_user_id)
):
    """
    获取用户的删除历史 (恢复期内).

    响应示例:
    {
        "items": [
            {
                "id": "proj_123",
                "title": "My Project",
                "is_deleted": true,
                "deleted_at": "2026-01-10T10:00:00Z",
                "recovery_expires_at": "2026-02-09T10:00:00Z",
                "days_until_permanent_delete": 29,
                "hours_until_permanent_delete": 696,
                "is_expiring_soon": false
            }
        ],
        "total": 1,
        "offset": 0,
        "limit": 20
    }
    """
    projects, total = await project_service.get_user_deleted_projects(
        user_id=user_id,
        offset=offset,
        limit=limit
    )

    return PaginatedResponse(
        items=projects,
        total=total,
        offset=offset,
        limit=limit
    )
```

**Step 2.3: 前端展示示例**

```typescript
// decodables-fe/app/dashboard/deleted/page.tsx
interface DeletedProject {
  id: string;
  title: string;
  deleted_at: string;
  recovery_expires_at: string;
  days_until_permanent_delete: number | null;
  hours_until_permanent_delete: number | null;
  is_expiring_soon: boolean;
}

function DeletedProjectCard({ project }: { project: DeletedProject }) {
  return (
    <Card>
      <h3>{project.title}</h3>

      {/* 恢复倒计时 */}
      {project.days_until_permanent_delete !== null && (
        <div className={project.is_expiring_soon ? 'text-red-500' : 'text-gray-500'}>
          {project.is_expiring_soon && <WarningIcon />}
          还有 {project.days_until_permanent_delete} 天可恢复
        </div>
      )}

      {/* 操作按钮 */}
      <Button onClick={() => restoreProject(project.id)}>恢复</Button>
      <Button variant="danger" onClick={() => permanentDelete(project.id)}>
        永久删除
      </Button>
    </Card>
  );
}
```

#### 预期成果

- ✅ DTO 自动计算恢复倒计时
- ✅ API 响应包含倒计时信息
- ✅ 前端可展示"还有 X 天可恢复"
- ✅ 即将过期的记录高亮提示

---

### Task 3: 定期清理任务 (优先级: P2)

#### 目标
创建 Cron Job 定期物理删除已过期 3-6 个月的软删除记录，减少数据库存储。

#### 实施步骤

**Step 3.1: 创建清理脚本**

```python
# scripts/cron/cleanup_expired_soft_deletes.py
"""
定期清理已过期的软删除记录

使用场景:
- Cron Job 每天凌晨 2 点运行
- 物理删除已过期 90 天的软删除记录

配置:
- CLEANUP_AFTER_DAYS: 90 (默认)
- DRY_RUN: True (测试模式，不实际删除)
- BATCH_SIZE: 100 (每批处理数量)
"""

import asyncio
import os
from datetime import datetime, timezone, timedelta
from typing import List
import logging

from infrastructure.database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# 配置
CLEANUP_AFTER_DAYS = int(os.getenv("CLEANUP_AFTER_DAYS", "90"))  # 90 天后物理删除
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))

# 需要清理的表 (22 张软删除表)
TABLES_TO_CLEANUP = [
    # Phase 2
    'profiles', 'projects', 'project_versions', 'assets',
    'marketplace_listings', 'asset_categories', 'system_assets',
    'notifications', 'campaign_participations', 'campaign_dismissals',
    'onboarding_steps', 'user_onboarding_progress', 'referrals',
    'credit_transactions',
    # Phase 3.1
    'marketplace_favorites', 'marketplace_reviews', 'campaigns',
    'daily_themes', 'holidays', 'asset_prompt_templates',
    'support_tickets', 'support_replies'
]

async def cleanup_table(table_name: str, cutoff_date: datetime) -> int:
    """
    清理单个表的过期记录.

    Args:
        table_name: 表名
        cutoff_date: 截止日期 (早于此日期的记录将被删除)

    Returns:
        删除的记录数
    """
    client = get_supabase_client()
    deleted_count = 0

    try:
        # 查询需要删除的记录 ID (分批)
        offset = 0
        while True:
            # 查询一批过期记录
            result = client.table(table_name) \
                .select("id") \
                .eq("is_deleted", True) \
                .lt("recovery_expires_at", cutoff_date.isoformat()) \
                .range(offset, offset + BATCH_SIZE - 1) \
                .execute()

            if not result.data:
                break

            ids = [row["id"] for row in result.data]

            if DRY_RUN:
                logger.info(f"  [DRY RUN] 将删除 {len(ids)} 条记录: {table_name}")
                deleted_count += len(ids)
            else:
                # 物理删除
                delete_result = client.table(table_name) \
                    .delete() \
                    .in_("id", ids) \
                    .execute()

                deleted_count += len(ids)
                logger.info(f"  已删除 {len(ids)} 条记录: {table_name}")

            offset += BATCH_SIZE

            # 如果返回数量 < BATCH_SIZE，说明已经没有更多记录
            if len(result.data) < BATCH_SIZE:
                break

    except Exception as e:
        logger.error(f"  清理 {table_name} 失败: {e}")
        raise

    return deleted_count

async def cleanup_expired_soft_deletes():
    """清理所有表的过期软删除记录"""

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=CLEANUP_AFTER_DAYS)

    logger.info("=" * 80)
    logger.info(f"开始清理过期软删除记录")
    logger.info(f"截止日期: {cutoff_date.isoformat()} (过期 {CLEANUP_AFTER_DAYS} 天)")
    logger.info(f"模式: {'DRY RUN (测试)' if DRY_RUN else 'PRODUCTION (实际删除)'}")
    logger.info("=" * 80)

    total_deleted = 0

    for table_name in TABLES_TO_CLEANUP:
        logger.info(f"\n处理表: {table_name}")
        try:
            count = await cleanup_table(table_name, cutoff_date)
            total_deleted += count
            logger.info(f"  ✅ {table_name}: 删除 {count} 条记录")
        except Exception as e:
            logger.error(f"  ❌ {table_name}: 失败 - {e}")

    logger.info("\n" + "=" * 80)
    logger.info(f"清理完成! 总共删除: {total_deleted} 条记录")
    logger.info("=" * 80)

    return total_deleted

async def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    try:
        deleted_count = await cleanup_expired_soft_deletes()
        print(f"\n✅ 清理成功! 删除 {deleted_count} 条记录")
        return 0
    except Exception as e:
        logger.error(f"\n❌ 清理失败: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
```

**Step 3.2: 添加 Cron Job 配置**

```yaml
# .github/workflows/cleanup-soft-deletes.yml
name: Cleanup Expired Soft Deletes

on:
  schedule:
    # 每天凌晨 2 点运行 (UTC)
    - cron: '0 2 * * *'
  workflow_dispatch:  # 允许手动触发

jobs:
  cleanup:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run cleanup (DRY RUN)
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
          DRY_RUN: "true"
          CLEANUP_AFTER_DAYS: "90"
        run: |
          python scripts/cron/cleanup_expired_soft_deletes.py

      # 如果需要实际删除，取消注释下面的步骤
      # - name: Run cleanup (PRODUCTION)
      #   env:
      #     SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
      #     SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
      #     DRY_RUN: "false"
      #     CLEANUP_AFTER_DAYS: "90"
      #   run: |
      #     python scripts/cron/cleanup_expired_soft_deletes.py
```

**Step 3.3: 添加监控和通知**

```python
# scripts/cron/cleanup_expired_soft_deletes.py (添加)
async def send_cleanup_notification(total_deleted: int, errors: List[str]):
    """发送清理结果通知到 Slack/Email"""
    import os
    import httpx

    slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
    if not slack_webhook:
        return

    message = f"""
🗑️ 软删除清理报告 ({datetime.now().strftime('%Y-%m-%d')})

✅ 成功删除: {total_deleted} 条记录
❌ 失败: {len(errors)} 个表

配置:
- 清理周期: {CLEANUP_AFTER_DAYS} 天
- 模式: {'DRY RUN' if DRY_RUN else 'PRODUCTION'}

{('错误:\n' + '\n'.join(errors)) if errors else ''}
"""

    async with httpx.AsyncClient() as client:
        await client.post(slack_webhook, json={"text": message})
```

#### 预期成果

- ✅ 自动清理脚本 (支持 DRY RUN 测试模式)
- ✅ Cron Job 每天自动运行
- ✅ 清理结果通知 (Slack/Email)
- ✅ 减少数据库存储空间

---

### Task 4: 扩展软删除支持 (优先级: P3)

#### 目标
为剩余 38 张表添加软删除支持。

#### 现状分析

当前软删除支持情况:
- ✅ 已支持: 22 张表 (36.7%)
- ⚠️  待添加: 38 张表 (63.3%)
- 📊 总计: 60 张表

#### 实施策略

**分批次添加** (按业务重要性):

**Batch 1: 核心业务表 (P0)** - 10 张
1. `users` - 用户账户 (如果存在)
2. `sessions` - 用户会话
3. `api_keys` - API 密钥
4. `webhooks` - Webhook 配置
5. `integrations` - 第三方集成
6. `workspace_members` - 工作空间成员
7. `team_members` - 团队成员
8. `project_collaborators` - 项目协作者
9. `asset_versions` - 素材版本
10. `marketplace_orders` - 市场订单

**Batch 2: 辅助功能表 (P1)** - 15 张
1. `comments` - 评论
2. `likes` - 点赞
3. `shares` - 分享
4. `bookmarks` - 收藏
5. `tags` - 标签
6. `categories` - 分类
7. `collections` - 合集
8. `playlists` - 播放列表
9. `templates` - 模板
10. `presets` - 预设
11. `filters` - 过滤器
12. `effects` - 特效
13. `animations` - 动画
14. `transitions` - 转场
15. `stickers` - 贴纸库

**Batch 3: 统计分析表 (P2)** - 13 张
1. `analytics_events` - 分析事件
2. `user_activities` - 用户活动
3. `feature_usage` - 功能使用
4. `error_logs` - 错误日志
5. `audit_logs` - 审计日志
6. `metrics` - 指标数据
7. `reports` - 报表
8. `exports` - 导出记录
9. `imports` - 导入记录
10. `backups` - 备份记录
11. `jobs` - 任务队列
12. `schedules` - 定时任务
13. `webhooks_logs` - Webhook 日志

#### 实施步骤

**Step 4.1: 创建批量添加脚本**

```python
# scripts/migrations/add_soft_delete_to_remaining_tables.py
"""
为剩余 38 张表批量添加软删除支持

执行步骤:
1. 添加软删除字段 (is_deleted, deleted_at, recovery_expires_at)
2. 添加约束
3. 添加索引
4. 添加触发器
"""

BATCH1_TABLES = [
    'users', 'sessions', 'api_keys', 'webhooks', 'integrations',
    'workspace_members', 'team_members', 'project_collaborators',
    'asset_versions', 'marketplace_orders'
]

BATCH2_TABLES = [
    'comments', 'likes', 'shares', 'bookmarks', 'tags',
    'categories', 'collections', 'playlists', 'templates',
    'presets', 'filters', 'effects', 'animations',
    'transitions', 'stickers'
]

BATCH3_TABLES = [
    'analytics_events', 'user_activities', 'feature_usage',
    'error_logs', 'audit_logs', 'metrics', 'reports',
    'exports', 'imports', 'backups', 'jobs',
    'schedules', 'webhooks_logs'
]

def generate_soft_delete_migration(table_name: str) -> str:
    """生成软删除迁移 SQL"""
    return f"""
-- 为 {table_name} 添加软删除支持

-- 1. 添加字段
ALTER TABLE {table_name}
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

-- 2. 添加约束
ALTER TABLE {table_name}
ADD CONSTRAINT chk_{table_name}_deleted_at_consistency
CHECK (
    (is_deleted = false AND deleted_at IS NULL) OR
    (is_deleted = true AND deleted_at IS NOT NULL)
);

ALTER TABLE {table_name}
ADD CONSTRAINT chk_{table_name}_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

-- 3. 添加索引
CREATE INDEX IF NOT EXISTS idx_{table_name}_active
ON {table_name}(user_id, created_at DESC)
WHERE is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_{table_name}_deleted_recoverable
ON {table_name}(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

-- 4. 添加触发器
DROP TRIGGER IF EXISTS trg_{table_name}_set_deleted_at ON {table_name};
CREATE TRIGGER trg_{table_name}_set_deleted_at
    BEFORE INSERT OR UPDATE ON {table_name}
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

COMMENT ON COLUMN {table_name}.recovery_expires_at IS '恢复期截止时间,过期后用户看不到此删除记录';
"""
```

**Step 4.2: 分批执行迁移**

```bash
# Phase 3.3.1 - Batch 1 (P0 核心业务表)
psql -U postgres -d decodables < migrations/v3/003_soft_delete_batch1.sql

# Phase 3.3.2 - Batch 2 (P1 辅助功能表)
psql -U postgres -d decodables < migrations/v3/004_soft_delete_batch2.sql

# Phase 3.3.3 - Batch 3 (P2 统计分析表)
psql -U postgres -d decodables < migrations/v3/005_soft_delete_batch3.sql
```

#### 预期成果

- ✅ 所有 60 张表支持软删除 (100% 覆盖)
- ✅ 统一的删除恢复机制
- ✅ 完整的约束和索引
- ✅ 自动化触发器

---

## 📅 实施时间线

| Phase | 任务 | 优先级 | 预计工时 | 依赖 |
|-------|------|--------|----------|------|
| **3.3.1** | Service 层调整 | P1 | 4h | Phase 3.2 |
| **3.3.2** | API 层增强 | P1 | 3h | 3.3.1 |
| **3.3.3** | 定期清理任务 | P2 | 4h | Phase 3.2 |
| **3.3.4** | 扩展软删除 - Batch 1 | P0 | 6h | - |
| **3.3.5** | 扩展软删除 - Batch 2 | P1 | 8h | 3.3.4 |
| **3.3.6** | 扩展软删除 - Batch 3 | P2 | 6h | 3.3.5 |
| **总计** | | | **31h** | |

**建议执行顺序**:
1. ✅ **Week 1**: Task 1 (Service 层) + Task 2 (API 层) - 7h
2. ✅ **Week 2**: Task 4.1 (Batch 1 核心表) - 6h
3. ⚠️  **Week 3**: Task 3 (清理任务) + Task 4.2 (Batch 2) - 12h
4. ⚠️  **Week 4**: Task 4.3 (Batch 3) + 测试 - 6h

---

## 🎯 验收标准

### Task 1: Service 层
- [ ] 所有 Service 使用 `list_deleted_recoverable()`
- [ ] 自动过滤已过期记录
- [ ] 测试覆盖率 ≥ 80%

### Task 2: API 层
- [ ] DTO 包含 `days_until_permanent_delete` 字段
- [ ] DTO 包含 `is_expiring_soon` 字段
- [ ] API 响应包含倒计时信息

### Task 3: 清理任务
- [ ] 清理脚本支持 DRY RUN 模式
- [ ] Cron Job 每天自动运行
- [ ] 清理结果通知 (Slack/Email)

### Task 4: 扩展软删除
- [ ] Batch 1: 10 张核心表添加软删除
- [ ] Batch 2: 15 张辅助表添加软删除
- [ ] Batch 3: 13 张统计表添加软删除
- [ ] 所有表测试通过

---

## 📊 成本收益分析

### 开发成本
- **开发工时**: 31 小时
- **测试工时**: 10 小时
- **总计**: 41 小时 (~1 周)

### 预期收益

1. **用户体验提升**
   - ✅ 清晰的恢复倒计时提示
   - ✅ 即将过期的高亮警告
   - ✅ 统一的删除恢复体验

2. **系统性能提升**
   - ✅ 自动清理减少数据库负载
   - ✅ 索引优化提升查询速度
   - ✅ 减少存储空间占用

3. **数据安全提升**
   - ✅ 100% 表支持软删除
   - ✅ 误删数据可恢复
   - ✅ 完整的审计日志

4. **运维成本降低**
   - ✅ 自动化清理任务
   - ✅ 减少手动数据恢复请求
   - ✅ 统一的删除管理

---

## 🚀 快速开始

### 立即执行 (P1 高优先级)

```bash
# 1. Service 层调整
cd /Users/zhangyi/Code_all/AI-WEB/decodables

# 搜索现有删除历史查询
grep -r "is_deleted.*True" domains/*/service.py

# 2. API 层增强
# 修改 DTO 添加计算属性 (见 Task 2 示例代码)

# 3. 运行测试
pytest tests/domains/ -v -k "deleted"
```

### 后续执行 (P2 中优先级)

```bash
# 定期清理任务
python scripts/cron/cleanup_expired_soft_deletes.py

# 扩展软删除支持
python scripts/migrations/add_soft_delete_to_remaining_tables.py --batch 1
```

---

**创建时间**: 2026-01-10
**预计完成**: 2026-02-10 (1 个月)
**优先级**: P1 (Service/API) > P2 (清理任务) > P3 (扩展支持)
**负责人**: 开发团队

如有疑问，请查阅:
- [Phase 3.2 完成报告](PHASE-3.2-COMPLETION-REPORT.md)
- [恢复期设计文档](RECOVERY-PERIOD-EXPIRY-DESIGN.md)
