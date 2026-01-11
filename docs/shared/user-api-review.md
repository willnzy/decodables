# User API 完整参考

> **状态**: ✅ Complete
> **版本**: 3.32
> **最后更新**: 2026-01-11
> **总端点数**: 123 个
> **DDD 合规**: 100%
> **测试覆盖率**: 65%+

本文档记录所有 User API 端点的完整信息，包括请求参数、响应格式、验证规则和限流配置。

---

## 目录

1. [Analytics 分析 (1个)](#1-analytics-分析)
2. [Billing 计费管理 (4个)](#2-billing-计费管理)
3. [Campaigns 活动 (3个)](#3-campaigns-活动)
4. [Config 配置 (3个)](#4-config-配置)
5. [Experiments 实验 (4个)](#5-experiments-实验)
6. [Export 导出 (6个)](#6-export-导出)
7. [Generation Images AI图片生成 (2个)](#7-generation-images-ai图片生成)
8. [Generation PDF PDF生成 (1个)](#8-generation-pdf-pdf生成)
9. [Generation Story AI故事生成 (2个)](#9-generation-story-ai故事生成)
10. [Generations 生成历史 (6个)](#10-generations-生成历史)
11. [Logs 日志 (2个)](#11-logs-日志)
12. [Marketplace 市场 (11个)](#12-marketplace-市场)
13. [Onboarding 新手引导 (6个)](#13-onboarding-新手引导)
14. [Payment 支付 (2个)](#14-payment-支付)
15. [Projects 项目管理 (10个)](#15-projects-项目管理)
16. [Referrals 推荐系统 (6个)](#16-referrals-推荐系统)
17. [Resources 系统资源 (7个)](#17-resources-系统资源)
18. [Support 客服支持 (4个)](#18-support-客服支持)
19. [System Resources 系统资源管理 (9个)](#19-system-resources-系统资源管理)
20. [Tasks 任务 (2个)](#20-tasks-任务)
21. [Templates 模板 (10个)](#21-templates-模板)
22. [Themes 主题 (1个)](#22-themes-主题)
23. [Tools 工具 (2个)](#23-tools-工具)
24. [User Assets 用户资产 (10个)](#24-user-assets-用户资产)
25. [User Profile 用户档案 (7个)](#25-user-profile-用户档案)
26. [Webhooks (2个)](#26-webhooks)

---

## 📋 接口总览 (123个)

| 序号 | 模块 | 方法 | 路径 | 函数名 | 文件 | 说明 |
|------|------|------|------|--------|------|------|
| 1 | Analytics | POST | /analytics/events | log_analytics_events | api/user/analytics.py | 批量记录分析事件 |
| 2 | Billing | GET | /billing/credits | get_credits | api/user/billing.py | 获取积分余额 |
| 3 | Billing | GET | /billing/transactions | get_transactions | api/user/billing.py | 获取交易历史 |
| 4 | Billing | GET | /billing/can-afford | check_can_afford | api/user/billing.py | 检查是否能负担操作 |
| 5 | Billing | POST | /billing/credits/add | add_credits | api/user/billing.py | 添加积分 (Admin Only) |
| 6 | Campaigns | GET | /campaigns/active | get_active_campaigns | api/user/campaigns.py | 获取活跃活动列表 |
| 7 | Campaigns | POST | /campaigns/{campaign_id}/claim | claim_campaign | api/user/campaigns.py | 领取活动奖励 |
| 8 | Campaigns | POST | /campaigns/{campaign_id}/dismiss | dismiss_notification | api/user/campaigns.py | 关闭活动通知 |
| 9 | Config | GET | /config | list_configs | api/user/config.py | 获取所有公开配置 |
| 10 | Config | GET | /config/group/{group_name} | get_group | api/user/config.py | 按组获取配置 |
| 11 | Config | GET | /config/{key} | get_config | api/user/config.py | 获取单个配置 |
| 12 | Experiments | POST | /experiments/{experiment_key}/assign | assign_variant | api/user/experiments.py | 分配实验组 |
| 13 | Experiments | POST | /experiments/{experiment_key}/exposure | record_exposure | api/user/experiments.py | 记录曝光事件 |
| 14 | Experiments | POST | /experiments/{experiment_key}/conversion | record_conversion | api/user/experiments.py | 记录转化事件 |
| 15 | Experiments | GET | /experiments/user/{user_identifier} | get_user_experiments | api/user/experiments.py | 获取用户实验列表 |
| 16 | Export | GET | /export/projects/{project_id}/pdf | export_pdf | api/user/export.py | 同步导出PDF |
| 17 | Export | GET | /export/projects/{project_id}/preview | export_preview | api/user/export.py | 生成预览图 |
| 18 | Export | GET | /export/projects/{project_id}/zip | export_zip | api/user/export.py | 同步导出ZIP |
| 19 | Export | POST | /export/projects/{project_id}/pdf/async | export_pdf_async | api/user/export.py | 异步导出PDF |
| 20 | Export | POST | /export/projects/{project_id}/zip/async | export_zip_async | api/user/export.py | 异步导出ZIP |
| 21 | Export | POST | /export/zip | batch_export_zip | api/user/export.py | 批量打包导出 (废弃) |
| 22 | Generation Images | POST | /generate/images | generate_images | api/user/generation_images.py | 同步生成图像 |
| 23 | Generation Images | POST | /generate/images/async | generate_images_async | api/user/generation_images.py | 异步生成图像 |
| 24 | Generation PDF | POST | /generate/pdf | generate_minibook_pdf | api/user/generation_pdf.py | 生成折叠式迷你书PDF |
| 25 | Generation Story | POST | /generate/story | generate_story | api/user/generation_story.py | 生成故事结构 |
| 26 | Generation Story | POST | /generate/inspiration | get_inspiration | api/user/generation_story.py | 获取创意灵感 |
| 27 | Generations | GET | /generations/history | get_history | api/user/generations.py | 获取生成历史 |
| 28 | Generations | PATCH | /generations/{generation_id} | update_generation | api/user/generations.py | 更新生成属性 |
| 29 | Generations | POST | /generations/{generation_id}/favorite | toggle_favorite | api/user/generations.py | 切换收藏状态 (废弃) |
| 30 | Generations | DELETE | /generations/batch | clear_history | api/user/generations.py | 清空历史 (废弃) |
| 31 | Generations | DELETE | /generations/{generation_id} | delete_generation | api/user/generations.py | 删除单条生成记录 |
| 32 | Generations | POST | /generations/batch-delete | batch_delete | api/user/generations.py | 批量删除 |
| 33 | Logs | POST | /logs/error | log_error | api/user/logs.py | 单条错误上报 |
| 34 | Logs | POST | /logs/errors | log_errors_batch | api/user/logs.py | 批量错误上报 |
| 35 | Marketplace | GET | /marketplace/listings | list_listings | api/user/marketplace.py | 获取市场商品列表 |
| 36 | Marketplace | GET | /marketplace/listings/{listing_id} | get_listing | api/user/marketplace.py | 获取商品详情 |
| 37 | Marketplace | POST | /marketplace/listings | create_listing | api/user/marketplace.py | 发布商品到市场 |
| 38 | Marketplace | PUT | /marketplace/listings/{listing_id} | update_listing | api/user/marketplace.py | 更新商品 |
| 39 | Marketplace | DELETE | /marketplace/listings/{listing_id} | delete_listing | api/user/marketplace.py | 下架商品 |
| 40 | Marketplace | POST | /marketplace/purchase | purchase_listing | api/user/marketplace.py | 购买商品 |
| 41 | Marketplace | GET | /marketplace/my-listings | get_my_listings | api/user/marketplace.py | 获取我的商品列表 |
| 42 | Marketplace | GET | /marketplace/seller/stats | get_seller_stats | api/user/marketplace.py | 获取卖家统计 |
| 43 | Marketplace | GET | /marketplace/leaderboard | get_leaderboard | api/user/marketplace.py | 获取排行榜 |
| 44 | Marketplace | POST | /marketplace/report | report_listing | api/user/marketplace.py | 举报商品 |
| 45 | Marketplace | GET | /marketplace/my-reports | get_my_reports | api/user/marketplace.py | 获取我的举报记录 |
| 46 | Onboarding | GET | /onboarding/steps | get_steps | api/user/onboarding.py | 获取可用引导步骤 |
| 47 | Onboarding | POST | /onboarding/steps/start | start_step | api/user/onboarding.py | 开始引导步骤 |
| 48 | Onboarding | POST | /onboarding/steps/complete | complete_step | api/user/onboarding.py | 完成引导步骤 |
| 49 | Onboarding | POST | /onboarding/steps/skip | skip_step | api/user/onboarding.py | 跳过引导步骤 |
| 50 | Onboarding | GET | /onboarding/checklist | get_checklist | api/user/onboarding.py | 获取引导清单进度 |
| 51 | Onboarding | GET | /onboarding/health | health_check | api/user/onboarding.py | 健康检查 |
| 52 | Payment | POST | /payment/checkout | create_checkout | api/user/payment.py | 创建Stripe结账会话 |
| 53 | Payment | POST | /payment/portal | create_portal | api/user/payment.py | 获取Stripe账单门户 |
| 54 | Projects | GET | /projects | get_projects | api/user/projects.py | 获取项目列表 |
| 55 | Projects | GET | /projects/dashboard | get_dashboard | api/user/projects.py | 仪表板项目视图 |
| 56 | Projects | GET | /projects/deleted | get_deleted | api/user/projects.py | 获取已删除项目 |
| 57 | Projects | GET | /projects/seller-stats | get_seller_stats | api/user/projects.py | 获取卖家统计 |
| 58 | Projects | POST | /projects | create_project | api/user/projects.py | 创建新项目 |
| 59 | Projects | GET | /projects/{project_id} | get_project | api/user/projects.py | 获取项目详情 |
| 60 | Projects | PUT | /projects/{project_id} | update_project | api/user/projects.py | 更新项目 |
| 61 | Projects | DELETE | /projects/{project_id} | delete_project | api/user/projects.py | 删除项目 |
| 62 | Projects | POST | /projects/{project_id}/restore | restore_project | api/user/projects.py | 恢复已删除项目 |
| 63 | Projects | POST | /projects/{project_id}/duplicate | duplicate_project | api/user/projects.py | 复制项目 |
| 64 | Referrals | POST | /referrals | create_referral | api/user/referrals.py | 创建推荐 |
| 65 | Referrals | GET | /referrals | list_referrals | api/user/referrals.py | 获取推荐列表 |
| 66 | Referrals | GET | /referrals/stats | get_stats | api/user/referrals.py | 获取推荐统计 |
| 67 | Referrals | GET | /referrals/code/{referral_code} | validate_code | api/user/referrals.py | 验证推荐码 |
| 68 | Referrals | POST | /referrals/{referral_id}/complete | complete_referral | api/user/referrals.py | 完成推荐 |
| 69 | Referrals | GET | /referrals/health | health_check | api/user/referrals.py | 健康检查 |
| 70 | Resources | GET | /resources | list_resources | api/user/resources.py | 获取资源列表 |
| 71 | Resources | GET | /resources/types | get_types | api/user/resources.py | 获取资源类型 |
| 72 | Resources | GET | /resources/categories/{type} | get_categories | api/user/resources.py | 获取分类 |
| 73 | Resources | GET | /resources/stickers | get_stickers | api/user/resources.py | 获取贴纸资源 |
| 74 | Resources | GET | /resources/backgrounds | get_backgrounds | api/user/resources.py | 获取背景资源 |
| 75 | Resources | GET | /resources/templates | get_templates | api/user/resources.py | 获取模板资源 |
| 76 | Resources | GET | /resources/{resource_id} | get_resource | api/user/resources.py | 获取单个资源 |
| 77 | Support | POST | /support/ticket | create_ticket | api/user/support.py | 创建工单 |
| 78 | Support | POST | /support/chat | chat | api/user/support.py | AI客服对话 |
| 79 | Support | POST | /support/contact | contact | api/user/support.py | 联系表单 |
| 80 | Support | POST | /support/feedback | submit_feedback | api/user/support.py | 反馈提交 |
| 81 | System Resources | GET | /system_resources | list_system_resources | api/user/system_resources.py | 列出系统资源 |
| 82 | System Resources | GET | /system_resources/stats | get_stats | api/user/system_resources.py | 获取资源统计 |
| 83 | System Resources | GET | /system_resources/{resource_id} | get_system_resource | api/user/system_resources.py | 获取单个系统资源 |
| 84 | System Resources | POST | /system_resources | create_system_resource | api/user/system_resources.py | 创建系统资源 |
| 85 | System Resources | PATCH | /system_resources/{resource_id} | update_system_resource | api/user/system_resources.py | 更新系统资源 |
| 86 | System Resources | POST | /system_resources/{resource_id}/replace | replace_resource_file | api/user/system_resources.py | 替换资源文件 |
| 87 | System Resources | DELETE | /system_resources/{resource_id} | delete_system_resource | api/user/system_resources.py | 删除系统资源 |
| 88 | System Resources | POST | /system_resources/batch | batch_operation | api/user/system_resources.py | 批量操作 |
| 89 | System Resources | GET | /system_resources/{resource_id}/audit-log | get_audit_log | api/user/system_resources.py | 获取审计日志 |
| 90 | Tasks | GET | /tasks/{task_id} | get_task | api/user/tasks.py | 查询任务状态 |
| 91 | Tasks | POST | /tasks/{task_id}/cancel | cancel_task | api/user/tasks.py | 取消任务 |
| 92 | Templates | GET | /templates/asset | list_asset_templates | api/user/templates.py | 列出资产模板 |
| 93 | Templates | POST | /templates/asset | create_asset_template | api/user/templates.py | 创建资产模板 |
| 94 | Templates | PUT | /templates/asset/{template_id} | update_asset_template | api/user/templates.py | 更新资产模板 |
| 95 | Templates | DELETE | /templates/asset/{template_id} | delete_asset_template | api/user/templates.py | 删除资产模板 |
| 96 | Templates | POST | /templates/asset/{template_id}/use | use_asset_template | api/user/templates.py | 使用资产模板 |
| 97 | Templates | GET | /templates/page | list_page_templates | api/user/templates.py | 列出页面模板 |
| 98 | Templates | POST | /templates/page | create_page_template | api/user/templates.py | 创建页面模板 |
| 99 | Templates | PUT | /templates/page/{template_id} | update_page_template | api/user/templates.py | 更新页面模板 |
| 100 | Templates | DELETE | /templates/page/{template_id} | delete_page_template | api/user/templates.py | 删除页面模板 |
| 101 | Templates | POST | /templates/page/{template_id}/use | use_page_template | api/user/templates.py | 使用页面模板 |
| 102 | Themes | GET | /themes/current | get_current_theme | api/user/themes.py | 获取当前主题 |
| 103 | Tools | POST | /tools/pdf-preview | pdf_preview | api/user/tools.py | PDF预览生成 |
| 104 | Tools | POST | /tools/ocr | ocr_text | api/user/tools.py | OCR文字识别 |
| 105 | User Assets | GET | /user_assets | list_user_assets | api/user/user_assets.py | 获取我的资产列表 |
| 106 | User Assets | POST | /user_assets | upload_asset | api/user/user_assets.py | 上传资产 |
| 107 | User Assets | DELETE | /user_assets/{asset_id} | delete_asset | api/user/user_assets.py | 删除资产 |
| 108 | User Assets | POST | /user_assets/from-url | add_asset_from_url | api/user/user_assets.py | 从URL添加资产 |
| 109 | User Assets | GET | /user_assets/check-url | check_url | api/user/user_assets.py | URL检查 |
| 110 | User Assets | POST | /user_assets/{asset_id}/increment-usage | increment_usage | api/user/user_assets.py | 使用次数增加 |
| 111 | User Assets | GET | /user_assets/dashboard | get_dashboard | api/user/user_assets.py | 资产Dashboard |
| 112 | User Assets | GET | /user_assets/seller-stats | get_seller_stats | api/user/user_assets.py | 卖家统计 |
| 113 | User Assets | GET | /user_assets/deleted | get_deleted | api/user/user_assets.py | 已删除资产 |
| 114 | User Assets | POST | /user_assets/{asset_id}/restore | restore_asset | api/user/user_assets.py | 恢复资产 |
| 115 | User Profile | GET | /user_profile/me | get_me | api/user/user_profile.py | 获取当前用户信息 |
| 116 | User Profile | GET | /user_profile/history | get_history | api/user/user_profile.py | 获取操作历史 |
| 117 | User Profile | GET | /user_profile/purchases | get_purchases | api/user/user_profile.py | 获取购买记录 |
| 118 | User Profile | GET | /user_profile/notifications | get_notifications | api/user/user_profile.py | 获取通知列表 |
| 119 | User Profile | POST | /user_profile/notifications/{id}/read | mark_notification_read | api/user/user_profile.py | 标记通知为已读 |
| 120 | User Profile | POST | /user_profile/notifications/read-all | mark_all_read | api/user/user_profile.py | 标记所有通知为已读 |
| 121 | User Profile | PUT | /user_profile/timezone | update_timezone | api/user/user_profile.py | 更新时区 |
| 122 | Webhooks | POST | /webhooks/clerk | clerk_webhook | api/user/webhooks.py | Clerk Webhook处理 |
| 123 | Webhooks | POST | /webhooks/stripe | stripe_webhook | api/user/webhooks.py | Stripe Webhook处理 |

---

## 1. Analytics 分析

### POST `/analytics/events`

批量记录分析事件

**限流**: 60 req/min

**请求体**:
```json
{
  "events": [
    {
      "event_type": "page_view",
      "event_data": {
        "page": "/editor",
        "duration": 120
      }
    }
  ]
}
```

**响应**:
```json
{
  "success": true,
  "events_recorded": 1
}
```

---

## 2. Billing 计费管理

### GET `/billing/credits`

获取积分余额

**响应**:
```json
{
  "monthly_credits": 450,
  "permanent_credits": 50,
  "total_credits": 500,
  "tier": "t2"
}
```

---

### GET `/billing/transactions`

获取交易历史

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `limit` | int | 20 | 每页数量 |
| `offset` | int | 0 | 偏移量 |
| `tx_type` | string | - | 交易类型筛选 |

**响应**:
```json
{
  "transactions": [
    {
      "id": "tx_xxx",
      "amount": -5,
      "bucket": "monthly",
      "type": "ai_generation",
      "description": "AI 图像生成",
      "created_at": "2026-01-11T12:00:00Z"
    }
  ],
  "total_count": 100
}
```

---

### GET `/billing/can-afford`

检查是否能负担操作

**参数** (二选一):
| 参数 | 类型 | 说明 |
|------|------|------|
| `amount` | int | 直接指定积分数量 |
| `operation` | string | 操作类型: `ai_image`, `ai_text`, `smart_scan` |

**响应**:
```json
{
  "can_afford": true,
  "current_balance": 500,
  "required_amount": 5
}
```

---

### POST `/billing/credits/add`

添加积分 (Admin Only)

**限流**: 10 req/min

**请求体**:
```json
{
  "amount": 100,
  "bucket": "permanent",
  "reason": "补偿奖励"
}
```

**响应**:
```json
{
  "success": true,
  "new_balance": {
    "monthly": 200,
    "permanent": 150,
    "total": 350
  }
}
```

---

## 3. Campaigns 活动

### GET `/campaigns/active`

获取活跃活动列表

**响应**:
```json
{
  "campaigns": [
    {
      "id": "uuid-xxx",
      "name": "新年活动",
      "description": "新年积分赠送",
      "reward_type": "credits_permanent",
      "reward_value": 50,
      "end_at": "2026-01-31T23:59:59Z"
    }
  ]
}
```

---

### POST `/campaigns/{campaign_id}/claim`

领取活动奖励

**响应**:
```json
{
  "success": true,
  "reward": {
    "type": "credits_permanent",
    "value": 50
  },
  "new_balance": 150
}
```

**错误**:
- `400`: 已领取或活动已结束
- `404`: 活动不存在

---

### POST `/campaigns/{campaign_id}/dismiss`

关闭活动通知

**响应**:
```json
{
  "success": true
}
```

---

## 4. Config 配置

### GET `/config`

获取所有公开配置

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `category` | string | 可选,按类别筛选 |

**响应**:
```json
{
  "configs": [
    {
      "key": "feature.new_editor.enabled",
      "value": true,
      "category": "feature"
    }
  ],
  "total": 15
}
```

---

### GET `/config/group/{group_name}`

按组获取配置

**响应**:
```json
{
  "group": "feature",
  "configs": [ ... ]
}
```

---

### GET `/config/{key}`

获取单个配置

**响应**:
```json
{
  "key": "feature.new_editor.enabled",
  "value": true
}
```

---

## 5. Experiments 实验

### POST `/experiments/{experiment_key}/assign`

分配实验组

**请求体**:
```json
{
  "user_identifier": "user_abc"
}
```

**响应**:
```json
{
  "experiment_key": "new_pricing_page",
  "variant": "treatment",
  "metadata": { ... }
}
```

---

### POST `/experiments/{experiment_key}/exposure`

记录曝光事件

**请求体**:
```json
{
  "user_identifier": "user_abc",
  "variant": "treatment"
}
```

**响应**:
```json
{
  "success": true
}
```

---

### POST `/experiments/{experiment_key}/conversion`

记录转化事件

**请求体**:
```json
{
  "user_identifier": "user_abc",
  "variant": "treatment",
  "metric_key": "purchase",
  "value": 9.90
}
```

**响应**:
```json
{
  "success": true
}
```

---

### GET `/experiments/user/{user_identifier}`

获取用户实验列表

**响应**:
```json
{
  "experiments": [
    {
      "experiment_key": "new_pricing_page",
      "variant": "treatment"
    }
  ]
}
```

---

## 6. Export 导出

### GET `/export/projects/{project_id}/pdf`

同步导出 PDF

**响应**: PDF 文件流

---

### GET `/export/projects/{project_id}/preview`

生成预览图

**响应**: 图片文件流

---

### GET `/export/projects/{project_id}/zip`

同步导出 ZIP

**响应**: ZIP 文件流

---

### POST `/export/projects/{project_id}/pdf/async`

异步导出 PDF

**限流**: 10 req/min

**响应**:
```json
{
  "task_id": "task_xxx",
  "status": "pending",
  "poll_url": "/api/v2/user/tasks/task_xxx"
}
```

**性能提升**: 5.3x (5s → 0.95s)

---

### POST `/export/projects/{project_id}/zip/async`

异步导出 ZIP

**限流**: 10 req/min

**响应**: 同 PDF async

---

### POST `/export/zip` (废弃)

批量打包导出 (已废弃,建议使用 async 版本)

---

## 7. Generation Images AI图片生成

### POST `/generate/images`

同步生成图像

**限流**: 10 req/min

**请求体**:
```json
{
  "prompts": ["一只可爱的猫咪"],
  "num_images": 1,
  "image_size": "square_hd",
  "generation_mode": "fast"
}
```

**响应**:
```json
{
  "image_urls": ["https://..."],
  "balance": {
    "monthly": 445,
    "permanent": 50,
    "total": 495
  },
  "model_used": "flux-schnell",
  "generation_id": "gen_xxx"
}
```

**积分消耗**:
- 基础: 5 积分/张
- 带参考图: +2 积分/张

**模型选择**:
- Free/Starter: `flux-schnell`
- Pro: `flux-dev`

---

### POST `/generate/images/async`

异步生成图像

**限流**: 10 req/min

**请求体**: 同上

**响应**:
```json
{
  "task_id": "task_xxx",
  "status": "pending",
  "credits_charged": 5,
  "poll_url": "/api/v2/user/tasks/task_xxx"
}
```

---

## 8. Generation PDF PDF生成

### POST `/generate/pdf`

生成折叠式迷你书 PDF (免费)

**请求体**:
```json
{
  "project_id": "proj_xxx",
  "image_urls": ["https://...", ...],
  "texts": ["封面文字", "第一页...", ...],
  "current_hash": "abc123"
}
```

**响应**: PDF 文件流

---

## 9. Generation Story AI故事生成

### POST `/generate/story`

生成故事结构

**限流**: 5 req/min

**请求体**:
```json
{
  "topic": "小兔子学勇气"
}
```

**响应**:
```json
{
  "pages": [
    {
      "page_number": 1,
      "text": "从前有一只小兔子...",
      "image_prompt": "一只可爱的小兔子在森林里"
    }
  ]
}
```

**积分消耗**: 1 积分

---

### POST `/generate/inspiration`

获取创意灵感 (免费)

**请求体**:
```json
{
  "category": "character"
}
```

**category 可选值**: `all`, `character`, `scene`, `story`

**响应**:
```json
{
  "suggestions": [
    "一只穿着太空服的小猫",
    "一个会说话的魔法南瓜"
  ],
  "category": "character",
  "fallback": false
}
```

---

## 10. Generations 生成历史

### GET `/generations/history`

获取生成历史

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `limit` | int | 20 | 每页数量 |
| `offset` | int | 0 | 偏移量 |
| `favorites_only` | bool | false | 仅显示收藏 |

**响应**:
```json
{
  "generations": [
    {
      "id": "gen_xxx",
      "prompt": "一只猫咪",
      "image_url": "https://...",
      "is_favorited": false,
      "created_at": "2026-01-11T00:00:00Z"
    }
  ],
  "total": 100,
  "limit": 20,
  "offset": 0
}
```

---

### PATCH `/generations/{generation_id}`

更新生成属性

**请求体**:
```json
{
  "is_favorited": true
}
```

**响应**:
```json
{
  "success": true,
  "is_favorited": true
}
```

---

### POST `/generations/{generation_id}/favorite` (废弃)

切换收藏状态 (建议使用 PATCH)

---

### DELETE `/generations/batch` (废弃)

清空历史 (已废弃,建议使用 batch-delete)

---

### DELETE `/generations/{generation_id}`

删除单条生成记录

**响应**:
```json
{
  "success": true,
  "deleted": true
}
```

---

### POST `/generations/batch-delete`

批量删除

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `keep_favorites` | bool | true | 保留收藏 |

**响应**:
```json
{
  "success": true,
  "deleted_count": 45
}
```

---

## 11. Logs 日志

### POST `/logs/error`

单条错误上报

**请求体**:
```json
{
  "level": "error",
  "message": "Failed to load resource",
  "stacktrace": "...",
  "user_agent": "Mozilla/5.0...",
  "url": "/editor"
}
```

**响应**:
```json
{
  "success": true,
  "log_id": "log_xxx"
}
```

---

### POST `/logs/errors`

批量错误上报

**请求体**:
```json
{
  "errors": [
    {
      "level": "error",
      "message": "..."
    }
  ]
}
```

**响应**:
```json
{
  "success": true,
  "logged_count": 2
}
```

---

## 12. Marketplace 市场

### GET `/marketplace/listings`

获取市场商品列表

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `featured` | bool | false | 仅精选 |
| `resource_type` | string | - | 资源类型筛选 |
| `sort` | string | latest | 排序方式 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 |

**sort 可选值**: `latest`, `popular`, `price_low`, `price_high`

**响应**:
```json
{
  "items": [
    {
      "id": "listing_xxx",
      "title": "可爱动物贴纸包",
      "description": "包含 20 个可爱动物贴纸",
      "thumbnail_url": "https://...",
      "resource_type": "sticker",
      "price_credits": 50,
      "allowed_tiers": ["t2", "t3"],
      "seller": {
        "id": "user_xxx",
        "username": "creator"
      },
      "download_count": 120
    }
  ],
  "total": 500,
  "offset": 0,
  "limit": 20
}
```

---

### GET `/marketplace/listings/{listing_id}`

获取商品详情

**响应**:
```json
{
  "id": "listing_xxx",
  "title": "可爱动物贴纸包",
  "description": "...",
  "resource_url": "https://...",
  "price_credits": 50,
  "allowed_tiers": ["t2", "t3"],
  "is_purchased": false,
  "can_purchase": true
}
```

---

### POST `/marketplace/listings`

发布商品到市场

**请求体**:
```json
{
  "title": "我的贴纸包",
  "description": "精心设计的贴纸",
  "thumbnail_url": "https://...",
  "resource_url": "https://...",
  "resource_type": "sticker",
  "price_credits": 30,
  "allowed_tiers": ["t2", "t3"],
  "submit_for_review": true
}
```

**权限**:
- t2: 仅能发布免费资源
- t3: 可发布任意价格资源

**响应**:
```json
{
  "listing_id": "listing_xxx",
  "moderation_status": "pending",
  "message": "商品已提交审核"
}
```

---

### PUT `/marketplace/listings/{listing_id}`

更新商品

**请求体** (所有字段可选):
```json
{
  "title": "更新后的标题",
  "price_credits": 40
}
```

**响应**:
```json
{
  "success": true,
  "listing": { ... }
}
```

---

### DELETE `/marketplace/listings/{listing_id}`

下架商品

**响应**:
```json
{
  "success": true,
  "listing_id": "listing_xxx"
}
```

---

### POST `/marketplace/purchase`

购买商品

**限流**: 10 req/min

**请求体**:
```json
{
  "listing_id": "listing_xxx"
}
```

**响应**:
```json
{
  "success": true,
  "purchase_id": "purchase_xxx",
  "resource_url": "https://...",
  "new_balance": 450
}
```

**错误**:
- `402`: 积分不足
- `403`: 等级不足
- `409`: 已购买

---

### GET `/marketplace/my-listings`

获取我的商品列表

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 |

**响应**:
```json
{
  "listings": [ ... ],
  "total": 5,
  "offset": 0,
  "limit": 20
}
```

---

### GET `/marketplace/seller/stats`

获取卖家统计

**响应**:
```json
{
  "total_listings": 5,
  "total_sales": 120,
  "total_revenue": 6000,
  "unique_buyers": 85
}
```

---

### GET `/marketplace/leaderboard`

获取排行榜

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `sort_by` | string | downloads | 排序方式 |
| `limit` | int | 10 | 最多返回数量 |

**sort_by 可选值**: `downloads`, `revenue`, `ratings`

**响应**:
```json
{
  "leaderboard": [
    {
      "seller_id": "user_xxx",
      "username": "creator",
      "total_downloads": 5200,
      "total_revenue": 125000
    }
  ]
}
```

---

### POST `/marketplace/report`

举报商品

**请求体**:
```json
{
  "listing_id": "listing_xxx",
  "reason": "inappropriate_content",
  "description": "包含不适宜内容"
}
```

**reason 可选值**: `inappropriate_content`, `copyright_violation`, `spam`, `other`

**响应**:
```json
{
  "success": true,
  "report_id": "report_xxx"
}
```

---

### GET `/marketplace/my-reports`

获取我的举报记录

**响应**:
```json
{
  "reports": [
    {
      "id": "report_xxx",
      "listing_id": "listing_xxx",
      "reason": "inappropriate_content",
      "status": "pending",
      "created_at": "2026-01-11T10:00:00Z"
    }
  ]
}
```

---

## 13. Onboarding 新手引导

### GET `/onboarding/steps`

获取可用引导步骤

**响应**:
```json
{
  "steps": [
    {
      "id": "uuid-xxx",
      "step_key": "create_first_project",
      "title": "创建第一个项目",
      "description": "开始你的第一个迷你书项目",
      "order": 1,
      "status": "pending",
      "min_tier": "t1"
    }
  ]
}
```

---

### POST `/onboarding/steps/start`

开始引导步骤

**请求体**:
```json
{
  "step_key": "create_first_project"
}
```

**响应**:
```json
{
  "success": true,
  "step": { ... }
}
```

---

### POST `/onboarding/steps/complete`

完成引导步骤

**请求体**:
```json
{
  "step_key": "create_first_project"
}
```

**响应**:
```json
{
  "success": true,
  "reward": {
    "type": "credits_permanent",
    "value": 10
  }
}
```

---

### POST `/onboarding/steps/skip`

跳过引导步骤

**请求体**:
```json
{
  "step_key": "create_first_project"
}
```

**响应**:
```json
{
  "success": true
}
```

---

### GET `/onboarding/checklist`

获取引导清单进度

**响应**:
```json
{
  "total_steps": 10,
  "completed_steps": 3,
  "skipped_steps": 1,
  "pending_steps": 6,
  "completion_percentage": 30.0
}
```

---

### GET `/onboarding/health`

健康检查

**响应**:
```json
{
  "status": "healthy"
}
```

---

## 14. Payment 支付

### POST `/payment/checkout`

创建 Stripe 结账会话

**限流**: 5 req/min

**请求体**:
```json
{
  "plan_type": "t2"
}
```

**plan_type 可选值**: `t2`, `t3`, `credits_100`, `credits_500`, `credits_2000`

**响应**:
```json
{
  "url": "https://checkout.stripe.com/...",
  "discount_applied": false
}
```

---

### POST `/payment/portal`

获取 Stripe 账单门户

**限流**: 10 req/min

**响应**:
```json
{
  "url": "https://billing.stripe.com/..."
}
```

**错误**:
- `400`: 无订阅用户

---

## 15. Projects 项目管理

### GET `/projects`

获取项目列表

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 |
| `search` | string | - | 搜索关键词 |
| `include_canvas_data` | bool | true | 是否包含画布数据 |

**响应**:
```json
{
  "items": [
    {
      "id": "proj_xxx",
      "title": "我的迷你书",
      "thumbnail_url": "https://...",
      "canvas_data": { ... },
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-02T00:00:00Z"
    }
  ],
  "total": 15,
  "offset": 0,
  "limit": 20
}
```

---

### GET `/projects/dashboard`

仪表板项目视图

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `view` | string | all | 视图类型 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 |

**view 可选值**: `all`, `bought`, `selling`

**响应**:
```json
{
  "items": [ ... ],
  "total_count": 50
}
```

---

### GET `/projects/deleted`

获取已删除项目

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 |

**响应**:
```json
{
  "deleted_projects": [
    {
      "id": "proj_xxx",
      "title": "已删除项目",
      "deleted_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

---

### GET `/projects/seller-stats`

获取卖家统计

**响应**:
```json
{
  "total_selling": 5,
  "total_sales": 120,
  "unique_buyers": 45
}
```

---

### POST `/projects`

创建新项目

**限流**: 20 req/min

**请求体**:
```json
{
  "title": "我的新迷你书",
  "canvas_data": { ... }
}
```

**响应**:
```json
{
  "id": "proj_xxx",
  "title": "我的新迷你书",
  "canvas_data": { ... },
  "created_at": "2026-01-11T00:00:00Z"
}
```

**错误**:
- `403`: 超出项目限制 (Free=1, Starter=20, Pro=200)

---

### GET `/projects/{project_id}`

获取项目详情

**响应**:
```json
{
  "id": "proj_xxx",
  "title": "我的迷你书",
  "canvas_data": { ... },
  "thumbnail_url": "https://...",
  "created_at": "2026-01-01T00:00:00Z"
}
```

---

### PUT `/projects/{project_id}`

更新项目

**请求体** (所有字段可选):
```json
{
  "title": "更新后的标题",
  "canvas_data": { ... },
  "thumbnail_url": "https://...",
  "used_listing_ids": ["listing_1", "listing_2"]
}
```

**响应**:
```json
{
  "status": "success",
  "locked_elements": []
}
```

---

### DELETE `/projects/{project_id}`

删除项目

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `permanent` | bool | false | 是否永久删除 |

**响应**:
```json
{
  "status": "success",
  "stage": 1
}
```

**删除阶段**: Stage 1 = 软删（可恢复），Stage 2 = 永久隐藏

---

### POST `/projects/{project_id}/restore`

恢复已删除项目

**响应**:
```json
{
  "status": "success",
  "project": { ... }
}
```

---

### POST `/projects/{project_id}/duplicate`

复制项目

**响应**:
```json
{
  "id": "proj_new_xxx",
  "title": "我的迷你书 (副本)",
  ...
}
```

---

## 16. Referrals 推荐系统

### POST `/referrals`

创建推荐

**响应**:
```json
{
  "success": true,
  "referral": {
    "id": "uuid-xxx",
    "referral_code": "abc123...",
    "status": "pending"
  }
}
```

---

### GET `/referrals`

获取推荐列表

**响应**:
```json
{
  "referrals": [
    {
      "id": "uuid-xxx",
      "referral_code": "abc123...",
      "status": "completed",
      "referred_user_id": "user_def",
      "reward_issued": true,
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

---

### GET `/referrals/stats`

获取推荐统计

**响应**:
```json
{
  "total_referrals": 15,
  "completed_referrals": 8,
  "pending_referrals": 7,
  "total_rewards": 400
}
```

---

### GET `/referrals/code/{referral_code}`

验证推荐码

**响应**:
```json
{
  "valid": true,
  "referrer_id": "user_abc"
}
```

---

### POST `/referrals/{referral_id}/complete`

完成推荐

**响应**:
```json
{
  "success": true,
  "reward": {
    "type": "credits_permanent",
    "value": 50
  }
}
```

---

### GET `/referrals/health`

健康检查

**响应**:
```json
{
  "status": "healthy"
}
```

---

## 17. Resources 系统资源

### GET `/resources`

获取资源列表

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `resource_type` | string | - | 资源类型 |
| `category` | string | - | 分类 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 |

**响应**:
```json
{
  "items": [
    {
      "id": "resource_xxx",
      "resource_type": "sticker",
      "category": "animals",
      "url": "https://...",
      "thumbnail_url": "https://...",
      "name": "Cute Cat"
    }
  ],
  "total": 500,
  "offset": 0,
  "limit": 20
}
```

---

### GET `/resources/types`

获取资源类型

**响应**:
```json
{
  "types": ["sticker", "background", "template"]
}
```

---

### GET `/resources/categories/{type}`

获取分类

**响应**:
```json
{
  "categories": [
    {
      "id": "cat_xxx",
      "name": "Animals",
      "resource_count": 120
    }
  ]
}
```

---

### GET `/resources/stickers`

获取贴纸资源

**参数**: 同 `/resources`

**响应**: 同 `/resources`

---

### GET `/resources/backgrounds`

获取背景资源

**参数**: 同 `/resources`

**响应**: 同 `/resources`

---

### GET `/resources/templates`

获取模板资源

**参数**: 同 `/resources`

**响应**: 同 `/resources`

---

### GET `/resources/{resource_id}`

获取单个资源

**响应**:
```json
{
  "id": "resource_xxx",
  "resource_type": "sticker",
  "url": "https://...",
  "name": "Cute Cat",
  "description": "A cute cat sticker"
}
```

---

## 18. Support 客服支持

### POST `/support/ticket`

创建工单

**请求体**:
```json
{
  "subject": "无法导出PDF",
  "description": "点击导出按钮后没有反应",
  "category": "technical"
}
```

**响应**:
```json
{
  "success": true,
  "ticket_id": "ticket_xxx"
}
```

---

### POST `/support/chat`

AI客服对话

**请求体**:
```json
{
  "message": "如何导出PDF?"
}
```

**响应**:
```json
{
  "reply": "您可以在编辑器右上角找到导出按钮..."
}
```

---

### POST `/support/contact`

联系表单

**请求体**:
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "message": "我想咨询..."
}
```

**响应**:
```json
{
  "success": true,
  "message": "感谢您的留言，我们会尽快回复"
}
```

---

### POST `/support/feedback`

反馈提交

**请求体**:
```json
{
  "type": "feature_request",
  "title": "希望添加深色模式",
  "description": "..."
}
```

**响应**:
```json
{
  "success": true,
  "feedback_id": "feedback_xxx"
}
```

---

## 19. System Resources 系统资源管理

### GET `/system_resources`

列出系统资源

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `resource_type` | string | - | 资源类型 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 |

**响应**:
```json
{
  "items": [ ... ],
  "total": 150,
  "offset": 0,
  "limit": 20
}
```

---

### GET `/system_resources/stats`

获取资源统计

**响应**:
```json
{
  "total_resources": 150,
  "by_type": {
    "sticker": 80,
    "background": 50,
    "template": 20
  }
}
```

---

### GET `/system_resources/{resource_id}`

获取单个系统资源

**响应**: 同 `/resources/{resource_id}`

---

### POST `/system_resources`

创建系统资源

**请求体**:
```json
{
  "resource_type": "sticker",
  "url": "https://...",
  "name": "New Sticker"
}
```

**响应**:
```json
{
  "success": true,
  "resource": { ... }
}
```

---

### PATCH `/system_resources/{resource_id}`

更新系统资源

**请求体** (所有字段可选):
```json
{
  "name": "Updated Name",
  "is_active": true
}
```

**响应**:
```json
{
  "success": true,
  "resource": { ... }
}
```

---

### POST `/system_resources/{resource_id}/replace`

替换资源文件

**请求体**:
```json
{
  "url": "https://new-url..."
}
```

**响应**:
```json
{
  "success": true
}
```

---

### DELETE `/system_resources/{resource_id}`

删除系统资源

**响应**:
```json
{
  "success": true,
  "resource_id": "resource_xxx"
}
```

---

### POST `/system_resources/batch`

批量操作

**请求体**:
```json
{
  "action": "activate",
  "resource_ids": ["res_1", "res_2"]
}
```

**action 可选值**: `activate`, `deactivate`, `delete`

**响应**:
```json
{
  "success": true,
  "affected_count": 2
}
```

---

### GET `/system_resources/{resource_id}/audit-log`

获取审计日志

**响应**:
```json
{
  "logs": [
    {
      "action": "updated",
      "admin_id": "admin_abc",
      "timestamp": "2026-01-11T10:00:00Z",
      "changes": { ... }
    }
  ]
}
```

---

## 20. Tasks 任务

### GET `/tasks/{task_id}`

查询任务状态

**响应**:
```json
{
  "task_id": "task_xxx",
  "status": "completed",
  "result": {
    "download_url": "https://..."
  },
  "created_at": "2026-01-11T10:00:00Z",
  "completed_at": "2026-01-11T10:00:05Z"
}
```

**status 可能值**: `pending`, `running`, `completed`, `failed`

---

### POST `/tasks/{task_id}/cancel`

取消任务

**响应**:
```json
{
  "success": true,
  "status": "cancelled"
}
```

---

## 21. Templates 模板

### GET `/templates/asset`

列出资产模板

**响应**:
```json
{
  "templates": [
    {
      "id": "template_xxx",
      "name": "My Asset Template",
      "style": "modern",
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

---

### POST `/templates/asset`

创建资产模板

**请求体**:
```json
{
  "name": "My Asset Template",
  "style": "modern",
  "template_data": { ... }
}
```

**响应**:
```json
{
  "success": true,
  "template": { ... }
}
```

---

### PUT `/templates/asset/{template_id}`

更新资产模板

**请求体** (所有字段可选):
```json
{
  "name": "Updated Name",
  "template_data": { ... }
}
```

**响应**:
```json
{
  "success": true,
  "template": { ... }
}
```

---

### DELETE `/templates/asset/{template_id}`

删除资产模板

**响应**:
```json
{
  "success": true,
  "template_id": "template_xxx"
}
```

---

### POST `/templates/asset/{template_id}/use`

使用资产模板

**响应**:
```json
{
  "success": true,
  "instance_data": { ... }
}
```

---

### GET `/templates/page`

列出页面模板

**响应**: 同 `/templates/asset`

---

### POST `/templates/page`

创建页面模板

**请求体**: 同 `/templates/asset`

**响应**: 同 `/templates/asset`

---

### PUT `/templates/page/{template_id}`

更新页面模板

**请求体**: 同 `/templates/asset/{template_id}`

**响应**: 同 `/templates/asset/{template_id}`

---

### DELETE `/templates/page/{template_id}`

删除页面模板

**响应**: 同 `/templates/asset/{template_id}`

---

### POST `/templates/page/{template_id}/use`

使用页面模板

**响应**: 同 `/templates/asset/{template_id}/use`

---

## 22. Themes 主题

### GET `/themes/current`

获取当前主题

**响应**:
```json
{
  "theme": {
    "id": "theme_xxx",
    "name": "春节主题",
    "start_date": "2026-02-01",
    "end_date": "2026-02-28",
    "assets": {
      "background": "https://...",
      "decorations": [ ... ]
    }
  }
}
```

---

## 23. Tools 工具

### POST `/tools/pdf-preview`

PDF预览生成

**限流**: 10 req/min

**请求体**: FormData with PDF file

**响应**: 图片文件流

---

### POST `/tools/ocr`

OCR文字识别

**限流**: 10 req/min

**请求体**: FormData with image file

**响应**:
```json
{
  "text": "识别出的文字内容...",
  "confidence": 0.95
}
```

**积分消耗**: 10 积分

---

## 24. User Assets 用户资产

### GET `/user_assets`

获取我的资产列表

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `asset_type` | string | - | 资产类型 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 |

**响应**:
```json
{
  "assets": [
    {
      "id": "asset_xxx",
      "asset_type": "sticker",
      "url": "https://...",
      "thumbnail_url": "https://...",
      "name": "My Sticker",
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "total": 45,
  "offset": 0,
  "limit": 20
}
```

---

### POST `/user_assets`

上传资产

**限流**: 20 req/min

**请求体**: FormData with file

**响应**:
```json
{
  "success": true,
  "asset": {
    "id": "asset_xxx",
    "url": "https://...",
    "asset_type": "sticker"
  }
}
```

---

### DELETE `/user_assets/{asset_id}`

删除资产

**响应**:
```json
{
  "success": true,
  "asset_id": "asset_xxx"
}
```

---

### POST `/user_assets/from-url`

从URL添加资产

**请求体**:
```json
{
  "url": "https://example.com/image.png",
  "asset_type": "sticker"
}
```

**响应**:
```json
{
  "success": true,
  "asset": { ... }
}
```

**SSRF 防护**: URL 白名单验证

---

### GET `/user_assets/check-url`

URL检查

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `url` | string | 要检查的URL |

**响应**:
```json
{
  "valid": true,
  "url": "https://..."
}
```

---

### POST `/user_assets/{asset_id}/increment-usage`

使用次数增加

**响应**:
```json
{
  "success": true,
  "usage_count": 15
}
```

---

### GET `/user_assets/dashboard`

资产Dashboard

**响应**:
```json
{
  "total_assets": 45,
  "by_type": {
    "sticker": 25,
    "background": 15,
    "template": 5
  },
  "total_usage": 250
}
```

---

### GET `/user_assets/seller-stats`

卖家统计

**响应**:
```json
{
  "total_downloads": 520,
  "total_revenue": 2600
}
```

---

### GET `/user_assets/deleted`

已删除资产

**响应**:
```json
{
  "assets": [
    {
      "id": "asset_xxx",
      "name": "Deleted Asset",
      "deleted_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

---

### POST `/user_assets/{asset_id}/restore`

恢复资产

**响应**:
```json
{
  "success": true,
  "asset": { ... }
}
```

---

## 25. User Profile 用户档案

### GET `/user_profile/me`

获取当前用户信息

**响应**:
```json
{
  "id": "user_xxx",
  "email": "user@example.com",
  "username": "username",
  "avatar_url": "https://...",
  "first_name": "John",
  "last_name": "Doe",
  "tier": "t2",
  "credits_monthly": 450,
  "credits_permanent": 50,
  "credits_total": 500,
  "is_member": true,
  "subscription_status": "active",
  "timezone": "America/New_York",
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### GET `/user_profile/history`

获取操作历史

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 |

**响应**:
```json
{
  "items": [
    {
      "id": "hist_xxx",
      "action": "project_created",
      "details": { ... },
      "created_at": "2026-01-11T10:00:00Z"
    }
  ],
  "total": 100,
  "offset": 0,
  "limit": 20
}
```

---

### GET `/user_profile/purchases`

获取购买记录

**响应**:
```json
{
  "purchases": [
    {
      "id": "purchase_xxx",
      "listing_id": "listing_xxx",
      "listing_title": "可爱动物贴纸包",
      "price_credits": 50,
      "purchased_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

---

### GET `/user_profile/notifications`

获取通知列表

**响应**:
```json
{
  "notifications": [
    {
      "id": "notif_xxx",
      "title": "欢迎加入",
      "content": "您已获得 50 积分",
      "type": "system",
      "is_read": false,
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

---

### POST `/user_profile/notifications/{id}/read`

标记通知为已读

**响应**:
```json
{
  "status": "success"
}
```

---

### POST `/user_profile/notifications/read-all`

标记所有通知为已读

**响应**:
```json
{
  "status": "success",
  "updated_count": 15
}
```

---

### PUT `/user_profile/timezone`

更新时区

**请求体**:
```json
{
  "timezone": "Asia/Shanghai"
}
```

**响应**:
```json
{
  "status": "success",
  "timezone": "Asia/Shanghai"
}
```

**验证**: pytz 时区验证

---

## 26. Webhooks

### POST `/webhooks/clerk`

Clerk Webhook 处理

**请求头**:
```http
svix-id: <event_id>
svix-timestamp: <timestamp>
svix-signature: <signature>
```

**事件处理**:
- `user.created`: 创建用户档案 + 赠送 50 永久积分
- `user.updated`: 更新用户信息
- `session.*`: 记录登录/登出活动

**响应**:
```json
{
  "status": "success",
  "reason": "user_created"
}
```

---

### POST `/webhooks/stripe`

Stripe Webhook 处理

**请求头**:
```http
Stripe-Signature: <signature>
```

**事件处理**:
- `checkout.session.completed`: 订阅启动 / 积分购买
- `invoice.payment_succeeded`: 订阅续费
- `customer.subscription.deleted`: 降级为 Free
- `charge.refunded`: 退款处理

**响应**:
```json
{
  "status": "processed",
  "action": "subscription_started",
  "user_id": "user_xxx"
}
```

---

*文档版本: v3.32*
*最后更新: 2026-01-11*
*更新内容:
- v3.32: 完整记录 123 个 User API 端点
- 包含所有请求参数、响应格式、验证规则和限流配置
- 按 26 个模块分类组织
- DDD 架构合规: 100%
- 测试覆盖率: 65%+*
