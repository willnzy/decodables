# Marketplace API - 5 星 Review (v2.1.0)

## 📊 评分总览

| 维度 | 得分 | 满分 | 说明 |
|------|------|------|------|
| 代码标准 | 90 | 100 | 代码质量优秀,清晰的分层 |
| **架构合规** | **80** | **100** | 🟡 部分端点缺少 Service 层,混合调用 |
| 安全性 | 100 | 100 | 安全修复完善 (v2.1.0) |
| 调用链完整性 | 85 | 100 | 混合架构,部分 CQRS,部分直调 Service |
| 测试覆盖率 | 98 | 100 | 43 个测试,覆盖全面 |

**综合评分**: ⭐⭐⭐⭐ (90.6/100)

**评级**: 4.5 星 (需要统一使用 Service 层才能达到满 5 星)

---

## 📋 模块信息

- **模块名称**: Marketplace (市场交易系统)
- **当前版本**: v2.1.0
- **文件位置**: `api/user/marketplace.py` (690 行)
- **测试文件**: `tests/api/user/test_marketplace.py` (1895 行)
- **端点数量**: 11 个
- **风险等级**: 🔴 CRITICAL (涉及支付、积分扣费、卖家收益)

### 端点列表

| 方法 | 路径 | 功能 | 调用方式 | 状态 |
|------|------|------|----------|------|
| GET | `/listings` | 列表查询 | ✅ Handler (CQRS) | Active |
| GET | `/listings/{id}` | 单个查询 | ✅ Handler (CQRS) | Active |
| POST | `/listings` | 创建列表 | ✅ Handler (CQRS) | Active |
| PUT | `/listings/{id}` | 更新列表 | ✅ Handler (CQRS) | Active |
| DELETE | `/listings/{id}` | 删除列表 | ✅ Handler (CQRS) | Active |
| POST | `/purchase` | 购买商品 | ✅ Handler (CQRS) | Active |
| GET | `/my-listings` | 我的列表 | ❌ 直调 Service | Active |
| GET | `/seller/stats` | 卖家统计 | ❌ 直调 Service | Active |
| GET | `/leaderboard` | 排行榜 | ❌ 直调 Service | Active |
| POST | `/report` | 举报 | ❌ 直调 Repository | Active |
| GET | `/my-reports` | 我的举报 | ❌ 直调 Repository | Active |

---

## ✅ 优点

### 1. 架构设计 (80/100) ⭐⭐⭐⭐

**CQRS 实现 (部分端点)**:
- ✅ 6/11 端点使用 Command/Query Handler
- ✅ 依赖注入 (DI) 通过 `get_container()`
- ✅ 清晰的 Command/Query 分离

**代码示例**:
```python
# ✅ 正确: 使用 CQRS Handler
@router.get("/listings")
async def list_listings(...):
    container = get_container()
    handler = container.search_listings_handler

    query = SearchListingsQuery(
        category=resource_type,
        price_filter=price,
        sort_by=sort,
        tier_filter=tier,
        featured=featured,
        limit=limit,
        offset=offset,
    )

    result = await handler.handle(query)
```

**问题**: 5/11 端点直接调用 Service/Repository:
```python
# ❌ 不一致: 直接调用 Service
@router.get("/my-listings")
async def get_my_listings(...):
    container = get_container()
    marketplace_service = container.marketplace_service  # 直调 Service

    listings, total_count = await marketplace_service.get_seller_listings_with_count(
        seller_id=user["id"],
        status=status_filter,
        limit=limit,
        offset=offset,
    )
```

```python
# ❌ 最差: 直接调用 Repository
@router.post("/report")
async def submit_report(...):
    support_repo = SupabaseSupportRepository(get_database_client())  # 直调 Repo
    report = await support_repo.create_report(user["id"], req.listing_id, req.reason)
```

### 2. 安全性 (100/100) ⭐⭐⭐⭐⭐

