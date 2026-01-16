# API 整合重构方案

> **版本**: v1.0
> **创建日期**: 2026-01-16
> **状态**: 草案 (Draft)

---

## 一、现状分析

### 1.1 API 端点统计

| 分类 | 端点数量 | 文件数量 |
|------|----------|----------|
| User API | 135 | 29 模块 |
| Admin API | 171 | 21 模块 |
| **总计** | **306** | **50 模块** |

### 1.2 端点分布分析

**User API 模块分布** (135 个端点):

| 模块 | 端点数 | 说明 |
|------|--------|------|
| Marketplace | 11 | 市场相关 |
| Projects | 10 | 项目管理 |
| User Assets | 10 | 用户资产 |
| Templates | 10 | 模板管理 |
| System Resources | 9 | 系统资源 |
| Resources | 7 | 资源列表 |
| User Profile | 7 | 用户档案 |
| Articles | 6 | 文章内容 |
| Export | 6 | 导出功能 |
| Generations | 6 | 生成历史 |
| Onboarding | 6 | 新手引导 |
| Referrals | 6 | 推荐系统 |
| Experiments | 4 | A/B 实验 |
| Feature Flags | 4 | 功能开关 |
| Billing | 4 | 计费管理 |
| Support | 4 | 客服支持 |
| Campaigns | 3 | 活动系统 |
| Config | 3 | 配置读取 |
| Generation Images | 2 | AI 图片生成 |
| Generation Story | 2 | AI 故事生成 |
| Logs | 2 | 日志上报 |
| Payment | 2 | 支付处理 |
| Pages | 2 | 静态页面 |
| Tasks | 2 | 任务管理 |
| Tools | 2 | 工具功能 |
| Webhooks | 2 | Webhook 处理 |
| Analytics | 1 | 分析事件 |
| Themes | 1 | 主题系统 |
| Generation PDF | 1 | PDF 生成 |

### 1.3 发现的问题

#### 问题 1: 功能重叠

| 重叠区域 | 涉及模块 | 问题描述 |
|----------|----------|----------|
| 资源管理 | Resources + System Resources + User Assets | 三套相似的资源列表/获取接口 |
| 卖家统计 | Projects + Marketplace + User Assets | 三处都有 `seller-stats` 接口 |
| 健康检查 | Onboarding + Referrals + Health | 多个模块有独立健康检查 |
| 删除/恢复 | Projects + User Assets | 相似的软删除 + 恢复逻辑 |

#### 问题 2: 响应格式不一致

| 类型 | 占比 | 示例 |
|------|------|------|
| 使用 response_model | ~45% | Config, Billing 模块 |
| 返回 raw dict | ~37% | Projects, Export 模块 |
| 混合使用 | ~18% | Marketplace, Templates |

#### 问题 3: 接口粒度过细

| 场景 | 当前设计 | 问题 |
|------|----------|------|
| 资源类型查询 | `/resources/stickers`, `/resources/backgrounds`, `/resources/templates` | 3 个接口可合并为 1 个 |
| 模板类型 | `/templates/asset/*` 和 `/templates/page/*` 各 5 个 | 可合并为通用接口 |
| 通知操作 | `read` + `read-all` 分开 | 可合并为 1 个带参数接口 |

#### 问题 4: 废弃接口未清理

| 废弃接口 | 模块 | 状态 |
|----------|------|------|
| POST `/generations/{id}/favorite` | Generations | 已标记废弃 |
| DELETE `/generations/batch` | Generations | 已标记废弃 |
| POST `/export/zip` | Export | 已标记废弃 |

---

## 二、整合策略

### 2.1 整合原则

1. **不影响前端调用**: 保持现有 API 路径兼容，新增整合接口
2. **渐进式迁移**: 先新增，后标记废弃，最后清理
3. **保持高性能**: 整合不能降低接口响应速度
4. **统一响应格式**: 全部采用 JSON + Pydantic response_model

### 2.2 整合方案

#### 方案 A: 资源模块整合 (节省 ~10 个接口)

**当前** (3 个模块, 26 个接口):
```
/resources/*           (7 个)
/system_resources/*    (9 个)
/user_assets/*         (10 个)
```

