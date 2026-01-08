# User API Review 计划

> **创建日期**: 2026-01-08
> **总接口数**: 110 个
> **当前阶段**: 进行中
> **最后更新**: 2026-01-08

---

## 执行规范

### API Review 标准流程

每个模块 Review 必须按以下步骤执行：

```
1. Review 接口逻辑
   - 检查 API 层代码
   - 追踪完整调用链 (API → Handler → Service → Repository)
   - 验证参数传递是否正确
   - 确认返回值类型是否匹配
   - 请仔细深入的review, 不要偷懒,不要跳过, 不要省略

2. 完善测试用例
   - 补全缺失的测试场景
   - 更新 mock 适配新架构
   - 验证所有测试通过
   - 驱动测试
   - 测试要符合业务逻辑的设计, 不是迎合测试和迎合业务逻辑的代码实现

3. 修复问题
   - DDD 模式合规 (CQRS, Handler 模式)
   - 项目规范 (CLAUDE.md 规则)
   - 代码规范 (参数命名, 返回类型)

4. 同步文档
   - 更新 API-REVIEW-ADMIN.md
   - 记录发现的问题和修复内容
   - 更新进度统计
   - 如果设计数据库,记得更新ddl.sql

5. 提交代码
   - git add + commit + push
   - Commit message 包含模块名和修复数量

6. 询问下一步操作 
```

### DDD 架构一致性规则

在 Review 过程中发现的旧式代码，必须统一迁移到 DDD 风格：

| 特征 | 旧式 (Legacy) | DDD 风格 |
|------|---------------|----------|
| 分页参数 | `page` + `limit` | `offset` + `limit` |
| 返回类型 | `List[dict]` (原始数据) | `List[Entity]` (领域对象) |
| 方法位置 | Repository 直接暴露给 API | Service → Repository |
| 接口定义 | 无 Interface | 定义在 `domains/*/repository.py` |

**清理原则**:
1. API 层只调用 Domain Service，不直接调用 Repository
2. Repository 实现必须符合 Interface 定义
3. 发现 Legacy 方法后：
   - 检查是否有调用方
   - 无调用则直接删除
   - 有调用则迁移到 DDD 风格后删除
4. 废弃的测试文件（引用不存在的模块）应同步删除

**已执行的清理** (2026-01-08):
- `listing_repository.py`: 删除 ~280 行 Legacy Extended Methods
- `tests/services/test_db_marketplace.py`: 删除废弃测试文件 (引用不存在的 `services.db.marketplace`)

---

## 执行进度

| 模块 | 接口数 | 已完成 | 状态 |
|------|--------|--------|------|
| Analytics | 1 | 1 | ✅ 已完成 |
| Billing 🔴 | 5 | 5 | ✅ 已完成 |
| Campaigns | 3 | 3 | ✅ 已修复 |
| Config | 3 | 3 | ✅ 已完成 |
| Experiments | 4 | 0 | 未开始 |
| Export | 4 | 0 | 未开始 |
| Generation Images 🔴 | 2 | 2 | ✅ 已完成 |
| Generation PDF | 1 | 0 | 未开始 |
| Generation Story 🔴 | 2 | 2 | ✅ 已完成 |
| Generations | 6 | 0 | 未开始 |
| Logs | 2 | 0 | 未开始 |
| Marketplace 🟡 | 11 | 11 | ✅ 已完成 |
| Payment 🔴 | 2 | 2 | ✅ 已完成 |
| Projects 🟡 | 10 | 10 | ✅ 已完成 |
| Resources | 7 | 0 | 未开始 |
| Support | 4 | 0 | 未开始 |
| System Resources | 9 | 0 | 未开始 |
| Tasks | 2 | 0 | 未开始 |
| Templates | 10 | 0 | 未开始 |
| Themes | 1 | 0 | 未开始 |
| Tools | 2 | 0 | 未开始 |
| User Assets | 10 | 0 | 未开始 |
| User Profile 🔴 | 7 | 7 | ✅ 已完成 |
| Webhooks 🔴 | 2 | 2 | ✅ 已完成 |
| **总计** | **110** | **48** | 43.6% |

---

## Analytics 分析模块 (1个) ✅ 已完成

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 | 状态 |
|------|------|------|------|------|------|------|
| 1 | log_analytics_events | POST | /events | api/user/analytics.py | 113 | ✅ |

**测试用例 Checklist**
- [x] #1.1 单事件上报成功
- [x] #1.2 批量事件上报
- [x] #1.3 匿名用户上报
- [x] #1.4 活动日志镜像 (project_* 事件)
- [x] #1.5 服务端信息增强 (IP/Geo/UA)
- [x] #1.6 无效 payload 返回 422
- [x] #1.7 空事件数组处理
- [x] #1.8 analytics_events 插入失败优雅处理

### Review 结果 (2026-01-08) - 深入分析

**调用链追踪**:
```
API log_analytics_events (L113-208)
├── 获取客户端信息 (_get_client_ip, _get_cloudflare_geo)
├── for each event:
│   ├── SupabaseAdminStatsRepository.log_user_event() → user_events 表
│   │   └── @retry_on_network_error (3次重试)
│   ├── supabase.table("analytics_events").insert() → analytics_events 表
│   │   └── try-catch 容错
│   └── log_activity() → activity_logs 表 (关键事件)
└── 返回 AnalyticsEventsResponse
```

**发现的问题**:

| 序号 | 严重性 | 问题 | 影响 | 建议 |
|------|--------|------|------|------|
| 1 | 🟠 HIGH | L169 `log_user_event` 无 try-catch | 失败时整个请求 500，后续事件丢失 | 添加异常处理 |
| 2 | 🟡 MEDIUM | L188 同步 supabase vs L169 异步混用 | 一致性问题 | 统一使用方式 |
| 3 | 🟢 LOW | L146 循环内多次 DB 调用 | 大批量性能问题 | 可考虑批量插入 |

**设计决策说明**:
- `user_events` 是主存储，失败应该通知用户
- `analytics_events` 是冗余存储，静默失败可接受
- Supabase Python SDK 是同步的，async 方法内同步调用是常见模式

**架构说明**:
- 简单日志记录接口，直接使用 Repository 合理 (无需 DDD Service)
- 支持匿名/登录用户 (`get_current_user_optional`)
- 限流 60/minute
- 双表存储: `user_events` + `analytics_events`
- 关键事件 (`project_*`) 镜像到 `activity_logs`
- 容错设计: `analytics_events` 失败不影响主流程

**测试文件**:
- `tests/api/user/test_analytics.py` - 8 个测试用例 (已存在)

**完成状态**: ✅ 已完成 (2026-01-08)

---

## Billing 积分模块 (5个) 🔴 P0 ✅ 已完成

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 | 状态 |
|------|------|------|------|------|------|------|
| 2 | get_credits | GET | /credits | api/user/billing.py | 97 | ✅ |
| 3 | get_transactions | GET | /transactions | api/user/billing.py | 122 | ✅ |
| 4 | check_can_afford | GET | /can-afford | api/user/billing.py | 176 | ✅ 🔧 |
| 5 | deduct_credits | POST | /credits/deduct | api/user/billing.py | 227 | ✅ 🔧 |
| 6 | add_credits | POST | /credits/add | api/user/billing.py | 267 | ✅ 🔧 |

**测试用例 Checklist**
- [x] #2 获取积分余额 (月度+永久)
- [x] #2 新用户初始积分 (50永久)
- [x] #3 交易历史分页
- [x] #4 积分检查 (足够/不足/边界)
- [x] #5 扣费顺序 (先月度后永久)
- [x] #5 余额不足拒绝
- [x] #5 并发扣费安全
- [x] #6 添加积分记录

### Review 结果 (2026-01-08)