**v2.1.0 安全修复清单**:
- ✅ **M-P0-001**: 原子化购买事务 (ON CONFLICT)
- ✅ **M-P0-002**: 积分回滚补偿事务
- ✅ **M-P0-003**: 购买前 Listing 状态二次验证
- ✅ **M-HIGH-001/002**: 分页 total count 精确计算
- ✅ **M-HIGH-003**: 异常消息净化 (不暴露内部细节)
- ✅ **M-HIGH-004**: Tier 验证对比数据库记录
- ✅ **M-MEDIUM-005**: 整数运算计算收益

**安全实现示例**:
```python
# M-HIGH-003: 异常消息净化
try:
    support_repo = SupabaseSupportRepository(get_database_client())
    report = await support_repo.create_report(user["id"], req.listing_id, req.reason)
except Exception as e:
    error_msg = str(e)
    if "already reported" in error_msg.lower():
        raise HTTPException(400, "You have already reported this listing")
    # 不暴露内部错误细节
    logger.error(f"Failed to submit report: {e}")
    raise HTTPException(500, "Failed to submit report")
```

### 3. 业务逻辑 (95/100) ⭐⭐⭐⭐⭐

**Tier 权限控制**:
```python
# Starter: 只能发布免费 Asset
if user_tier == "starter":
    if req.resource_type != "asset":
        raise HTTPException(403, "Starter users can only publish assets")
    if req.price_credits > 0:
        raise HTTPException(403, "Starter users can only publish free assets")
```

**二级分类系统**:
- ✅ `resource_type`: asset / project (顶层)
- ✅ `category`: sticker / template 等 (二级分类)
- ✅ `source`: system / user / ai / community (来源)
- ✅ `allowed_tiers`: 访问控制列表

**错误处理**:
```python
# 详细的错误分类
if not result.success:
    error = result.error or "Purchase failed"

    if "insufficient" in error.lower():
        raise HTTPException(402, error)  # 402 Payment Required
    if "not found" in error.lower():
        raise HTTPException(404, "Listing not found")
    if "access" in error.lower() or "tier" in error.lower():
        raise HTTPException(403, error)  # 403 Forbidden

    raise HTTPException(400, error)
```

### 4. 测试覆盖率 (98/100) ⭐⭐⭐⭐⭐

**测试统计**:
- 总测试数: **43**
- 通过率: **100%**
- 测试类: **11 个**
- 行数: **1895 行**

**覆盖场景**:
- ✅ 成功路径 (11 个)
- ✅ 错误处理 (404, 400, 403, 402, 422, 500)
- ✅ 权限控制 (Free/Starter/Pro)
- ✅ 分页/过滤 (page, limit, status)
- ✅ 业务逻辑 (二级分类、默认值、tier 限制)
- ✅ 安全功能 (报告去重、异常净化)

**测试质量**:
```python
# 完善的测试场景
def test_create_listing_starter_paid_forbidden(
    self,
    override_get_current_user_starter,
):
    """
    Test: Starter user cannot create paid asset (403)

    Given: Starter tier user
    When: POST with price_credits=10
    Then: Returns 403 Forbidden
    """
    response = client.post(
        "/api/v2/user/marketplace/listings",
        json={
            "title": "Paid Asset",
            "resource_type": "asset",
            "price_credits": 10,
        },
    )

    assert response.status_code == 403
    data = response.json()
    assert "Starter users can only publish free assets" in data["message"]
```

### 5. 代码质量 (90/100) ⭐⭐⭐⭐

**优点**:
- ✅ 清晰的文档注释 (每个端点)
- ✅ Pydantic 模型验证
- ✅ Rate Limiting (60/min, 10/min)
- ✅ 日志记录 (`logger.error`)
- ✅ 审计日志 (`log_activity`)

**Request/Response 模型**:
```python
class ListingCreateRequest(BaseModel):
    """Request to create a listing."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    resource_url: Optional[str] = None
    resource_type: str = Field(..., pattern="^(asset|project)$")
    category: Optional[str] = None
    source: str = Field("user", pattern="^(system|user|ai|community)$")
    resource_id: Optional[str] = None
    price_credits: int = Field(0, ge=0, le=500)
    allowed_tiers: Optional[List[str]] = None
    version: Optional[str] = "1.0"
    changelog: Optional[str] = None
```

