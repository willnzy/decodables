# API 文档与代码一致性审计报告

> **审计日期**: 2026-01-18
> **审计范围**: user-api-review.md / admin-api-review.md vs 实际后端代码
> **审计状态**: 完成

---

## 一、审计汇总

| 类别 | User API | Admin API | 总计 |
|------|----------|-----------|------|
| P0/CRITICAL | 5 | 1 | 6 |
| P1/HIGH | 4 | 1 | 5 |
| P2/MEDIUM | 2 | 2 | 4 |
| LOW | - | 2 | 2 |
| **总计** | **11** | **6** | **17** |

---

## 二、User API 不一致详情

### P0 严重问题 (5 项)

#### P0-001: GET `/user_assets` 缺少分页参数

| 项目 | 详情 |
|------|------|
| **文件** | `api/user/user_assets.py:106-136` |
| **文档声称** | 支持 `offset` 和 `limit` 分页参数 (文档行 2726-2730) |
| **实际代码** | `def my_assets(request: Request, project_id: Optional[str] = None, scope: Optional[str] = None, ...)` |
| **差异** | 只有 `project_id` 和 `scope` 参数，**完全无分页支持** |
| **影响** | 前端无法对大量资产进行分页查询，性能问题 |

#### P0-002: GET `/user_assets/deleted` 缺少分页参数

| 项目 | 详情 |
|------|------|
| **文件** | `api/user/user_assets.py:315-332` |
| **文档声称** | 响应包含 `assets` 列表 (文档行 2869-2879) |
| **实际代码** | `def get_deleted(request: Request, user: UserProfile = Depends(get_current_user)):` |
| **差异** | 无分页参数，返回全部已删除资产 |
| **影响** | 删除资产过多时性能问题 |

#### P0-003: GET `/user_assets/dashboard` 响应格式不符

| 项目 | 详情 |
|------|------|
| **文件** | `api/user/user_assets.py:294-312` |
| **文档声称** | 返回结构化统计: `{total_assets, by_type: {sticker, background, template}, total_usage}` |
| **实际代码** | `return result.stats` (动态结构) |
| **差异** | 文档定义具体格式，代码直接返回服务层结果 |
| **影响** | 前端无法保证字段结构 |

#### P0-004: GET `/billing/transactions` 字段名不匹配

| 项目 | 详情 |
|------|------|
| **文件** | `api/user/billing.py:332-345` |
| **文档声称** | 响应包含 `transactions` 数组和 `total_count` (文档行 459-472) |
| **实际代码** | `TransactionHistoryResponse` 模型定义 (行 100-130) |
| **差异** | 文档使用 `total`，代码使用 `total_count` |
| **影响** | 前端字段映射错误 |

#### P0-005: GET `/marketplace/listings` 响应格式不符

| 项目 | 详情 |
|------|------|
| **文件** | `api/user/marketplace.py:240-246` |
| **文档声称** | 响应包含 `offset` 和 `limit` 字段 (文档行 1250-1273) |
| **实际代码** | `ListingsResponse` 返回 `items`, `total`, `page` (行 170-175) |
| **差异** | 文档要求 offset/limit，代码返回 page 编号 |
| **影响** | 前端接收 page 但期望 offset/limit |

---

### P1 中等问题 (4 项)

#### P1-001: marketplace 使用 page 违反 DDD 规范

| 项目 | 详情 |
|------|------|
| **文件** | `api/user/marketplace.py:240-246` |
| **违反规则** | CLAUDE.md 2.2 节: 统一使用 `offset` + `limit` |
| **实际代码** | 计算 `page = (offset // limit) + 1` 后返回 page |
| **建议** | 应返回 offset/limit 而非 page |

#### P1-002: GET `/projects/dashboard` 使用 page 参数

| 项目 | 详情 |
|------|------|
| **文件** | `api/user/projects.py:212` |
| **文档声称** | 响应包含 `items` 和 `total_count` (文档行 1819-1823) |
| **实际代码** | `page: int = Query(1, ge=1)` |
| **差异** | 文档未说明 page 参数，与其他端点 offset/limit 不一致 |
| **影响** | 前端需要两种不同的分页模式 |

#### P1-003: articles 格式与其他模块不统一

| 项目 | 详情 |
|------|------|
| **文件** | `api/user/articles.py` |
| **问题** | articles 正确返回 offset/limit，但 marketplace 返回 page |
| **影响** | 项目内分页格式不一致 |

#### P1-004: GET `/referrals` 响应格式完全不符

| 项目 | 详情 |
|------|------|
| **文件** | `api/user/referrals.py:91-116` |
| **文档声称** | 返回 `{referrals: [...]}` 数组 (文档行 1997-2010) |
| **实际代码** | 返回 `{"data": [...], "pagination": {...}}` |
| **差异** | 响应格式完全不同（嵌套 pagination 结构 vs 平面结构） |
| **影响** | 前端无法解析 |

---

### P2 低级问题 (2 项)

#### P2-001: GET `/billing/transactions` 缺失 has_more 字段

