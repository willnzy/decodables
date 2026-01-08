# Admin API Review 计划

> **创建日期**: 2026-01-08
> **总接口数**: 125 个 (Admin 123 + Health 2)
> **当前阶段**: 未开始

---

## 执行进度

| 模块 | 接口数 | 已完成 | 状态 |
|------|--------|--------|------|
| AI Insights | 5 | 0 | 未开始 |
| AI Models Config | 8 | 0 | 未开始 |
| Campaigns | 8 | 0 | 未开始 |
| Config | 8 | 0 | 未开始 |
| Events | 5 | 0 | 未开始 |
| Experiments | 14 | 0 | 未开始 |
| Logs | 4 | 0 | 未开始 |
| Metrics | 7 | 0 | 未开始 |
| Moderation | 10 | 0 | 未开始 |
| Notifications | 5 | 0 | 未开始 |
| Stats | 18 | 0 | 未开始 |
| Subscriptions | 3 | 0 | 未开始 |
| System | 11 | 0 | 未开始 |
| Tasks Management | 4 | 0 | 未开始 |
| Users | 13 | 0 | 未开始 |
| Health | 2 | 0 | 未开始 |
| **总计** | **125** | **0** | - |

---

## AI Insights 模块 (5个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 1 | adm_get_ai_insights | GET | /insights | api/admin/ai.py | 34 |
| 2 | adm_get_ai_recommendations | GET | /recommendations | api/admin/ai.py | 45 |
| 3 | adm_get_behavior_analysis | GET | /behavior-analysis | api/admin/ai.py | 56 |
| 4 | adm_generate_ai_report | POST | /generate-report | api/admin/ai.py | 68 |
| 5 | adm_get_quick_insights | GET | /quick-insights | api/admin/ai.py | 92 |

**测试用例 Checklist**
- [ ] #1 获取AI洞察数据
- [ ] #2 获取AI推荐
- [ ] #3 用户行为分析
- [ ] #4 生成AI报告
- [ ] #5 快速洞察

**完成状态**: 未开始

---

## AI Models Config 模块 (8个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 6 | get_ai_config | GET | /config | api/admin/ai_models.py | 75 |
| 7 | update_text_config | PUT | /config/text | api/admin/ai_models.py | 86 |
| 8 | update_image_config | PUT | /config/image | api/admin/ai_models.py | 97 |
| 9 | update_admin_config | PUT | /config/admin | api/admin/ai_models.py | 108 |
| 10 | update_canary_config | PUT | /config/canary | api/admin/ai_models.py | 115 |
| 11 | toggle_provider | PUT | /providers/toggle | api/admin/ai_models.py | 134 |
| 12 | get_usage | GET | /usage | api/admin/ai_models.py | 144 |
| 13 | clear_cache | POST | /cache/clear | api/admin/ai_models.py | 157 |

**测试用例 Checklist**
- [ ] #6 获取AI配置
- [ ] #7 更新文本AI配置
- [ ] #8 更新图片AI配置
- [ ] #9 更新管理员AI配置
- [ ] #10 更新金丝雀配置
- [ ] #11 切换AI提供商
- [ ] #12 获取AI使用量统计
- [ ] #13 清除AI缓存

**完成状态**: 未开始

---

## Campaigns 活动管理 (8个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 14 | list_campaigns | GET | / | api/admin/campaigns.py | 74 |
| 15 | get_campaign | GET | /{campaign_id} | api/admin/campaigns.py | 93 |
| 16 | create_campaign | POST | / | api/admin/campaigns.py | 107 |
| 17 | update_campaign | PUT | /{campaign_id} | api/admin/campaigns.py | 140 |
| 18 | delete_campaign | DELETE | /{campaign_id} | api/admin/campaigns.py | 162 |
| 19 | activate_campaign | POST | /{campaign_id}/activate | api/admin/campaigns.py | 180 |
| 20 | pause_campaign | POST | /{campaign_id}/pause | api/admin/campaigns.py | 198 |
| 21 | get_campaign_stats | GET | /{campaign_id}/stats | api/admin/campaigns.py | 216 |