---

## 🔴 关键问题

### **MARKET-CRITICAL-1: 架构不一致 (Architecture 80/100)**

**问题描述**:
- 11 个端点中,6 个使用 CQRS (Handler),5 个直调 Service/Repository
- 混合架构导致调用链不一致
- 违反"统一架构风格"原则

**违规端点**:

| 端点 | 问题 | 行号 |
|------|------|------|
| `GET /my-listings` | 直调 `marketplace_service` | 447-498 |
| `GET /seller/stats` | 直调 `marketplace_service` | 501-527 |
| `GET /leaderboard` | 直调 `marketplace_service` | 549-581 |
| `POST /report` | 直调 `SupabaseSupportRepository` | 616-658 |
| `GET /my-reports` | 直调 `SupabaseSupportRepository` | 661-689 |

**问题影响**:
1. **一致性**: 不同端点有不同的调用模式,新开发者容易困惑
2. **可测试性**: 直调 Service 的端点需要 mock 不同的依赖
3. **重构风险**: 未来重构时需要处理两种不同的架构模式
4. **架构演进**: 无法统一升级到新架构模式

**修复建议**:

**方案 1: 统一使用 CQRS (推荐)**
- 创建 5 个新的 Query/Command:
  - `GetMyListingsQuery` → `GetMyListingsQueryHandler`
  - `GetSellerStatsQuery` → `GetSellerStatsQueryHandler`
  - `GetLeaderboardQuery` → `GetLeaderboardQueryHandler`
  - `CreateReportCommand` → `CreateReportCommandHandler`
  - `GetMyReportsQuery` → `GetMyReportsQueryHandler`
- API 层统一通过 Handler 调用
- 测试统一 mock Handler

**方案 2: 统一使用 Service (不推荐)**
- 将现有的 6 个 Handler 改为直调 Service
- 但这样会**降低**架构层次,不符合 DDD 原则

**代码示例 (方案 1)**:
```python
# 创建 Query Handler
class GetMyListingsQuery:
    def __init__(
        self,
        user_id: str,
        status: Optional[ListingStatus],
        limit: int,
        offset: int,
    ):
        self.user_id = user_id
        self.status = status
        self.limit = limit
        self.offset = offset

class GetMyListingsQueryHandler:
    def __init__(self, marketplace_service):
        self.service = marketplace_service

    async def handle(self, query: GetMyListingsQuery) -> GetMyListingsResult:
        try:
            listings, total = await self.service.get_seller_listings_with_count(
                seller_id=query.user_id,
                status=query.status,
                limit=query.limit,
                offset=query.offset,
            )
            return GetMyListingsResult(
                success=True,
                listings=listings,
                total_count=total,
            )
        except Exception as e:
            logger.error(f"Get my listings failed: {e}")
            return GetMyListingsResult(
                success=False,
                error=f"Failed to get listings: {str(e)}",
            )

# API 层调用
@router.get("/my-listings")
async def get_my_listings(...):
    container = get_container()
    handler = container.get_my_listings_handler  # 使用 Handler

    query = GetMyListingsQuery(
        user_id=user["id"],
        status=status_filter,
        limit=limit,
        offset=offset,
    )

    result = await handler.handle(query)

    if not result.success:
        raise HTTPException(500, "Failed to get listings")

    return ListingsResponse(
        items=[l.to_dict() for l in result.listings],
        total=result.total_count,
        page=page,
    )
```

---

## 🟡 次要问题

### MARKET-MEDIUM-1: 报告系统未使用 Domain 层

**问题**: `/report` 和 `/my-reports` 直接使用 `SupabaseSupportRepository`
- 应该有 `domains/support/support_service.py`
- 或者创建 `ReportService`
- API 层不应该直接操作 Repository

