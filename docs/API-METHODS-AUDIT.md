# API HTTP Methods Audit Report

> 根据 API-HTTP-METHODS-GUIDELINES.md 审查所有 API 端点

## 审查标准

- ✅ 符合规范
- ⚠️ 需要优化
- ❌ 不符合规范

---

## 1. 公开 API

### analytics_api.py
- `POST /events` ✅ - 批量记录事件，使用 POST 正确

### assets_api.py
- `GET /` ✅ - 获取资源列表
- `POST /` ✅ - 创建新资源
- `DELETE /{asset_id}` ✅ - 删除资源
- `POST /from-url` ✅ - 从 URL 创建资源 (操作型)
- `GET /check-url` ✅ - 检查 URL 状态
- `POST /{asset_id}/increment-usage` ✅ - 增加使用次数 (操作型)
- `GET /dashboard` ✅ - 获取统计数据
- `GET /deleted` ✅ - 获取已删除列表
- `POST /{asset_id}/restore` ✅ - 恢复操作

### billing_api.py
- `GET /credits` ✅ - 获取积分余额
- `GET /transactions` ✅ - 获取交易历史
- `GET /can-afford` ✅ - 检查是否可承担
- `POST /credits/deduct` ✅ - 扣除积分 (操作型)
- `POST /credits/add` ✅ - 添加积分 (操作型)

### campaigns_api.py
- `GET /active` ✅ - 获取活跃活动
- `POST /{campaign_id}/claim` ✅ - 领取奖励 (操作型)
- `POST /{campaign_id}/dismiss` ✅ - 关闭提示 (操作型)

### config_api.py
- `GET /` ✅ - 获取所有配置
- `GET /group/{group_name}` ✅ - 获取分组配置
- `GET /{key}` ✅ - 获取单个配置

### credits_api.py
- `GET /` ✅ - 获取积分信息
- `GET /history` ✅ - 获取积分历史

### experiments_api.py (公开)
- `POST /{experiment_key}/assign` ✅ - 分配变体 (操作型)
- `POST /{experiment_key}/exposure` ✅ - 记录曝光 (操作型)
- `POST /{experiment_key}/conversion` ✅ - 记录转化 (操作型)
- `GET /user/{user_identifier}` ✅ - 获取用户实验

### export_api.py
- `GET /projects/{project_id}/pdf` ✅ - 导出 PDF
- `GET /projects/{project_id}/preview` ✅ - 获取预览
- `POST /zip` ⚠️ - **应改为 GET** `/projects/{project_id}/zip?items=...`
- `GET /projects/{project_id}/zip` ✅ - 获取 ZIP

**优化建议**: `POST /zip` 应改为 `GET /projects/{project_id}/zip`，将 items 作为查询参数

### generation_api.py
- `POST /images` ✅ - 生成图片 (操作型)
- `POST /images/async` ✅ - 异步生成 (操作型)
- `POST /story` ✅ - 生成故事 (操作型)
- `POST /inspiration` ✅ - 获取灵感 (操作型)
- `POST /pdf` ✅ - 生成 PDF (操作型)

### generations_api.py
- `GET /history` ✅ - 获取历史记录
- `POST /{generation_id}/favorite` ⚠️ - **应改为 PATCH** (部分更新资源状态)
- `DELETE /{generation_id}` ✅ - 删除记录
- `DELETE /batch` ⚠️ - **应改为 POST** `/batch-delete` (批量操作)

**优化建议**:
- `POST /favorite` → `PATCH /{generation_id}` with `{"favorite": true}`
- `DELETE /batch` → `POST /batch-delete`

### logs_api.py
- `POST /error` ✅ - 记录错误 (无需认证)
- `POST /errors` ✅ - 批量记录错误

### marketplace_api.py
- `GET /listings` ✅ - 获取商品列表
- `GET /listings/{listing_id}` ✅ - 获取单个商品
- `POST /listings` ✅ - 创建商品
- `PUT /listings/{listing_id}` ✅ - 更新商品
- `DELETE /listings/{listing_id}` ✅ - 删除商品
- `POST /purchase` ✅ - 购买操作
- `GET /my-listings` ✅ - 获取我的商品
- `GET /seller/stats` ✅ - 获取卖家统计

### payment_api.py
- `POST /checkout` ✅ - 创建支付会话
- `GET /plans` ✅ - 获取订阅计划
- `POST /portal` ✅ - 创建客户门户会话

### platform_api.py
- `GET /feature-flags` ✅ - 获取功能标志
- `GET /feature-flags/{flag_key}` ✅ - 获取单个标志
- `POST /experiments/{key}/assign` ✅ - 分配变体

