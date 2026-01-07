# Decodables 后台架构清理与优化计划

## 执行总结

**当前架构健康度**: 85/100
**总工作量**: 5-6 天
**优先级**: P1 (高) > P2 (中) > P3 (低)

---

## 现状分析

### 代码统计

| 目录 | 文件数 | 代码行数 | 状态 |
|------|--------|----------|------|
| core/ | 28 | 2,893 | ✅ 框架层完整 |
| shared/ | 34 | 7,136 | ✅ 共享层完整 |
| domains/ | 52 | 9,651 | ✅ 领域层完整 |
| application/ | 32 | 4,278 | ✅ 应用层完整 |
| infrastructure/ | 33 | 7,162 | ⚠️ 有 extended 文件 |
| api/ | 43 | 10,447 | ⚠️ 部分文件过大 |
| tests/ | 133+ | 39,603 | ⚠️ 有重复测试 |
| **总计** | **439** | **85,268** | |

### 主要问题

1. **10 个 Extended 仓储文件** (向后兼容层,需删除)
2. **3 个根目录兼容文件** (exceptions.py, middleware.py, schemas.py)
3. **测试文件重复** (tests/api/ vs tests/api/user/)
4. **2 个超大 API 文件** (marketplace.py 615行, generation.py 549行)

---

## Phase 1: Extended 仓储清理 (P1, 2-3天)

### 背景
10 个 `*_extended.py` 文件是之前从 `services/db/` 迁移时创建的向后兼容层,导致:
- 两套仓储实现并存 (标准 + extended)
- 混淆 DDD 职责边界
- 增加维护成本

### 文件清单

| Extended 文件 | 标准文件 | 行数 | 主要方法 |
|--------------|---------|------|---------|
| listing_repository_extended.py | listing_repository.py | 576 | get_marketplace_listings, get_trending |
| project_repository_extended.py | project_repository.py | 507 | get_dashboard_projects, get_deleted |
| credit_repository_extended.py | credit_repository.py | 445 | deduct_credits, add_credits |
| user_repository_extended.py | user_repository.py | 305 | search_users, get_by_tier |
| asset_repository_extended.py | asset_repository.py | 420 | save_asset, get_deleted_assets |
| admin_users_repository_extended.py | - | 380 | admin_adjust_credits, get_full_audit |
| admin_stats_repository_extended.py | - | 468 | log_user_event, get_analytics |
| admin_moderation_repository_extended.py | - | 315 | create_moderation, get_queue |
| notification_repository_extended.py | - | 298 | send_notification, get_user_notifications |
| support_repository_extended.py | - | 286 | create_ticket, send_feedback |

### 执行步骤

**Day 1: 核心仓储合并**
```bash
1. listing_repository: 合并 get_marketplace_listings, get_trending 等方法
2. project_repository: 合并 get_dashboard_projects, get_deleted_projects 等
3. credit_repository: 合并 deduct_credits, add_credits (已有,验证)
4. user_repository: 合并 search_users, get_users_by_tier 等

测试验证: pytest tests/domains/
```

**Day 2: Admin 仓储合并**
```bash
1. 创建 admin_repository.py (或合并到现有文件)
2. 迁移 admin_users_repository_extended 方法
3. 迁移 admin_stats_repository_extended 方法
4. 迁移 admin_moderation_repository_extended 方法

测试验证: pytest tests/api/admin/
```

**Day 3: 其他仓储合并 + 清理**
```bash
1. asset_repository: 合并 save_asset, get_deleted_assets 等
2. notification_repository: 合并发送通知相关方法
3. support_repository: 合并工单相关方法

4. 搜索所有 *Extended 引用并替换:
   grep -r "Extended" api/ infrastructure/ --include="*.py"

5. 删除 10 个 extended 文件
6. 运行完整测试套件

测试验证: pytest tests/ -v
```

---

## Phase 2: 测试重复清理 (P1, 1天)

### 背景
发现 `tests/api/` (25 files) 和 `tests/api/user/` (27 files) 可能存在重复测试。

### 执行步骤

**分析重复**
```bash
# 1. 列出两个目录的文件
ls tests/api/*.py > /tmp/api_root.txt
ls tests/api/user/*.py > /tmp/api_user.txt

# 2. 比较文件名
comm -12 <(sort /tmp/api_root.txt) <(sort /tmp/api_user.txt)

# 3. 对比内容
for file in tests/api/test_*_api.py; do
    user_file="tests/api/user/$(basename $file _api.py).py"
    if [ -f "$user_file" ]; then
        diff -q "$file" "$user_file"
    fi
done
```

**清理策略**
```
原则:
- tests/api/ → 保留端到端集成测试
- tests/api/user/ → 保留用户路由单元测试
- tests/api/admin/ → 保留管理路由单元测试

如果内容完全相同 → 删除 tests/api/ 中的文件
如果内容部分重叠 → 合并到 tests/api/user/ 或 tests/api/admin/
```