**测试用例 Checklist**
- [ ] #14 获取活动列表
- [ ] #15 获取活动详情
- [ ] #16 创建活动
- [ ] #17 更新活动配置
- [ ] #18 删除活动
- [ ] #19 激活活动
- [ ] #20 暂停活动
- [ ] #21 获取活动统计

**完成状态**: 未开始

---

## Config 配置管理 (8个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 22 | adm_get_all_configs | GET | /config | api/admin/config.py | 60 |
| 23 | adm_get_config | GET | /config/{config_key:path} | api/admin/config.py | 70 |
| 24 | adm_update_config | PUT | /config | api/admin/config.py | 82 |
| 25 | adm_batch_update_configs | PUT | /config/batch | api/admin/config.py | 106 |
| 26 | adm_clear_config_cache | POST | /config/cache/clear | api/admin/config.py | 128 |
| 27 | adm_get_rate_limits | GET | /rate-limits | api/admin/config.py | 143 |
| 28 | adm_apply_rate_limit_preset | POST | /rate-limits/preset | api/admin/config.py | 149 |
| 29 | adm_get_rate_limit_presets | GET | /rate-limits/presets | api/admin/config.py | 180 |

**测试用例 Checklist**
- [ ] #22 获取所有配置
- [ ] #23 获取单个配置
- [ ] #24 更新配置
- [ ] #25 批量更新配置
- [ ] #26 清除配置缓存
- [ ] #27 获取限流配置
- [ ] #28 应用限流预设
- [ ] #29 获取限流预设列表

**完成状态**: 未开始

---

## Events 事件管理 (5个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 30 | adm_get_user_events | GET | /events | api/admin/events.py | 34 |
| 31 | adm_get_event_stats | GET | /events/stats | api/admin/events.py | 57 |
| 32 | adm_get_aggregated_stats | GET | /aggregated/{stat_type} | api/admin/events.py | 74 |
| 33 | adm_get_aggregated_stats_range | GET | /aggregated/{stat_type}/range | api/admin/events.py | 95 |
| 34 | adm_run_aggregation | POST | /aggregation/run | api/admin/events.py | 107 |

**测试用例 Checklist**
- [ ] #30 获取用户事件列表
- [ ] #31 获取事件统计
- [ ] #32 获取聚合统计
- [ ] #33 获取时间范围聚合统计
- [ ] #34 手动运行聚合任务

**完成状态**: 未开始

---

## Experiments 实验管理 (14个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 35 | list_experiments | GET | / | api/admin/experiments.py | 117 |
| 36 | create_experiment | POST | / | api/admin/experiments.py | 130 |
| 37 | get_experiment | GET | /{experiment_key} | api/admin/experiments.py | 163 |
| 38 | update_experiment | PUT | /{experiment_key} | api/admin/experiments.py | 175 |
| 39 | update_experiment_status | PUT | /{experiment_key}/status | api/admin/experiments.py | 216 |
| 40 | delete_experiment | DELETE | /{experiment_key} | api/admin/experiments.py | 233 |
| 41 | get_experiment_results | GET | /{experiment_key}/results | api/admin/experiments.py | 255 |
| 42 | trigger_aggregation | POST | /{experiment_key}/aggregate | api/admin/experiments.py | 272 |
| 43 | trigger_all_aggregation | POST | /aggregate-all | api/admin/experiments.py | 284 |
| 44 | clear_cache | POST | /cache/clear | api/admin/experiments.py | 293 |
| 45 | get_ai_analysis | POST | /{experiment_key}/ai-analysis | api/admin/experiments.py | 300 |
| 46 | get_quick_recommendation | GET | /{experiment_key}/quick-recommendation | api/admin/experiments.py | 326 |
| 47 | get_experiment_trend | GET | /{experiment_key}/trend | api/admin/experiments.py | 351 |
| 48 | get_hourly_trend | GET | /{experiment_key}/hourly-trend | api/admin/experiments.py | 401 |

**测试用例 Checklist**
- [ ] #35 获取实验列表
- [ ] #36 创建实验
- [ ] #37 获取实验详情
- [ ] #38 更新实验配置
- [ ] #39 更新实验状态
- [ ] #40 删除实验
- [ ] #41 获取实验结果
- [ ] #42 触发单个实验聚合
- [ ] #43 触发全部实验聚合
- [ ] #44 清除实验缓存
- [ ] #45 AI分析实验结果
- [ ] #46 快速推荐
- [ ] #47 获取实验趋势
- [ ] #48 获取小时级趋势