### projects_api.py
- `GET /` ✅ - 获取项目列表
- `POST /` ✅ - 创建项目
- `GET /{project_id}` ✅ - 获取项目
- `PUT /{project_id}` ✅ - 更新项目
- `DELETE /{project_id}` ✅ - 删除项目
- `POST /{project_id}/duplicate` ✅ - 复制项目 (操作型)
- `POST /{project_id}/restore` ✅ - 恢复项目 (操作型)
- `GET /deleted` ✅ - 获取已删除列表
- `GET /{project_id}/pages` ✅ - 获取页面列表
- `POST /{project_id}/pages` ✅ - 创建页面
- `GET /pages/{page_id}` ✅ - 获取页面
- `PUT /pages/{page_id}` ✅ - 更新页面
- `DELETE /pages/{page_id}` ✅ - 删除页面
- `POST /pages/{page_id}/duplicate` ✅ - 复制页面

### resources_api.py
- `GET /stickers` ✅ - 获取贴纸列表
- `GET /stickers/{sticker_id}` ✅ - 获取单个贴纸
- `GET /backgrounds` ✅ - 获取背景列表
- `GET /backgrounds/{background_id}` ✅ - 获取单个背景

### support_api.py
- `POST /ticket` ✅ - 提交工单
- `POST /chat` ✅ - AI 聊天支持
- `POST /contact` ✅ - 联系表单
- `POST /feedback` ✅ - 提交反馈

### tasks_api.py
- `GET /{task_id}` ✅ - 获取任务状态
- `POST /{task_id}/cancel` ✅ - 取消任务 (操作型)

### templates_api.py
- `GET /asset/{template_id}` ✅ - 获取素材模板
- `POST /asset/{template_id}/use` ✅ - 使用模板 (操作型)
- `GET /asset` ✅ - 获取模板列表
- `POST /asset` ✅ - 创建模板
- `PUT /asset/{template_id}` ✅ - 更新模板
- `DELETE /asset/{template_id}` ✅ - 删除模板
- `GET /page/{template_id}` ✅ - 获取页面模板
- `POST /page/{template_id}/use` ✅ - 使用页面模板
- `GET /page` ✅ - 获取页面模板列表
- `POST /page` ✅ - 创建页面模板
- `PUT /page/{template_id}` ✅ - 更新页面模板
- `DELETE /page/{template_id}` ✅ - 删除页面模板

### themes_api.py
- `GET /current` ✅ - 获取当前主题

### tools_api.py
- `POST /pdf-preview` ✅ - PDF 预览 (文件上传)
- `POST /ocr` ✅ - OCR 识别 (文件上传)

### user_api.py
- `GET /profile` ✅ - 获取用户资料
- `PUT /profile` ✅ - 更新用户资料
- `POST /onboarding` ✅ - 完成引导 (操作型)
- `GET /preferences` ✅ - 获取偏好设置
- `PUT /preferences` ✅ - 更新偏好设置

### webhooks_api.py
- `POST /clerk` ✅ - Clerk webhook
- `POST /stripe` ✅ - Stripe webhook

### websocket_api.py
- `WebSocket /task/{task_id}` ✅ - WebSocket 连接

---

## 2. Admin API

### admin/ai_api.py
- `GET /insights` ✅ - 获取洞察
- `GET /recommendations` ✅ - 获取推荐
- `GET /behavior-analysis` ✅ - 获取行为分析
- `POST /generate-report` ✅ - 生成报告 (操作型)
- `GET /quick-insights` ✅ - 获取快速洞察
- `GET /config` ✅ - 获取配置
- `PUT /config/text` ✅ - 更新文本配置
- `PUT /config/image` ✅ - 更新图片配置
- `PUT /config/canary` ✅ - 更新灰度配置
- `PUT /providers/toggle` ⚠️ - **应改为 PATCH** `/providers/{provider}` (部分更新)
- `GET /usage` ✅ - 获取使用统计
- `POST /cache/clear` ✅ - 清空缓存 (操作型)

**优化建议**: `PUT /providers/toggle` → `PATCH /providers/{provider}` with `{"enabled": true/false}`

### admin/campaigns_api.py
- `GET /` ✅ - 获取活动列表
- `POST /` ✅ - 创建活动
- `GET /{campaign_id}` ✅ - 获取活动
- `PUT /{campaign_id}` ✅ - 更新活动
- `DELETE /{campaign_id}` ✅ - 删除活动
- `POST /{campaign_id}/activate` ✅ - 激活活动 (操作型)
- `POST /{campaign_id}/pause` ✅ - 暂停活动 (操作型)
- `GET /{campaign_id}/stats` ✅ - 获取统计

### admin/config_api.py
- `GET /` ✅ - 获取所有配置
- `POST /` ✅ - 创建配置
- `GET /{key}` ✅ - 获取配置
- `PUT /{key}` ✅ - 更新配置
- `DELETE /{key}` ✅ - 删除配置
- `POST /rate-limits/update` ⚠️ - **应改为 PUT** `/rate-limits`
- `POST /cache/clear` ✅ - 清空缓存

**优化建议**: `POST /rate-limits/update` → `PUT /rate-limits`

### admin/events_api.py
- `GET /` ✅ - 获取事件列表 (路径为空，应补充 `/events`)
- `GET /stats` ✅ - 获取事件统计
- `GET /aggregated/{stat_type}` ✅ - 获取聚合数据
- `GET /aggregated/{stat_type}/range` ✅ - 获取范围数据
- `POST /aggregation/run` ✅ - 触发聚合 (操作型)

