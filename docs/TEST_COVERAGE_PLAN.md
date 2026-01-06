# 后台测试覆盖率提升计划

**目标**: 所有后台代码覆盖率达到 95%+  
**当前状态**: 测试通过 1,476 / 总计 2,036 (约 72.5% 通过率)  
**预计总工时**: 12-15 个工作日

---

## 📊 模块统计

| 目录 | 文件数 | 测试优先级 | 预计工时 |
|------|--------|------------|----------|
| services/db/ | 13 | P0 - 核心 | 2 天 |
| services/ai/ | 19 | P1 - 高 | 3 天 |
| services/ (根目录) | 19 | P1 - 高 | 2 天 |
| routers/ | 40 | P0 - 核心 | 3 天 |
| services/cache/ | 5 | P2 - 中 | 0.5 天 |
| services/experiments/ | 7 | P2 - 中 | 0.5 天 |
| services/task_queue/ | 4 | P2 - 中 | 0.5 天 |
| services/websocket/ | 2 | P2 - 中 | 0.5 天 |
| services/capi/ | 4 | P3 - 低 | 0.5 天 |
| services/ai_reports/ | 4 | P3 - 低 | 0.5 天 |
| scheduled_tasks/ | 24 | P3 - 低 | 1 天 |

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

### 阶段 4: 路由层测试 (3 天)

**目标**: `routers/` 所有端点 95%+ 覆盖率

#### 4.1 用户相关 (0.5 天)

| 模块 | 测试文件 | 状态 |
|------|----------|------|
| user_profile.py | test_user_api.py | ⚠️ 部分 |
| user_assets.py | tests/api/test_user_assets_api.py | 🆕 新建 |
| user_notifications.py | tests/api/test_user_notifications_api.py | 🆕 新建 |

#### 4.2 项目相关 (0.5 天)

| 模块 | 测试文件 | 状态 |
|------|----------|------|
| projects.py | test_projects_api.py | ⚠️ 部分 |

#### 4.3 市场相关 (0.5 天)

| 模块 | 测试文件 | 状态 |
|------|----------|------|
| marketplace.py | tests/api/test_marketplace_api.py | 🆕 新建 |

#### 4.4 AI 生成相关 (0.5 天)

| 模块 | 测试文件 | 状态 |
|------|----------|------|
| generation.py | test_generation_api.py | ⚠️ 部分 |
| templates.py | tests/api/test_templates_api.py | 🆕 新建 |

#### 4.5 导出与工具 (0.5 天)

| 模块 | 测试文件 | 状态 |
|------|----------|------|
| export.py | test_export_api.py | ⚠️ 部分 |
| upload.py | test_upload_api.py | ⚠️ 部分 |
| tools.py | tests/api/test_tools_api.py | 🆕 新建 |

#### 4.6 管理员相关 (0.5 天)

| 模块 | 测试文件 | 状态 |
|------|----------|------|
| admin/*.py | tests/api/test_admin_api.py | 🆕 新建 |

**验收标准**: `pytest --cov=routers --cov-fail-under=95`

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

### 阶段 6: 计划任务测试 (1 天)

**目标**: `scheduled_tasks/` 所有模块 95%+ 覆盖率

| 模块目录 | 测试文件 | 状态 |
|----------|----------|------|
| aggregators/ | tests/scheduled/test_aggregators.py | 🆕 新建 |
| campaign_scheduler/ | tests/scheduled/test_campaign_scheduler.py | 🆕 新建 |
| metrics_etl/ | tests/scheduled/test_metrics_etl.py | 🆕 新建 |
| storage_cleanup.py | tests/scheduled/test_storage_cleanup.py | 🆕 新建 |

---

### 阶段 7: 最终验证与 CI 配置 (0.5 天)

#### 任务清单

- [ ] **7.1** 运行完整覆盖率报告
  ```bash
  pytest --cov=services --cov=routers --cov=scheduled_tasks \
         --cov-report=html --cov-fail-under=95
  ```

- [ ] **7.2** 更新 pytest.ini 启用覆盖率门槛
  ```ini
  addopts = 
      --cov=services
      --cov=routers
      --cov-fail-under=95
  ```

- [ ] **7.3** 配置 GitHub Actions CI
  ```yaml
  - name: Run tests with coverage
    run: pytest --cov --cov-fail-under=95
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

| 阶段 | 预计完成日 | 验收标准 |
|------|------------|----------|
| 阶段 0 | Day 2 | 0 失败测试 |
| 阶段 1 | Day 4 | services/db/ 95%+ |
| 阶段 2 | Day 7 | services/ai/ 95%+ |
| 阶段 3 | Day 9 | services/ 95%+ |
| 阶段 4 | Day 12 | routers/ 95%+ |
| 阶段 5 | Day 14 | 辅助服务 95%+ |
| 阶段 6 | Day 15 | scheduled_tasks/ 95%+ |
| 阶段 7 | Day 15.5 | CI 配置完成，全局 95%+ |

---

## 📝 注意事项

1. **Mock 策略**: 所有外部依赖（Supabase, Redis, Stripe, AI APIs）必须 Mock
2. **测试隔离**: 每个测试独立，不依赖执行顺序
3. **边界测试**: 包含正常、异常、边界三类用例
4. **业务规则**: 测试必须验证 `后台业务逻辑说明.md` 中的规则
5. **向后兼容**: 测试新代码不破坏现有功能

---

*文档版本: v1.0*  
*最后更新: 2026-01-06*