**完成状态**: 未开始

---

## Logs 日志管理 (4个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 49 | get_error_logs | GET | /errors | api/admin/logs.py | 36 |
| 50 | get_error_stats | GET | /errors/stats | api/admin/logs.py | 113 |
| 51 | get_operation_logs | GET | /operations | api/admin/logs.py | 170 |
| 52 | export_operation_logs | GET | /operations/export | api/admin/logs.py | 195 |

**测试用例 Checklist**
- [ ] #49 获取错误日志列表
- [ ] #50 获取错误统计
- [ ] #51 获取操作日志
- [ ] #52 导出操作日志

**完成状态**: 未开始

---

## Metrics 指标管理 (7个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 53 | get_daily_metrics | GET | /daily | api/admin/metrics.py | 36 |
| 54 | get_monthly_metrics | GET | /monthly | api/admin/metrics.py | 55 |
| 55 | get_retention_metrics | GET | /retention | api/admin/metrics.py | 68 |
| 56 | get_funnel_metrics | GET | /funnel | api/admin/metrics.py | 80 |
| 57 | get_error_metrics | GET | /errors | api/admin/metrics.py | 110 |
| 58 | get_dau_trend | GET | /dau-trend | api/admin/metrics.py | 142 |
| 59 | refresh_metrics | POST | /refresh | api/admin/metrics.py | 155 |

**测试用例 Checklist**
- [ ] #53 获取日指标
- [ ] #54 获取月指标
- [ ] #55 获取留存指标
- [ ] #56 获取漏斗指标
- [ ] #57 获取错误指标
- [ ] #58 获取DAU趋势
- [ ] #59 刷新指标数据

**完成状态**: 未开始

---

## Moderation 审核管理 (10个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 60 | adm_moderation_list | GET | /marketplace/moderation/list | api/admin/moderation.py | 56 |
| 61 | adm_moderation_detail | GET | /marketplace/moderation/{listing_id} | api/admin/moderation.py | 76 |
| 62 | adm_moderation_approve | POST | /marketplace/moderation/{listing_id}/approve | api/admin/moderation.py | 87 |
| 63 | adm_moderation_reject | POST | /marketplace/moderation/{listing_id}/reject | api/admin/moderation.py | 111 |
| 64 | adm_moderation_delete | POST | /marketplace/moderation/{listing_id}/delete | api/admin/moderation.py | 146 |
| 65 | adm_moderation_unpublish | POST | /marketplace/moderation/{listing_id}/unpublish | api/admin/moderation.py | 161 |
| 66 | adm_get_reports | GET | /reports | api/admin/moderation.py | 180 |
| 67 | adm_get_reports_stats | GET | /reports/stats | api/admin/moderation.py | 195 |
| 68 | adm_get_report_detail | GET | /reports/{report_id} | api/admin/moderation.py | 209 |
| 69 | adm_respond_to_report | POST | /reports/{report_id}/respond | api/admin/moderation.py | 220 |

**测试用例 Checklist**
- [ ] #60 获取待审核列表
- [ ] #61 获取审核详情
- [ ] #62 通过审核
- [ ] #63 拒绝审核
- [ ] #64 删除内容
- [ ] #65 下架内容
- [ ] #66 获取举报列表
- [ ] #67 获取举报统计
- [ ] #68 获取举报详情
- [ ] #69 响应举报

**完成状态**: 未开始

---

## Notifications 通知管理 (5个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 70 | adm_broadcast | POST | /broadcast | api/admin/notifications.py | 63 |
| 71 | adm_send_notification | POST | /notification/send | api/admin/notifications.py | 87 |
| 72 | adm_batch_notification | POST | /notification/batch | api/admin/notifications.py | 122 |
| 73 | adm_notification_stats | GET | /notification/stats | api/admin/notifications.py | 157 |
| 74 | adm_notification_history | GET | /notification/history | api/admin/notifications.py | 165 |