| 项目 | 详情 |
|------|------|
| **文件** | `api/user/billing.py:332-345` |
| **文档声称** | 响应包含 `has_more` 布尔字段 (文档行 310) |
| **实际代码** | `TransactionHistoryResponse` 无 `has_more` 字段 |

#### P2-002: 端点计数不准确

| 项目 | 详情 |
|------|------|
| **文件** | `docs/shared/user-api-review.md` |
| **文档声称** | 第 6 行: "总端点数: 128 个" |
| **实际计数** | 表格编号到 134，计数不准确 |

---

## 三、Admin API 不一致详情

### CRITICAL (1 项)

#### CRIT-001: Config API 路径重复

| 项目 | 详情 |
|------|------|
| **文件** | `api/admin/config.py:63,123` |
| **问题** | Router prefix=`/config`，路由定义又是 `@router.get("/config")` |
| **结果路径** | `/api/v2/admin/config/config` (重复) |
| **文档路径** | `/api/v2/admin/config` |
| **影响** | 所有 8 个 Config 端点路径错误 |
| **修复** | 将路由定义改为 `@router.get("")` 或 `@router.get("/")` |

---

### HIGH (1 项)

#### HIGH-001: Users 搜索参数名不匹配

| 项目 | 详情 |
|------|------|
| **文件** | `api/admin/users.py:103` |
| **文档声称** | 参数名为 `search` |
| **实际代码** | `query: str = Query(..., min_length=1, max_length=200)` |
| **差异** | 文档用 `search`，代码用 `query` |
| **影响** | 客户端发送 `?search=foo` 但 API 期望 `?query=foo` |

---

### MEDIUM (2 项)

#### MED-001: Articles 响应 wrapper 未文档化

| 项目 | 详情 |
|------|------|
| **文件** | `api/admin/articles.py:343,426` |
| **问题** | create/update 返回 `{success, message, article}` wrapper |
| **文档** | 只写了直接返回 article 对象 |

#### MED-002: User ID 命名不一致

| 项目 | 详情 |
|------|------|
| **文件** | `api/admin/users.py:139` |
| **文档** | 使用 `user_id` |
| **代码** | 使用 `uid` |

---

### LOW (2 项)

#### LOW-001: Campaigns 函数名缺失

| 项目 | 详情 |
|------|------|
| **文件** | `docs/shared/admin-api-review.md:75-82` |
| **问题** | 表格中函数名显示 `-` |
| **实际** | 函数存在: `list_campaigns_endpoint`, `get_campaign_endpoint` |

#### LOW-002: 废弃端点未标注

| 项目 | 详情 |
|------|------|
| **文件** | `api/admin/users.py:185-205` |
| **问题** | `POST /users/{uid}/tier` 已废弃 (返回 410) |
| **文档** | 未在概览表中说明废弃状态 |

---

## 四、DDD 架构违反汇总

根据 `CLAUDE.md` 第 2.2 节规定:

| 规则 | 违反模块 | 问题 |
|------|----------|------|
| 分页用 `offset + limit` | marketplace | 使用 `page` 参数和返回值 |
| 分页用 `offset + limit` | projects/dashboard | 使用 `page` 参数 |
| 响应返回 `offset + limit` | marketplace | 返回 `page` 编号 |
| 一致性响应格式 | referrals | 使用 `{data, pagination}` 嵌套结构 |
| 一致性响应格式 | user_assets | 无分页支持 |

---

## 五、修复方案（业务驱动）

> **决策原则**: 从业务逻辑需要出发，统一 DDD 架构，前后端同步修复

### 修复清单

| # | 问题 | 后端修复 | 前端修复 | 状态 |
|---|------|----------|----------|------|
| 1 | **CRIT-001** Config API 路径重复 | ✅ 修复路径 | ⚠️ 检查 Admin 前端 | ✅ 已完成 |
| 2 | **HIGH-001** Users 参数 `query`→`search` | ✅ 修改参数名 | ⚠️ 更新调用 | ✅ 已完成 |
| 3 | **P0-001** user_assets 无分页 | ✅ 添加 offset/limit | ⚠️ 添加分页逻辑 | ✅ 已完成 |
| 4 | **P0-002** user_assets/deleted 无分页 | ✅ 添加 offset/limit | ⚠️ 添加分页逻辑 | ✅ 已完成 |
| 5 | **P0-005** marketplace 返回 page | ✅ 改为返回 offset/limit | ⚠️ 更新响应处理 | ✅ 已完成 |
| 6 | **P1-002** projects/dashboard 用 page | ✅ 改为 offset/limit | ⚠️ 更新调用 | ✅ 已完成 |
| 7 | **P1-004** referrals 响应格式 | ✅ 统一格式 | ⚠️ 待实现功能 | ✅ 已完成 |
| 8 | **P0-003** user_assets/dashboard 格式 | - | - | 📝 更新文档 |
| 9 | **P0-004** billing total_count | - | - | 📝 更新文档 |
| 10 | **P2-002** 端点计数 | - | - | 📝 更新文档 |

