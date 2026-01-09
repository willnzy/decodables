# 后台测试覆盖率提升计划

> **版本**: 2.0 (DDD 架构)
> **更新日期**: 2026-01-08
> **架构版本**: v3.1.0

**目标**: 所有后台代码覆盖率达到 80%+ (关键模块 95%+)
**当前状态**: 135 个测试文件, 约 36,975 行测试代码

---

## 📊 模块统计 (v3.1 DDD 架构)

| 目录 | 文件数 | 代码行数 | 测试优先级 | 说明 |
|------|--------|----------|------------|------|
| domains/billing/ | ~10 | ~2,000 | P0 - 核心 | 积分、支付 |
| domains/identity/ | ~8 | ~1,500 | P0 - 核心 | 用户身份 |
| domains/creation/ | ~12 | ~2,500 | P1 - 高 | 项目创作 |
| domains/marketplace/ | ~10 | ~2,000 | P1 - 高 | 市场交易 |
| domains/platform/ | ~8 | ~1,000 | P2 - 中 | Feature Flags |
| domains/content/ | ~6 | ~700 | P2 - 中 | 系统资源 |
| application/commands/ | ~15 | ~2,000 | P1 - 高 | 写操作 |
| application/queries/ | ~15 | ~2,000 | P1 - 高 | 读操作 |
| application/services/ | ~20 | ~2,500 | P2 - 中 | 定时任务 |
| infrastructure/repositories/ | ~15 | ~4,000 | P1 - 高 | 数据访问 |
| api/user/ | ~27 | ~6,000 | P0 - 核心 | 用户 API |
| api/admin/ | ~16 | ~4,000 | P2 - 中 | 管理 API |
| shared/ai/ | ~15 | ~4,000 | P1 - 高 | AI 服务 |
| shared/payment/ | ~5 | ~1,500 | P0 - 核心 | Stripe |
| core/ | ~29 | ~3,300 | P2 - 中 | 框架组件 |

---

## 🚀 分阶段执行计划

### 阶段 0: 修复现有测试 (1-2 天)

**目标**: 让现有 560 个失败测试通过

#### 任务清单

- [ ] **0.1** 修复参数签名不匹配 (35 个测试)
  - `test_db_users.py`: 修复 `create_user_profile`, `credit_deduct` 等
  - `test_db_marketplace.py`: 修复 `execute_purchase` 等
  - `test_db_projects.py`: 修复 `get_project_detail`, `count_user_projects` 等
  - `test_db_admin.py`: 修复 `admin_get_user_growth_stats` 等

- [ ] **0.2** 修复 Mock 路径问题
  - 确保 Mock 路径与实际导入路径一致
  - 修复 MagicMock 返回值设置

- [ ] **0.3** 修复测试收集错误 (152 个)
  - `test_themes.py`: 添加 python-multipart 依赖检查
  - 其他导入问题

**验收标准**: `pytest tests/ -q` 无失败和错误

---

### 阶段 1: 核心业务逻辑测试 (2 天)

**目标**: 确保 `services/db/` 所有模块 95%+ 覆盖率

#### 任务清单

| 模块 | 测试文件 | 状态 | 预计测试数 |
|------|----------|------|------------|
| core.py | test_db_other.py | ⚠️ 部分 | +10 |
| users.py | test_db_users.py | ⚠️ 部分 | +15 |
| projects.py | test_db_projects.py | ⚠️ 部分 | +15 |
| marketplace.py | test_db_marketplace.py | ⚠️ 部分 | +10 |
| assets.py | test_db_assets.py | ⚠️ 部分 | +10 |
| admin_stats.py | test_db_admin.py | ⚠️ 部分 | +15 |
| admin_users.py | test_db_admin.py | ⚠️ 部分 | +10 |
| admin_moderation.py | test_db_admin.py | ⚠️ 部分 | +10 |
| notifications.py | test_db_other.py | ⚠️ 部分 | +10 |
| payments.py | test_db_other.py | ⚠️ 部分 | +10 |
| config.py | test_db_other.py | ⚠️ 部分 | +10 |
| support.py | test_db_other.py | ⚠️ 部分 | +5 |

**验收标准**: `pytest --cov=services/db --cov-fail-under=95`

---

### 阶段 2: AI 服务测试 (3 天)

**目标**: `services/ai/` 所有模块 95%+ 覆盖率

#### 2.1 基础设施 (1 天)

| 模块 | 测试文件 | 状态 |
|------|----------|------|
| base.py | test_ai_base.py | ✅ 存在 |
| model_config.py | test_ai_model_config.py | ✅ 存在 |
| retry.py | tests/services/test_ai_retry.py | 🆕 新建 |
| ai_cache.py | test_ai_cache.py | ✅ 存在 |
| usage_tracker.py | test_ai_usage_tracker.py | ✅ 存在 |

