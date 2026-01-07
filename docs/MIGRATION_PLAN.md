# 后端架构迁移计划

> 从扁平 services 架构迁移到三层架构 + 轻量 DDD

## 迁移策略：渐进式迁移

采用 **Strangler Fig Pattern** (绞杀者模式)：
- 新旧系统并行运行
- 逐步将流量迁移到新架构
- 最终完全替换旧架构

```
旧: /api/xxx     → services/db_service.py
新: /api/v2/xxx  → container → handlers → services → repositories
```

---

## 阶段划分

### Phase A: 基础设施 ✓ 已完成

| 任务 | 状态 | 说明 |
|------|------|------|
| core/ 框架层 | ✓ | 异常、缓存、数据库、中间件 |
| domains/ 领域层 | ✓ | 5 个领域聚合 |
| infrastructure/ 基础设施层 | ✓ | 6 个 Repository 实现 |
| application/ 应用层 | ✓ | 15 命令 + 10 查询 handlers |
| container.py | ✓ | 依赖注入容器 |
| api/ 示例 | ✓ | billing + credits API |
| 单元测试 | ✓ | domains + application 测试 |

---

### Phase B: 核心功能迁移 (优先级 P0)

**目标**: 迁移最核心的业务逻辑，这些是收入和用户体验的关键路径

#### B1: Billing/Credits 完整迁移

| 端点 | 旧路径 | 新路径 | 依赖 |
|------|--------|--------|------|
| 获取积分余额 | GET /api/user/me | GET /api/v2/credits | - |
| 积分历史 | GET /api/user/history | GET /api/v2/credits/history | - |
| 扣除积分 | (内部调用) | POST /api/v2/billing/credits/deduct | - |
| 添加积分 | (内部调用) | POST /api/v2/billing/credits/add | - |

**迁移步骤**:
1. [ ] 前端调用新 API `/api/v2/credits`
2. [ ] 添加 Feature Flag 控制切换
3. [ ] 监控新旧 API 响应一致性
4. [ ] 确认无问题后移除旧端点

#### B2: User Profile 迁移

| 端点 | 旧路径 | 新路径 |
|------|--------|--------|
| 获取用户信息 | GET /api/user/me | GET /api/v2/user/profile |
| 更新时区 | PUT /api/user/timezone | PUT /api/v2/user/timezone |
| 更新资料 | (内部) | PUT /api/v2/user/profile |

**迁移步骤**:
1. [ ] 创建 `api/user_api.py`
2. [ ] 添加 GetUserProfileHandler 端点
3. [ ] 前端切换调用
4. [ ] 验证并移除旧端点

---

### Phase C: 项目管理迁移 (优先级 P0)

#### C1: Projects CRUD

| 端点 | 旧路径 | 新路径 |
|------|--------|--------|
| 列表 | GET /api/projects | GET /api/v2/projects |
| 详情 | GET /api/projects/{id} | GET /api/v2/projects/{id} |
| 创建 | POST /api/projects | POST /api/v2/projects |
| 更新 | PUT /api/projects/{id} | PUT /api/v2/projects/{id} |
| 删除 | DELETE /api/projects/{id} | DELETE /api/v2/projects/{id} |
| 恢复 | POST /api/projects/{id}/restore | POST /api/v2/projects/{id}/restore |
| 复制 | POST /api/projects/{id}/duplicate | POST /api/v2/projects/{id}/duplicate |

**迁移步骤**:
1. [ ] 创建 `api/projects_api.py`
2. [ ] 实现所有 CRUD 端点
3. [ ] 添加项目限制检查 (使用 IdentityService)
4. [ ] 前端切换调用
5. [ ] 验证并移除旧端点

---

### Phase D: Marketplace 迁移 (优先级 P1)

#### D1: Listings