**整合后** (1 个通用 + 2 个特化):
```
/unified-resources/*   (通用查询接口)
  - GET /              (列表查询, source=user|system|all)
  - GET /{id}          (详情)
  - GET /stats         (统计)

/user_assets/*         (用户特有操作)
  - POST /             (上传)
  - DELETE /{id}       (删除)
  - POST /{id}/restore (恢复)

/system_resources/*    (管理员操作)
  - POST /             (创建)
  - PATCH /{id}        (更新)
  - DELETE /{id}       (删除)
```

**收益**: 减少 ~6-8 个重复的列表/查询接口

---

#### 方案 B: 模板接口整合 (节省 5 个接口)

**当前** (2 类型 × 5 操作 = 10 个接口):
```
/templates/asset       (list, create, update, delete, use)
/templates/page        (list, create, update, delete, use)
```

**整合后** (5 个通用接口):
```
/templates
  - GET /?type=asset|page      (列表)
  - POST /                     (创建, type 在 body)
  - PUT /{id}                  (更新)
  - DELETE /{id}               (删除)
  - POST /{id}/use             (使用)
```

**收益**: 减少 5 个接口，代码维护更简单

---

#### 方案 C: 卖家统计接口整合 (节省 2 个接口)

**当前** (3 个独立接口):
```
/projects/seller-stats
/marketplace/seller/stats
/user_assets/seller-stats
```

**整合后** (1 个统一接口):
```
/seller/stats?include=projects,listings,assets
```

**响应**:
```json
{
  "projects": {
    "total_selling": 5,
    "total_sales": 120,
    "unique_buyers": 45
  },
  "listings": {
    "total_listings": 5,
    "total_sales": 120,
    "total_revenue": 6000
  },
  "assets": {
    "total_downloads": 520,
    "total_revenue": 2600
  },
  "summary": {
    "total_revenue": 8600,
    "total_buyers": 85
  }
}
```

**收益**: 减少 2 个接口，前端一次请求获取全部数据

---

#### 方案 D: 通知接口整合 (节省 1 个接口)

**当前** (2 个接口):
```
POST /notifications/{id}/read      (单条)
POST /notifications/read-all       (全部)
```

**整合后** (1 个接口):
```
POST /notifications/mark-read
Body: { "ids": ["id1", "id2"] }     // 指定 IDs
Body: { "all": true }               // 全部
```

---

#### 方案 E: 废弃接口清理

**立即可清理** (已废弃标记):
```
POST /generations/{id}/favorite    → 使用 PATCH /generations/{id}
DELETE /generations/batch          → 使用 POST /generations/batch-delete
POST /export/zip                   → 使用 POST /export/zip/async
```

---

### 2.3 响应格式统一

#### 标准响应结构

**列表响应**:
```json
{
  "items": [...],
  "total": 100,
  "offset": 0,
  "limit": 20,
  "has_more": true
}
```

**单项响应**:
```json
{
  "data": { ... },
  "meta": {
    "created_at": "...",
    "updated_at": "..."
  }
}
```

**操作响应**:
```json
{
  "success": true,
  "message": "操作成功",
  "data": { ... }  // 可选
}
```

**错误响应**:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "验证失败",
    "details": [
      { "field": "email", "reason": "格式错误" }
    ]
  }
}
```

#### Pydantic 模型规范

```python
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, List

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """通用分页响应"""
    items: List[T]
    total: int
    offset: int
    limit: int
    has_more: bool

class DataResponse(BaseModel, Generic[T]):
    """通用数据响应"""
    data: T
    meta: Optional[dict] = None

class OperationResponse(BaseModel):
    """操作结果响应"""
    success: bool
    message: Optional[str] = None
    data: Optional[dict] = None

class ErrorDetail(BaseModel):
    """错误详情"""
    field: Optional[str] = None
    reason: str

class ErrorResponse(BaseModel):
    """错误响应"""
    code: str
    message: str
    details: Optional[List[ErrorDetail]] = None