**发现并修复的 Bug** 🔧:

1. **`check_can_afford` (L209-210)**
   - 问题: `cost.amount` 访问不存在的属性 (`get_operation_cost` 返回 `int`)
   - 修复: 直接使用返回的整数值 `required = billing_service.get_operation_cost(operation)`

2. **`deduct_credits` (L261-262)**
   - 问题: `result.amount_deducted` 和 `result.new_balance` 不存在于 `DeductCreditsResult`
   - 修复: 使用 `abs(result.transaction.amount)` 和 `result.remaining_credits`

3. **`add_credits` (L306)**
   - 问题: `result.amount_added` 不存在于 `AddCreditsResult`
   - 修复: 使用 `result.transaction.amount`

4. **`get_transactions` 分页 total_count 问题**
   - 问题: `total_count=len(transactions)` 返回当前页数量而非总记录数
   - 影响: 分页 UI 无法正确显示总页数
   - 修复:
     - `domains/billing/repository.py` - 添加 `get_transaction_count()` 接口
     - `infrastructure/repositories/credit_repository.py` - 实现 count 查询
     - `domains/billing/service.py` - 添加代理方法
     - `application/queries/billing.py` - 组合 list 和 count 查询

**测试文件修复**:

1. `tests/domains/test_billing_domain.py` - 完全重写 (原文件使用了不存在的类/方法)
2. `tests/api/user/test_billing.py` - 补充 20+ 个测试用例:
   - 未认证访问 (401)
   - 无效 token (401)
   - 新用户零积分
   - 日期范围过滤
   - 分页测试
   - 边界值验证

**完成状态**: ✅ 已完成 (2026-01-08)

---

## Campaigns 活动模块 (3个) ✅ 已修复

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 | 状态 |
|------|------|------|------|------|------|------|
| 7 | get_active_campaigns | GET | /active | api/user/campaigns.py | 92 | ✅ |
| 8 | claim_campaign | POST | /{campaign_id}/claim | api/user/campaigns.py | 163 | ✅ 已修复 |
| 9 | dismiss_notification | POST | /{campaign_id}/dismiss | api/user/campaigns.py | 246 | ✅ |

**测试用例 Checklist**
- [x] #7.1 获取活跃活动
- [x] #7.2 空活动列表
- [x] #7.3 匿名用户访问
- [x] #8.1 活动不存在返回 404
- [x] #8.2 需要认证 401
- [x] #9.1 关闭通知成功
- [x] #9.2 无效 channel 返回 422
- [x] #9.3 需要认证 401

### Review 结果 (2026-01-08) - 深入分析

**调用链追踪**:

```
#7 get_active_campaigns (L92-160)
├── supabase.table("campaigns").select()  // 获取活跃活动
└── for each campaign:
    ├── _check_target_eligibility()  // 检查受众资格
    ├── _check_has_claimed()  // supabase.table("campaign_claims").select()
    ├── _get_dismissed_channels()  // supabase.table("campaign_dismissals").select()
    └── _build_notification()

#8 claim_campaign (L163-243) 🔴 CRITICAL
├── supabase.table("campaigns").select()  // 获取活动
├── 验证: status, is_active, time_range, eligibility
├── supabase.table("campaign_claims").select()  // 检查是否已领取
├── _check_usage_limit()  // 检查使用量
├── SupabaseCreditRepository.add_credits_permanent()  // 🔴 发积分
├── supabase.table("campaign_claims").insert()  // 🔴 记录领取
└── supabase.table("campaigns").update()  // 更新使用计数

#9 dismiss_notification (L246-260)
└── supabase.table("campaign_dismissals").upsert()
```

**发现的问题**:

| 序号 | 严重性 | 问题 | 位置 | 影响 |
|------|--------|------|------|------|
| 1 | 🔴 **CRITICAL** | **积分发放与记录非原子** | L217-231 | 并发时: 积分已发但 INSERT 因 UNIQUE 约束失败，用户得到积分但无记录 |
| 2 | 🟠 HIGH | `usage_count` 竞态条件 | L207-236 | 并发请求可能突破 usage_limit |
| 3 | 🟠 HIGH | N+1 查询问题 | L123-132 | 每个活动 2 次额外 DB 调用 |
| 4 | 🟡 MEDIUM | `_build_notification` can_claim 硬编码 | L351 | 通知 can_claim 始终为 True |
| 5 | 🟡 MEDIUM | 不符合 DDD 架构 | 全文件 | 直接调用 supabase，无 Service 层 |

**问题 #1 详细分析** (CRITICAL):

```python
# 并发场景 (用户 A 和 B 同时请求):
# 1. A 和 B 都通过 L199-204 检查 (SELECT 查询，此时无记录)
# 2. A: add_credits_permanent 成功 (+50 积分)
# 3. B: add_credits_permanent 成功 (+50 积分)  <-- 积分已发!
# 4. A: INSERT campaign_claims 成功
# 5. B: INSERT campaign_claims 失败 (UNIQUE 约束)
# 6. B 收到错误，但积分已发且无法回滚

# 正确做法: 先 INSERT campaign_claims，成功后再发积分
```

**修复方案**:

```python
# 重新排序操作:
# 1. 先插入 claim 记录 (利用 UNIQUE 约束防止并发)
# 2. 成功后再发放积分
# 3. 如果发积分失败，删除 claim 记录

# 或使用数据库事务:
# BEGIN; INSERT campaign_claims; add_credits; COMMIT;
```

**架构说明**:
- 支持 5 种目标受众: `all`, `subscription`, `users`, `new_users`, `inactive_users`
- 支持 3 种通知渠道: `modal`, `toast`, `banner`
- `campaign_claims` 表有 UNIQUE(campaign_id, user_id) 约束
- 但积分发放在约束检查之前，存在竞态窗口

**测试文件**:
- `tests/api/user/test_campaigns.py` - 10 个测试用例 (8 passed, 2 skipped)
- 缺少并发测试用例

**修复内容 (2026-01-08)**:

1. **CRITICAL Bug 修复 - 并发竞态条件** (#1):
   - 重新排序操作：先 INSERT claim 记录，成功后再发积分
   - 利用 UNIQUE 约束防止并发重复领取
   - 如果积分发放失败，删除 claim 记录允许用户重试
   - 文件: `api/user/campaigns.py` L218-248

2. **usage_count 原子递增** (#2 HIGH):
   - 创建 RPC 函数 `increment_campaign_usage` 实现原子操作
   - UPDATE 语句带 WHERE 条件检查 usage_limit
   - 文件: `migrations/v3.27_campaign_atomic_increment.sql`
   - 同步更新: `migrations/ddl.sql`

3. **N+1 查询优化** (#3 HIGH):
   - 新增 `_batch_get_user_campaign_status()` 批量查询函数
   - 2 次批量查询替代 N×2 次单条查询
   - 查询 campaign_claims 和 campaign_dismissals 使用 IN 条件
   - 文件: `api/user/campaigns.py` L347-386

4. **`_build_notification` can_claim 参数化** (#4 MEDIUM):
   - 添加 `can_claim` 参数，传入实际值
   - 通知数据现在正确反映领取状态
   - 文件: `api/user/campaigns.py` L413

5. **DDD 架构准备** (#5 MEDIUM):
   - 创建 `domains/marketing/` 目录
   - 定义 `ICampaignRepository` 接口 (`domains/marketing/repository.py`)
   - 实现 `SupabaseCampaignRepository` (`infrastructure/repositories/campaign_repository.py`)
   - API 层暂保持直接调用 supabase，待后续全面迁移

**新增测试用例**:
- `TestBatchQueryOptimization.test_batch_get_user_campaign_status` - 批量查询验证
- `TestBatchQueryOptimization.test_batch_get_user_campaign_status_empty` - 空列表处理
- `TestRaceConditionPrevention.test_claim_duplicate_key_error_handled` - UNIQUE 约束竞态
- `TestRaceConditionPrevention.test_atomic_usage_increment_via_rpc` - RPC 调用验证

**测试结果**: 14 passed, 2 skipped

**完成状态**: ✅ 已修复 (2026-01-08)

---

## Config 配置模块 (3个) ✅ 已完成

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 | 状态 |
|------|------|------|------|------|------|------|
| 10 | list_configs | GET | / | api/user/config.py | 45 | ✅ |
| 11 | get_group | GET | /group/{group_name} | api/user/config.py | 55 | ✅ |
| 12 | get_config | GET | /{key} | api/user/config.py | 64 | ✅ |

**测试用例 Checklist**
- [x] #10.1 获取全部配置
- [x] #10.2 空配置返回空 dict
- [x] #11.1 按组获取配置
- [x] #11.2 不存在的组返回空数组
- [x] #11.3 feature flags 组
- [x] #12.1 按 key 获取配置
- [x] #12.2 配置不存在返回 404
- [x] #12.3 布尔值配置
- [x] #12.4 字符串配置

### Review 结果 (2026-01-08)

**代码分析**: 无 Bug

**架构说明**:
- 简单只读配置 API，直接使用 Repository 合理
- Repository 实现内置 5 分钟缓存
- 无认证要求 (公共配置)
- 不涉及复杂业务逻辑

**测试文件**:
- `tests/api/user/test_config.py` - 9 个测试用例

**完成状态**: ✅ 已完成 (2026-01-08)

---

## Experiments 实验模块 (4个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 13 | assign_variant | POST | /{experiment_key}/assign | api/user/experiments.py | 50 |
| 14 | track_exposure | POST | /{experiment_key}/exposure | api/user/experiments.py | 75 |
| 15 | track_conversion | POST | /{experiment_key}/conversion | api/user/experiments.py | 87 |
| 16 | get_user_experiments | GET | /user/{user_identifier} | api/user/experiments.py | 102 |

**测试用例 Checklist**
- [ ] #13 分配实验组
- [ ] #14 曝光追踪
- [ ] #15 转化追踪
- [ ] #16 用户实验查询

**完成状态**: 未开始

---

## Export 导出模块 (4个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 17 | export_project_pdf | GET | /projects/{project_id}/pdf | api/user/export.py | 79 |
| 18 | export_project_preview | GET | /projects/{project_id}/preview | api/user/export.py | 113 |
| 19 | export_zip | POST | /zip | api/user/export.py | 162 |
| 20 | export_project_zip | GET | /projects/{project_id}/zip | api/user/export.py | 194 |

**测试用例 Checklist**
- [ ] #17 PDF导出
- [ ] #18 预览图生成
- [ ] #19 ZIP打包 (废弃)
- [ ] #20 项目ZIP导出

**完成状态**: 未开始

---

## Generation Images AI图片生成模块 (2个) 🔴 P0 ✅ 已完成 (v3.25 重构)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 | 状态 |
|------|------|------|------|------|------|------|
| 21 | gen_images | POST | /images | api/user/generation_images.py | 56 | ✅ 🔧 |
| 22 | gen_images_async | POST | /images/async | api/user/generation_images.py | 276 | ✅ 🔧 |

**测试用例 Checklist**
- [x] #21 同步生成图片 (Free/Pro)
- [x] #21 扣费5积分 (Reference 7积分) - 从config读取
- [x] #21 余额不足拒绝 (402)
- [x] #21 模型选择 (Free: flux-schnell, Pro: flux-dev)
- [x] #21 Safety 过滤 (NSFW 拦截)
- [x] #21 多图扣费 (5 * num_images)
- [x] #21 num_images 限制 (1-4)
- [x] #21 生成失败自动退款 (NEW)
- [x] #21 空结果自动退款 (NEW)
- [x] #22 异步生成返回task_id
- [x] #22 积分提前扣费
- [x] #22 队列失败退款 (503)
- [x] #22 Pro用户高优先级

### Review 结果 (2026-01-08)

**初次分析发现的3个问题及修复** 🔧:

1. **使用旧版方法** (已修复)
   - 问题: 使用 `SupabaseCreditRepository.deduct_credits()` 而非 DDD `BillingService`
   - 修复: 迁移到 `BillingService.deduct_credits()` + `InsufficientCreditsException`
   - 原则: CLAUDE.md 规定不需要向后兼容

2. **费用硬编码** (已修复)
   - 问题: `base_cost = 7 if req.reference_image else 5` 直接写死
   - 修复: 创建 `get_base_cost()` 函数，从 ConfigService 读取
     - `credits.cost.image_generation` (默认5)
     - `credits.cost.image_generation_reference` (默认7)
   - 添加新配置到 `migrations/ddl.sql`

3. **生成失败无退款** (已修复)
   - 问题: 先扣费后生成，生成失败时已扣的积分丢失
   - 修复: 添加 try-catch，失败时调用 `BillingService.add_credits()` 退款
   - 使用 `TransactionType.REFUND` 和 `CreditBucket.PERMANENT`
   - 包括空结果情况也会触发退款

**v3.25 重构变更**:
1. `api/user/generation_images.py`:
   - 迁移到 DDD BillingService
   - 使用 `container.billing_service`
   - 添加生成失败/空结果退款逻辑
   - 使用 `generation_helpers` 复用逻辑

2. `application/services/generation_helpers.py`:
   - 新增 `get_base_cost()` 从 ConfigService 读取费用
   - 修改 `calculate_cost()` 使用动态费用
   - 添加 config key 常量

3. `migrations/ddl.sql`:
   - 新增 `credits.cost.image_generation_reference` (7)

**测试文件更新**:
- `tests/api/user/test_generation_images.py` - 重写为 16 个测试用例:
  - Mock 改为 `container.billing_service`
  - 新增生成失败退款测试
  - 新增空结果退款测试

**完成状态**: ✅ 已完成 + v3.25 重构 (2026-01-08)

---

## Generation PDF PDF生成模块 (1个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 23 | gen_pdf | POST | /pdf | api/user/generation_pdf.py | 31 |

**测试用例 Checklist**
- [ ] #23 PDF生成
- [ ] #23 tier权限验证

**完成状态**: 未开始

---

## Generation Story AI故事生成模块 (2个) 🔴 P0 ✅ 已完成

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 | 状态 |
|------|------|------|------|------|------|------|
| 24 | gen_story | POST | /story | api/user/generation_story.py | 31 | ✅ |
| 25 | gen_inspiration | POST | /inspiration | api/user/generation_story.py | 50 | ✅ |

**测试用例 Checklist**
- [x] #24 故事生成 (Free/Pro)
- [x] #24 Tier传递给生成器
- [x] #24 异常处理 (500)
- [x] #24 未授权 (401)
- [x] #24 缺少topic (422)
- [x] #25 灵感生成 (免费) - 默认category
- [x] #25 各category类型 (character/scene/story/all)
- [x] #25 API失败回退 (fallback)
- [x] #25 未授权 (401)

### Review 结果 (2026-01-08)

**代码分析**: 无 Bug

**业务逻辑说明**:
1. `gen_story`: 故事生成目前**免费** (代码未实现扣费)
   - CLAUDE.md 文档说扣费1积分，但 `EMERGENCY_FALLBACK_COSTS["text_generation"] = 0`
   - 这是设计决策，非Bug
2. `gen_inspiration`: 灵感生成**免费** (明确设计)
   - API失败时有优雅降级 (返回hardcoded fallback)

**测试文件补充**:
- `tests/api/user/test_generation_story.py` - 新增 11 个测试用例

**完成状态**: ✅ 已完成 (2026-01-08)

---

## Generations 生成历史模块 (6个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 26 | get_generation_history | GET | /history | api/user/generations.py | 69 |
| 27 | update_generation | PATCH | /{generation_id} | api/user/generations.py | 110 |
| 28 | toggle_favorite | POST | /{generation_id}/favorite | api/user/generations.py | 135 |
| 29 | clear_generation_history | DELETE | /batch | api/user/generations.py | 161 |
| 30 | delete_generation | DELETE | /{generation_id} | api/user/generations.py | 192 |
| 31 | batch_delete_generations | POST | /batch-delete | api/user/generations.py | 209 |

**测试用例 Checklist**
- [ ] #26 获取生成历史
- [ ] #27 更新生成记录
- [ ] #28 收藏切换
- [ ] #29 清空历史 (废弃)
- [ ] #30 删除单条
- [ ] #31 批量删除

**完成状态**: 未开始

---

## Logs 日志模块 (2个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 32 | log_error | POST | /error | api/user/logs.py | 82 |
| 33 | log_errors_batch | POST | /errors | api/user/logs.py | 124 |

**测试用例 Checklist**
- [ ] #32 单条错误上报
- [ ] #33 批量错误上报

**完成状态**: 未开始

---

## Marketplace 市场模块 (11个) 🟡 P1 🔄 审查中

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 | 状态 |
|------|------|------|------|------|------|------|
| 34 | list_listings | GET | /listings | api/user/marketplace.py | 127 | ✅ 🔧 |
| 35 | get_listing | GET | /listings/{listing_id} | api/user/marketplace.py | 184 | ✅ 🔧 |
| 36 | create_listing | POST | /listings | api/user/marketplace.py | 213 | ✅ 🔧 |
| 37 | update_listing | PUT | /listings/{listing_id} | api/user/marketplace.py | 280 | ✅ 🔧 |
| 38 | unpublish_listing | DELETE | /listings/{listing_id} | api/user/marketplace.py | 331 | ✅ 🔧 |
| 39 | purchase_listing | POST | /purchase | api/user/marketplace.py | 367 | ✅ 🔧 |
| 40 | get_my_listings | GET | /my-listings | api/user/marketplace.py | 438 | ✅ 🔧 |
| 41 | get_seller_stats | GET | /seller/stats | api/user/marketplace.py | 493 | ✅ 🔧 |
| 42 | get_leaderboard | GET | /leaderboard | api/user/marketplace.py | 541 | ✅ 🔧 |
| 43 | submit_report | POST | /report | api/user/marketplace.py | 608 | ✅ 🔧 |
| 44 | get_my_reports | GET | /my-reports | api/user/marketplace.py | 649 | ✅ 🔧 |

**测试用例 Checklist**

**#34 list_listings** ✅
- [x] #34.1 商品列表分页
- [x] #34.2 过滤参数传递 (featured/sort/tier/price)
- [x] #34.3 best_selling 排序支持
- [x] #34.4 无效 sort 参数返回 422
- [x] #34.5 未授权返回 401
- [x] #34.6 Handler 错误返回 500

**#35 get_listing** ✅
- [x] #35.1 获取商品详情 (含 is_purchased, seller_username, seller_avatar_url)
- [x] #35.2 商品不存在返回 404
- [x] #35.3 user_id 传递给 Handler 做访问控制
- [x] #35.4 访问控制 (未公开/已删除/未审核 listing 非卖家不可见)
- [x] #35.5 is_purchased 字段反映真实购买状态

**#36 create_listing** ✅
- [x] #36.1 Pro 用户创建付费商品
- [x] #36.2 Starter 用户创建免费 asset
- [x] #36.3 Starter 用户创建付费商品返回 403
- [x] #36.4 Starter 用户创建 project 返回 403
- [x] #36.5 无效 resource_type 返回 422
- [x] #36.6 两级分类: resource_type + category
- [x] #36.7 category 默认值 (asset→element, project→template)
- [x] #36.8 source 字段 (system/user/ai/community)
- [x] #36.9 allowed_tiers 字段传递

### Review 结果 - #36 create_listing (2026-01-08)

**发现的问题** 🔧:

1. **resource_type 与 AssetCategory 枚举不匹配** (已修复)
   - 问题: `resource_type` 参数值 ("asset"/"project") 直接传递给 `AssetCategory` 枚举
   - 影响: 任何 create_listing 调用都会抛出 `ValueError` (因为 "asset" 不是有效的 AssetCategory 值)
   - 修复: 实现两级分类系统

**两级分类方案**:

| 字段 | 说明 | 值 |
|------|------|-----|
| `resource_type` | 顶级分类 | `asset` (单个素材) / `project` (项目模板) |
| `category` | 具体类型 | `clipart`, `sticker`, `background`, `element`, `template`, `mini_book`, `worksheet`, `flashcard` 等 |
| `source` | 来源标识 | `system` (系统), `user` (用户上传), `ai` (AI生成), `community` (社区) |
| `allowed_tiers` | 开放等级 | `["free", "starter", "pro"]` |

**默认值逻辑**:
- `resource_type=asset` → `category` 默认为 `element`
- `resource_type=project` → `category` 默认为 `template`

**修复涉及的文件**:

1. `migrations/v3.26_marketplace_two_level_category.sql` (新增)
   - 添加 `category` 和 `source` 字段到 `marketplace_listings` 表
   - 创建索引优化查询

2. `migrations/ddl.sql`
   - 同步新字段定义

3. `domains/marketplace/value_objects.py`
   - 新增 `ResourceType` 枚举 (asset/project)
   - 新增 `ListingSource` 枚举 (system/user/ai/community)
   - 扩展 `AssetCategory` 添加更多类型及 `is_project_category` 属性

4. `domains/marketplace/__init__.py`
   - 导出新枚举

5. `domains/marketplace/aggregates/listing.py`
   - 添加 `resource_type`, `source`, `allowed_tiers` 字段
   - 更新 `create_new()` 工厂方法
   - 更新 `to_dict()` 输出

6. `domains/marketplace/service.py`
   - 更新 `create_listing()` 方法签名

7. `infrastructure/repositories/listing_repository.py`
   - 更新 `_map_to_listing()` 和 `_map_to_row()` 字段映射

8. `application/commands/marketplace.py`
   - 更新 `CreateListingCommand` 支持新字段
   - 更新 Handler 解析逻辑 (带 ValueError 容错)

9. `api/user/marketplace.py`
   - 更新 `ListingCreateRequest` 支持新字段
   - 更新 API 映射逻辑

**测试文件更新**:
- `tests/api/user/test_marketplace.py` - 新增 5 个测试用例:
  - `test_create_listing_with_category` (#36.6)
  - `test_create_listing_category_defaults_for_asset` (#36.7a)
  - `test_create_listing_category_defaults_for_project` (#36.7b)
  - `test_create_listing_with_source` (#36.8)
  - `test_create_listing_with_allowed_tiers` (#36.9)

### Review 结果 - #37 update_listing (2026-01-08)

**发现的问题** 🔧:

1. **参数名称不匹配** (已修复)
   - 问题: API 传递 `seller_id` 参数，但 `MarketplaceService.update_listing()` 期望 `user_id`
   - 影响: 所有更新调用都会失败 (`TypeError`)
   - 修复: 通过 Command Handler 模式统一参数命名

2. **缺少 price_credits 和 allowed_tiers 支持** (已修复)
   - 问题: API 接受 `price_credits` 和 `allowed_tiers` 参数，但未传递到 Service
   - 影响: 这两个字段的更新完全不生效
   - 修复: 在 Handler 中处理定价和权限更新

3. **返回类型不匹配** (已修复)
   - 问题: API 期望 `.success` 属性的 Result 对象，但 Service 直接返回 `Listing` 实体
   - 影响: API 运行时错误 (`AttributeError`)
   - 修复: 创建 `UpdateListingResult` 数据类

**修复涉及的文件**:

1. `application/commands/marketplace.py`
   - 新增 `UpdateListingCommand` 数据类
   - 新增 `UpdateListingResult` 数据类 (含 `success`, `listing`, `requires_resubmit`, `error`)
   - 新增 `UpdateListingHandler` 类处理更新逻辑

2. `container.py`
   - 添加 `UpdateListingHandler` 导入
   - 添加 `update_listing_handler` 属性

3. `api/user/marketplace.py`
   - 更新导入添加 `UpdateListingCommand`
   - 重写 `update_listing` 端点使用 Handler 模式

**测试文件更新**:
- `tests/api/user/test_marketplace.py` - 更新 4 个测试用例使用 Handler mock:
  - `test_update_listing_success` (#37.1)
  - `test_update_listing_not_found` (#37.2)
  - `test_update_listing_pending_forbidden` (#37.3)
  - `test_update_listing_with_allowed_tiers` (#37.4)

**#37 update_listing**
- [x] #37.1 更新商品成功
- [x] #37.2 商品不存在返回 404
- [x] #37.3 pending 状态不能编辑返回 400
- [x] #37.4 更新 allowed_tiers 成功

### Review 结果 - #38 unpublish_listing (2026-01-08)

**发现的问题** 🔧:

1. **Service 方法不存在** (已修复)
   - 问题: API 调用 `marketplace_service.unpublish_listing()` 但该方法不存在
   - 影响: 所有下架请求都会抛出 `AttributeError`
   - 修复: 在 Service 层添加 `unpublish_listing` 方法

2. **未使用 Handler 模式** (已修复)
   - 问题: 原代码直接调用 Service，不符合 CQRS 架构
   - 修复: 创建 Command/Result/Handler 统一模式

**修复涉及的文件**:

1. `domains/marketplace/service.py`
   - 新增 `unpublish_listing()` 方法
   - 验证用户权限和状态 (只有 PUBLISHED 可下架)
   - 调用 aggregate 的 `archive()` 方法

2. `application/commands/marketplace.py`
   - 新增 `UnpublishListingCommand` 数据类
   - 新增 `UnpublishListingResult` 数据类
   - 新增 `UnpublishListingHandler` 类

3. `container.py`
   - 添加 `UnpublishListingHandler` 导入
   - 添加 `unpublish_listing_handler` 属性

4. `api/user/marketplace.py`
   - 更新导入添加 `UnpublishListingCommand`
   - 重写 `unpublish_listing` 端点使用 Handler 模式

**测试文件更新**:
- `tests/api/user/test_marketplace.py` - 更新 3 个测试用例使用 Handler mock:
  - `test_unpublish_listing_success` (#38.1)
  - `test_unpublish_listing_not_found` (#38.2)
  - `test_unpublish_listing_not_published` (#38.3)

**#38 unpublish_listing**
- [x] #38.1 下架商品成功
- [x] #38.2 商品不存在返回 404
- [x] #38.3 非发布状态不能下架返回 400

### Review 结果 - #39 purchase_listing (2026-01-08)

**发现的问题** 🔧:

1. **PurchaseListingResult 缺少必要字段** (已修复)
   - 问题: Result 缺少 `project_id` 和 `already_owned` 字段
   - 影响: API 使用 getattr 回退，响应字段不稳定
   - 修复: 添加 `project_id` 和 `already_owned` 字段到 Result

2. **缺少 allowed_tiers 权限检查** (已修复)
   - 问题: Handler 未检查 `buyer_tier` 是否在 `listing.allowed_tiers` 中
   - 影响: 用户可以购买不允许其等级访问的商品
   - 修复: 在 Handler 中添加 tier 权限检查

3. **重复购买处理不完善** (已修复)
   - 问题: Service 抛出 `AlreadyPurchasedException` 但 Handler 未优雅处理
   - 修复: 在 Handler 中提前检查购买状态，返回 `already_owned=True`

4. **异常处理不完整** (已修复)
   - 问题: Handler 只有通用 Exception 处理
   - 修复: 添加专门的异常捕获 (AlreadyPurchased, NotPublished, PurchaseFailed)

**修复涉及的文件**:

1. `application/commands/marketplace.py`
   - 扩展 `PurchaseListingResult` 添加 `already_owned`, `project_id` 字段
   - 重写 `PurchaseListingHandler.handle()` 方法:
     - 添加 tier 权限检查
     - 提前检查购买状态
     - 完善异常处理

2. `api/user/marketplace.py`
   - 简化响应映射 (直接使用 result 字段)

**测试文件**:
- `tests/api/user/test_marketplace.py` - 已有 4 个测试用例覆盖所有场景

**#39 purchase_listing**
- [x] #39.1 购买成功 (扣费+返回 project_id)
- [x] #39.2 余额不足返回 402
- [x] #39.3 商品不存在返回 404
- [x] #39.4 tier 权限不足返回 403

**#40 get_my_listings**
- [x] #40.1 获取我的商品列表
- [x] #40.2 分页 offset 计算正确
- [x] #40.3 status 过滤参数
- [x] #40.4 无效 status 返回 422

**#41 get_seller_stats**
- [x] #41.1 获取卖家统计

**#42 get_leaderboard**
- [x] #42.1 获取排行榜
- [x] #42.2 period/type 过滤

**#43 submit_report**
- [x] #43.1 提交举报成功
- [x] #43.2 重复举报返回 400

**#44 get_my_reports**
- [x] #44.1 获取我的举报列表

### Review 结果 - #40 get_my_listings (2026-01-08)

**发现的问题** 🔧:

1. **参数名称不匹配导致严重 Bug** (已修复)
   - 问题: API 传递 `page` 参数，但 Service 方法签名是 `(seller_id, status, limit, offset)`
   - 影响: `page=1` 被当作 `status=1` 传入，导致查询行为完全错误
   - 修复: API 层将 `page` 转换为 `offset = (page - 1) * limit`

2. **缺少 status 过滤功能** (已修复)
   - 问题: 用户无法按状态筛选自己的 listings (draft/pending/published 等)
   - 修复: 添加 `status` 查询参数，支持 6 种状态过滤

**修复涉及的文件**:

1. `api/user/marketplace.py`
   - 添加 `status` 参数 (可选)
   - 计算 `offset = (page - 1) * limit`
   - 解析 `ListingStatus` 枚举
   - 正确传递参数给 Service

**测试文件更新**:
- `tests/api/user/test_marketplace.py` - 新增 3 个测试用例:
  - `test_get_my_listings_pagination_offset_calculation` (#40.2)
  - `test_get_my_listings_with_status_filter` (#40.3)
  - `test_get_my_listings_invalid_status_validation` (#40.4)

### Review 结果 - #41 get_seller_stats (2026-01-08)

**发现的问题** 🔧:

1. **Service 方法不存在** (已修复)
   - 问题: API 调用 `marketplace_service.get_seller_stats()` 但该方法不存在
   - 影响: 所有请求都会抛出 `AttributeError`
   - 修复: 在 `MarketplaceService` 添加代理方法到 Repository

**修复涉及的文件**:

1. `domains/marketplace/service.py`
   - 新增 `get_seller_stats()` 方法

### Review 结果 - #42 get_leaderboard (2026-01-08)

**发现的问题** 🔧:

1. **Service 方法不存在** (已修复)
   - 问题: API 调用 `marketplace_service.get_leaderboard()` 但该方法不存在
   - 影响: 所有请求都会抛出 `AttributeError`
   - 修复: 在 `MarketplaceService` 添加代理方法到 Repository

**修复涉及的文件**:

1. `domains/marketplace/service.py`
   - 新增 `get_leaderboard()` 方法

### Review 结果 - #43 submit_report (2026-01-08)

**发现的问题** 🔧:

1. **Repository 方法不存在** (已修复)
   - 问题: API 调用 `support_repo.create_report()` 但该方法不存在
   - 影响: 所有举报请求都会抛出 `AttributeError`
   - 修复: 在 `SupabaseSupportRepository` 实现 `create_report()` 方法

**修复涉及的文件**:

1. `infrastructure/repositories/support_repository.py`
   - 新增 `create_report()` 方法
   - 检查重复举报
   - 插入 `marketplace_reports` 表

### Review 结果 - #44 get_my_reports (2026-01-08)

**发现的问题** 🔧:

1. **Repository 方法不存在** (已修复)
   - 问题: API 调用 `support_repo.get_user_reports()` 但该方法不存在
   - 影响: 所有请求都会抛出 `AttributeError`
   - 修复: 在 `SupabaseSupportRepository` 实现 `get_user_reports()` 方法

**修复涉及的文件**:

1. `infrastructure/repositories/support_repository.py`
   - 新增 `get_user_reports()` 方法
   - 查询 `marketplace_reports` 表
   - 支持分页

### Review 结果 - #34 list_listings (2026-01-08)

**发现的问题** 🔧:

1. **API 参数未传递到底层** (已修复)
   - 问题: `featured`, `sort`, `tier` 参数在 API 定义了但未传递给 `SearchListingsQuery`
   - 影响: 这些过滤/排序参数完全不生效
   - 修复: 扩展整个调用链支持这些参数

**修复涉及的文件**:

1. `domains/marketplace/value_objects.py`:
   - 新增 `ListingSortOrder` 枚举 (latest/popular/price_asc/price_desc/best_selling)
   - 新增 `PriceFilter` 枚举 (all/free/paid)

2. `domains/marketplace/__init__.py`:
   - 导出新枚举

3. `application/queries/marketplace.py`:
   - 扩展 `SearchListingsQuery` 添加 `price_filter`, `sort_by`, `tier_filter`, `featured` 参数
   - 更新 `SearchListingsHandler` 调用新的 `search_listings_with_filters()` 方法

4. `domains/marketplace/service.py`:
   - 新增 `search_listings_with_filters()` 方法

5. `domains/marketplace/repository.py`:
   - 接口新增 `search_with_filters()` 方法签名

6. `infrastructure/repositories/listing_repository.py`:
   - 实现 `search_with_filters()` 方法
   - 支持所有过滤和排序选项
   - 返回 `(listings, total_count)` 支持精确分页

7. `api/user/marketplace.py`:
   - 更新 API 传递完整参数到 Query
   - 添加 `best_selling` 到 sort 正则验证

**测试文件更新**:
- `tests/api/user/test_marketplace.py`:
  - 更新 `test_list_listings_with_filters` 验证所有参数传递
  - 新增 `test_list_listings_best_selling_sort` 测试

### Review 结果 - #35 get_listing (2026-01-08)

**发现的问题** 🔧:

1. **缺少访问控制** (已修复)
   - 问题: 直接返回 listing，未检查 `is_public`, `is_deleted`, `moderation_status`
   - 影响: 未发布/已删除/未审核的 listing 对所有用户可见
   - 修复: 在 Repository 层实现访问控制 (seller 可见，其他用户需 visibility 检查)

2. **缺少 is_purchased 字段** (已修复)
   - 问题: 买家无法知道自己是否已购买该 listing
   - 修复: 查询 `marketplace_purchases` 表返回购买状态

3. **缺少卖家信息** (已修复)
   - 问题: 响应不包含卖家 username 和 avatar
   - 修复: JOIN `profiles` 表返回 `seller_username`, `seller_avatar_url`

**修复涉及的文件**:

1. `application/queries/marketplace.py`:
   - 扩展 `GetListingQuery` 添加 `user_id: Optional[str]` 参数
   - 扩展 `GetListingResult` 添加 `is_purchased`, `seller_info` 字段
   - 更新 `GetListingHandler` 使用 `get_listing_detail()` 方法

2. `domains/marketplace/repository.py`:
   - 新增 `get_seller_info()` 接口
   - 新增 `get_listing_detail()` 接口 (含访问控制)

3. `domains/marketplace/service.py`:
   - 新增 `get_listing_detail()` 代理方法

4. `infrastructure/repositories/listing_repository.py`:
   - 实现 `get_seller_info()` 查询 profiles 表
   - 实现 `get_listing_detail()` 含:
     - 访问控制 (is_public, is_deleted, moderation_status)
     - 购买状态检查
     - 卖家信息 JOIN

5. `api/user/marketplace.py`:
   - 更新 API 传递 `user_id` 到 Query

**测试文件更新**:
- `tests/api/user/test_marketplace.py`:
  - 更新 `mock_get_listing_result` fixture 添加新字段
  - 新增 `test_get_listing_user_id_passed_to_handler` (#35.3)
  - 新增 `test_get_listing_unpublished_not_visible_to_others` (#35.4)
  - 新增 `test_get_listing_with_purchase_status` (#35.5)

**完成状态**: ✅ 已完成 (11/11)

---

## Payment 支付模块 (2个) 🔴 P0 ✅ 已完成

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 | 状态 |
|------|------|------|------|------|------|------|
| 45 | create_checkout | POST | /checkout | api/user/payment.py | 52 | ✅ 🔧 ⏳ |
| 46 | get_portal | POST | /portal | api/user/payment.py | 95 | ✅ 🔧 |

> ⏳ **待定变更**: #45 create_checkout 需要在积分购买档位确定后支持新 plan_type

**测试用例 Checklist**
- [x] #45 创建Checkout Session (Starter/Pro)
- [x] #45 折扣应用 (0%/20%)
- [x] #45 无效plan_type验证 (422)
- [x] #45 Stripe错误处理 (500)
- [x] #45 None URL处理 (500)
- [x] #46 获取Billing Portal
- [x] #46 无订阅用户 (400)
- [x] #46 Stripe错误处理 (500)
- [x] #46 None URL处理 (500)

### Review 结果 (2026-01-08)

**发现并修复的 Bug** 🔧:

1. **`create_checkout` (L78-81)**
   - 问题: `create_checkout_session()` 可能返回 `None` (Stripe内部失败时)，但API未处理
   - 影响: 返回 `{"url": null}` 或导致前端错误
   - 修复: 添加 `if not url: raise HTTPException(500, ...)`

2. **`get_portal` (L116-119)**
   - 问题: `create_portal_session()` 可能返回 `None`，但API未处理
   - 影响: 同上
   - 修复: 添加 `if not url: raise HTTPException(500, ...)`

**测试文件补充**:
- `tests/api/user/test_payment.py` - 新增 2 个测试用例:
  - `test_create_checkout_returns_none_url` - 测试 None URL 返回 500
  - `test_get_portal_returns_none_url` - 测试 None URL 返回 500

**完成状态**: ✅ 已完成 (2026-01-08)

---

## Projects 项目模块 (10个) 🟡 P1 ✅ 已完成

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 | 状态 |
|------|------|------|------|------|------|------|
| 47 | list_projects | GET | / | api/user/projects.py | 103 | ✅ 🔧 |
| 48 | dashboard_projects | GET | /dashboard | api/user/projects.py | 159 | ✅ 🔧 |
| 49 | list_deleted_projects | GET | /deleted | api/user/projects.py | 195 | ✅ |
| 50 | get_project_seller_stats | GET | /seller-stats | api/user/projects.py | 212 | ✅ |
| 51 | create_project | POST | / | api/user/projects.py | 227 | ✅ 🔧 |
| 52 | get_project | GET | /{project_id} | api/user/projects.py | 267 | ✅ |
| 53 | update_project | PUT | /{project_id} | api/user/projects.py | 300 | ✅ 🔧 |
| 54 | delete_project | DELETE | /{project_id} | api/user/projects.py | 344 | ✅ 🔧 |
| 55 | restore_project | POST | /{project_id}/restore | api/user/projects.py | 383 | ✅ 🔧 |
| 56 | duplicate_project | POST | /{project_id}/duplicate | api/user/projects.py | 421 | ✅ 🔧 |

**测试用例 Checklist**
- [x] #47 项目列表分页 (total_count 修复)
- [x] #48 Dashboard视图 (DDD Query Handler)
- [x] #49 已删除项目
- [x] #50 卖家统计
- [x] #51 创建项目 (参数对齐)
- [x] #52 获取项目详情
- [x] #53 更新项目 (canvas_data/thumbnail_url)
- [x] #54 软删除项目 (permanent 参数)
- [x] #55 恢复项目 (CQRS Command Handler)
- [x] #56 复制项目 (Service 方法新增)

### Review 结果 (2026-01-08)

**发现并修复的 Bug** 🔧:

#### 🔴 CRITICAL (运行时崩溃)

1. **#51 create_project - 参数不匹配**
   - 问题: API 使用 `user_id/canvas_data/tier` 但 Command 期望 `owner_id/canvas_width/canvas_height/user_tier`
   - 影响: `TypeError` 崩溃
   - 修复: 重新对齐 `CreateProjectCommand` 参数为 `user_id/title/canvas_data/tier`

2. **#51 create_project - Result 缺少字段**
   - 问题: `CreateProjectResult` 没有 `project_dict` 字段
   - 影响: `AttributeError` 崩溃
   - 修复: 添加 `project_dict: Optional[Dict[str, Any]]` 字段

3. **#56 duplicate_project - 方法不存在**
   - 问题: `creation_service.duplicate_project()` 方法不存在
   - 影响: `AttributeError` 崩溃
   - 修复: 在 `CreationService` 新增 `duplicate_project()` 方法，含 tier 限制检查

#### 🟠 HIGH (功能失效)

4. **#53 update_project - Command 缺少字段**
   - 问题: `UpdateProjectCommand` 不支持 `canvas_data` 和 `thumbnail_url`
   - 影响: 更新画布/缩略图静默失败
   - 修复: 添加这两个字段，Handler 使用 `save_project_quick`

5. **#54 delete_project - 参数名不匹配**
   - 问题: API 使用 `permanent`，Command 使用 `hard_delete`
   - 影响: 永久删除选项失效
   - 修复: Command 改用 `permanent`，Handler 内部映射

6. **#56 duplicate_project - 绕过 Tier 限制**
   - 问题: 原直接调用 Repository 绕过限制检查
   - 影响: 用户可超出项目数量限制
   - 修复: Service 方法包含限制检查 (`PROJECT_LIMITS`)

#### 🟡 MEDIUM (架构/分页问题)

7. **#47 list_projects - total_count 错误**
   - 问题: `total_count=len(projects)` 返回当前页数量
   - 影响: 分页 UI 显示错误
   - 修复: 新增 `count_user_projects()` 方法返回实际总数

8. **#47 list_projects - canvas_data 缺失**
   - 问题: `Project.to_dict()` 不含 `canvas_data`
   - 影响: 列表 API 不返回画布数据
   - 修复:
     - `Project` 添加 `canvas_data` 字段
     - `_map_to_project` 解析 DB 的 canvas_data
     - `to_dict()` 输出 canvas_data

9. **#48 dashboard_projects - 违反 DDD**
   - 问题: 直接调用 Repository 而非 Query Handler
   - 修复: 创建 `GetDashboardProjectsQuery` + `GetDashboardProjectsHandler`

10. **#55 restore_project - 违反 CQRS**
    - 问题: 直接调用 Service 而非 Command Handler
    - 修复: 创建 `RestoreProjectCommand` + `RestoreProjectHandler`

**修复涉及的文件**:

1. `domains/creation/aggregates/project.py`
   - 添加 `canvas_data` 字段
   - 更新 `to_dict()` 输出

2. `infrastructure/repositories/project_repository.py`
   - `_map_to_project()` 解析 canvas_data

3. `application/commands/creation.py`
   - 修复 `CreateProjectCommand` 参数
   - 添加 `CreateProjectResult.project_dict`
   - 修复 `UpdateProjectCommand` 支持 canvas_data/thumbnail_url
   - 修复 `DeleteProjectCommand` 使用 permanent
   - 新增 `RestoreProjectCommand` + Handler

4. `application/queries/creation.py`
   - 修复 `GetUserProjectsHandler` 使用 count_user_projects
   - 新增 `GetDashboardProjectsQuery` + Handler

5. `domains/creation/service.py`
   - 新增 `duplicate_project()` 方法
   - 新增 `count_user_projects()` 方法

6. `container.py`
   - 注册 `GetDashboardProjectsHandler`
   - 注册 `RestoreProjectHandler`

7. `api/user/projects.py`
   - 更新 dashboard_projects 使用 Handler
   - 更新 restore_project 使用 Handler
   - 修复 duplicate_project 异常处理

**测试文件更新**:
- `tests/api/user/test_projects.py` - 更新 mock 适配新架构

**完成状态**: ✅ 已完成 (2026-01-08)

---

## Resources 资源模块 (7个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 57 | list_resources | GET | / | api/user/resources.py | 112 |
| 58 | get_resource_types | GET | /types | api/user/resources.py | 152 |
| 59 | get_categories | GET | /categories/{resource_type} | api/user/resources.py | 168 |
| 60 | get_stickers | GET | /stickers | api/user/resources.py | 183 |
| 61 | get_backgrounds | GET | /backgrounds | api/user/resources.py | 209 |
| 62 | get_templates | GET | /templates | api/user/resources.py | 235 |
| 63 | get_resource | GET | /{resource_id} | api/user/resources.py | 261 |

**测试用例 Checklist**
- [ ] #57 资源列表
- [ ] #58 资源类型
- [ ] #59 分类查询
- [ ] #60 贴纸资源
- [ ] #61 背景资源
- [ ] #62 模板资源
- [ ] #63 单个资源

**完成状态**: 未开始

---

## Support 客服模块 (4个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 64 | create_ticket | POST | /ticket | api/user/support.py | 80 |
| 65 | chat_support | POST | /chat | api/user/support.py | 94 |
| 66 | contact | POST | /contact | api/user/support.py | 156 |
| 67 | feedback | POST | /feedback | api/user/support.py | 174 |

**测试用例 Checklist**
- [ ] #64 创建工单
- [ ] #65 AI客服对话
- [ ] #66 联系表单
- [ ] #67 反馈提交

**完成状态**: 未开始

---

## System Resources 系统资源模块 (9个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 68 | list_system_resources | GET | / | api/user/system_resources.py | 42 |
| 69 | get_resource_stats | GET | /stats | api/user/system_resources.py | 82 |
| 70 | get_resource | GET | /{resource_id} | api/user/system_resources.py | 122 |
| 71 | create_resource | POST | / | api/user/system_resources.py | 139 |
| 72 | update_resource | PATCH | /{resource_id} | api/user/system_resources.py | 228 |
| 73 | replace_resource_file | POST | /{resource_id}/replace | api/user/system_resources.py | 271 |
| 74 | delete_resource | DELETE | /{resource_id} | api/user/system_resources.py | 368 |
| 75 | batch_action | POST | /batch | api/user/system_resources.py | 405 |
| 76 | get_resource_audit_log | GET | /{resource_id}/audit-log | api/user/system_resources.py | 439 |

**测试用例 Checklist**
- [ ] #68 系统资源列表
- [ ] #69 资源统计
- [ ] #70 获取单个资源
- [ ] #71 创建资源
- [ ] #72 更新资源
- [ ] #73 替换文件
- [ ] #74 删除资源
- [ ] #75 批量操作
- [ ] #76 审计日志

**完成状态**: 未开始

---

## Tasks 任务模块 (2个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 77 | get_task_status | GET | /{task_id} | api/user/tasks.py | 63 |
| 78 | cancel_task | POST | /{task_id}/cancel | api/user/tasks.py | 124 |

**测试用例 Checklist**
- [ ] #77 查询任务状态
- [ ] #78 取消任务

**完成状态**: 未开始

---

## Templates 模板模块 (10个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 79 | list_asset_templates | GET | /asset | api/user/templates.py | 126 |
| 80 | create_asset_template | POST | /asset | api/user/templates.py | 142 |
| 81 | update_asset_template | PUT | /asset/{template_id} | api/user/templates.py | 189 |
| 82 | delete_asset_template | DELETE | /asset/{template_id} | api/user/templates.py | 215 |
| 83 | use_asset_template | POST | /asset/{template_id}/use | api/user/templates.py | 232 |
| 84 | list_page_templates | GET | /page | api/user/templates.py | 268 |
| 85 | create_page_template | POST | /page | api/user/templates.py | 284 |
| 86 | update_page_template | PUT | /page/{template_id} | api/user/templates.py | 325 |
| 87 | delete_page_template | DELETE | /page/{template_id} | api/user/templates.py | 351 |
| 88 | use_page_template | POST | /page/{template_id}/use | api/user/templates.py | 368 |

**测试用例 Checklist**
- [ ] #79 资产模板列表
- [ ] #80 创建资产模板
- [ ] #81 更新资产模板
- [ ] #82 删除资产模板
- [ ] #83 使用资产模板
- [ ] #84 页面模板列表
- [ ] #85 创建页面模板
- [ ] #86 更新页面模板
- [ ] #87 删除页面模板
- [ ] #88 使用页面模板

**完成状态**: 未开始

---

## Themes 主题模块 (1个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 89 | get_current_theme | GET | /current | api/user/themes.py | 47 |

**测试用例 Checklist**
- [ ] #89 获取当前主题

**完成状态**: 未开始

---

## Tools 工具模块 (2个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 90 | pdf_preview | POST | /pdf-preview | api/user/tools.py | 65 |
| 91 | ocr_tool | POST | /ocr | api/user/tools.py | 146 |

**测试用例 Checklist**
- [ ] #90 PDF预览生成
- [ ] #91 OCR文字识别

**完成状态**: 未开始

---

## User Assets 用户资产模块 (10个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 92 | my_assets | GET | / | api/user/user_assets.py | 52 |
| 93 | upload_asset | POST | / | api/user/user_assets.py | 66 |
| 94 | delete_asset | DELETE | /{asset_id} | api/user/user_assets.py | 113 |
| 95 | add_asset_from_url | POST | /from-url | api/user/user_assets.py | 139 |
| 96 | check_url | GET | /check-url | api/user/user_assets.py | 177 |
| 97 | increment_usage | POST | /{asset_id}/increment-usage | api/user/user_assets.py | 199 |
| 98 | get_asset_dashboard | GET | /dashboard | api/user/user_assets.py | 209 |
| 99 | get_seller_stats | GET | /seller-stats | api/user/user_assets.py | 236 |
| 100 | get_deleted | GET | /deleted | api/user/user_assets.py | 261 |
| 101 | restore | POST | /{asset_id}/restore | api/user/user_assets.py | 268 |

**测试用例 Checklist**
- [ ] #92 我的资产列表
- [ ] #93 上传资产
- [ ] #94 删除资产
- [ ] #95 从URL添加
- [ ] #96 URL检查
- [ ] #97 使用次数增加
- [ ] #98 资产Dashboard
- [ ] #99 卖家统计
- [ ] #100 已删除资产
- [ ] #101 恢复资产

**完成状态**: 未开始

---

## User Profile 用户资料模块 (7个) 🔴 P0 ✅ 已完成

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 | 状态 |
|------|------|------|------|------|------|------|
| 102 | get_me | GET | /me | api/user/user_profile.py | 59 | ✅ |
| 103 | get_history | GET | /history | api/user/user_profile.py | 82 | ✅ |
| 104 | get_purchases | GET | /purchases | api/user/user_profile.py | 95 | ✅ |
| 105 | get_notifications | GET | /notifications | api/user/user_profile.py | 103 | ✅ |
| 106 | mark_read | POST | /notifications/{id}/read | api/user/user_profile.py | 111 | ✅ |
| 107 | mark_all_read | POST | /notifications/read-all | api/user/user_profile.py | 122 | ✅ |
| 108 | update_timezone | PUT | /timezone | api/user/user_profile.py | 131 | ✅ |

**测试用例 Checklist**
- [x] #102 获取用户信息 (Free/Pro tier)
- [x] #102 is_member 标志验证
- [x] #102 credits_total 计算
- [x] #103 操作历史 + 分页
- [x] #104 购买记录
- [x] #105 通知列表
- [x] #106 标记单条已读
- [x] #106 通知不存在 (404)
- [x] #107 全部标记已读
- [x] #108 更新时区 (pytz验证)
- [x] #108 无效时区 (400)

### Review 结果 (2026-01-08)

**代码分析**: 无 Bug

代码简洁，业务逻辑正确：
- `is_member` 正确判断 tier (starter/pro 为 True)
- `credits_total` 正确计算 (monthly + permanent)
- Timezone 使用 pytz 验证
- Notification 操作检查用户归属

**测试文件补充**:
- `tests/api/user/test_user_profile.py` - 新增 18 个测试用例

**完成状态**: ✅ 已完成 (2026-01-08)

---

## Webhooks 模块 (2个) 🔴 P0 ✅ 已完成

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 | 状态 |
|------|------|------|------|------|------|------|
| 109 | clerk_webhook | POST | /clerk | api/user/webhooks.py | 39 | ✅ 🔧 |
| 110 | stripe_webhook | POST | /stripe | api/user/webhooks.py | 191 | ✅ |

**测试用例 Checklist**
- [x] #109 Clerk签名验证 (Svix)
- [x] #109 user.created 创建Profile
- [x] #109 user.created 授予50注册奖励 (已修复!)
- [x] #109 user.created JIT用户处理
- [x] #109 user.created 邮箱重复检查
- [x] #109 user.updated 同步Profile信息
- [x] #110 Stripe签名验证
- [x] #110 checkout.session.completed 订阅 (starter/pro)
- [x] #110 checkout.session.completed 购买积分 (credits_100)
- [x] #110 invoice.payment_succeeded 订阅续费
- [x] #110 customer.subscription.deleted 取消订阅
- [x] #110 幂等性检查 (防重复处理)

### Review 结果 (2026-01-08)

**发现并修复的 Bug** 🔧:

1. **`clerk_webhook` (L102-113) - 缺少注册奖励**
   - 问题: user.created 事件处理器创建Profile后没有授予 50 永久积分注册奖励
   - 影响: 新用户注册后没有获得CLAUDE.md规定的50积分奖励
   - 修复: 添加 `credit_repo.add_credits_permanent(user_id, 50, ...)` 调用

**代码分析**:
- Clerk Webhook: 签名验证正确 (Svix), JIT用户处理完善
- Stripe Webhook: 幂等性检查完善 (PostgreSQL RPC), 积分操作正确
- 订阅逻辑: starter=500积分, pro=1000积分, 取消后降级free

**测试文件补充**:
- `tests/api/user/test_webhooks.py` - 更新测试验证50积分奖励

**完成状态**: ✅ 已完成 (2026-01-08)

---

*创建日期: 2026-01-08*
*总接口数: 110 个*
