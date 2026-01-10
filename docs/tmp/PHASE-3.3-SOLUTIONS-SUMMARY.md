# Phase 3.3 问题解决方案总结

**创建时间**: 2026-01-10
**基于**: Phase 3.2 完成状态

---

## 🎯 你提出的 4 个问题

### 问题 1: Service 层调整
> 修改 Service 层的删除历史查询方法，使用 `list_deleted_recoverable()` 替代现有查询

### 问题 2: API 层展示
> DTO 中添加 `days_until_permanent_delete` 字段，前端显示恢复倒计时

### 问题 3: 定期清理任务
> Cron Job 物理删除过期 3-6 个月的记录，减少数据库存储空间

### 问题 4: 扩展软删除支持
> 为剩余 38 张表添加软删除支持

---

## ✅ 解决方案总结

### 📁 已创建的文档

#### 1. **[PHASE-3.3-IMPLEMENTATION-PLAN.md](PHASE-3.3-IMPLEMENTATION-PLAN.md)** (详细实施计划)

**内容**:
- ✅ 4 个任务的详细实施步骤
- ✅ 完整的代码示例
- ✅ 测试策略
- ✅ 时间线规划 (31h 总工时)

**重点章节**:
- Task 1: Service 层调整 (4h) - 完整代码示例
- Task 2: API 层增强 (3h) - DTO 计算属性 + 前端展示
- Task 3: 定期清理任务 (4h) - Python 脚本 + Cron Job
- Task 4: 扩展软删除 (20h) - 分 3 批次执行

#### 2. **[NEXT-STEPS-PRIORITY-GUIDE.md](NEXT-STEPS-PRIORITY-GUIDE.md)** (优先级指南)

**内容**:
- ✅ 3 种执行方案 (渐进式/一次性/按需)
- ✅ 优先级排序 (P1 > P2 > P3)
- ✅ 快速决策表
- ✅ 立即行动指南

**核心建议**:
```
🥇 优先级 1: Service 层 + API 层 (7h) - 必做
🥈 优先级 2: Batch 1 核心表 (6h) - 推荐
🥉 优先级 3: 定期清理任务 (4h) - 可选
🏅 优先级 4: Batch 2/3 剩余表 (14h) - 按需
```

---

## 🚀 核心代码示例

### 1️⃣ Service 层调整

#### 修改前 (旧代码)
```python
async def get_user_deleted_projects(
    self, user_id: str, offset: int = 0, limit: int = 20
) -> tuple[List[ProjectDTO], int]:
    """获取用户删除的项目"""
    # ❌ 手动查询，未过滤已过期记录
    projects, total = await self.repository.list(
        filters={"user_id": user_id, "is_deleted": True},
        offset=offset,
        limit=limit,
        order_by=("deleted_at", "desc")
    )
    return [self._to_dto(p) for p in projects], total
```

#### 修改后 (新代码)
```python
async def get_user_deleted_projects(
    self, user_id: str, offset: int = 0, limit: int = 20
) -> tuple[List[ProjectDTO], int]:
    """获取用户删除的项目 (仅恢复期内)"""
    # ✅ 使用新方法，自动过滤已过期
    projects, total = await self.repository.list_deleted_recoverable(
        user_id=user_id,
        offset=offset,
        limit=limit
    )
    return [self._to_dto(p) for p in projects], total
```

**改进点**:
- ✅ 自动过滤已过期记录
- ✅ 使用统一方法
- ✅ 代码更简洁

---

### 2️⃣ API 层增强

#### DTO 添加计算属性
```python
from datetime import datetime, timezone
from pydantic import BaseModel, computed_field

class ProjectDTO(BaseModel):
    id: str
    title: str
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    recovery_expires_at: Optional[datetime] = None

    # 🆕 计算属性: 距离永久删除的天数
    @computed_field
    @property
    def days_until_permanent_delete(self) -> Optional[int]:
        """计算剩余天数"""
        if not self.is_deleted or not self.recovery_expires_at:
            return None

        now = datetime.now(timezone.utc)
        if self.recovery_expires_at <= now:
            return None  # 已过期

        delta = self.recovery_expires_at - now
        return delta.days

    # 🆕 计算属性: 是否即将过期
    @computed_field
    @property
    def is_expiring_soon(self) -> bool:
        """是否即将过期 (≤ 3 天)"""
        days = self.days_until_permanent_delete
        return days is not None and days <= 3
```

