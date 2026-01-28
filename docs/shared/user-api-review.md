# User API 完整参考

> **状态**: ✅ Complete
> **版本**: 3.43
> **最后更新**: 2026-01-27
> **总端点数**: 148 个
> **DDD 合规**: 100%
> **测试覆盖率**: 65%+

本文档记录所有 User API 端点的完整信息，包括请求参数、响应格式、验证规则和限流配置。

---

## 目录

1. [Analytics 分析 (1个)](#1-analytics-分析)
2. [Articles 文章 (6个)](#2-articles-文章) **UPDATED**
3. [Billing 计费管理 (4个)](#3-billing-计费管理)
4. [Campaigns 活动 (3个)](#4-campaigns-活动)
5. [Config 配置 (3个)](#5-config-配置)
6. [Experiments 实验 (4个)](#6-experiments-实验)
7. [Feature Flags 功能开关 (4个)](#7-feature-flags-功能开关) **NEW**
8. [Export 导出 (6个)](#8-export-导出)
9. [Generation Images AI图片生成 (2个)](#9-generation-images-ai图片生成)
10. [Generation PDF PDF生成 (1个)](#10-generation-pdf-pdf生成)
11. [Generation Story AI故事生成 (2个)](#11-generation-story-ai故事生成)
12. [Generations 生成历史 (6个)](#12-generations-生成历史)
13. [Logs 日志 (2个)](#13-logs-日志)
14. [Marketplace 市场 (11个)](#14-marketplace-市场)
15. [Onboarding 新手引导 (6个)](#15-onboarding-新手引导)
16. [Payment 支付 (2个)](#16-payment-支付)
17. [Pages 静态页面内容 (2个)](#17-pages-静态页面内容) **NEW**
18. [Projects 项目管理 (13个)](#18-projects-项目管理)
19. [Referrals 推荐系统 (6个)](#19-referrals-推荐系统)
20. [Resources 系统资源 (4个)](#20-resources-系统资源)
21. [Seller 卖家统计 (1个)](#21-seller-卖家统计) **NEW**
22. [Support 客服支持 (4个)](#22-support-客服支持)
23. [System Resources 系统资源管理 (9个)](#23-system-resources-系统资源管理)
24. [Tasks 任务 (2个)](#24-tasks-任务)
25. [Templates 模板 (10个)](#25-templates-模板)
26. [Themes 主题 (1个)](#26-themes-主题)
27. [Tools 工具 (2个)](#27-tools-工具)
28. [User Assets 用户资产 (13个)](#28-user-assets-用户资产)
29. [User Profile 用户档案 (7个)](#29-user-profile-用户档案)
30. [Webhooks (2个)](#30-webhooks)
31. [Workspaces 工作区 (6个)](#31-workspaces-工作区) **NEW v3.43**
32. [Tags 标签系统 (6个)](#32-tags-标签系统) **NEW v3.43**
33. [Project Tags 项目标签 (4个)](#33-project-tags-项目标签) **NEW v3.43**
34. [Asset Tags 素材标签 (4个)](#34-asset-tags-素材标签) **NEW v3.43**
35. [Folders 文件夹 (6个)](#35-folders-文件夹) **NEW v3.33**

---

## 📋 接口总览 (162个)

| 序号 | 模块 | 方法 | 路径 | 函数名 | 文件 | 说明 |
|------|------|------|------|--------|------|------|
| 1 | Analytics | POST | /analytics/events | log_analytics_events | api/user/analytics.py | 批量记录分析事件 |
| 2 | Articles | GET | /articles | list_articles | api/user/articles.py | 获取已发布文章列表 |
| 3 | Articles | GET | /articles/featured | get_featured_articles | api/user/articles.py | 获取精选文章 (v1.1.0) |
| 4 | Articles | GET | /articles/categories | get_categories | api/user/articles.py | 获取分类及文章数 |
| 5 | Articles | GET | /articles/search | search_articles | api/user/articles.py | 搜索已发布文章 |
| 6 | Articles | GET | /articles/{slug} | get_article | api/user/articles.py | 获取文章详情 |
| 7 | Articles | GET | /articles/{slug}/related | get_related_articles | api/user/articles.py | 获取相关文章 (v1.2.0) |
| 8 | Billing | GET | /billing/credits | get_credits | api/user/billing.py | 获取积分余额 |
| 9 | Billing | GET | /billing/transactions | get_transactions | api/user/billing.py | 获取交易历史 |
| 10 | Billing | GET | /billing/can-afford | check_can_afford | api/user/billing.py | 检查是否能负担操作 |
| 11 | Billing | POST | /billing/credits/add | add_credits | api/user/billing.py | 添加积分 (Admin Only) |
| 12 | Campaigns | GET | /campaigns/active | get_active_campaigns | api/user/campaigns.py | 获取活跃活动列表 |
| 13 | Campaigns | POST | /campaigns/{campaign_id}/claim | claim_campaign | api/user/campaigns.py | 领取活动奖励 |
| 14 | Campaigns | POST | /campaigns/{campaign_id}/dismiss | dismiss_notification | api/user/campaigns.py | 关闭活动通知 |
| 15 | Config | GET | /config | list_configs | api/user/config.py | 获取所有公开配置 |
| 16 | Config | GET | /config/group/{group_name} | get_group | api/user/config.py | 按组获取配置 |
| 17 | Config | GET | /config/{key} | get_config | api/user/config.py | 获取单个配置 |
| 18 | Experiments | POST | /experiments/{experiment_key}/assign | assign_variant | api/user/experiments.py | 分配实验组 |
| 19 | Experiments | POST | /experiments/{experiment_key}/exposure | record_exposure | api/user/experiments.py | 记录曝光事件 |
| 20 | Experiments | POST | /experiments/{experiment_key}/conversion | record_conversion | api/user/experiments.py | 记录转化事件 |
| 21 | Experiments | GET | /experiments/user/{user_identifier} | get_user_experiments | api/user/experiments.py | 获取用户实验列表 |
| 22 |
| 23 | Feature Flags | GET | /feature-flags/client/flags | get_client_flags | api/user/feature_flags.py | 获取当前用户所有 Flag 状态 |
| 24 | Feature Flags | GET | /feature-flags/hierarchy | get_hierarchy | api/user/feature_flags.py | 获取 Flag 层级配置 (v1.1) |
| 25 | Feature Flags | POST | /feature-flags/exposure | record_exposure | api/user/feature_flags.py | 记录 Flag 曝光事件 |
| 26 | Feature Flags | POST | /feature-flags/conversion | record_conversion | api/user/feature_flags.py | 记录转化事件 (实验) |
| 27 | Export | GET | /export/projects/{project_id}/pdf | export_pdf | api/user/export.py | 同步导出PDF |
| 28 | Export | GET | /export/projects/{project_id}/preview | export_preview | api/user/export.py | 生成预览图 |
| 29 | Export | GET | /export/projects/{project_id}/zip | export_zip | api/user/export.py | 同步导出ZIP |
| 30 | Export | POST | /export/projects/{project_id}/pdf/async | export_pdf_async | api/user/export.py | 异步导出PDF |
| 31 | Export | POST | /export/projects/{project_id}/zip/async | export_zip_async | api/user/export.py | 异步导出ZIP |
| 33 | Generation Images | POST | /generate/images | generate_images | api/user/generation_images.py | 同步生成图像 |
| 34 | Generation Images | POST | /generate/images/async | generate_images_async | api/user/generation_images.py | 异步生成图像 |
| 35 | Generation PDF | POST | /generate/pdf | generate_minibook_pdf | api/user/generation_pdf.py | 生成折叠式迷你书PDF |
| 36 | Generation Story | POST | /generate/story | generate_story | api/user/generation_story.py | 生成故事结构 |
| 37 | Generation Story | POST | /generate/inspiration | get_inspiration | api/user/generation_story.py | 获取创意灵感 |
| 38 | Generations | GET | /generations/history | get_history | api/user/generations.py | 获取生成历史 |
| 39 | Generations | PATCH | /generations/{generation_id} | update_generation | api/user/generations.py | 更新生成属性 |
| 42 | Generations | DELETE | /generations/{generation_id} | delete_generation | api/user/generations.py | 删除单条生成记录 |
| 43 | Generations | POST | /generations/batch-delete | batch_delete | api/user/generations.py | 批量删除 |
| 44 | Logs | POST | /logs/error | log_error | api/user/logs.py | 单条错误上报 |
| 45 | Logs | POST | /logs/errors | log_errors_batch | api/user/logs.py | 批量错误上报 |
| 46 | Marketplace | GET | /marketplace/listings | list_listings | api/user/marketplace.py | 获取市场商品列表 |
| 47 | Marketplace | GET | /marketplace/listings/{listing_id} | get_listing | api/user/marketplace.py | 获取商品详情 |
| 48 | Marketplace | POST | /marketplace/listings | create_listing | api/user/marketplace.py | 发布商品到市场 |
| 49 | Marketplace | PUT | /marketplace/listings/{listing_id} | update_listing | api/user/marketplace.py | 更新商品 |
| 50 | Marketplace | DELETE | /marketplace/listings/{listing_id} | delete_listing | api/user/marketplace.py | 下架商品 |
| 51 | Marketplace | POST | /marketplace/purchase | purchase_listing | api/user/marketplace.py | 购买商品 |
| 52 | Marketplace | GET | /marketplace/my-listings | get_my_listings | api/user/marketplace.py | 获取我的商品列表 |
| 54 | Marketplace | GET | /marketplace/leaderboard | get_leaderboard | api/user/marketplace.py | 获取排行榜 |
| 55 | Marketplace | POST | /marketplace/report | report_listing | api/user/marketplace.py | 举报商品 |
| 56 | Marketplace | GET | /marketplace/my-reports | get_my_reports | api/user/marketplace.py | 获取我的举报记录 |
| 57 | Onboarding | GET | /onboarding/steps | get_steps | api/user/onboarding.py | 获取可用引导步骤 |
| 58 | Onboarding | POST | /onboarding/steps/start | start_step | api/user/onboarding.py | 开始引导步骤 |
| 59 | Onboarding | POST | /onboarding/steps/complete | complete_step | api/user/onboarding.py | 完成引导步骤 |
| 60 | Onboarding | POST | /onboarding/steps/skip | skip_step | api/user/onboarding.py | 跳过引导步骤 |
| 61 | Onboarding | GET | /onboarding/checklist | get_checklist | api/user/onboarding.py | 获取引导清单进度 |
| 62 | Onboarding | GET | /onboarding/health | health_check | api/user/onboarding.py | 健康检查 |
| 63 | Payment | POST | /payment/checkout | create_checkout | api/user/payment.py | 创建Stripe结账会话 |
| 64 | Payment | POST | /payment/portal | create_portal | api/user/payment.py | 获取Stripe账单门户 |
| 65 | Projects | GET | /projects | get_projects | api/user/projects.py | 获取项目列表 |
| 66 | Projects | GET | /projects/dashboard | get_dashboard | api/user/projects.py | 仪表板项目视图 |
| 67 | Projects | GET | /projects/deleted | get_deleted | api/user/projects.py | 获取已删除项目 |
| 69 | Projects | POST | /projects | create_project | api/user/projects.py | 创建新项目 |
| 70 | Projects | GET | /projects/{project_id} | get_project | api/user/projects.py | 获取项目详情 |
| 71 | Projects | PUT | /projects/{project_id} | update_project | api/user/projects.py | 更新项目 |
| 72 | Projects | DELETE | /projects/{project_id} | delete_project | api/user/projects.py | 删除项目 |
| 73 | Projects | POST | /projects/{project_id}/restore | restore_project | api/user/projects.py | 恢复已删除项目 |
| 74 | Projects | POST | /projects/{project_id}/duplicate | duplicate_project | api/user/projects.py | 复制项目 |
| 74a | Projects | POST | /projects/{project_id}/move | move_project | api/user/projects.py | 移动到文件夹 (v3.33) |
| 74b | Projects | POST | /projects/{project_id}/star | star_project | api/user/projects.py | 切换收藏状态 (v3.33) |
| 74c | Projects | GET | /projects/folder/{folder_id} | get_projects_by_folder | api/user/projects.py | 获取文件夹内项目 (v3.33) |
| 74d | Projects | GET | /projects/starred | get_starred_projects | api/user/projects.py | 获取收藏项目 (v3.33) |
| 75 | Referrals | POST | /referrals | create_referral | api/user/referrals.py | 创建推荐 |
| 76 | Referrals | GET | /referrals | list_referrals | api/user/referrals.py | 获取推荐列表 |
| 77 | Referrals | GET | /referrals/stats | get_stats | api/user/referrals.py | 获取推荐统计 |
| 78 | Referrals | GET | /referrals/code/{referral_code} | validate_code | api/user/referrals.py | 验证推荐码 |
| 79 | Referrals | POST | /referrals/{referral_id}/complete | complete_referral | api/user/referrals.py | 完成推荐 |
| 80 | Referrals | GET | /referrals/health | health_check | api/user/referrals.py | 健康检查 |
| 81 | Resources | GET | /resources | list_resources | api/user/resources.py | 获取资源列表 |
| 82 | Resources | GET | /resources/types | get_types | api/user/resources.py | 获取资源类型 |
| 83 | Resources | GET | /resources/categories/{type} | get_categories | api/user/resources.py | 获取分类 |
| 87 | Resources | GET | /resources/{resource_id} | get_resource | api/user/resources.py | 获取单个资源 |
| 88 | Support | POST | /support/ticket | create_ticket | api/user/support.py | 创建工单 |
| 89 | Support | POST | /support/chat | chat | api/user/support.py | AI客服对话 |
| 90 | Support | POST | /support/contact | contact | api/user/support.py | 联系表单 |
| 91 | Support | POST | /support/feedback | submit_feedback | api/user/support.py | 反馈提交 |
| 92 | System Resources | GET | /system_resources | list_system_resources | api/user/system_resources.py | 列出系统资源 |
| 93 | System Resources | GET | /system_resources/stats | get_stats | api/user/system_resources.py | 获取资源统计 |
| 94 | System Resources | GET | /system_resources/{resource_id} | get_system_resource | api/user/system_resources.py | 获取单个系统资源 |
| 95 | System Resources | POST | /system_resources | create_system_resource | api/user/system_resources.py | 创建系统资源 |
| 96 | System Resources | PATCH | /system_resources/{resource_id} | update_system_resource | api/user/system_resources.py | 更新系统资源 |
| 97 | System Resources | POST | /system_resources/{resource_id}/replace | replace_resource_file | api/user/system_resources.py | 替换资源文件 |
| 98 | System Resources | DELETE | /system_resources/{resource_id} | delete_system_resource | api/user/system_resources.py | 删除系统资源 |
| 99 | System Resources | POST | /system_resources/batch | batch_operation | api/user/system_resources.py | 批量操作 |
| 100 | System Resources | GET | /system_resources/{resource_id}/audit-log | get_audit_log | api/user/system_resources.py | 获取审计日志 |
| 101 | Tasks | GET | /tasks/{task_id} | get_task | api/user/tasks.py | 查询任务状态 |
| 102 | Tasks | POST | /tasks/{task_id}/cancel | cancel_task | api/user/tasks.py | 取消任务 |
| 103 | Prompt Templates | GET | /prompt_template/asset | list_asset_templates | api/user/templates.py | 列出用户素材提示词模板 |
| 104 | Prompt Templates | POST | /prompt_template/asset | create_asset_template | api/user/templates.py | 创建用户素材提示词模板 |
| 105 | Prompt Templates | PUT | /prompt_template/asset/{template_id} | update_asset_template | api/user/templates.py | 更新用户素材提示词模板 |
| 106 | Prompt Templates | DELETE | /prompt_template/asset/{template_id} | delete_asset_template | api/user/templates.py | 删除用户素材提示词模板 |
| 107 | Prompt Templates | POST | /prompt_template/asset/{template_id}/use | use_asset_template | api/user/templates.py | 使用用户素材提示词模板 |
| 108 | Prompt Templates | GET | /prompt_template/page | list_page_templates | api/user/templates.py | 列出用户页面提示词模板 |
| 109 | Prompt Templates | POST | /prompt_template/page | create_page_template | api/user/templates.py | 创建用户页面提示词模板 |
| 110 | Prompt Templates | PUT | /prompt_template/page/{template_id} | update_page_template | api/user/templates.py | 更新用户页面提示词模板 |
| 111 | Prompt Templates | DELETE | /prompt_template/page/{template_id} | delete_page_template | api/user/templates.py | 删除用户页面提示词模板 |
| 112 | Prompt Templates | POST | /prompt_template/page/{template_id}/use | use_page_template | api/user/templates.py | 使用用户页面提示词模板 |
| 113 | Themes | GET | /themes/current | get_current_theme | api/user/themes.py | 获取当前主题 |
| 114 | Tools | POST | /tools/pdf-preview | pdf_preview | api/user/tools.py | PDF预览生成 |
| 115 | Tools | POST | /tools/ocr | ocr_text | api/user/tools.py | OCR文字识别 |
| 116 | User Assets | GET | /user_assets | list_user_assets | api/user/user_assets.py | 获取我的资产列表 |
| 117 | User Assets | POST | /user_assets | upload_asset | api/user/user_assets.py | 上传资产 |
| 118 | User Assets | DELETE | /user_assets/{asset_id} | delete_asset | api/user/user_assets.py | 删除资产 |
| 119 | User Assets | POST | /user_assets/from-url | add_asset_from_url | api/user/user_assets.py | 从URL添加资产 |
| 120 | User Assets | GET | /user_assets/check-url | check_url | api/user/user_assets.py | URL检查 |
| 121 | User Assets | POST | /user_assets/{asset_id}/increment-usage | increment_usage | api/user/user_assets.py | 使用次数增加 |
| 122 | User Assets | GET | /user_assets/dashboard | get_asset_dashboard | api/user/user_assets.py | 资产Dashboard (带view过滤) |
| 124 | User Assets | GET | /user_assets/deleted | get_deleted | api/user/user_assets.py | 已删除资产 |
| 125 | User Assets | POST | /user_assets/{asset_id}/restore | restore_asset | api/user/user_assets.py | 恢复资产 |
| 125a | User Assets | POST | /user_assets/{asset_id}/move | move_asset | api/user/user_assets.py | 移动到文件夹 (v3.33) |
| 125b | User Assets | POST | /user_assets/{asset_id}/star | star_asset | api/user/user_assets.py | 切换收藏状态 (v3.33) |
| 125c | User Assets | GET | /user_assets/folder/{folder_id} | get_assets_by_folder | api/user/user_assets.py | 获取文件夹内资产 (v3.33) |
| 125d | User Assets | GET | /user_assets/starred | get_starred_assets | api/user/user_assets.py | 获取收藏资产 (v3.33) |
| 126 | User Profile | GET | /user_profile/me | get_me | api/user/user_profile.py | 获取当前用户信息 |
| 127 | User Profile | GET | /user_profile/history | get_history | api/user/user_profile.py | 获取操作历史 |
| 128 | User Profile | GET | /user_profile/purchases | get_purchases | api/user/user_profile.py | 获取购买记录 |
| 129 | User Profile | GET | /user_profile/notifications | get_notifications | api/user/user_profile.py | 获取通知列表 |
| 130 | User Profile | POST | /user_profile/notifications/{id}/read | mark_notification_read | api/user/user_profile.py | 标记通知为已读 |
| 131 | User Profile | POST | /user_profile/notifications/read-all | mark_all_read | api/user/user_profile.py | 标记所有通知为已读 |
| 132 | User Profile | PUT | /user_profile/timezone | update_timezone | api/user/user_profile.py | 更新时区 |
| 133 | Webhooks | POST | /webhooks/clerk | clerk_webhook | api/user/webhooks.py | Clerk Webhook处理 |
| 134 | Webhooks | POST | /webhooks/stripe | stripe_webhook | api/user/webhooks.py | Stripe Webhook处理 |
| 135 | Folders | GET | /folders | list_folders | api/user/folders.py | 获取文件夹列表 (v3.33) |
| 136 | Folders | POST | /folders | create_folder | api/user/folders.py | 创建文件夹 (v3.33) |
| 137 | Folders | PATCH | /folders/{folder_id} | update_folder | api/user/folders.py | 更新文件夹 (v3.33) |
| 138 | Folders | DELETE | /folders/{folder_id} | delete_folder | api/user/folders.py | 删除文件夹 (v3.33) |
| 139 | Folders | POST | /folders/reorder | reorder_folders | api/user/folders.py | 重排序文件夹 (v3.33) |
| 140 | Folders | GET | /folders/{folder_id} | get_folder | api/user/folders.py | 获取文件夹详情 (v3.33) |

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

## 2. Articles 文章 **NEW**

公开文章 API，用于帮助文档 (Manual)、新闻公告 (News) 和更新日志 (Changelog)。

**无需认证** - 所有端点均为公开访问。

### GET `/articles`

获取已发布文章列表

**限流**: 60 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `category` | string | - | 分类筛选: `manual`, `news`, `changelog` |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 (1-100) |

**响应**:
```json
{
  "items": [
    {
      "id": "uuid-xxx",
      "slug": "how-to-add-images",
      "title": "How to Add Images",
      "summary": "Learn how to upload and manage images...",
      "category": "manual",
      "tags": ["editor", "images"],
      "cover_image": "https://...",
      "published_at": "2026-01-10T10:00:00Z",
      "view_count": 120
    }
  ],
  "total": 45,
  "offset": 0,
  "limit": 20
}
```

---

### GET `/articles/featured`

获取精选文章 (v1.1.0)

**限流**: 60 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `category` | string | - | 分类筛选: `manual`, `news`, `changelog` |
| `limit` | int | 4 | 最大数量 (1-20) |

**响应**:
```json
{
  "items": [
    {
      "id": "uuid-xxx",
      "slug": "new-ai-feature",
      "title": "New Feature: AI Design Assistant",
      "summary": "Introducing our new AI-powered...",
      "category": "news",
      "tags": ["feature", "update"],
      "cover_image": "https://...",
      "published_at": "2026-01-12T10:00:00Z",
      "view_count": 250
    }
  ],
  "total": 3,
  "offset": 0,
  "limit": 4
}
```

---

### GET `/articles/categories`

获取分类及文章数量

**限流**: 60 req/min

**响应**:
```json
{
  "categories": [
    {
      "category": "manual",
      "display_name": "Help & Documentation",
      "count": 15
    },
    {
      "category": "news",
      "display_name": "News & Announcements",
      "count": 8
    },
    {
      "category": "changelog",
      "display_name": "Changelog",
      "count": 12
    }
  ]
}
```

---

### GET `/articles/search`

搜索已发布文章

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `q` | string | **必填** | 搜索关键词 (2-100字符) |
| `category` | string | - | 分类筛选 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 (1-100) |

**响应**: 同 `/articles`

---

### GET `/articles/{slug}`

获取文章详情

**限流**: 60 req/min

**路径参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `slug` | string | 文章 slug (URL友好标识) |

**响应**:
```json
{
  "id": "uuid-xxx",
  "slug": "how-to-add-images",
  "title": "How to Add Images",
  "content": "# How to Add Images\n\nYou can add images...",
  "summary": "Learn how to upload and manage images...",
  "category": "manual",
  "tags": ["editor", "images"],
  "cover_image": "https://...",
  "published_at": "2026-01-10T10:00:00Z",
  "view_count": 121,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-10T10:00:00Z"
}
```

**说明**: 获取文章详情会自动增加 `view_count`。

**错误**:
- `404`: 文章不存在或未发布

---

### GET `/articles/{slug}/related`

获取相关文章 (v1.2.0)

**限流**: 60 req/min

**路径参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `slug` | string | 文章 slug (URL友好标识) |

**查询参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `limit` | int | 3 | 最大数量 (1-10) |

**响应**:
```json
[
  {
    "id": "uuid-xxx",
    "slug": "working-with-text",
    "title": "Working with Text in Your Project",
    "summary": "Learn how to add and format text...",
    "category": "manual",
    "tags": ["text", "tutorial"],
    "cover_image": "https://...",
    "published_at": "2026-01-10T10:00:00Z",
    "view_count": 98
  },
  {
    "id": "uuid-xxx",
    "slug": "advanced-editing-tips",
    "title": "Advanced Editing Tips",
    "summary": "Master advanced editing techniques...",
    "category": "manual",
    "tags": ["advanced", "tips"],
    "cover_image": "https://...",
    "published_at": "2026-01-09T10:00:00Z",
    "view_count": 156
  }
]
```

**说明**: 返回与当前文章同类别的其他已发布文章（排除当前文章）。

**错误**:
- `404`: 文章不存在或未发布

---

## 3. Billing 计费管理

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
    "monthly": 100,
    "permanent": 150,
    "total": 250
  }
}
```

---

## 4. Campaigns 活动

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

## 5. Config 配置

> **CMS-Lite 功能 (v3.33+)**: 支持 `array` 和 `richtext` 类型，用于 Landing 页面内容管理

### GET `/config`

获取所有公开配置

**公开配置白名单** (PUBLIC_CONFIG_PATTERNS):
- `FEATURE_*` - Feature Flags 功能开关
- `UI_*` - UI 配置
- `LANDING_*` - Landing 页面内容 (CMS-Lite)
- `SITE_*` - 网站公共信息 (名称、联系方式、社交媒体)
- `PRICING_*` - 定价展示信息 (功能列表、档位)

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `category` | string | 可选,按类别筛选 |

**响应**:
```json
{
  "configs": [
    {
      "key": "FEATURE_NEW_EDITOR",
      "value": true,
      "value_type": "boolean",
      "category": "feature"
    },
    {
      "key": "LANDING_EXAMPLE_PROMPTS",
      "value": "[{\"emoji\":\"🦕\",\"text\":\"Dinosaur adventure\"}]",
      "value_type": "array",
      "category": "page_content"
    }
  ],
  "total": 25
}
```

**value_type 类型**:
- `text` - 短文本
- `number` - 浮点数字
- `integer` - 整数
- `boolean` - 布尔值
- `json` - JSON 对象
- `array` - JSON 数组 (前端需 JSON.parse)
- `richtext` - Markdown/HTML 富文本

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

## 6. Experiments 实验

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

## 7. Feature Flags 功能开关

> v3.35 新增：Feature Flag 客户端端点，支持树状依赖评估

### GET `/feature-flags/client/flags`

获取当前用户所有 Flag 状态

**限流**: 无限流

**响应**:
```json
{
  "flags": {
    "editor": true,
    "editor_toolbar": true,
    "editor_toolbar_drawing": true,
    "dashboard": true,
    "marketplace": true
  },
  "variants": {
    "editor": "treatment",
    "onboarding_flow": "variant_b"
  },
  "evaluated_at": "2026-01-12T10:30:00Z"
}
```

---

### GET `/feature-flags/hierarchy`

获取 Flag 层级配置 (v1.1 新增)

**限流**: 无限流

**响应**:
```json
{
  "hierarchy": {
    "editor_toolbar": ["editor"],
    "editor_toolbar_drawing": ["editor", "editor_toolbar"],
    "dashboard_projects_batch": ["dashboard", "dashboard_projects"]
  },
  "updated_at": "2026-01-12T00:00:00Z"
}
```

---

### POST `/feature-flags/exposure`

记录 Flag 曝光事件

**限流**: 无限流

**请求体**:
```json
{
  "flag_key": "editor_toolbar_drawing",
  "variant": "treatment",
  "context": {
    "page": "/editor",
    "component": "toolbar"
  }
}
```

**响应**:
```json
{
  "success": true,
  "exposure_id": "uuid-xxx"
}
```

---

### POST `/feature-flags/conversion`

记录转化事件 (实验类型 Flag)

**限流**: 无限流

**请求体**:
```json
{
  "flag_key": "exp_checkout_flow",
  "metric": "purchase",
  "value": 99.99,
  "metadata": {
    "product_id": "prod_123",
    "quantity": 1
  }
}
```

**响应**:
```json
{
  "success": true
}
```

---

## 8. Export 导出

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

## 9. Generation Images AI图片生成

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

## 10. Generation PDF PDF生成

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

## 11. Generation Story AI故事生成

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

## 12. Generations 生成历史

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

## 13. Logs 日志

> **更新 (v3.1.0, 2026-01-12)**: 完整支持前端 errorLogger.ts 的错误上报格式

### POST `/logs/error`

单条错误上报 (无需认证)

**限流**: 30/分钟

**请求体**:
```json
{
  "error_id": "api_err_1736690412345",
  "error_type": "api_error",
  "error_code": "FETCH_FAILED",
  "message": "Failed to load resource",
  "status_code": 500,
  "endpoint": "/api/v2/user/projects",
  "method": "GET",
  "request_id": "req_abc123",
  "user_code": "26010914305278900123456789",
  "session_id": "sess_xxx",
  "page_url": "https://app.makedecodables.com/editor",
  "user_agent": "Mozilla/5.0...",
  "stack_trace": "Error: Failed to fetch...",
  "context": { "attempt": 1 },
  "client_timestamp": "2026-01-12T10:30:00.000Z"
}
```

**验证规则**:
| 字段 | 验证 | 说明 |
|------|------|------|
| `error_id` | 必填, 1-100 字符, `[a-zA-Z0-9_-]+` | 前端生成的唯一 ID |
| `error_type` | 必填, 1-50 字符 | 错误类型 (api_error/network_error/react_error/promise_error) |
| `status_code` | 可选, 100-599 | HTTP 状态码 (网络错误时传 null) |
| `method` | 可选, GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS | HTTP 方法 |
| `context` | 可选, 最大 10KB | 附加上下文信息 |

**响应**:
```json
{
  "status": "ok"
}
```

---

### POST `/logs/errors`

批量错误上报 (无需认证)

**限流**: 10/分钟

**请求体**:
```json
{
  "errors": [
    {
      "error_id": "api_err_1",
      "error_type": "api_error",
      "message": "Error 1"
    },
    {
      "error_id": "api_err_2",
      "error_type": "network_error",
      "message": "Error 2"
    }
  ]
}
```

**验证规则**:
- `errors` 数组最多 50 条 (超过需拆分批次)
- 每条记录的验证规则同单条上报

**响应**:
```json
{
  "status": "ok",
  "errors_received": 2
}
```

**前端实现注意事项** (errorLogger.ts):
- 网络错误时 `status_code` 应传 `null` (不传 0)
- 上传失败时自动存入 localStorage 队列
- 队列最大 200 条，超出时丢弃最旧的
- 连续失败 5 次后自动清空队列
- 批量上传时自动拆分为 50 条/批

---

## 14. Marketplace 市场

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
  "resource_type": "asset",
  "category": "sticker",
  "source": "user",
  "price_credits": 30,
  "allowed_tiers": ["t2", "t3"],
  "allow_preview": true,
  "version": "1.0",
  "changelog": ""
}
```

**字段说明**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | ✅ | 商品标题 (1-200字符) |
| description | string | ❌ | 商品描述 (最多2000字符) |
| thumbnail_url | string | ❌ | 缩略图URL |
| resource_url | string | ❌ | 资源URL |
| resource_type | string | ✅ | "asset" 或 "project" |
| category | string | ❌ | 分类 (clipart/sticker/template等) |
| source | string | ❌ | 来源 (system/user/ai/community) |
| price_credits | int | ❌ | 价格 0-500，默认0 |
| allowed_tiers | string[] | ❌ | 可访问的Tier |
| allow_preview | bool | ❌ | 是否允许购买前预览，默认true |
| version | string | ❌ | 版本号，默认"1.0" |
| changelog | string | ❌ | 更新日志 |

**权限**:
- t2 (Starter): 仅能发布免费资源 (price_credits=0, resource_type='asset')
- t3 (Pro): 可发布任意价格资源 (0-500 credits)

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
  "description": "更新后的描述",
  "thumbnail_url": "https://...",
  "resource_url": "https://...",
  "price_credits": 40,
  "allowed_tiers": ["t2", "t3"],
  "allow_preview": true,
  "version": "1.1",
  "changelog": "修复了一些问题"
}
```

**状态转换说明**:

| 原状态 | 更新后状态 | 说明 |
|--------|------------|------|
| draft | draft | 草稿可自由编辑，不触发审核 |
| pending | - | 待审核状态不可编辑 |
| approved (published) | pending | 已发布商品编辑后需重新审核 |
| rejected | pending | 被拒绝商品编辑后可重新提交审核 |
| archived (unpublished) | pending | 下架商品编辑后可重新发布，需审核 |
| suspended | - | 被封禁商品不可编辑，需联系客服 |

**注意**:
- 修改任何字段 (title, description, price_credits 等) 都会触发重新审核
- 关联项目的 `listing_status` 会同步更新为 "pending"
- `requires_resubmit: true` 表示需要等待管理员审核

**响应**:
```json
{
  "status": "updated",
  "listing_id": "listing_xxx",
  "requires_resubmit": true
}
```

---

### DELETE `/marketplace/listings/{listing_id}`

下架商品 (Unpublish)

将商品从市场下架，状态变为 `archived`。下架后的商品可以通过 PUT 请求重新编辑并发布（需重新审核）。

**注意**:
- 只有 `approved` (已发布) 状态的商品可以下架
- 下架后关联项目的 `listing_status` 会同步更新为 `archived`
- 下架不会删除商品数据，卖家可以随时重新发布

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

## 15. Onboarding 新手引导

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

## 16. Payment 支付

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

## 17. Pages 静态页面内容 **NEW**

> v3.36 新增：静态页面 CMS 系统，用于动态管理 About Us、Contact Us、Privacy Policy 等页面内容。
> 设计文档：[static-pages-cms-design.md](static-pages-cms-design.md)

**无需认证** - 所有端点均为公开访问。

### GET `/pages/{page_name}`

获取页面所有区块内容（参数已替换）

**限流**: 60 req/min

**路径参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `page_name` | string | 页面标识符 |

**有效 page_name 值**:
- `about-us` - 关于我们
- `contact-us` - 联系我们 (Hybrid: 静态内容 + 表单)
- `privacy-policy` - 隐私政策
- `term-of-service` - 服务条款
- `billing-policy` - 计费政策
- `marketplace-guidelines` - 市场指南

**响应**:
```json
{
  "page": "about-us",
  "sections": {
    "hero": {
      "title": "About Make Decodables",
      "subtitle": "Our Mission",
      "description": "We're on a mission to empower educators...",
      "enabled": true
    },
    "features": {
      "title": "Why Choose Us",
      "items": [
        {
          "icon": "BookOpen",
          "title": "Easy Book Creation",
          "description": "Create foldable mini-books in minutes..."
        }
      ],
      "enabled": true
    },
    "cta": {
      "title": "Ready to Create?",
      "description": "Join thousands of educators...",
      "cta": {
        "text": "Start Creating Now",
        "href": "/dashboard",
        "variant": "primary"
      },
      "enabled": true
    }
  },
  "globals": {
    "company_name": "Make Decodables",
    "company_email": "info@makedecodables.com",
    "company_whatsapp": "+1 (725) 290 0525"
  },
  "lastUpdated": "2026-01-12T10:00:00Z"
}
```

**说明**:
- 参数引用 (`{{GLOBAL_*}}`) 在后端已替换为实际值
- 只返回 `enabled: true` 的区块
- 缓存: 60 秒

**错误**:
- `404`: 页面不存在

---

### GET `/pages/{page_name}/{section}`

获取单个区块内容

**限流**: 60 req/min

**路径参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `page_name` | string | 页面标识符 |
| `section` | string | 区块名称 (如 `hero`, `features`, `cta`) |

**响应**:
```json
{
  "section": "hero",
  "data": {
    "title": "About Make Decodables",
    "subtitle": "Our Mission",
    "description": "We're on a mission to empower educators...",
    "enabled": true
  },
  "globals": {
    "company_name": "Make Decodables"
  }
}
```

**错误**:
- `404`: 页面或区块不存在

---

## 18. Projects 项目管理

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
  "total": 50,
  "offset": 0,
  "limit": 20,
  "has_more": true
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

### POST `/projects`

创建新项目

**限流**: 20 req/min

**请求体**:
```json
{
  "title": "我的新迷你书",
  "canvas_data": { ... },
  "idempotency_key": "550e8400-e29b-41d4-a716-446655440000"  // 可选, v1.1.0
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | 否 | 项目标题，默认 "Untitled" |
| `canvas_data` | object | 否 | 画布数据 (Fabric.js JSON) |
| `idempotency_key` | string | 否 | 幂等键 (UUID v4)，用于安全重试 |

**幂等性支持** (v1.1.0):
> 业界最佳实践 (Stripe/PayPal/AWS)

- 客户端生成 UUID 作为 `idempotency_key` 随请求发送
- 如果请求失败（网络错误、500等），客户端使用**相同的 key** 重试
- 服务端检查该 key 是否已存在项目：
  - 存在：返回已创建的项目（不重复创建）
  - 不存在：创建新项目并关联该 key
- 防止"幽灵项目"问题（DB 写入成功但响应失败导致客户端不知道项目已创建）

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
- `500`: 服务器错误（可使用相同 idempotency_key 重试）

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

### POST `/projects/{project_id}/move`

移动项目到指定文件夹 (v3.33 Phase 2.6)

**请求体**:
```json
{
  "folder_id": "uuid-xxx"  // null 表示移到根目录
}
```

**响应**:
```json
{
  "success": true,
  "project": {
    "id": "proj_xxx",
    "folder_id": "uuid-xxx"
  }
}
```

**错误**:
- `404`: 项目不存在或无权访问
- `400`: 文件夹不存在或类型不匹配

---

### POST `/projects/{project_id}/star`

切换项目收藏状态 (v3.33 Phase 2.6)

**请求体**:
```json
{
  "is_starred": true
}
```

**响应**:
```json
{
  "success": true,
  "project": {
    "id": "proj_xxx",
    "is_starred": true
  }
}
```

---

### GET `/projects/folder/{folder_id}`

获取指定文件夹内的项目列表 (v3.33 Phase 2.6)

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 50 | 每页数量 |
| `search` | string | - | 搜索关键词 |

**说明**: folder_id 为 "root" 时返回根目录项目 (folder_id=NULL)

**响应**:
```json
{
  "items": [...],
  "total": 10,
  "offset": 0,
  "limit": 50
}
```

---

### GET `/projects/starred`

获取收藏的项目列表 (v3.33 Phase 2.6)

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 50 | 每页数量 |

**响应**:
```json
{
  "items": [...],
  "total": 5,
  "offset": 0,
  "limit": 50
}
```

---

## 18. Referrals 推荐系统

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

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 (1-100) |

**响应**:
```json
{
  "items": [
    {
      "id": "uuid-xxx",
      "referral_code": "abc123...",
      "status": "completed",
      "referred_user_id": "user_def",
      "reward_issued": true,
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "total": 15,
  "offset": 0,
  "limit": 20,
  "has_more": false
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

## 19. Resources 系统资源

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

## 21. Seller 卖家统计 **NEW**

> v3.39 新增：统一的卖家统计端点，整合了 projects、marketplace、assets 三个模块的卖家数据。
>
> **整合的端点** (已废弃):
> - `GET /projects/seller-stats` → 使用 `?include=projects`
> - `GET /marketplace/seller/stats` → 使用 `?include=listings`
> - `GET /user_assets/seller-stats` → 使用 `?include=assets`

### GET `/seller/stats`

获取统一的卖家统计数据

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `include` | string | 全部 | 逗号分隔的数据类型: projects, listings, assets |

**示例请求**:
```
GET /api/v2/user/seller/stats?include=projects,listings
```

**响应**:
```json
{
  "projects": {
    "total_selling": 5,
    "total_sales": 120,
    "unique_buyers": 45,
    "total_revenue": 6000.0
  },
  "listings": {
    "total_earned_credits": 2500,
    "listings_count": 10,
    "total_sales": 80,
    "total_usage": 520
  },
  "assets": {
    "total_assets": 25,
    "total_downloads": 340,
    "total_revenue": 1700.0
  },
  "summary": {
    "total_revenue": 7825.0,
    "total_sales": 540,
    "total_items": 40
  }
}
```

**说明**:
- `include` 参数可选，不传则返回所有数据
- 各模块字段说明:
  - `projects`: 项目销售数据
  - `listings`: 市场商品数据 (credits 按 0.05 美元/积分换算)
  - `assets`: 素材销售数据
  - `summary`: 汇总数据 (始终返回)

---

## 22. Support 客服支持

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

## 23. System Resources 系统资源管理

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

## 24. Tasks 任务

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

## 25. Prompt Templates 用户提示词模板

### GET `/prompt_template/asset`

列出用户素材提示词模板

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

### POST `/prompt_template/asset`

创建用户素材提示词模板

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

### PUT `/prompt_template/asset/{template_id}`

更新用户素材提示词模板

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

### DELETE `/prompt_template/asset/{template_id}`

删除用户素材提示词模板

**响应**:
```json
{
  "success": true,
  "template_id": "template_xxx"
}
```

---

### POST `/prompt_template/asset/{template_id}/use`

使用用户素材提示词模板

**响应**:
```json
{
  "success": true,
  "instance_data": { ... }
}
```

---

### GET `/prompt_template/page`

列出用户页面提示词模板

**响应**: 同 `/prompt_template/asset`

---

### POST `/prompt_template/page`

创建用户页面提示词模板

**请求体**: 同 `/prompt_template/asset`

**响应**: 同 `/prompt_template/asset`

---

### PUT `/prompt_template/page/{template_id}`

更新用户页面提示词模板

**请求体**: 同 `/prompt_template/asset/{template_id}`

**响应**: 同 `/prompt_template/asset/{template_id}`

---

### DELETE `/prompt_template/page/{template_id}`

删除用户页面提示词模板

**响应**: 同 `/prompt_template/asset/{template_id}`

---

### POST `/prompt_template/page/{template_id}/use`

使用用户页面提示词模板

**响应**: 同 `/prompt_template/asset/{template_id}/use`

---

## 26. Themes 主题

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

## 27. Tools 工具

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

## 28. User Assets 用户资产

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

资产Dashboard - 获取用户素材列表，支持视图过滤 (v3.3.0 重构)

**Query 参数**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| view | string | 否 | "all" | 视图类型: "all"(全部), "bought"(已购买), "selling"(正在销售) |
| offset | int | 否 | 0 | 跳过的记录数 |
| limit | int | 否 | 15 | 返回的记录数 (1-100) |
| search | string | 否 | - | 搜索关键词 (按name字段) |

**响应**:
```json
{
  "items": [
    {
      "id": "8153ab03-6212-4ba5-b489-ebd7aa802106",
      "url": "https://...",
      "type": "image",
      "name": null,
      "category": null,
      "source": "upload",
      "usage_count": 0,
      "prompt": null,
      "description": null,
      "metadata": {},
      "is_purchased": false,
      "source_listing_id": null,
      "origin_owner_id": null,
      "created_at": "2026-01-26T22:40:17.344175+00:00",
      "updated_at": "2026-01-26T22:40:17.344175+00:00"
    }
  ],
  "total": 1,
  "offset": 0,
  "limit": 15,
  "has_more": false,
  "counts": {
    "all": 1,
    "bought": 0,
    "selling": 0
  }
}
```

**视图说明**:
- `all`: 用户的所有素材 (is_deleted=false)
- `bought`: 已购买的素材 (is_purchased=true)
- `selling`: 正在销售的素材 (通过 marketplace_listings 查询)

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

### POST `/user_assets/{asset_id}/move`

移动资产到指定文件夹 (v3.33 Phase 2.6)

**请求体**:
```json
{
  "folder_id": "uuid-xxx"  // null 表示移到根目录
}
```

**响应**:
```json
{
  "success": true,
  "asset": {
    "id": "asset_xxx",
    "folder_id": "uuid-xxx"
  }
}
```

**错误**:
- `404`: 资产不存在或无权访问
- `400`: 文件夹不存在或类型不匹配

---

### POST `/user_assets/{asset_id}/star`

切换资产收藏状态 (v3.33 Phase 2.6)

**请求体**:
```json
{
  "is_starred": true
}
```

**响应**:
```json
{
  "success": true,
  "asset": {
    "id": "asset_xxx",
    "is_starred": true
  }
}
```

---

### GET `/user_assets/folder/{folder_id}`

获取指定文件夹内的资产列表 (v3.33 Phase 2.6)

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 50 | 每页数量 |
| `search` | string | - | 搜索关键词 |

**说明**: folder_id 为 "root" 时返回根目录资产 (folder_id=NULL)

**响应**:
```json
{
  "items": [...],
  "total": 10,
  "offset": 0,
  "limit": 50
}
```

---

### GET `/user_assets/starred`

获取收藏的资产列表 (v3.33 Phase 2.6)

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 50 | 每页数量 |

**响应**:
```json
{
  "items": [...],
  "total": 5,
  "offset": 0,
  "limit": 50
}
```

---

## 29. User Profile 用户档案

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

## 30. Webhooks

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

## 31. Workspaces 工作区

> **v3.43 新增** - Workspace + Tag 系统 Phase 1
> **端点数**: 6 个
> **文件**: `api/user/workspaces.py`

### GET `/workspaces`

获取用户的所有工作区列表。

**认证**: 必须

**限流**: 60/minute

**响应**:
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "My Workspace",
      "description": "Default workspace",
      "owner_id": "user_xxx",
      "is_default": true,
      "is_personal": true,
      "is_active": true,
      "created_at": "2026-01-27T00:00:00Z",
      "updated_at": "2026-01-27T00:00:00Z"
    }
  ],
  "total": 1
}
```

### GET `/workspaces/current`

获取当前用户的默认工作区。

**认证**: 必须

**限流**: 60/minute

**响应**:
```json
{
  "id": "uuid",
  "name": "My Workspace",
  "description": null,
  "owner_id": "user_xxx",
  "is_default": true,
  "is_personal": true,
  "is_active": true,
  "created_at": "2026-01-27T00:00:00Z",
  "updated_at": "2026-01-27T00:00:00Z"
}
```

### GET `/workspaces/{workspace_id}`

获取指定工作区详情。

**认证**: 必须 (仅 owner)

**限流**: 60/minute

**响应**: 同 `/workspaces/current`

### PATCH `/workspaces/{workspace_id}`

更新工作区信息。

**认证**: 必须 (仅 owner)

**限流**: 30/minute

**请求体**:
```json
{
  "name": "Updated Name",
  "description": "Updated description"
}
```

**响应**: 更新后的工作区对象

### DELETE `/workspaces/{workspace_id}`

删除工作区 (软删除)。

**认证**: 必须 (仅 owner)

**限流**: 10/minute

**约束**: 不能删除默认工作区

**响应**:
```json
{
  "success": true,
  "message": "Workspace deleted"
}
```

### GET `/workspaces/{workspace_id}/stats`

获取工作区统计信息。

**认证**: 必须 (仅 owner)

**限流**: 30/minute

**响应**:
```json
{
  "workspace_id": "uuid",
  "tag_count": 25,
  "project_count": 10,
  "asset_count": 50
}
```

---

## 32. Tags 标签系统

> **v3.43 新增** - Workspace + Tag 系统 Phase 1
> **端点数**: 6 个
> **文件**: `api/user/tags.py`

### GET `/tags`

获取用户工作区的所有标签。

**认证**: 必须

**限流**: 60/minute

**查询参数**:
| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| group_name | string | 否 | 按分组过滤 |

**响应**:
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Grade 1",
      "color": "blue",
      "icon": "🎓",
      "group_name": "Grade Level",
      "sort_order": 0,
      "usage_count": 15
    }
  ],
  "total": 25
}
```

### GET `/tags/by-group`

获取按分组组织的标签。

**认证**: 必须

**限流**: 60/minute

**响应**:
```json
{
  "Grade Level": [
    {"id": "uuid", "name": "Grade 1", "color": "blue", ...}
  ],
  "Phonics Pattern": [
    {"id": "uuid", "name": "CVC Words", "color": "purple", ...}
  ]
}
```

### POST `/tags`

创建新标签。

**认证**: 必须

**限流**: 30/minute

**请求体**:
```json
{
  "name": "New Tag",
  "color": "green",
  "group_name": "Custom",
  "icon": "📚"
}
```

**验证规则**:
- name: 1-50 字符，必填
- color: gray/red/orange/yellow/green/blue/purple/pink
- group_name: 可选，最多 50 字符
- icon: 可选，最多 10 字符 (emoji)

**响应**: 创建的标签对象

### PATCH `/tags/{tag_id}`

更新标签。

**认证**: 必须 (仅 workspace owner)

**限流**: 30/minute

**请求体**:
```json
{
  "name": "Updated Name",
  "color": "red",
  "group_name": "New Group",
  "icon": "🔥"
}
```

**响应**: 更新后的标签对象

### DELETE `/tags/{tag_id}`

删除标签 (会解除所有关联)。

**认证**: 必须 (仅 workspace owner)

**限流**: 30/minute

**响应**:
```json
{
  "success": true,
  "message": "Tag deleted"
}
```

### GET `/tags/presets`

获取系统预设的标签分组。

**认证**: 必须

**限流**: 60/minute

**响应**:
```json
{
  "items": [
    {
      "id": "uuid",
      "group_name": "grade_level",
      "display_name": "Grade Level",
      "description": "Organize by student grade level",
      "icon": "🎓",
      "preset_tags": [
        {"name": "Pre-K", "color": "pink"},
        {"name": "Kindergarten", "color": "purple"}
      ],
      "is_default": true
    }
  ]
}
```

---

## 33. Project Tags 项目标签

> **v3.43 新增** - Workspace + Tag 系统 Phase 1
> **端点数**: 4 个
> **文件**: `api/user/tags.py`

### GET `/projects/{project_id}/tags`

获取项目的所有标签。

**认证**: 必须

**限流**: 60/minute

**响应**:
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Grade 1",
      "color": "blue",
      "group_name": "Grade Level"
    }
  ]
}
```

### POST `/projects/{project_id}/tags`

为项目添加标签。

**认证**: 必须

**限流**: 30/minute

**请求体**:
```json
{
  "tag_ids": ["uuid1", "uuid2"]
}
```

**验证规则**:
- tag_ids: 至少 1 个，UUID 格式
- 每个项目最多 10 个标签

**响应**: 更新后的项目标签列表

### PUT `/projects/{project_id}/tags`

替换项目的所有标签。

**认证**: 必须

**限流**: 30/minute

**请求体**:
```json
{
  "tag_ids": ["uuid1", "uuid2"]
}
```

**响应**: 替换后的项目标签列表

### DELETE `/projects/{project_id}/tags/{tag_id}`

移除项目的指定标签。

**认证**: 必须

**限流**: 30/minute

**响应**:
```json
{
  "success": true,
  "message": "Tag removed from project"
}
```

---

## 34. Asset Tags 素材标签

> **v3.43 新增** - Workspace + Tag 系统 Phase 1
> **端点数**: 4 个
> **文件**: `api/user/tags.py`

### GET `/assets/{asset_id}/tags`

获取素材的所有标签。

**认证**: 必须

**限流**: 60/minute

**响应**:
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Animals",
      "color": "green",
      "group_name": "Topic"
    }
  ]
}
```

### POST `/assets/{asset_id}/tags`

为素材添加标签。

**认证**: 必须

**限流**: 30/minute

**请求体**:
```json
{
  "tag_ids": ["uuid1", "uuid2"]
}
```

**验证规则**:
- tag_ids: 至少 1 个，UUID 格式
- 每个素材最多 10 个标签

**响应**: 更新后的素材标签列表

### PUT `/assets/{asset_id}/tags`

替换素材的所有标签。

**认证**: 必须

**限流**: 30/minute

**请求体**:
```json
{
  "tag_ids": ["uuid1", "uuid2"]
}
```

**响应**: 替换后的素材标签列表

### DELETE `/assets/{asset_id}/tags/{tag_id}`

移除素材的指定标签。

**认证**: 必须

**限流**: 30/minute

**响应**:
```json
{
  "success": true,
  "message": "Tag removed from asset"
}
```

---

## 35. Folders 文件夹

> **v3.33 新增** - Workspace + Tag 系统 Phase 2.6
> **端点数**: 6 个
> **文件**: `api/user/folders.py`

文件夹系统用于组织 Projects 和 Assets，支持 8 色系统和自定义排序。

**Folder 结构**:
| 字段 | 类型 | 说明 |
|------|------|------|
| id | uuid | 文件夹 ID |
| workspace_id | uuid | 所属工作区 |
| folder_type | string | 类型: "project" 或 "asset" |
| name | string | 文件夹名称 (1-100 字符) |
| color | string | 颜色: slate/red/orange/amber/emerald/cyan/blue/violet |
| sort_order | int | 排序顺序 |
| item_count | int | 包含项目/资产数量 (计算字段) |
| created_by | string | 创建者 user_id |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### GET `/folders`

获取文件夹列表。

**认证**: 必须

**限流**: 60/minute

**参数**:
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| folder_type | string | 是 | - | "project" 或 "asset" |

**响应**:
```json
{
  "items": [
    {
      "id": "uuid-xxx",
      "workspace_id": "ws_xxx",
      "folder_type": "project",
      "name": "My Folder",
      "color": "blue",
      "sort_order": 0,
      "item_count": 5,
      "created_by": "user_xxx",
      "created_at": "2026-01-28T10:00:00Z",
      "updated_at": "2026-01-28T10:00:00Z"
    }
  ],
  "total": 3
}
```

### POST `/folders`

创建新文件夹。

**认证**: 必须

**限流**: 30/minute

**请求体**:
```json
{
  "folder_type": "project",
  "name": "My Folder",
  "color": "blue"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| folder_type | string | 是 | "project" 或 "asset" |
| name | string | 是 | 1-100 字符 |
| color | string | 否 | 默认 "slate" |

**验证规则**:
- name 在同一 workspace + folder_type 下必须唯一

**响应**: 创建的 Folder 对象

**错误**:
- `400`: 名称已存在或参数无效

### GET `/folders/{folder_id}`

获取文件夹详情。

**认证**: 必须

**响应**: Folder 对象

**错误**:
- `404`: 文件夹不存在或无权访问

### PATCH `/folders/{folder_id}`

更新文件夹。

**认证**: 必须

**限流**: 30/minute

**请求体**:
```json
{
  "name": "Updated Name",
  "color": "violet"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 否 | 新名称 |
| color | string | 否 | 新颜色 |

**响应**: 更新后的 Folder 对象

**错误**:
- `400`: 名称冲突
- `404`: 文件夹不存在

### DELETE `/folders/{folder_id}`

删除文件夹。

**认证**: 必须

**限流**: 30/minute

**说明**: 删除文件夹后，其中的项目/资产会移到根目录 (folder_id=NULL)。

**响应**:
```json
{
  "success": true,
  "message": "Folder deleted"
}
```

**错误**:
- `404`: 文件夹不存在

### POST `/folders/reorder`

重新排序文件夹。

**认证**: 必须

**限流**: 30/minute

**请求体**:
```json
{
  "folder_type": "project",
  "folder_ids": ["uuid-1", "uuid-2", "uuid-3"]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| folder_type | string | 是 | "project" 或 "asset" |
| folder_ids | array | 是 | 排序后的文件夹 ID 列表 |

**验证规则**:
- 所有 folder_ids 必须属于当前 workspace

**响应**:
```json
{
  "success": true
}
```

**错误**:
- `400`: 包含无效文件夹 ID

---

*文档版本: v3.34*
*最后更新: 2026-01-28*
*更新内容:
- v3.34: 路由顺序修复 (2026-01-28)
  - 修复: `GET /projects/starred` 和 `GET /projects/folder/{folder_id}` 返回 404
  - 原因: FastAPI 路由匹配顺序问题，`/{project_id}` 通配符先于具体路由
  - 解决: 将 `/starred` 和 `/folder/{folder_id}` 移至 `/{project_id}` 之前
- v3.33: 新增 Folder + Star 系统 (14 个端点)
  - 新增: Folders 文件夹 (6个端点) - CRUD、重排序
  - 新增: Projects 移动/收藏 (4个端点) - move/star/folder/starred
  - 新增: Assets 移动/收藏 (4个端点) - move/star/folder/starred
  - 总端点数: 148 → 162
- v3.43: 新增 Workspace + Tag 系统 (20 个端点)
  - 新增: Workspaces 工作区 (6个端点) - CRUD、统计
  - 新增: Tags 标签系统 (6个端点) - CRUD、预设、分组
  - 新增: Project Tags 项目标签 (4个端点) - 项目-标签关联
  - 新增: Asset Tags 素材标签 (4个端点) - 素材-标签关联
  - 总端点数: 128 → 148
- v3.40: DDD 合规审计修复
  - 修复: `GET /projects/dashboard` 响应格式改为 `{items, total, offset, limit, has_more}`
  - 修复: `GET /referrals` 响应格式改为 DDD 标准分页格式 `{items, total, offset, limit, has_more}`
  - 新增: `GET /referrals` 添加 offset/limit 分页参数
- v3.39: API 整合优化 - 新增统一 Seller 模块 (1个端点)，删除 7 个冗余端点
  - 新增: `GET /seller/stats` 统一卖家统计 (整合 projects/marketplace/assets)
  - 删除: `GET /projects/seller-stats`, `GET /marketplace/seller/stats`, `GET /user_assets/seller-stats`
  - 删除: `GET /resources/stickers`, `GET /resources/backgrounds`, `GET /resources/templates` (使用 `?resource_type=` 参数)
  - 删除: `POST /generations/{id}/favorite`, `DELETE /generations/batch`, `POST /export/zip` (废弃端点)
- v3.36: 新增 Pages 静态页面内容模块 (2个公开端点)，支持 CMS 动态内容管理
- v3.35: 新增 Feature Flags 客户端端点 (4个)
- v3.33: 新增 Articles 文章模块 (4个公开端点)
- v3.32: 完整记录 123 个 User API 端点
- 包含所有请求参数、响应格式、验证规则和限流配置
- 按 34 个模块分类组织
- DDD 架构合规: 100%
- 测试覆盖率: 65%+*