**测试用例 Checklist**
- [ ] #70 全员广播
- [ ] #71 发送单个通知
- [ ] #72 批量发送通知
- [ ] #73 通知统计
- [ ] #74 通知历史

**完成状态**: 未开始

---

## Stats 统计管理 (18个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 75 | get_dashboard_stats | GET | /dashboard | api/admin/stats.py | 67 |
| 76 | get_user_growth_stats | GET | /user-growth | api/admin/stats.py | 78 |
| 77 | get_revenue_stats | GET | /revenue | api/admin/stats.py | 91 |
| 78 | get_project_stats | GET | /projects | api/admin/stats.py | 104 |
| 79 | get_credit_usage_stats | GET | /credits | api/admin/stats.py | 116 |
| 80 | get_tier_distribution | GET | /tier-distribution | api/admin/stats.py | 128 |
| 81 | get_conversion_funnel | GET | /conversion-funnel | api/admin/stats.py | 138 |
| 82 | get_export_stats | GET | /exports | api/admin/stats.py | 153 |
| 83 | get_asset_usage_stats | GET | /assets | api/admin/stats.py | 162 |
| 84 | get_tier_activity | GET | /tier-activity | api/admin/stats.py | 171 |
| 85 | get_subscription_events | GET | /subscription-events | api/admin/stats.py | 177 |
| 86 | get_page_views | GET | /page-views | api/admin/stats.py | 186 |
| 87 | get_project_details | GET | /project-details | api/admin/stats.py | 195 |
| 88 | get_returning_users | GET | /returning-users | api/admin/stats.py | 204 |
| 89 | get_tier_trend | GET | /tier-trend | api/admin/stats.py | 210 |
| 90 | get_tier_conversion | GET | /tier-conversion | api/admin/stats.py | 216 |
| 91 | get_performance_metrics | GET | /performance | api/admin/stats.py | 222 |
| 92 | get_user_distribution | GET | /user-distribution | api/admin/stats.py | 231 |

**测试用例 Checklist**
- [ ] #75 仪表盘概览
- [ ] #76 用户增长统计
- [ ] #77 收入统计
- [ ] #78 项目统计
- [ ] #79 积分使用统计
- [ ] #80 用户等级分布
- [ ] #81 转化漏斗
- [ ] #82 导出统计
- [ ] #83 素材使用统计
- [ ] #84 等级活跃度
- [ ] #85 订阅事件
- [ ] #86 页面访问
- [ ] #87 项目详情
- [ ] #88 回访用户
- [ ] #89 等级趋势
- [ ] #90 等级转化
- [ ] #91 性能指标
- [ ] #92 用户分布

**完成状态**: 未开始

---

## Subscriptions 订阅管理 (3个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 93 | adm_refund | POST | /refund | api/admin/subscriptions.py | 73 |
| 94 | adm_cancel_subscription | POST | /subscription/cancel | api/admin/subscriptions.py | 165 |
| 95 | adm_downgrade_subscription | POST | /subscription/downgrade | api/admin/subscriptions.py | 266 |

**测试用例 Checklist**
- [ ] #93 退款处理
- [ ] #94 取消订阅
- [ ] #95 降级订阅

**完成状态**: 未开始

---

## System 系统管理 (11个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 96 | get_configs | GET | /configs | api/admin/system.py | 53 |
| 97 | get_config_groups | GET | /configs/groups | api/admin/system.py | 69 |
| 98 | create_config | POST | /configs | api/admin/system.py | 79 |
| 99 | update_config | PUT | /configs/{key:path} | api/admin/system.py | 99 |
| 100 | delete_config | DELETE | /configs/{key:path} | api/admin/system.py | 118 |
| 101 | get_config_audit | GET | /configs/audit | api/admin/system.py | 131 |
| 102 | invalidate_cache | POST | /configs/cache/invalidate | api/admin/system.py | 146 |
| 103 | get_cache_status | GET | /system/cache/status | api/admin/system.py | 163 |
| 104 | list_cache_keys | GET | /system/cache/keys | api/admin/system.py | 186 |
| 105 | delete_cache_key | DELETE | /system/cache/key/{key:path} | api/admin/system.py | 214 |
| 106 | clear_all_cache | POST | /system/cache/clear-all | api/admin/system.py | 231 |