#### API 响应示例
```json
{
  "items": [
    {
      "id": "proj_123",
      "title": "My Project",
      "is_deleted": true,
      "deleted_at": "2026-01-10T10:00:00Z",
      "recovery_expires_at": "2026-02-09T10:00:00Z",
      "days_until_permanent_delete": 29,
      "is_expiring_soon": false
    }
  ],
  "total": 1
}
```

#### 前端展示 (TypeScript)
```typescript
function DeletedProjectCard({ project }: { project: DeletedProject }) {
  return (
    <div className="card">
      <h3>{project.title}</h3>

      {/* 恢复倒计时 */}
      {project.days_until_permanent_delete !== null && (
        <div className={project.is_expiring_soon ? 'text-red-500' : 'text-gray-500'}>
          {project.is_expiring_soon && <WarningIcon />}
          还有 {project.days_until_permanent_delete} 天可恢复
        </div>
      )}

      <Button onClick={() => restore(project.id)}>恢复</Button>
    </div>
  );
}
```

**用户体验**:
- ✅ 清晰的倒计时提示
- ✅ 即将过期红色警告
- ✅ 一键恢复按钮

---

### 3️⃣ 定期清理任务

#### Python 清理脚本
```python
# scripts/cron/cleanup_expired_soft_deletes.py
import asyncio
from datetime import datetime, timezone, timedelta
from infrastructure.database.supabase_client import get_supabase_client

CLEANUP_AFTER_DAYS = 90  # 过期 90 天后物理删除
DRY_RUN = True  # 测试模式

async def cleanup_table(table_name: str, cutoff_date: datetime) -> int:
    """清理单个表的过期记录"""
    client = get_supabase_client()
    deleted_count = 0

    # 查询需要删除的记录
    result = client.table(table_name) \
        .select("id") \
        .eq("is_deleted", True) \
        .lt("recovery_expires_at", cutoff_date.isoformat()) \
        .execute()

    if not result.data:
        return 0

    ids = [row["id"] for row in result.data]

    if DRY_RUN:
        print(f"[DRY RUN] 将删除 {len(ids)} 条记录: {table_name}")
    else:
        # 物理删除
        client.table(table_name).delete().in_("id", ids).execute()
        print(f"已删除 {len(ids)} 条记录: {table_name}")

    return len(ids)

async def main():
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=CLEANUP_AFTER_DAYS)
    print(f"清理截止日期: {cutoff_date.isoformat()}")

    total = 0
    for table in ['projects', 'assets', ...]:  # 22 张表
        count = await cleanup_table(table, cutoff_date)
        total += count

    print(f"总共删除: {total} 条记录")

if __name__ == "__main__":
    asyncio.run(main())
```

#### Cron Job 配置
```yaml
# .github/workflows/cleanup-soft-deletes.yml
name: Cleanup Expired Soft Deletes

on:
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨 2 点 (UTC)

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run cleanup
        env:
          DRY_RUN: "true"
          CLEANUP_AFTER_DAYS: "90"
        run: python scripts/cron/cleanup_expired_soft_deletes.py
```

**功能特性**:
- ✅ 支持 DRY RUN 测试模式
- ✅ 可配置清理周期 (默认 90 天)
- ✅ 批量处理 (防止一次删除过多)
- ✅ 日志记录

---

### 4️⃣ 扩展软删除支持

#### 批量添加脚本
```python
# scripts/migrations/add_soft_delete_to_remaining_tables.py

BATCH1_TABLES = [  # P0 核心表
    'users', 'sessions', 'api_keys', 'webhooks',
    'workspace_members', 'project_collaborators',
    'asset_versions', 'marketplace_orders'
]

def generate_migration(table_name: str) -> str:
    """生成软删除迁移 SQL"""
    return f"""
-- 为 {table_name} 添加软删除支持

ALTER TABLE {table_name}
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

ALTER TABLE {table_name}
ADD CONSTRAINT chk_{table_name}_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

CREATE INDEX idx_{table_name}_deleted_recoverable
ON {table_name}(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();
"""
```

#### 执行策略
```bash
# Batch 1 (10 张核心表) - 6h
psql -d decodables < migrations/v3/003_soft_delete_batch1.sql

# Batch 2 (15 张辅助表) - 8h
psql -d decodables < migrations/v3/004_soft_delete_batch2.sql

# Batch 3 (13 张统计表) - 6h
psql -d decodables < migrations/v3/005_soft_delete_batch3.sql
```

**分批理由**:
- ✅ 降低风险 (逐步验证)
- ✅ 核心优先 (重要表先完成)
- ✅ 灵活调整 (可按需暂停)