| 端点 | 旧路径 | 新路径 |
|------|--------|--------|
| 列表 | GET /api/marketplace/items | GET /api/v2/marketplace/listings |
| 详情 | GET /api/marketplace/item/{id} | GET /api/v2/marketplace/listings/{id} |
| 发布 | POST /api/marketplace/publish | POST /api/v2/marketplace/listings |
| 下架 | POST /api/marketplace/unpublish | DELETE /api/v2/marketplace/listings/{id} |

#### D2: Purchases (涉及跨域协调)

| 端点 | 说明 |
|------|------|
| POST /api/v2/marketplace/purchase | 使用 PurchaseListingHandler (跨 marketplace + billing) |

**迁移步骤**:
1. [ ] 创建 `api/marketplace_api.py`
2. [ ] 实现 listings CRUD
3. [ ] 实现 purchase 端点 (使用跨域 handler)
4. [ ] 添加乐观锁/幂等性
5. [ ] 前端切换调用

---

### Phase E: Platform 功能迁移 (优先级 P2)

#### E1: Feature Flags

| 端点 | 新路径 |
|------|--------|
| 评估 Flag | GET /api/v2/platform/flags/{key} |
| 创建 Flag | POST /api/v2/platform/flags (admin) |

#### E2: Experiments

| 端点 | 新路径 |
|------|--------|
| 获取变体 | GET /api/v2/experiments/{key}/variant |
| 分配变体 | POST /api/v2/experiments/{key}/assign |

---

## 迁移检查清单

### 每个端点迁移前

- [ ] 旧端点有完整的测试覆盖
- [ ] 新端点逻辑与旧端点一致
- [ ] 新端点有对应的单元测试
- [ ] 错误响应格式一致

### 每个端点迁移后

- [ ] 前端已切换到新 API
- [ ] 监控无异常
- [ ] 旧端点添加废弃警告 (1 周)
- [ ] 移除旧端点代码

---

## Feature Flag 控制

使用 Feature Flag 控制迁移：

```python
# 在新旧 API 之间切换
USE_V2_CREDITS_API = "use_v2_credits_api"
USE_V2_PROJECTS_API = "use_v2_projects_api"
USE_V2_MARKETPLACE_API = "use_v2_marketplace_api"
```

前端根据 Flag 决定调用哪个版本：

```typescript
const creditsEndpoint = featureFlags.isEnabled('use_v2_credits_api')
  ? '/api/v2/credits'
  : '/api/user/me';
```

---

## 回滚策略

每个阶段的回滚方案：

1. **即时回滚**: 关闭 Feature Flag，流量回到旧 API
2. **代码回滚**: git revert 新端点提交
3. **数据回滚**: 新架构使用相同数据库表，无需数据回滚

---

## 时间线建议

| 阶段 | 内容 | 建议优先级 |
|------|------|------------|
| Phase A | 基础设施 | ✓ 已完成 |
| Phase B | Billing/Credits | 高 - 核心收入 |
| Phase C | Projects | 高 - 核心功能 |
| Phase D | Marketplace | 中 - 增长功能 |
| Phase E | Platform | 低 - 内部工具 |

---

## 风险和缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 新旧 API 行为不一致 | 用户体验问题 | 对比测试，A/B 验证 |
| 数据库事务问题 | 数据不一致 | 使用原子 RPC，添加幂等性 |
| 性能下降 | 响应变慢 | 添加缓存，监控 P99 |
| 依赖注入复杂度 | 维护困难 | 完善文档，统一模式 |

---

## 监控指标

迁移期间需要监控：

1. **API 响应时间**: 新旧 API P50/P95/P99 对比
2. **错误率**: 新 API 错误率 < 0.1%
3. **业务指标**: 积分扣费成功率、购买成功率
4. **用户反馈**: 支持工单数量

---

## 下一步行动

1. **Phase B1**: 完成 Credits API 前端切换
2. 添加 API 响应对比测试
3. 创建 Feature Flag 控制迁移
4. 开始 Projects API 迁移

---

*最后更新: 2026-01-07*