**优化建议**: `GET /` 应改为 `GET /events` 以明确路径

### admin/experiments_api.py
- `GET /` ✅ - 获取实验列表
- `POST /` ✅ - 创建实验
- `GET /{experiment_key}` ✅ - 获取实验
- `PUT /{experiment_key}` ✅ - 更新实验
- `DELETE /{experiment_key}` ✅ - 删除实验
- `PUT /{experiment_key}/status` ✅ - 更新状态
- `GET /{experiment_key}/results` ✅ - 获取结果
- `POST /{experiment_key}/aggregate` ✅ - 触发聚合 (操作型)
- `POST /aggregate-all` ✅ - 聚合所有 (操作型)
- `POST /cache/clear` ✅ - 清空缓存 (操作型)
- `POST /{experiment_key}/ai-analysis` ✅ - AI 分析 (操作型)
- `GET /{experiment_key}/quick-recommendation` ✅ - 获取推荐
- `GET /{experiment_key}/trend` ✅ - 获取趋势
- `GET /{experiment_key}/hourly-trend` ✅ - 获取小时趋势

### admin/logs_api.py
- `GET /errors` ✅ - 获取错误日志
- `GET /errors/stats` ✅ - 获取错误统计
- `GET /operations` ✅ - 获取操作日志
- `GET /operations/export` ✅ - 导出日志

### admin/metrics_api.py
- `GET /daily` ✅ - 获取日指标
- `GET /monthly` ✅ - 获取月指标
- `GET /retention` ✅ - 获取留存
- `GET /funnel` ✅ - 获取漏斗
- `GET /errors` ✅ - 获取错误指标
- `GET /dau-trend` ✅ - 获取 DAU 趋势
- `POST /refresh` ✅ - 刷新指标 (操作型)

### admin/moderation_api.py
- `GET /pending` ✅ - 获取待审核
- `POST /{listing_id}/approve` ✅ - 批准 (操作型)
- `POST /{listing_id}/reject` ✅ - 拒绝 (操作型)
- `GET /reports` ✅ - 获取举报
- `POST /reports/{report_id}/resolve` ✅ - 处理举报 (操作型)

### admin/notifications_api.py
- `POST /broadcast` ✅ - 广播通知
- `POST /single` ✅ - 单个通知
- `POST /batch` ✅ - 批量通知

### admin/stats_api.py
- `GET /dashboard` ✅ - 获取仪表盘
- `GET /users/growth` ✅ - 获取用户增长
- `GET /revenue` ✅ - 获取收入
- `GET /credits-usage` ✅ - 获取积分使用
- `GET /tier-distribution` ✅ - 获取等级分布
- `GET /funnel` ✅ - 获取转化漏斗

### admin/subscriptions_api.py
- `POST /refund` ✅ - 退款 (操作型)
- `POST /cancel` ✅ - 取消订阅 (操作型)
- `POST /downgrade` ✅ - 降级 (操作型)

### admin/system_api.py
- `GET /` ✅ - 获取系统配置
- `PUT /` ✅ - 更新系统配置
- `POST /cache/clear` ✅ - 清空缓存 (操作型)

### admin/tasks_api.py
- `GET /` ✅ - 获取任务列表
- `GET /{task_id}` ✅ - 获取任务
- `GET /{task_id}/logs` ✅ - 获取任务日志
- `POST /{task_id}/trigger` ✅ - 触发任务 (操作型)

### admin/users_api.py
- `GET /search` ✅ - 搜索用户
- `GET /{user_id}` ✅ - 获取用户
- `GET /{user_id}/audit` ✅ - 获取审计日志
- `POST /{user_id}/credits` ✅ - 调整积分 (操作型)
- `PUT /{user_id}/tier` ⚠️ - **应改为 PATCH** (部分更新)
- `GET /{user_id}/payments` ✅ - 获取支付记录

**优化建议**: `PUT /{user_id}/tier` → `PATCH /{user_id}` with `{"tier": "..."}`

---

## 总结

### 需要优化的端点 (7 个)

1. **export_api.py**
   - `POST /zip` → `GET /projects/{project_id}/zip?items=...`

2. **generations_api.py**
   - `POST /{generation_id}/favorite` → `PATCH /{generation_id}`
   - `DELETE /batch` → `POST /batch-delete`

3. **admin/ai_api.py**
   - `PUT /providers/toggle` → `PATCH /providers/{provider}`

4. **admin/config_api.py**
   - `POST /rate-limits/update` → `PUT /rate-limits`

5. **admin/events_api.py**
   - `GET /` → `GET /events`

6. **admin/users_api.py**
   - `PUT /{user_id}/tier` → `PATCH /{user_id}`

### 总体评价

- **符合规范**: 95% (约 200+ 个端点)
- **需要优化**: 5% (7 个端点)

大部分 API 设计符合 RESTful 规范，小部分端点可以进行优化以更好地遵循行业标准。