---

## 📊 工作量估算

| 任务 | 工时 | 优先级 | 用户价值 | 技术债 |
|------|------|--------|----------|--------|
| **Task 1: Service 层** | 4h | P1 | ⭐⭐⭐⭐⭐ | 高 |
| **Task 2: API 层** | 3h | P1 | ⭐⭐⭐⭐⭐ | 中 |
| **Task 3: 清理任务** | 4h | P2 | ⭐⭐⭐ | 低 |
| **Task 4.1: Batch 1** | 6h | P0 | ⭐⭐⭐⭐ | 高 |
| **Task 4.2: Batch 2** | 8h | P1 | ⭐⭐⭐ | 中 |
| **Task 4.3: Batch 3** | 6h | P2 | ⭐⭐ | 低 |
| **总计** | 31h | | | |

---

## 🎯 推荐执行路径

### 路径 A: 快速交付 (推荐 👍)

```
Step 1 (Day 1): Task 1 + Task 2 (7h)
  → 用户立即看到倒计时提示

Step 2 (Day 2): Task 4.1 Batch 1 (6h)
  → 核心业务表支持软删除

Step 3 (Day 3): Task 3 清理任务 (4h)
  → 自动化清理

Step 4 (按需): Task 4.2 + 4.3 (14h)
  → 100% 表支持
```

**总工时**: 17h (核心) + 14h (可选) = 31h

### 路径 B: 最小化 MVP

```
仅执行: Task 1 + Task 2 (7h)
  → 解决用户体验问题
  → 其他任务按需执行
```

**总工时**: 7h

---

## 📝 验收标准

### Task 1: Service 层
- [ ] 所有 Service 使用 `list_deleted_recoverable()`
- [ ] 自动过滤已过期记录
- [ ] 测试覆盖率 ≥ 80%

### Task 2: API 层
- [ ] DTO 包含 `days_until_permanent_delete`
- [ ] DTO 包含 `is_expiring_soon`
- [ ] 前端可展示倒计时

### Task 3: 清理任务
- [ ] 支持 DRY RUN 模式
- [ ] Cron Job 每天运行
- [ ] 清理结果通知

### Task 4: 扩展软删除
- [ ] Batch 1: 10 张表完成
- [ ] Batch 2: 15 张表完成
- [ ] Batch 3: 13 张表完成

---

## 🚀 下一步

### 选项 1: 立即开始 (推荐)

告诉我:
```
"开始执行 Task 1: Service 层调整"
```

我会:
1. 搜索现有删除历史查询
2. 修改 Service 方法
3. 更新测试
4. Git 提交

### 选项 2: 先评估

告诉我:
```
"搜索一下有哪些 Service 需要修改"
```

我会帮你分析现有代码。

### 选项 3: 查看详细计划

阅读:
- [PHASE-3.3-IMPLEMENTATION-PLAN.md](PHASE-3.3-IMPLEMENTATION-PLAN.md) - 完整实施计划
- [NEXT-STEPS-PRIORITY-GUIDE.md](NEXT-STEPS-PRIORITY-GUIDE.md) - 优先级指南

---

## 📚 相关文档

1. **设计文档**:
   - [RECOVERY-PERIOD-EXPIRY-DESIGN.md](RECOVERY-PERIOD-EXPIRY-DESIGN.md) - 设计方案

2. **完成报告**:
   - [PHASE-3.2-COMPLETION-REPORT.md](PHASE-3.2-COMPLETION-REPORT.md) - Repository 层
   - [PHASE-3.2-CONSTRAINTS-INDEXES-COMPLETION.md](PHASE-3.2-CONSTRAINTS-INDEXES-COMPLETION.md) - 约束和索引

3. **实施计划**:
   - [PHASE-3.3-IMPLEMENTATION-PLAN.md](PHASE-3.3-IMPLEMENTATION-PLAN.md) - 详细计划
   - [NEXT-STEPS-PRIORITY-GUIDE.md](NEXT-STEPS-PRIORITY-GUIDE.md) - 优先级指南

4. **本文档**:
   - [PHASE-3.3-SOLUTIONS-SUMMARY.md](PHASE-3.3-SOLUTIONS-SUMMARY.md) - 解决方案总结

---

**创建时间**: 2026-01-10
**建议**: 从 Task 1+2 开始 (7h)，快速交付用户价值 🚀
**准备好了吗? 告诉我你的选择!** 💪