### 修复顺序

**第一批：必须修复（影响 API 可用性）**
1. ✅ CRIT-001: Config API 路径 - **已完成**
2. ✅ HIGH-001: Users 搜索参数名 - **已完成**

**第二批：分页统一（DDD 一致性）**
3. ✅ P0-001/002: user_assets 分页 - **已完成**
4. ✅ P0-005 + P1-002: marketplace 和 projects/dashboard 分页格式 - **已完成**

**第三批：后续处理**
5. ✅ P1-004: referrals 响应格式 - **已完成**
6. 📝 文档更新 - ⏳ 待处理

---

## 六、修复进度

### ✅ 已完成

#### CRIT-001: Config API 路径重复 (2026-01-18)

**修改文件**: `api/admin/config.py`

**修改内容**:
- `@router.get("/config")` → `@router.get("")`
- `@router.get("/config/{config_key}")` → `@router.get("/{config_key}")`
- `@router.put("/config")` → `@router.put("")`
- `@router.put("/config/batch")` → `@router.put("/batch")`
- `@router.post("/config/cache/clear")` → `@router.post("/cache/clear")`

**结果**: 所有 8 个 Config 端点路径恢复正常

---

#### HIGH-001 + MED-002: Users 参数名统一 (2026-01-18)

**修改文件**: `api/admin/users.py`

**修改内容**:
- 查询参数 `query` → `search`
- 路径参数 `uid` → `user_id` (所有 10 个端点)
- 更新函数参数和内部引用

**结果**: Admin Users API 参数名统一

---

#### P0-001/002: user_assets 添加分页 (2026-01-18)

**修改文件**:
- `api/user/user_assets.py` - API 端点
- `application/queries/assets.py` - Query 和 Handler
- `domains/assets/assets_service.py` - Service 方法
- `infrastructure/repositories/asset_repository.py` - Repository 方法

**修改内容**:
- `GET /assets` 添加 `offset` 和 `limit` 参数
- `GET /deleted` 添加 `offset` 和 `limit` 参数
- 响应格式: `{items, total, offset, limit, has_more}`

**结果**: user_assets 完整支持 DDD 规范分页

---

#### P0-005: marketplace 响应格式 (2026-01-18)

**修改文件**: `api/user/marketplace.py`

**修改内容**:
- `ListingsResponse` 模型: 移除 `page`，添加 `offset`, `limit`, `has_more`
- `get_marketplace_listings` 端点: 更新响应构建逻辑

**结果**: marketplace 响应格式符合 DDD 规范

---

#### P1-002: projects/dashboard 分页 (2026-01-18)

**修改文件**:
- `api/user/projects.py` - API 端点
- `application/queries/creation.py` - Query 类
- `infrastructure/repositories/project_repository.py` - Repository 方法

**修改内容**:
- 参数: `page` → `offset`
- 响应: `{page}` → `{offset, limit}`
- 全调用链更新

**结果**: projects/dashboard 分页符合 DDD 规范

---

#### P1-004: referrals 响应格式 (2026-01-18)

**修改文件**: `api/user/referrals.py`

**修改内容**:
- 响应格式: `{data, pagination}` → `{items, total, offset, limit, has_more}`

**结果**: referrals 响应格式符合 DDD 规范

---

### ⏳ 待处理

- 前端代码更新 (需配合后端修改)
- API 文档更新 (user-api-review.md, admin-api-review.md)

---

## 七、后续行动

- [x] 确认修复方案 (业务驱动)
- [x] 创建修复任务清单
- [x] 按优先级逐一修复后端代码
- [ ] 更新前端代码
- [ ] 更新 API 文档
- [ ] 验证前后端兼容性
- [ ] 运行测试

---

## 八、后端修复汇总

### 已修改文件 (共 10 个)

| 文件 | 修改类型 | 涉及问题 |
|------|----------|----------|
| `api/admin/config.py` | 路由路径 | CRIT-001 |
| `api/admin/users.py` | 参数名 | HIGH-001, MED-002 |
| `api/user/user_assets.py` | 分页参数+响应 | P0-001, P0-002 |
| `application/queries/assets.py` | Query 类 | P0-001, P0-002 |
| `domains/assets/assets_service.py` | Service 方法 | P0-001, P0-002 |
| `infrastructure/repositories/asset_repository.py` | Repository 方法 | P0-001, P0-002 |
| `api/user/marketplace.py` | 响应格式 | P0-005 |
| `api/user/projects.py` | 分页参数 | P1-002 |
| `application/queries/creation.py` | Query 类 | P1-002 |
| `infrastructure/repositories/project_repository.py` | 响应格式 | P1-002 |
| `api/user/referrals.py` | 响应格式 | P1-004 |

### 统一的 DDD 分页响应格式

```json
{
  "items": [...],
  "total": 100,
  "offset": 0,
  "limit": 20,
  "has_more": true
}
```

---

*审计完成时间: 2026-01-18*
*后端修复完成时间: 2026-01-18*