**测试用例 Checklist**
- [ ] #96 获取系统配置列表
- [ ] #97 获取配置分组
- [ ] #98 创建系统配置
- [ ] #99 更新系统配置
- [ ] #100 删除系统配置
- [ ] #101 获取配置审计日志
- [ ] #102 使缓存失效
- [ ] #103 获取缓存状态
- [ ] #104 列出缓存键
- [ ] #105 删除缓存键
- [ ] #106 清除所有缓存

**完成状态**: 未开始

---

## Tasks Management 任务管理 (4个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 107 | get_tasks_status | GET | /status | api/admin/tasks_mgmt.py | 34 |
| 108 | get_task_logs | GET | /logs | api/admin/tasks_mgmt.py | 63 |
| 109 | get_tasks_health | GET | /health | api/admin/tasks_mgmt.py | 85 |
| 110 | run_task_manually | POST | /{task_name}/run | api/admin/tasks_mgmt.py | 121 |

**测试用例 Checklist**
- [ ] #107 获取任务状态
- [ ] #108 获取任务日志
- [ ] #109 获取任务健康状态
- [ ] #110 手动运行任务

**完成状态**: 未开始

---

## Users 用户管理 (13个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 111 | search_users_api | GET | /users | api/admin/users.py | 70 |
| 112 | get_users_by_tier_api | GET | /users/by-tier/{tier} | api/admin/users.py | 82 |
| 113 | get_user_audit | GET | /users/{uid} | api/admin/users.py | 94 |
| 114 | adjust_user_credits | POST | /users/{uid}/credits | api/admin/users.py | 105 |
| 115 | update_user | PATCH | /users/{uid} | api/admin/users.py | 126 |
| 116 | update_user_tier | POST | /users/{uid}/tier | api/admin/users.py | 157 |
| 117 | create_user_discount_api | POST | /users/{uid}/discount | api/admin/users.py | 189 |
| 118 | get_user_payments | GET | /users/{uid}/payments | api/admin/users.py | 208 |
| 119 | get_user_projects | GET | /users/{uid}/projects | api/admin/users.py | 233 |
| 120 | get_user_asset_usage | GET | /users/{uid}/asset-usage | api/admin/users.py | 247 |
| 121 | get_user_env_stats | GET | /users/{uid}/env-stats | api/admin/users.py | 277 |
| 122 | restore_project_api | POST | /projects/{project_id}/restore | api/admin/users.py | 331 |
| 123 | get_projects_feed | GET | /projects/feed | api/admin/users.py | 346 |

**测试用例 Checklist**
- [ ] #111 搜索用户
- [ ] #112 按等级获取用户
- [ ] #113 获取用户审计详情
- [ ] #114 调整用户积分
- [ ] #115 更新用户信息
- [ ] #116 更新用户等级
- [ ] #117 创建用户折扣
- [ ] #118 获取用户支付记录
- [ ] #119 获取用户项目
- [ ] #120 获取用户素材使用
- [ ] #121 获取用户环境统计
- [ ] #122 恢复已删除项目
- [ ] #123 获取项目Feed

**完成状态**: 未开始

---

## Health 健康检查 (2个)

| 序号 | 函数 | 方法 | 路由 | 文件 | 行号 |
|------|------|------|------|------|------|
| 124 | health_check | GET | /health | api/health.py | 31 |
| 125 | detailed_health_check | GET | /health/detailed | api/health.py | 64 |

**测试用例 Checklist**
- [ ] #124 基础健康检查
- [ ] #125 详细健康检查 (数据库/缓存/外部服务)

**完成状态**: 未开始

---

## 附录: 测试优先级说明

### P3 优先级 (Admin API)

Admin API 作为内部管理工具，测试优先级为 P3:

1. **权限验证为主**: 确保所有接口都需要 Admin 认证
2. **基础功能覆盖**: 正常路径测试
3. **不需要边界测试**: Admin 用户可信，无需恶意输入测试

### 测试范围

- 认证鉴权测试 (Admin role check)
- 基础 CRUD 操作
- 数据格式校验
- 关键业务逻辑 (退款、积分调整等)

### 不需要测试

- 性能压测
- 并发安全 (Admin 操作量小)
- 复杂边界条件