**修复建议**:
1. 创建 `domains/support/support_service.py`
2. 实现 `create_report()` 和 `get_user_reports()`
3. Repository 作为 Service 的依赖
4. API 层通过 Handler 调用 Service

### MARKET-MEDIUM-2: 分页参数不一致

**问题**: 不同端点使用不同的分页参数
- `/listings`: `page` + `limit` (前端分页)
- `/my-listings`: `page` + `limit` (前端分页)
- `/my-reports`: `page` + `limit` (前端分页)

**现状**: 已经在 API 层转换为 `offset = (page - 1) * limit`

**建议**:
- 当前实现合理,保持前端友好的 `page` 参数
- 后端内部统一使用 `offset + limit`

### MARKET-LOW-1: Deprecated 端点缺失

**观察**: 代码注释中提到有 deprecated 端点,但实际没有
```python
# 端点数量: 6 个 (2 个 deprecated)
```

**建议**: 移除注释或补充 deprecated 端点说明

---

## 📊 对标 5 星标准

### 5 星要求

| 维度 | 5 星要求 | 当前状态 | 差距 |
|------|----------|----------|------|
| 代码标准 | 95-100 | 90 | -5 (可优化) |
| **架构合规** | **95-100** | **80** | **-15 (需统一 CQRS)** |
| 安全性 | 95-100 | 100 | ✅ 超标 |
| 调用链完整性 | 90-100 | 85 | -5 (混合调用) |
| 测试覆盖率 | 95-100 | 98 | ✅ 达标 |

### 升级到 5 星的必要条件

**必须完成**:
1. ✅ 创建 5 个新的 Query/Command Handler
   - `GetMyListingsQueryHandler`
   - `GetSellerStatsQueryHandler`
   - `GetLeaderboardQueryHandler`
   - `CreateReportCommandHandler`
   - `GetMyReportsQueryHandler`
2. ✅ 统一所有端点使用 CQRS 模式
3. ✅ 移除 API 层对 Service/Repository 的直接调用
4. ✅ 更新测试 mock Handler 而不是 Service

**可选优化**:
5. 🔸 创建 `SupportService` 封装报告逻辑
6. 🔸 补充 Leaderboard 的过滤条件测试
7. 🔸 添加 Rate Limiting 测试 (需要 Redis)

---

## 📂 推荐架构

### 当前架构 (v2.1.0)

```
api/user/marketplace.py
├── Listings CRUD (6/6) → CQRS Handlers ✅
│   ├── GET /listings → SearchListingsHandler
│   ├── GET /listings/{id} → GetListingHandler
│   ├── POST /listings → CreateListingHandler
│   ├── PUT /listings/{id} → UpdateListingHandler
│   ├── DELETE /listings/{id} → UnpublishListingHandler
│   └── POST /purchase → PurchaseListingHandler
│
├── Seller Features (3/3) → 直调 Service ❌
│   ├── GET /my-listings → marketplace_service
│   ├── GET /seller/stats → marketplace_service
│   └── GET /leaderboard → marketplace_service
│
└── Report System (2/2) → 直调 Repository ❌
    ├── POST /report → SupabaseSupportRepository
    └── GET /my-reports → SupabaseSupportRepository
```

### 目标架构 (v3.0.0)

```
api/user/marketplace.py
├── Listings CRUD (6/6) → CQRS Handlers ✅
├── Seller Features (3/3) → CQRS Handlers ✅
│   ├── GET /my-listings → GetMyListingsHandler
│   ├── GET /seller/stats → GetSellerStatsHandler
│   └── GET /leaderboard → GetLeaderboardHandler
│
└── Report System (2/2) → CQRS Handlers ✅
    ├── POST /report → CreateReportHandler
    └── GET /my-reports → GetMyReportsHandler

application/
├── queries/marketplace.py (已有 2 个 Query)
│   ├── + GetMyListingsQuery
│   ├── + GetSellerStatsQuery
│   ├── + GetLeaderboardQuery
│   └── + GetMyReportsQuery
│
└── commands/marketplace.py (已有 4 个 Command)
    └── + CreateReportCommand

application/handlers/marketplace/
├── query_handlers.py (已有 2 个)
│   ├── + GetMyListingsQueryHandler
│   ├── + GetSellerStatsQueryHandler
│   ├── + GetLeaderboardQueryHandler
│   └── + GetMyReportsQueryHandler
│
└── command_handlers.py (已有 4 个)
    └── + CreateReportCommandHandler

domains/support/
└── support_service.py (新建)
    ├── create_report()
    └── get_user_reports_with_count()
```

