# Phase 8: services/db/ 完全迁移计划

> **目标**: 将 services/db/ (3088 行) 完全迁移到 v2 架构,确保零功能遗漏

**日期**: 2026-01-07
**状态**: Planning

---

## 迁移原则

1. ✅ **零功能遗漏** - 所有函数必须迁移
2. ✅ **保持业务逻辑不变** - 只改结构,不改逻辑
3. ✅ **符合 DDD 架构** - domains → application → infrastructure
4. ✅ **向后兼容** - 创建兼容层
5. ✅ **逐个验证** - 每个文件迁移后验证

---

## 迁移策略

### 策略: 增强现有 Repositories + 新建必要 Repositories

**原因**:
- 已有 7 个 repositories 覆盖核心 domains
- 避免重复代码
- 保持架构一致性

---

## 文件迁移映射

### Group 1: 已有 Repository (增强功能)

| 源文件 | 目标 Repository | 行数 | 操作 |
|--------|----------------|------|------|
| **users.py** | user_repository.py + credit_repository.py | ~350 | 拆分迁移 |
| **projects.py** | project_repository.py | ~300 | 增强 |
| **marketplace.py** | listing_repository.py | ~418 | 增强 |

### Group 2: 新建 Repository (核心业务)

| 源文件 | 目标 Repository | Domain | 行数 | 优先级 |
|--------|----------------|--------|------|--------|
| **config.py** | config_repository.py | platform | ~240 | P0 |
| **payments.py** | payment_repository.py | billing | ~140 | P0 |
| **assets.py** | asset_repository.py | creation | ~180 | P1 |

### Group 3: 新建 Infrastructure 模块

| 源文件 | 目标 | 行数 | 优先级 |
|--------|------|------|--------|
| **notifications.py** | infrastructure/notifications/ | ~130 | P1 |
| **support.py** | infrastructure/support/ | ~120 | P2 |
| **admin_users.py** | infrastructure/admin/users.py | ~150 | P2 |
| **admin_moderation.py** | infrastructure/admin/moderation.py | ~170 | P2 |
| **admin_stats.py** | infrastructure/admin/analytics.py | ~600 | P2 |

### Group 4: 工具函数

| 源文件 | 目标 | 操作 |
|--------|------|------|
| **utils.py** | 分散到各 domain/infrastructure | 分析后分配 |

---

## 迁移顺序 (优先级)

### Phase 8.1: 核心配置 (P0)
**文件**: config.py → platform/repository.py
**原因**: 系统配置是基础设施,优先迁移

**步骤**:
1. 检查 platform domain 是否需要 IConfigRepository
2. 创建 infrastructure/repositories/config_repository.py
3. 迁移所有配置相关函数
4. 更新 API 使用新 repository
5. 验证功能

### Phase 8.2: 支付记录 (P0)
**文件**: payments.py → billing/repository.py
**原因**: 与 credit_repository 密切相关

**步骤**:
1. 扩展 billing domain (如需要)
2. 创建 infrastructure/repositories/payment_repository.py
3. 迁移支付记录函数
4. 更新 API
5. 验证功能

### Phase 8.3: 用户数据拆分 (P0)
**文件**: users.py → user_repository.py + credit_repository.py
**原因**: 高重叠度,需要仔细拆分

**步骤**:
1. 分析 users.py 每个函数归属
2. Profile 相关 → user_repository.py
3. Credit 相关 → credit_repository.py
4. Tier/Discount → 确定归属
5. 更新所有导入
6. 验证功能

### Phase 8.4: 项目增强 (P1)
**文件**: projects.py → project_repository.py
**步骤**:
1. 对比现有 project_repository 与 projects.py
2. 将缺失函数添加到 project_repository
3. 更新 API
4. 验证功能

### Phase 8.5: 市场增强 (P1)
**文件**: marketplace.py → listing_repository.py
**步骤**:
1. 对比现有 listing_repository 与 marketplace.py
2. 将缺失函数添加到 listing_repository
3. 更新 API
4. 验证功能

### Phase 8.6: 资产管理 (P1)
**文件**: assets.py → asset_repository.py (新建)
**步骤**:
1. 创建 creation domain 的 Asset aggregate (如需要)
2. 创建 infrastructure/repositories/asset_repository.py
3. 迁移资产相关函数
4. 更新 API
5. 验证功能

### Phase 8.7: 通知系统 (P1)
**文件**: notifications.py → infrastructure/notifications/
**步骤**:
1. 创建 infrastructure/notifications/ 模块
2. 决定是否需要 domain (可能不需要)
3. 迁移通知函数
4. 更新 API
5. 验证功能

### Phase 8.8: 管理员功能 (P2)
**文件**: admin_*.py → infrastructure/admin/
**步骤**:
1. 创建 infrastructure/admin/ 目录结构
2. 分别迁移 users.py, moderation.py, analytics.py
3. 更新管理员 API
4. 验证功能

### Phase 8.9: 支持系统 (P2)
**文件**: support.py → infrastructure/support/
**步骤**:
1. 创建 infrastructure/support/ 模块
2. 迁移支持/反馈/报告函数
3. 更新 API
4. 验证功能

### Phase 8.10: 工具函数清理 (P2)
**文件**: utils.py
**步骤**:
1. 分析每个工具函数的用途
2. 分散到相应的 domain 或 infrastructure
3. 更新所有引用
4. 删除 utils.py

---

## 验证检查清单

每个阶段完成后必须验证:

- [ ] 所有函数已迁移 (无遗漏)
- [ ] 业务逻辑保持不变
- [ ] API 调用正常工作
- [ ] 导入路径正确更新
- [ ] 测试通过 (如有)
- [ ] 无 lint 错误
- [ ] Git commit 提交

---

## 向后兼容策略

为了确保平滑过渡,创建兼容层:

```python
# services/db/__init__.py (过渡期保留)
"""
数据访问层 (已迁移到 infrastructure/repositories)

此文件保留用于向后兼容,所有导入重定向到新位置.
"""

# 重定向到新位置
from infrastructure.repositories.user_repository import SupabaseUserRepository
from infrastructure.repositories.config_repository import SupabaseConfigRepository

# 创建兼容函数
_user_repo = SupabaseUserRepository(get_database_client())

def get_user_profile(user_id: str):
    """兼容函数 - 调用新 repository"""
    return _user_repo.get_by_id(user_id)

# ... 其他兼容函数
```

**清理计划**: 所有 API 更新后,删除兼容层

---

## 风险控制

| 风险 | 缓解措施 |
|------|----------|
| 功能遗漏 | 逐行对比,创建迁移清单 |
| 逻辑改变 | 只改结构,不改逻辑 |
| API 中断 | 创建兼容层,渐进式迁移 |
| 测试不足 | 每阶段手动验证关键功能 |

---

## 预估工作量

| 阶段 | 文件数 | 行数 | 预估时间 |
|------|--------|------|----------|
| 8.1-8.3 (P0) | 3 | ~730 | 2-3 小时 |
| 8.4-8.7 (P1) | 4 | ~1028 | 3-4 小时 |
| 8.8-8.10 (P2) | 5 | ~1330 | 2-3 小时 |
| **总计** | **12** | **3088** | **7-10 小时** |

---

## 成功标准

- [x] 所有 services/db/*.py 文件已删除
- [x] 所有函数已迁移到对应位置
- [x] 所有 API 正常工作
- [x] 架构符合 DDD 原则
- [x] 文档已更新
- [x] 代码已提交

---

**下一步**: 开始 Phase 8.1 - 迁移 config.py