---

## Phase 3: 向后兼容层清理 (P2, 0.5天)

### 文件清单

| 文件 | 行数 | 引用次数 | 作用 |
|------|------|---------|------|
| exceptions.py | 88 | 2 | 重导出 core.exceptions |
| middleware.py | 252 | 2 | 已迁移到 core.middleware |
| schemas.py | 13 | 未知 | 重导出 schemas/ 包 |

### 执行步骤

```bash
# 1. 查找所有引用
grep -r "from exceptions import" --include="*.py"
grep -r "from middleware import" --include="*.py"
grep -r "from schemas import" --include="*.py" | grep -v "from schemas\."

# 2. 替换引用
find . -name "*.py" -exec sed -i '' \
  's/from exceptions import/from core.exceptions import/g' {} \;

find . -name "*.py" -exec sed -i '' \
  's/from middleware import/from core.middleware import/g' {} \;

# 3. 验证语法
python -m py_compile $(find . -name "*.py" -not -path "./__pycache__/*")

# 4. 删除文件
rm exceptions.py middleware.py schemas.py

# 5. 测试
pytest tests/ -v
```

---

## Phase 4: API 文件拆分 (P2, 1天)

### 目标
将超大 API 文件拆分为多个模块,提升可维护性。

### 文件清单

| 文件 | 行数 | 建议拆分 |
|------|------|---------|
| api/user/marketplace.py | 615 | → marketplace_listings.py (300行) + marketplace_purchases.py (200行) + marketplace_sellers.py (115行) |
| api/user/generation.py | 549 | → generation_images.py (300行) + generation_story.py (150行) + generation_pdf.py (99行) |

### 执行步骤

**拆分 marketplace.py**
```python
# marketplace_listings.py (300行)
- GET /marketplace
- GET /marketplace/{listing_id}
- POST /marketplace/publish

# marketplace_purchases.py (200行)
- GET /marketplace/purchases
- POST /marketplace/{listing_id}/purchase
- POST /marketplace/{listing_id}/download

# marketplace_sellers.py (115行)
- GET /marketplace/seller/stats
- PUT /marketplace/{listing_id}
- DELETE /marketplace/{listing_id}
```

**拆分 generation.py**
```python
# generation_images.py (300行)
- POST /generation/images
- POST /generation/images/async

# generation_story.py (150行)
- POST /generation/story
- GET /generation/inspiration

# generation_pdf.py (99行)
- POST /generation/pdf
```

---

## Phase 5: 最终清理 (P3, 0.1天)

```bash
# 删除 schemas.py (确认无引用后)
rm schemas.py

# 清理临时文件
rm -f /tmp/api_root.txt /tmp/api_user.txt

# 最终验证
pytest tests/ -v
python -m py_compile $(find . -name "*.py" -not -path "./__pycache__/*")
```

---

## 验收标准

### 架构健康度目标: 95/100

- ✅ 无 extended 仓储文件
- ✅ 无向后兼容层文件
- ✅ 无重复测试文件
- ✅ 单文件 ≤ 400 行 (API 层)
- ✅ 测试通过率 ≥ 90%

### 代码指标

| 指标 | 当前 | 目标 |
|------|------|------|
| Python 文件数 | 439 | ~420 (删除 ~19 个) |
| 总代码行数 | 85,268 | ~82,000 (减少冗余) |
| Extended 文件 | 10 | 0 |
| 兼容层文件 | 3 | 0 |
| 超 400 行 API 文件 | 2 | 0 |

---

## 风险控制

### 回滚策略

每个 Phase 完成后立即提交 git:
```bash
git add -A
git commit -m "refactor(phase-N): [描述]"
git push
```

如果发现问题:
```bash
git revert HEAD
```

### 测试要求

每个 Phase 完成后必须:
1. 运行单元测试: `pytest tests/`
2. 运行集成测试: `pytest tests/integration/`
3. 手动测试关键 API 端点
4. 检查语法: `python -m py_compile`

---

## 时间线

| 阶段 | 工作量 | 优先级 | 预计完成 |
|------|--------|--------|----------|
| Phase 1: Extended 仓储清理 | 2-3天 | P1 | Day 1-3 |
| Phase 2: 测试重复清理 | 1天 | P1 | Day 4 |
| Phase 3: 向后兼容层清理 | 0.5天 | P2 | Day 5 |
| Phase 4: API 文件拆分 | 1天 | P2 | Day 6 |
| Phase 5: 最终清理 | 0.1天 | P3 | Day 6 |

**总计**: 5-6 天

---

**计划制定**: 2026-01-08
**预计完成**: 2026-01-15
**负责人**: 开发团队