---

## 📈 升级路线图

### Phase 1: 创建 Seller Queries (必须)

**工作量**: 3 小时

1. 创建 `GetMyListingsQuery` + `GetMyListingsQueryHandler`
   - 输入: `user_id`, `status`, `limit`, `offset`
   - 输出: `GetMyListingsResult(success, listings, total_count)`
   - 调用: `marketplace_service.get_seller_listings_with_count()`

2. 创建 `GetSellerStatsQuery` + `GetSellerStatsQueryHandler`
   - 输入: `user_id`
   - 输出: `GetSellerStatsResult(success, stats)`
   - 调用: `marketplace_service.get_seller_stats()`

3. 创建 `GetLeaderboardQuery` + `GetLeaderboardQueryHandler`
   - 输入: `period`, `type`
   - 输出: `GetLeaderboardResult(success, items)`
   - 调用: `marketplace_service.get_leaderboard()`

### Phase 2: 创建 Support Service (必须)

**工作量**: 2 小时

4. 创建 `domains/support/__init__.py`
5. 创建 `domains/support/support_service.py`
   - `create_report(user_id, listing_id, reason)` → `Report`
   - `get_user_reports_with_count(user_id, page, limit)` → `tuple[List[Report], int]`
6. 注入到 Container

### Phase 3: 创建 Report Commands/Queries (必须)

**工作量**: 2 小时

7. 创建 `CreateReportCommand` + `CreateReportCommandHandler`
   - 输入: `user_id`, `listing_id`, `reason`
   - 输出: `CreateReportResult(success, report_id)`
   - 调用: `support_service.create_report()`

8. 创建 `GetMyReportsQuery` + `GetMyReportsQueryHandler`
   - 输入: `user_id`, `page`, `limit`
   - 输出: `GetMyReportsResult(success, reports, total_count)`
   - 调用: `support_service.get_user_reports_with_count()`

### Phase 4: API 重构 (必须)

**工作量**: 2 小时

9. 重构 5 个端点使用新 Handler
   - `GET /my-listings` (447-498 行)
   - `GET /seller/stats` (501-527 行)
   - `GET /leaderboard` (549-581 行)
   - `POST /report` (616-658 行)
   - `GET /my-reports` (661-689 行)

10. 移除直接调用 Service/Repository

### Phase 5: 测试更新 (必须)

**工作量**: 3 小时

11. 更新 5 个端点的测试
    - Mock 新 Handler 而不是 Service/Repository
    - 验证 Query/Command 参数正确
    - 保持 100% 通过率

### Phase 6: Container 更新 (必须)

**工作量**: 1 小时

12. 注册新 Handler 到 Container
    - `get_my_listings_handler`
    - `get_seller_stats_handler`
    - `get_leaderboard_handler`
    - `create_report_handler`
    - `get_my_reports_handler`

13. 注册 `SupportService`

---

## 🎯 预期成果

### 升级到 v3.0.0 后

| 维度 | v2.1.0 | v3.0.0 | 改进 |
|------|--------|--------|------|
| 代码标准 | 90 | 95 | +5 |
| **架构合规** | **80** | **100** | **+20** |
| 安全性 | 100 | 100 | ✅ |
| 调用链完整性 | 85 | 95 | +10 |
| 测试覆盖率 | 98 | 98 | ✅ |
| **综合评分** | **90.6** | **97.6** | **+7** |
| **星级评定** | **⭐⭐⭐⭐** | **⭐⭐⭐⭐⭐** | **+0.5 星** |

### 代码行数变化