#### 2.2 适配器层 (1 天)

| 模块 | 测试文件 | 状态 |
|------|----------|------|
| adapters/openai_adapter.py | test_openai_adapter.py | ✅ 存在 |
| adapters/qwen_adapter.py | test_qwen_adapter.py | ✅ 存在 |
| adapters/fal_adapter.py | test_fal_adapter.py | ✅ 存在 |
| adapters/wanx_adapter.py | tests/services/test_wanx_adapter.py | 🆕 新建 |
| adapters/gemini_adapter.py | tests/services/test_gemini_adapter.py | 🆕 新建 |

#### 2.3 服务层 (1 天)

| 模块 | 测试文件 | 状态 |
|------|----------|------|
| unified_text_service.py | test_unified_text_service.py | ✅ 存在 |
| unified_image_service.py | test_unified_image_service.py | ✅ 存在 |
| prompt_enhancer.py | test_prompt_enhancer.py | ✅ 存在 |
| story_generator.py | test_story_generator.py | ✅ 存在 |
| zine_generator.py | test_zine_generator.py | ✅ 存在 |
| image_generator.py | test_image_generator.py | ✅ 存在 |
| canary.py | test_ai_canary.py | ✅ 存在 |
| prompt_templates.py | tests/services/test_prompt_templates.py | 🆕 新建 |

**验收标准**: `pytest --cov=services/ai --cov-fail-under=95`

---

### 阶段 3: 根目录服务测试 (2 天)

**目标**: `services/*.py` 所有模块 95%+ 覆盖率

#### 任务清单

| 模块 | 测试文件 | 状态 |
|------|----------|------|
| access_control.py | test_access_control.py | ✅ 完成 |
| credit_service.py | test_credit_service.py | ✅ 完成 |
| marketplace_service.py | test_marketplace_service.py | ⚠️ 部分 |
| payment_service.py | test_payment_service.py | ⚠️ 部分 |
| resource_service.py | test_resource_service.py | ✅ 存在 |
| config_service.py | test_config_service.py | ✅ 存在 |
| analytics_service.py | test_analytics_service.py | ✅ 存在 |
| rate_limiter.py | test_rate_limiter.py | ✅ 存在 |
| experiment_service.py | test_experiment_service.py | ✅ 存在 |
| experiment_ai_service.py | test_experiment_ai_service.py | ✅ 存在 |
| service_factory.py | test_service_factory.py | ✅ 存在 |
| setup_assistant.py | test_setup_assistant.py | ✅ 存在 |
| generation_helpers.py | tests/services/test_generation_helpers.py | 🆕 新建 |
| system_resource_helpers.py | tests/services/test_system_resource_helpers.py | 🆕 新建 |
| ai_chat_service.py | tests/services/test_ai_chat_service.py | 🆕 新建 |
| ai_report_service.py | test_ai_report_service.py | ✅ 存在 |
| capi_service.py | test_capi_service.py | ✅ 存在 |
| db_service.py | test_db_service.py | ✅ 完成 |

**验收标准**: `pytest --cov=services --cov-fail-under=95`

---

### 阶段 4: API 层测试

**目标**: `api/` 所有端点 80%+ 覆盖率

#### 4.1 用户 API (api/user/)

| 模块 | 测试目录 | 状态 |
|------|----------|------|
| profile.py | tests/api/user/ | ✅ 存在 |
| credits.py | tests/api/user/ | ✅ 存在 |
| projects.py | tests/api/user/ | ✅ 存在 |
| assets.py | tests/api/user/ | ✅ 存在 |
| marketplace.py | tests/api/user/ | ✅ 存在 |
| generation.py | tests/api/user/ | ✅ 存在 |

#### 4.2 管理 API (api/admin/)

