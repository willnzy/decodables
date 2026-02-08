# Make Decodables 后端测试完整指南

> **版本**: 3.0 (DDD 架构)
> **更新日期**: 2026-01-10
> **架构版本**: v3.1.0

---

## 目录

**Part 1: 测试覆盖率提升计划**
1. [模块统计](#part-1-测试覆盖率提升计划)
2. [分阶段执行计划](#12-分阶段执行计划)
3. [集成测试指南](#13-集成测试指南)

**Part 2: CI 测试局限性与解决方案**
1. [潜在问题清单](#part-2-ci-测试局限性与解决方案)
2. [分层测试策略](#22-分层测试策略)
3. [GitHub Actions 配置](#23-github-actions-配置)

---

# Part 1: 测试覆盖率提升计划

**目标**: 所有后台代码覆盖率达到 80%+ (关键模块 95%+)
**当前状态**: 135 个测试文件, 约 36,975 行测试代码

## 1.1 模块统计 (v3.1 DDD 架构)

| 目录 | 文件数 | 代码行数 | 测试优先级 | 说明 |
|------|--------|----------|------------|------|
| domains/billing/ | ~10 | ~2,000 | P0 - 核心 | 积分、支付 |
| domains/identity/ | ~8 | ~1,500 | P0 - 核心 | 用户身份 |
| domains/creation/ | ~12 | ~2,500 | P1 - 高 | 项目创作 |
| domains/marketplace/ | ~10 | ~2,000 | P1 - 高 | 市场交易 |
| domains/platform/ | ~8 | ~1,000 | P2 - 中 | Feature Flags |
| domains/content/ | ~6 | ~700 | P2 - 中 | 系统资源 |
| domains/themes/ | ~4 | ~600 | P2 - 中 | 主题管理 (67 tests ✅) |
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

## 1.2 分阶段执行计划

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
  - ~~`test_themes.py`: 添加 python-multipart 依赖检查~~ ✅ 已完成 (2026-01-12)
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

## 1.3 集成测试指南

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

## 1.4 每日检查清单

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

## 1.5 里程碑

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

## 1.6 注意事项

1. **Mock 策略**: 所有外部依赖（Supabase, Redis, Stripe, AI APIs）必须 Mock
2. **测试隔离**: 每个测试独立，不依赖执行顺序
3. **边界测试**: 包含正常、异常、边界三类用例
4. **业务规则**: 测试必须验证 `后台业务逻辑说明.md` 中的规则
5. **向后兼容**: 测试新代码不破坏现有功能

---

# Part 2: CI 测试局限性与解决方案

> 完全依赖 CI 测试可能遇到的问题及应对策略

## 2.1 潜在问题清单

### 2.1.1 反馈延迟 (⏱️ 影响：中)

**问题**:
- 每次 push 需要等待 3-5 分钟 CI 完成
- 小错误也需要完整 CI 周期
- 频繁修改时开发效率降低

**场景示例**:
```python
# 你写了一个拼写错误
def get_user_proflie(user_id):  # 注意：proflie 拼写错误
    pass

# 工作流
1. push → 等 3 分钟 → CI 失败（NameError）
2. 修复 → push → 再等 3 分钟 → CI 通过

# 总耗时：6 分钟（本可以 10 秒发现）
```

**解决方案** ✅:

**方案 A: Pre-commit Hook（推荐）**
```bash
# 安装 pre-commit
pip install pre-commit

# 创建 .pre-commit-config.yaml
cat > .pre-commit-config.yaml <<EOF
repos:
  - repo: local
    hooks:
      - id: pytest-quick
        name: Quick Test Check
        entry: pytest tests/ -x --tb=short -q
        language: system
        pass_filenames: false
        stages: [commit]
EOF

# 安装 hook
pre-commit install

# 现在每次 commit 前会自动运行快速测试
git commit -m "feat: add new feature"
# → 自动运行 pytest → 失败则阻止 commit
```

**方案 B: 本地快速验证脚本**
```bash
# 创建快速验证脚本
cat > scripts/quick_test.sh <<'EOF'
#!/bin/bash
# 快速验证当前修改

echo "🧪 Running quick tests..."

# 只运行核心测试（10-30秒）
pytest tests/test_credits_logic.py \
       tests/test_payment_service.py \
       tests/business_rules/ \
       -x --tb=short -q

if [ $? -eq 0 ]; then
  echo "✅ Quick tests passed! Safe to push."
else
  echo "❌ Quick tests failed! Fix before pushing."
  exit 1
fi
EOF

chmod +x scripts/quick_test.sh

# 使用
./scripts/quick_test.sh && git push
```

**方案 C: Git Alias（最简单）**
```bash
# 添加 git 别名
git config alias.test-push '!pytest tests/ -x -q && git push'

# 使用
git test-push  # 测试通过后自动 push
```

**推荐策略**:
```
小改动（如修复拼写错误）→ 本地快速测试（10秒）→ push
大改动（如新功能）→ 本地完整测试（2分钟）→ push → CI 最终验证
```

---

### 2.1.2 CI 配额限制 (💰 影响：中-高)

**GitHub Actions 配额**:

| 仓库类型 | 免费配额 | 每次 CI 耗时 | 可用次数/月 |
|----------|----------|--------------|-------------|
| **Public** | 无限制 ✅ | 3-5 分钟 | 无限制 |
| **Private** | 2000 分钟/月 | 3-5 分钟 | ~400-600 次 |

**你的配置**:
- 6 个并行 jobs（不累加，按最长 job 计算）
- 每次 push 约消耗 3-5 分钟

**Private Repo 场景**:
```
2000 分钟/月 ÷ 5 分钟/次 = 400 次 CI 运行/月
400 次 ÷ 30 天 = 13 次/天

如果团队 3 人，每人每天只能 push 4 次！
```

**解决方案** ✅:

**方案 A: 只在关键分支运行完整测试**
```yaml
# .github/workflows/test.yml
on:
  push:
    branches: [main, develop]  # 只在主分支运行
  pull_request:
    branches: [main, develop]  # PR 时运行

# Feature 分支不触发 CI，节省配额
```

**方案 B: 跳过 CI（特殊情况）**
```bash
# 文档修改不需要测试
git commit -m "docs: update README [skip ci]"
git push

# GitHub Actions 会跳过此次 CI
```

**方案 C: 优化 CI 执行时间**
```yaml
# 使用缓存加速（你已配置 ✅）
- uses: actions/setup-python@v5
  with:
    cache: 'pip'  # 缓存依赖，节省 30-60 秒

# 并行测试（可选，需要 pytest-xdist）
- name: Run tests in parallel
  run: pytest -n auto tests/
```

**方案 D: 升级到 Team Plan（付费）**
- $4/user/month
- 3000 分钟/月/user
- 适合团队协作

---

### 2.1.3 Mock 环境 vs 真实环境 (🔍 影响：高)

**问题**:
CI 使用 Mock 环境变量，可能无法发现真实环境问题。

**你的 CI 配置**:
```yaml
env:
  STRIPE_SECRET_KEY: 'sk_test_mock'
  SUPABASE_URL: 'https://mock.supabase.co'
  SUPABASE_KEY: 'mock_supabase_key'
```

**可能遗漏的问题**:

| 问题类型 | CI 测试 | 真实环境 |
|----------|---------|----------|
| Stripe API 调用 | ✅ Mock 通过 | ❌ 真实 API 失败（key 无效） |
| Supabase RPC 函数 | ✅ Mock 通过 | ❌ 函数不存在 |
| 数据库约束 | ✅ Mock 通过 | ❌ 唯一约束违反 |
| 第三方 Webhook | ✅ Mock 通过 | ❌ 签名验证失败 |

**示例**:
```python
# 代码
def create_checkout_session(user_id, price_id):
    session = stripe.checkout.Session.create(
        customer=user_id,
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription"
    )
    return session.url

# CI 测试（Mock）
@patch('stripe.checkout.Session.create')
def test_create_checkout(mock_create):
    mock_create.return_value = MagicMock(url="https://checkout.stripe.com/xxx")
    result = create_checkout_session("user_123", "price_123")
    assert result == "https://checkout.stripe.com/xxx"
# ✅ CI 通过

# 真实环境
# ❌ 实际运行时 Stripe API 报错：Invalid price_id
```

**解决方案** ✅:

**方案 A: Staging 环境测试（推荐）**
```yaml
# .github/workflows/staging-test.yml
name: Staging Environment Tests

on:
  push:
    branches: [staging]

jobs:
  staging-integration-test:
    name: Staging Integration Tests
    runs-on: ubuntu-latest

    steps:
      - name: Run tests against staging
        run: |
          pytest tests/integration/ \
                 --base-url=https://staging-api.foliaz.com \
                 -v
        env:
          # 使用真实的 staging 环境变量
          STRIPE_SECRET_KEY: ${{ secrets.STRIPE_TEST_KEY }}
          SUPABASE_URL: ${{ secrets.STAGING_SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.STAGING_SUPABASE_KEY }}
```

**方案 B: 定期运行真实环境测试**
```yaml
# .github/workflows/nightly-integration.yml
name: Nightly Integration Tests

on:
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨 2 点运行

jobs:
  real-environment-test:
    runs-on: ubuntu-latest
    steps:
      - name: Test against real Stripe/Supabase
        run: pytest tests/integration/ -v
        env:
          STRIPE_SECRET_KEY: ${{ secrets.STRIPE_TEST_KEY }}
          # 真实测试环境
```

**方案 C: 手动 Staging 测试（Phase 3）**
```bash
# Phase 3 任务：部署到 Staging 后手动测试
# 见 Part 1.3 集成测试指南

1. 部署到 staging
2. 手动测试 Webhook（24 项清单）
3. 测试真实支付流程
4. 测试真实 Clerk 用户创建
```

**分层测试策略**:
```
Layer 1 (CI - Mock): 快速反馈，覆盖 95% 逻辑
  ↓
Layer 2 (Staging - Real): 每天/每周运行，发现集成问题
  ↓
Layer 3 (Manual): 上线前手动测试关键流程
```

---

### 2.1.4 并发问题难以发现 (⚙️ 影响：高)

**问题**:
CI 测试通常是单线程，无法发现并发问题。

**示例场景**:
```python
# 代码：积分扣减（无锁）
def deduct_credits(user_id, amount):
    user = get_user(user_id)
    if user.credits >= amount:
        user.credits -= amount  # ⚠️ 非原子操作
        save_user(user)
        return True
    return False

# CI 测试（单线程）
def test_deduct_credits():
    user = create_user(credits=100)
    result = deduct_credits(user.id, 50)
    assert result == True
    assert get_user(user.id).credits == 50
# ✅ CI 通过

# 生产环境（并发）
# 用户同时点击两次"生成"按钮
# Thread 1: 读取 credits=100 → 扣 50 → 写入 50
# Thread 2: 读取 credits=100 → 扣 50 → 写入 50
# ❌ 最终 credits=50（应该是 0）
```

**解决方案** ✅:

**方案 A: 并发测试**
```python
# tests/edge_cases/test_concurrent_credits.py
import concurrent.futures

def test_concurrent_credit_deduction():
    """测试并发扣积分"""
    user = create_user(credits=100)

    # 10 个线程同时扣 10 积分
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(deduct_credits, user.id, 10)
            for _ in range(10)
        ]
        results = [f.result() for f in futures]

    # 验证最终积分正确
    final_credits = get_user(user.id).credits
    assert final_credits == 0, f"Expected 0, got {final_credits}"
    # ❌ 测试失败，发现并发问题！
```

**方案 B: 数据库原子操作（已实现 ✅）**
```python
# 你的代码已使用 Supabase RPC（原子操作）
result = supabase.rpc(
    'deduct_user_credits_atomic',
    {'p_user_id': user_id, 'p_amount': amount}
).execute()
# ✅ 数据库层面保证原子性
```

**方案 C: 压力测试（Phase 3）**
```bash
# 使用 Locust 进行压力测试
# 见 BACKEND-DEVELOPMENT-SOP.md Phase 3

locust -f tests/load/locustfile.py \
       --host=https://staging-api.foliaz.com \
       --users=100 \
       --spawn-rate=10
```

---

### 2.1.5 本地环境差异 (🖥️ 影响：低-中)

**问题**:
- CI: Ubuntu 22.04 + Python 3.11
- 本地: macOS/Windows + Python 3.12

**可能的问题**:
- 依赖版本不同
- 文件路径分隔符不同（`/` vs `\`）
- 时区差异

**解决方案** ✅:

**方案 A: Docker 本地测试（最彻底）**
```dockerfile
# Dockerfile.test
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["pytest", "tests/", "-v"]
```

```bash
# 本地运行 CI 环境
docker build -f Dockerfile.test -t decodables-test .
docker run decodables-test

# 与 CI 环境完全一致 ✅
```

**方案 B: pyenv 管理 Python 版本**
```bash
# 安装与 CI 相同的 Python 版本
pyenv install 3.11.9
pyenv local 3.11.9

# 验证
python --version  # Python 3.11.9
```

---

## 2.2 分层测试策略

### 2.2.1 测试金字塔

```
         ┌─────────────────────┐
         │   手动测试（1%）     │  Staging 关键流程
         │  Phase 3 上线前     │
         └─────────────────────┘
                   ▲
         ┌─────────────────────┐
         │  集成测试（9%）      │  Staging 环境
         │  每天/每周运行       │  真实 API 调用
         └─────────────────────┘
                   ▲
         ┌─────────────────────┐
         │   API 测试（30%）   │  CI (Mock)
         │  每次 push 运行     │  快速反馈
         └─────────────────────┘
                   ▲
         ┌─────────────────────┐
         │  单元测试（60%）     │  CI + 本地
         │  开发时频繁运行      │  最快反馈
         └─────────────────────┘
```

### 2.2.2 具体策略

| 阶段 | 测试类型 | 运行位置 | 频率 | 目的 |
|------|----------|----------|------|------|
| **开发中** | 单元测试 | 本地 | 每次修改 | 快速验证逻辑 |
| **Commit 前** | 快速测试 | 本地 (pre-commit hook) | 每次 commit | 避免低级错误 |
| **Push 后** | 全量测试 | CI (Mock) | 每次 push | 回归测试 |
| **每天/每周** | 集成测试 | Staging (真实 API) | 定期 | 发现集成问题 |
| **上线前** | 端到端测试 | Staging (手动) | 每次发版 | 验证关键流程 |

---

## 2.3 GitHub Actions 配置

### 2.3.1 当前 API 测试状态

**✅ 已有测试** (5 个 API 文件):
- tests/api/test_export_api.py
- tests/api/test_generation_api.py
- tests/api/test_projects_api.py
- tests/api/test_upload_api.py
- tests/api/test_user_api.py

**⚠️ 缺失测试** (33 个 API 文件):
- 19 个公开 API
- 14 个 Admin API

### 2.3.2 选项 A: 扩展现有 api-tests job（推荐）

**当前配置** (`.github/workflows/test.yml:101-134`):
```yaml
api-tests:
  name: API Tests
  runs-on: ubuntu-latest

  steps:
    - name: Run API tests
      run: |
        pytest tests/api/ \
               -v --tb=short || echo "::warning::Some API tests failed"
```

**优化后**:
```yaml
api-tests:
  name: API Tests (v2)
  runs-on: ubuntu-latest

  steps:
    - name: Run v2 API tests
      run: |
        # Public APIs
        pytest tests/api/ \
               -v --tb=short

        # Admin APIs (如果存在)
        pytest tests/api/admin/ \
               -v --tb=short || echo "::warning::Admin API tests not yet implemented"
      env:
        TESTING: 'true'
        # ... 环境变量
```

### 2.3.3 本地测试命令速查

#### 快速验证（单个文件）
```bash
# 测试单个 API 文件
pytest tests/api/test_billing_api.py -v

# 测试单个函数
pytest tests/api/test_billing_api.py::test_deduct_credits -v

# 显示详细错误
pytest tests/api/test_billing_api.py -vv --tb=long
```

#### 分层测试
```bash
# 只测试 API 层
pytest tests/api/ -v

# 只测试 Application 层
pytest tests/application/ -v

# 只测试 Domain 层
pytest tests/domains/ -v

# 测试 v2 架构全部
pytest tests/api/ tests/application/ tests/domains/ -v
```

#### 覆盖率检查
```bash
# 查看 API 层覆盖率
pytest tests/api/ --cov=api --cov-report=term-missing

# 查看全部覆盖率
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html
```

#### CI 失败后调试
```bash
# 1. 查看 GitHub Actions 日志，找到失败的测试
# 2. 本地运行该测试
pytest tests/api/test_xxx.py::test_failed_function -vv

# 3. 进入 pdb 调试
pytest tests/api/test_xxx.py::test_failed_function --pdb
```

### 2.3.4 测试覆盖率目标

| 层级 | 当前 | 目标 | 优先级 |
|------|------|------|--------|
| **API 层** | ~13% (5/38) | 80%+ (31+/38) | 🔴 高 |
| **Application 层** | ~50% (2/4估计) | 90%+ | 🟠 中 |
| **Domain 层** | ~60% (3/5估计) | 90%+ | 🟠 中 |
| **Services 层** | ~60% (已有) | 70%+ | 🟡 低 |

### 2.3.5 最佳实践

#### ✅ DO (推荐)

1. **依赖 CI 运行全部测试**:
   - 每次 push 自动运行
   - 环境一致，结果可靠
   - 无需本地配置环境

2. **本地只运行正在开发的测试**:
   - 快速反馈
   - 节省时间
   - 避免本地环境问题

3. **使用 GitHub Actions Summary**:
   - 查看测试结果摘要
   - 无需下载日志

4. **失败时才本地调试**:
   - 使用 `-vv --tb=long` 查看详细错误
   - 使用 `--pdb` 进入调试器

#### ❌ DON'T (不推荐)

1. ❌ 不要在本地运行全部测试:
   - 耗时长（可能 10+ 分钟）
   - 环境差异可能导致误报
   - CI 已经会运行

2. ❌ 不要在 commit 前运行所有测试:
   - 影响开发效率
   - CI 会自动运行
   - 只需确保新写的测试通过

3. ❌ 不要跳过写测试:
   - 代码改动 = 业务代码 + 测试代码
   - 测试是文档的一部分

---

## 2.4 风险评估矩阵

| 问题 | 影响 | 概率 | 严重性 | 优先级 |
|------|------|------|--------|--------|
| 反馈延迟 | 开发效率 | 高 | 低 | 🟡 中 |
| CI 配额限制 | 成本/可用性 | 中（Private） | 中 | 🟠 中-高 |
| Mock vs 真实环境 | 生产 Bug | 高 | 高 | 🔴 高 |
| 并发问题 | 数据一致性 | 中 | 高 | 🔴 高 |
| 环境差异 | CI/本地不一致 | 低 | 低 | 🟢 低 |

---

## 2.5 总结

### 2.5.1 CI 测试的优势

- 环境一致
- 自动化执行
- 并行测试（快速）
- 无需本地配置

### 2.5.2 需要补充的测试

1. **本地快速验证**（Pre-commit hook）
2. **Staging 真实环境测试**（每天/每周）
3. **并发/压力测试**（上线前）
4. **手动测试关键流程**（上线前）

### 2.5.3 推荐策略

```
95% 依赖 CI (Mock) + 5% 补充测试 (Staging/手动)
```

这样可以:
- ✅ 保持开发效率
- ✅ 发现大部分问题
- ✅ 降低生产风险
- ✅ 控制 CI 成本

---

*文档版本: v3.0*
*最后更新: 2026-01-10*
*架构版本: v3.1.0 (DDD)*

---
---

## 附录: 模块质量评审汇总

> 来源: `MODULE-QUALITY-REVIEWS.md`
> 添加日期: 2026-01-10

### 评分维度

每个模块从以下 5 个维度评分（每维度 1-5 星）:

1. **架构完整性** - DDD 架构、层次清晰、依赖合理
2. **安全性** - SQL注入、XSS防护、数据脱敏
3. **可维护性** - 代码质量、文档完善、命名规范
4. **可测试性** - 测试覆盖、边界条件、Mock 隔离
5. **性能优化** - 索引优化、RPC 函数、查询效率

**总分**: 25 星 (5 维度 × 5 星)

**评级**:
- ⭐⭐⭐⭐⭐ 23-25 星: 生产就绪
- ⭐⭐⭐⭐ 20-22 星: 良好，minor 改进
- ⭐⭐⭐ 15-19 星: 及格，需改进
- ⭐⭐ 10-14 星: 不合格，需重构
- ⭐ 5-9 星: 严重问题

### 模块评审总览

| 模块 | 最终版本 | 总评分 | 状态 | 关键改进 |
|------|----------|--------|------|----------|
| **Experiments** | v3.31 | ⭐⭐⭐⭐⭐ 25/25 | ✅ 生产就绪 | 完整 DDD + 安全 + 性能优化 |
| **Config** | v2.2.0 | ⭐⭐⭐⭐⭐ 24/25 | ✅ 生产就绪 | 敏感数据脱敏 + RPC 优化 |
| **Webhooks** | v2.5.0 | ⭐⭐⭐⭐⭐ 24/25 | ✅ 生产就绪 | Stripe/Clerk 集成完善 |
| **Payment** | v2.3.0 | ⭐⭐⭐⭐⭐ 23/25 | ✅ 生产就绪 | 积分原子操作 + 事务 |
| **Analytics** | v2.3.0 | ⭐⭐⭐⭐ 22/25 | ✅ 良好 | 事件追踪 + 隐私保护 |
| **Generations** | v3.0.0 | ⭐⭐⭐⭐ 22/25 | ✅ 良好 | AI 生成统一 + 积分扣费 |
| **Export** | v3.0.0 | ⭐⭐⭐⭐ 21/25 | ✅ 良好 | PDF/PNG/SVG 导出 |
| **Marketplace** | v3.0.0 | ⭐⭐⭐⭐ 21/25 | ✅ 良好 | 素材分类 + 审核流程 |
| **User Profile** | v2.2.0 | ⭐⭐⭐⭐ 20/25 | ✅ 良好 | 档案管理 + 隐私设置 |
| **Generation-Images** | v3.28 | ⭐⭐⭐⭐ 20/25 | ✅ 良好 | Flux/DALL-E 集成 |
| **Generation-PDF** | v3.26 | ⭐⭐⭐ 19/25 | ⚠️ 需改进 | PDF 生成 + 模板 |
| **Generation-Story** | v3.28 | ⭐⭐⭐ 19/25 | ⚠️ 需改进 | 故事生成 + GPT-4 |

### 最佳实践模块: Experiments (v3.31)

**总评分**: ⭐⭐⭐⭐⭐ 25/25 (满分)

**关键成就**:
1. 完整的 DDD 架构
2. SQL 注入防护 (15+ 测试用例)
3. XSS 防护 (10+ 测试用例)
4. 敏感数据脱敏
5. 6 个 RPC 函数 (100x 性能提升)
6. 65 个测试用例 (100% 覆盖)

详见完整文档: [MODULE-QUALITY-REVIEWS.md](MODULE-QUALITY-REVIEWS.md)

---

*最后更新: 2026-01-10*
*维护者: Make Decodables 后端团队*