| 文件 | v2.1.0 | v3.0.0 (预估) | 变化 |
|------|--------|---------------|------|
| `api/user/marketplace.py` | 690 | ~650 | -40 (-6%) |
| `application/queries/marketplace.py` | ~150 | ~300 | +150 |
| `application/commands/marketplace.py` | ~200 | ~250 | +50 |
| `application/handlers/marketplace/query_handlers.py` | ~200 | ~350 | +150 |
| `application/handlers/marketplace/command_handlers.py` | ~250 | ~300 | +50 |
| `domains/support/support_service.py` | 0 | ~150 | 🆕 新建 |
| `tests/api/user/test_marketplace.py` | 1895 | ~2100 | +205 (+11%) |

### 架构改进

```
v2.1.0 (4.5 星): 混合架构
API → Handler (6/11) ✅
API → Service (3/11) ❌
API → Repository (2/11) ❌

v3.0.0 (5 星): 统一 CQRS
API → Handler (11/11) ✅
Handler → Service ✅
Service → Repository ✅
```

---

## 📝 总结

**当前状态**: ⭐⭐⭐⭐ (90.6/100)
- ✅ 安全性卓越 (100/100) - v2.1.0 修复完善
- ✅ 测试覆盖优秀 (98/100) - 43 个测试
- ✅ 业务逻辑完善 (95/100) - Tier 权限、二级分类
- 🟡 **架构不一致** (80/100) - 混合调用模式

**升级到 5 星的关键**:
1. 统一所有端点使用 CQRS 模式
2. 创建 5 个新 Handler (Seller + Report)
3. 创建 `SupportService` 封装报告逻辑
4. 移除 API 层对 Service/Repository 的直接调用

**工作量估算**:
- Phase 1-3: Handler + Service 创建 (~7 小时)
- Phase 4-5: API + 测试重构 (~5 小时)
- Phase 6: Container 更新 (~1 小时)
- **总计**: ~13 小时

**风险评估**: 🟡 MEDIUM
- 11 个端点中 5 个需要重构
- 需要创建新的 Service 层 (Support)
- 测试需要更新 mock 方式
- 但业务逻辑不变,风险可控

**优先级**: HIGH
- Marketplace 是核心交易系统
- 涉及支付、积分、卖家收益 (高风险)
- 架构统一有利于长期维护
- 当前 90.6 分已经很高,升级性价比好

---

## 📋 与 Generations 对比

| 维度 | Generations v2.1.0 | Marketplace v2.1.0 | 差异 |
|------|-------------------|-------------------|------|
| 架构合规 | **60** (无 Service) | **80** (混合) | Market +20 |
| 调用链 | 80 (API→DB 直调) | 85 (混合) | Market +5 |
| 安全性 | 100 | 100 | 持平 |
| 测试覆盖 | 95 (15 个) | 98 (43 个) | Market +3 |
| **综合评分** | **84** | **90.6** | **Market +6.6** |
| **星级** | **⭐⭐⭐⭐** | **⭐⭐⭐⭐** (4.5) | Market 更接近 5 星 |

**关键差异**:
1. **Marketplace 已经有部分 CQRS** (6/11 端点)
   - Generations 完全没有 Service 层
2. **Marketplace 安全修复更完善** (v2.1.0 修复清单)
   - Generations 也有安全修复但范围较小
3. **Marketplace 业务复杂度更高**
   - 涉及支付、积分、权限控制
   - Generations 只是 CRUD

**升级难度对比**:
- Generations → 5 星: 需要**从零创建** Service 层 (7 小时)
- Marketplace → 5 星: 需要**补全** 剩余 5 个 Handler (13 小时)
- **结论**: Generations 升级更简单,但 Marketplace 当前质量更高

---

**审查人**: Claude Sonnet 4.5
**审查日期**: 2026-01-10
**下一步建议**:
1. 优先完成 Marketplace 升级 (更接近 5 星)
2. 或先完成 Generations 升级 (工作量更小)
3. 两者都是核心模块,建议两周内完成