| 模块 | 测试目录 | 状态 |
|------|----------|------|
| admin/*.py | tests/api/admin/ | ✅ 存在 |

**验收标准**: `pytest --cov=api --cov-fail-under=80`

---

### 阶段 5: 辅助服务测试 (2 天)

**目标**: 缓存、实验、任务队列等辅助服务 95%+ 覆盖率

#### 5.1 缓存服务 (0.5 天)

| 模块 | 测试文件 | 状态 |
|------|----------|------|
| cache/cache_service.py | test_cache_service.py | ✅ 存在 |
| cache/redis_client.py | test_redis_client.py | ✅ 存在 |
| cache/cache_keys.py | test_cache_keys.py | ✅ 存在 |
| cache/memory_cache.py | tests/services/test_memory_cache.py | 🆕 新建 |

#### 5.2 实验服务 (0.5 天)

| 模块 | 测试文件 | 状态 |
|------|----------|------|
| experiments/*.py | test_experiment_service.py | ⚠️ 部分 |

#### 5.3 任务队列 (0.5 天)

| 模块 | 测试文件 | 状态 |
|------|----------|------|
| task_queue/queue_service.py | tests/services/test_queue_service.py | 🆕 新建 |
| task_queue/progress_tracker.py | tests/services/test_progress_tracker.py | 🆕 新建 |
| task_queue/task_handlers.py | tests/services/test_task_handlers.py | 🆕 新建 |

#### 5.4 WebSocket (0.5 天)

| 模块 | 测试文件 | 状态 |
|------|----------|------|
| websocket/connection_manager.py | tests/services/test_websocket.py | 🆕 新建 |

**验收标准**: 所有辅助服务模块 95%+ 覆盖率

---

### 阶段 6: 应用服务测试

**目标**: `application/services/` 所有模块 80%+ 覆盖率

| 模块目录 | 测试位置 | 状态 |
|----------|----------|------|
| application/services/aggregators/ | tests/application/ | ⚠️ 待补充 |
| application/services/campaigns/ | tests/application/ | ⚠️ 待补充 |
| application/services/experiments/ | tests/application/ | ⚠️ 待补充 |
| application/services/metrics/ | tests/application/ | ⚠️ 待补充 |

---

### 阶段 7: 最终验证与 CI 配置 (0.5 天)

#### 任务清单

- [ ] **7.1** 运行完整覆盖率报告
  ```bash
  pytest --cov=domains --cov=application --cov=api --cov=infrastructure \
         --cov-report=html --cov-fail-under=80
  ```

- [ ] **7.2** 更新 pytest.ini 启用覆盖率门槛
  ```ini
  addopts =
      --cov=domains
      --cov=application
      --cov=api
      --cov-fail-under=80
  ```

- [ ] **7.3** 配置 GitHub Actions CI
  ```yaml
  - name: Run tests with coverage
    run: pytest --cov --cov-fail-under=80
  ```

- [ ] **7.4** 更新 README.md 添加覆盖率徽章

---

## 📋 每日检查清单

每完成一个阶段后，执行以下检查：

```bash
# 1. 运行所有测试
pytest tests/ -q

# 2. 检查目标模块覆盖率
pytest --cov=<target_module> --cov-report=term-missing

# 3. 生成 HTML 报告
pytest --cov=<target_module> --cov-report=html

# 4. 确认无新增 linting 错误
python -m py_compile <modified_files>
```

---

## 🎯 里程碑

| 阶段 | 验收标准 |
|------|----------|
| 阶段 0 | 0 失败测试 |
| 阶段 1 | domains/billing/ 95%+, domains/identity/ 90%+ |
| 阶段 2 | shared/ai/ 80%+ |
| 阶段 3 | domains/creation/, domains/marketplace/ 80%+ |
| 阶段 4 | api/ 80%+ |
| 阶段 5 | infrastructure/ 80%+ |
| 阶段 6 | application/services/ 80%+ |
| 阶段 7 | CI 配置完成，全局 80%+ |

---

## 📝 注意事项

1. **Mock 策略**: 所有外部依赖（Supabase, Redis, Stripe, AI APIs）必须 Mock
2. **测试隔离**: 每个测试独立，不依赖执行顺序
3. **边界测试**: 包含正常、异常、边界三类用例
4. **业务规则**: 测试必须验证 `后台业务逻辑说明.md` 中的规则
5. **向后兼容**: 测试新代码不破坏现有功能

---

## 🔗 集成测试指南

### Staging 环境 Webhook 测试

#### 前提条件

- ✅ Staging 环境已部署最新代码
- ✅ Staging 环境可公网访问
- ✅ 有 Clerk 和 Stripe 的测试账号访问权限
- ✅ 环境变量已正确配置:
  - `CLERK_WEBHOOK_SECRET`
  - `STRIPE_WEBHOOK_SECRET`
  - `STRIPE_SECRET_KEY` (test mode)

#### Clerk Webhook 测试清单

**配置步骤**:
1. 访问 [Clerk Dashboard](https://dashboard.clerk.com) → Webhooks
2. 添加端点: `https://your-staging-domain.com/api/v2/webhooks/clerk`
3. 订阅事件: `user.created`, `user.updated`, `session.created`, `session.ended`, `session.removed`, `session.revoked`
4. 复制 Signing Secret 并更新环境变量
5. 重启 staging 服务

**测试项**:
- [ ] `user.created` 事件创建用户记录
- [ ] `user.updated` 事件同步用户信息
- [ ] `session.created` 事件记录登录日志
- [ ] `session.ended` 事件记录登出日志
- [ ] Webhook 签名验证通过 (无 400 Invalid signature 错误)
- [ ] Clerk Dashboard 显示 webhook 状态为 "Healthy"

**验证方法**:
```sql
-- 验证用户创建
SELECT * FROM profiles WHERE id = 'user_xxx';

-- 验证用户更新
SELECT avatar_url, username FROM profiles WHERE id = 'user_xxx';

-- 验证登录日志
SELECT * FROM user_activities
WHERE user_id = 'user_xxx' AND activity_type = 'user_login'
ORDER BY created_at DESC LIMIT 1;
```

#### Stripe Webhook 测试清单

**配置步骤**:
1. 访问 [Stripe Dashboard (Test Mode)](https://dashboard.stripe.com/test/webhooks)
2. 添加端点: `https://your-staging-domain.com/api/v2/webhooks/stripe`
3. 选择事件: `checkout.session.completed`, `invoice.payment_succeeded`, `customer.subscription.deleted`, `customer.subscription.updated`
4. 复制 Signing Secret 并更新环境变量
5. 重启 staging 服务

**测试项**:
- [ ] `checkout.session.completed` (积分购买) - 增加永久积分
- [ ] `checkout.session.completed` (订阅开通) - 更新 tier 和月度积分
- [ ] `invoice.payment_succeeded` (续费) - 刷新月度积分
- [ ] `customer.subscription.deleted` (取消) - 降级到 free tier
- [ ] Webhook 幂等性 - 重复事件被忽略
- [ ] Webhook 签名验证通过 (无 400 错误)
- [ ] Stripe Dashboard 显示 webhook 状态为成功 (绿色勾号)

**验证方法**:
```sql
-- 验证积分购买
SELECT credits_permanent FROM profiles WHERE id = 'user_xxx';
SELECT * FROM credits_history
WHERE user_id = 'user_xxx' AND change_type = 'topup_purchase'
ORDER BY created_at DESC LIMIT 1;

-- 验证订阅开通
SELECT tier, credits_monthly, subscription_status FROM profiles
WHERE id = 'user_xxx';

-- 验证订阅续费
SELECT credits_monthly FROM profiles WHERE id = 'user_xxx';
SELECT * FROM credits_history
WHERE user_id = 'user_xxx' AND change_type = 'monthly_refresh'
ORDER BY created_at DESC LIMIT 1;

-- 验证订阅取消
SELECT tier, subscription_status FROM profiles WHERE id = 'user_xxx';

-- 验证幂等性
SELECT * FROM webhook_events WHERE event_id = 'evt_xxx';
```

**使用 Stripe 测试卡号**:
```
卡号: 4242 4242 4242 4242
有效期: 任意未来日期 (如 12/34)
CVC: 任意 3 位数字 (如 123)
```

#### 性能监控指标

在 staging 测试期间，监控以下指标:

| 指标 | 目标值 | 检查位置 |
|------|--------|----------|
| Webhook 响应时间 | < 2s | Clerk/Stripe Dashboard |
| Webhook 成功率 | > 99% | Clerk/Stripe Dashboard |
| 数据库写入延迟 | < 500ms | Staging 日志 |

#### 常见问题排查

**问题 1: Webhook 返回 400 Invalid signature**
- 检查环境变量 `CLERK_WEBHOOK_SECRET` 或 `STRIPE_WEBHOOK_SECRET` 是否正确
- 重新复制 Signing Secret 并更新
- 重启服务

**问题 2: Webhook 返回 500 Internal Server Error**
- 查看 staging 日志定位错误
- 检查数据库连接
- 检查依赖服务 (Supabase, Stripe API)

**问题 3: Webhook 成功但数据库无变化**
- 确认 webhook payload 中的 `user_id` 或 `customer_id` 存在
- 检查数据库中是否有对应的用户记录
- 查看日志中的详细错误信息

#### 切换到生产环境

**前提条件**:
- [x] Staging 环境所有测试通过
- [x] Webhook 幂等性机制验证通过
- [x] 无 500 错误或签名验证失败
- [x] 数据库数据正确更新
- [x] 性能指标达标

**切换步骤**:
1. 在 Clerk/Stripe 生产环境添加 v2 端点
2. 更新生产环境变量 (使用生产环境的 Signing Secret)
3. **保留旧端点**: 暂时不要删除 v1 端点，观察 7 天
4. 监控 v2 webhook 成功率和流量
5. 确认 v2 处理所有事件后，7 天后废弃 v1 端点

**回滚计划**:
- 在 Clerk/Stripe Dashboard 中禁用 v2 端点
- 启用 v1 端点
- 如必要，回滚代码: `git revert <commit_hash>`

---

*文档版本: v2.0*
*最后更新: 2026-01-08*
*架构版本: v3.1.0 (DDD)*