```

---

## 三、实施计划

### 3.1 分阶段执行

#### Phase 1: 响应格式统一 (低风险)

**工作量**: ~2 天
**影响范围**: 所有接口

1. 创建通用响应模型 (`core/api/responses.py`)
2. 逐模块添加 response_model
3. 确保向后兼容 (字段结构不变，只是增加类型约束)

**验证方式**: 运行所有测试 + 前端回归测试

---

#### Phase 2: 废弃接口清理 (低风险)

**工作量**: ~0.5 天
**影响范围**: 3 个废弃接口

1. 确认前端未使用这些接口
2. 删除代码
3. 更新文档

---

#### Phase 3: 卖家统计整合 (中等风险)

**工作量**: ~1 天
**影响范围**: 3 个接口

1. 新增 `/seller/stats` 统一接口
2. 前端切换到新接口
3. 标记旧接口为废弃
4. 下个版本删除旧接口

---

#### Phase 4: 模板接口整合 (中等风险)

**工作量**: ~1.5 天
**影响范围**: 10 个接口

1. 新增通用模板接口
2. 前端切换
3. 废弃旧接口

---

#### Phase 5: 资源模块整合 (高风险)

**工作量**: ~3 天
**影响范围**: 26 个接口

这个需要更详细的设计，建议作为独立的重构任务。

---

### 3.2 风险评估

| Phase | 风险等级 | 回滚难度 | 建议 |
|-------|----------|----------|------|
| 1 | 低 | 简单 | 立即执行 |
| 2 | 低 | 简单 | 立即执行 |
| 3 | 中 | 简单 | 需前端配合 |
| 4 | 中 | 中等 | 需前端配合 |
| 5 | 高 | 复杂 | 需独立评审 |

---

## 四、预期收益

### 4.1 端点数量变化

| 阶段 | 减少数量 | 累计减少 |
|------|----------|----------|
| Phase 2 | -3 | -3 |
| Phase 3 | -2 | -5 |
| Phase 4 | -5 | -10 |
| Phase 5 | -8 | -18 |

**最终**: 306 → 288 端点 (减少 ~6%)

### 4.2 其他收益

1. **代码维护成本降低**: 减少重复逻辑
2. **前端调用简化**: 一次请求获取更多数据
3. **类型安全提升**: 100% Pydantic response_model
4. **文档自动生成**: OpenAPI 更准确

---

## 五、不建议整合的模块

以下模块职责清晰，不建议整合:

| 模块 | 原因 |
|------|------|
| Billing | 核心计费逻辑，独立更安全 |
| Payment | Stripe 集成，独立更清晰 |
| Webhooks | 第三方回调，必须独立 |
| Analytics | 数据分析专用 |
| Experiments | A/B 测试专用 |
| Feature Flags | 功能开关专用 |
| Generation * | AI 生成专用，已按功能分类 |

---

## 六、JSON 响应格式默认化分析

### 6.1 当前状态

| 类型 | 数量 | 说明 |
|------|------|------|
| 已返回 JSON | ~95% | 大部分接口 |
| 返回文件流 | ~5% | Export PDF/ZIP, 预览图 |

### 6.2 结论

**所有 API 都已默认返回 JSON 格式**，除了:

1. **文件导出接口**: 必须返回二进制流
   - `GET /export/projects/{id}/pdf`
   - `GET /export/projects/{id}/zip`
   - `GET /export/projects/{id}/preview`
   - `POST /tools/pdf-preview`

2. **这些接口不应改为 JSON**: 返回文件是正确的设计

### 6.3 推荐改进

将现有的 raw dict 返回改为 Pydantic response_model:

```python
# 当前
@router.get("/projects")
async def get_projects(...):
    return {"items": [...], "total": 100}

# 改进后
@router.get("/projects", response_model=PaginatedResponse[ProjectItem])
async def get_projects(...) -> PaginatedResponse[ProjectItem]:
    return PaginatedResponse(items=[...], total=100, ...)
```

---

## 七、下一步行动

### 7.1 建议优先级

1. **[P0] Phase 1 + 2**: 响应格式统一 + 废弃清理 (低风险，高收益)
2. **[P1] Phase 3**: 卖家统计整合 (前端配合后执行)
3. **[P2] Phase 4**: 模板接口整合 (需评估前端改动量)
4. **[P3] Phase 5**: 资源模块整合 (需独立设计文档)

### 7.2 等待确认

1. 前端团队是否能配合 Phase 3-4 的接口切换?
2. 是否有其他整合需求?
3. 时间线要求?

---

**文档结束**

*创建者: Claude Code*
*创建时间: 2026-01-16*
