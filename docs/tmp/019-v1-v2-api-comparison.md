# v1/v2 API 功能差异对比报告

> **生成时间**: 2026-01-08
> **对比对象**: routers/ (v1) vs api/ (v2)
> **对比数量**: 17 对路由

---

## 📊 总体统计

| 指标 | v1 (routers/) | v2 (api/) | 差异 |
|------|---------------|-----------|------|
| **总端点数** | 30 | 6 | -24 |
| **缺失端点** | - | - | 25 ❌ |
| **新增端点** | - | - | 1 ✨ |
| **覆盖率** | 100% | 20.0% | - |

**关键发现**:
- ✅ v2 已实现 6 个端点
- ❌ v2 缺失 25 个端点
- ✨ v2 新增 1 个端点

---

## 🎯 优先级分组

### 🔴 P0 - 核心功能 (极高优先级)

| 路由对 | v1 端点 | v2 端点 | 缺失 | 新增 | 状态 |
|--------|---------|---------|------|------|------|
| generation | 0 | 0 | 0 | 0 | ✅ 完整 |
| generations | 0 | 0 | 0 | 0 | ✅ 完整 |
| payment | 2 | 0 | 2 | 0 | ❌ 缺 2 |
| webhooks | 0 | 0 | 0 | 0 | ✅ 完整 |

### 🟠 P1 - 高频功能 (高优先级)

| 路由对 | v1 端点 | v2 端点 | 缺失 | 新增 | 状态 |
|--------|---------|---------|------|------|------|
| campaigns | 0 | 0 | 0 | 0 | ✅ 完整 |
| marketplace | 11 | 0 | 11 | 0 | ❌ 缺 11 |
| projects | 8 | 0 | 8 | 0 | ❌ 缺 8 |
| templates | 0 | 0 | 0 | 0 | ✅ 完整 |

### 🟡 P2 - 常用功能 (中优先级)

| 路由对 | v1 端点 | v2 端点 | 缺失 | 新增 | 状态 |
|--------|---------|---------|------|------|------|
| analytics | 0 | 0 | 0 | 0 | ✅ 完整 |
| config | 2 | 2 | 0 | 0 | ✅ 完整 |
| resources | 0 | 0 | 0 | 0 | ✅ 完整 |
| tasks | 0 | 0 | 0 | 0 | ✅ 完整 |
| themes | 0 | 0 | 0 | 0 | ✅ 完整 |

### 🟢 P3 - 低频功能 (低优先级)

| 路由对 | v1 端点 | v2 端点 | 缺失 | 新增 | 状态 |
|--------|---------|---------|------|------|------|
| export | 4 | 4 | 1 | 1 | ❌ 缺 1 |
| logs | 0 | 0 | 0 | 0 | ✅ 完整 |
| support | 3 | 0 | 3 | 0 | ❌ 缺 3 |
| tools | 0 | 0 | 0 | 0 | ✅ 完整 |

---

## 📋 详细对比

### analytics (routers/analytics.py ↔ api/analytics_api.py)

#### v1 端点:

(无端点)


#### v2 端点:

(无端点)


---

### campaigns (routers/campaigns.py ↔ api/campaigns_api.py)

#### v1 端点:

(无端点)


#### v2 端点:

(无端点)


---

### config (routers/config.py ↔ api/config_api.py)

#### v1 端点:

| 方法 | 路径 | 函数名 | 认证 |
|------|------|--------|------|
| GET | `/{key}` | get_config | 🔓 |
| GET | `/group/{group_name}` | get_group | 🔓 |

#### v2 端点:

| 方法 | 路径 | 函数名 | 认证 |
|------|------|--------|------|
| GET | `/group/{group_name}` | get_group | 🔓 |
| GET | `/{key}` | get_config | 🔓 |

---

### export (routers/export.py ↔ api/export_api.py)

#### v1 端点:

| 方法 | 路径 | 函数名 | 认证 |
|------|------|--------|------|
| GET | `/api/projects/{project_id}/pdf` | get_project_pdf | 🔒 |
| GET | `/api/projects/{project_id}/preview` | preview_project_as_image | 🔒 |
| POST | `/api/export/zip` | dl_zip | 🔒 |
| GET | `/api/projects/{project_id}/zip` | get_project_zip | 🔒 |

#### v2 端点:

| 方法 | 路径 | 函数名 | 认证 |
|------|------|--------|------|
| GET | `/projects/{project_id}/pdf` | export_project_pdf | 🔒 |
| GET | `/projects/{project_id}/preview` | export_project_preview | 🔒 |
| POST | `/zip` | export_zip | 🔒 |
| GET | `/projects/{project_id}/zip` | export_project_zip | 🔒 |

#### ❌ v2 缺失的端点 (1 个):

| 方法 | 路径 | 函数名 |
|------|------|--------|
| POST | `/api/export/zip` | dl_zip |

#### ✨ v2 新增的端点 (1 个):

| 方法 | 路径 | 函数名 |
|------|------|--------|
| POST | `/zip` | export_zip |

---

### generation (routers/generation.py ↔ api/generation_api.py)

#### v1 端点:

(无端点)


#### v2 端点:

(无端点)


---

### generations (routers/generations.py ↔ api/generations_api.py)

#### v1 端点:

(无端点)


#### v2 端点:

(无端点)


---

### logs (routers/logs.py ↔ api/logs_api.py)

#### v1 端点:

(无端点)


#### v2 端点:

(无端点)


---

### marketplace (routers/marketplace.py ↔ api/marketplace_api.py)

#### v1 端点:

| 方法 | 路径 | 函数名 | 认证 |
|------|------|--------|------|
| GET | `/items` | list_items | 🔒 |
| GET | `/item/{listing_id}` | get_item | 🔒 |
| POST | `/publish` | publish_item | 🔓 |
| POST | `/unpublish` | unpublish_item | 🔒 |
| POST | `/purchase` | purchase_item | 🔒 |
| GET | `/my-listings` | get_my_listings | 🔒 |
| PUT | `/listings/{listing_id}` | update_listing | 🔒 |
| GET | `/seller/stats` | get_seller_stats | 🔒 |
| GET | `/leaderboard` | get_leaderboard_data | 🔒 |
| POST | `/report` | submit_report | 🔒 |
| GET | `/my-reports` | get_my_reports | 🔒 |

#### v2 端点:

(无端点)


#### ❌ v2 缺失的端点 (11 个):

| 方法 | 路径 | 函数名 |
|------|------|--------|
| POST | `/purchase` | purchase_item |
| GET | `/items` | list_items |
| GET | `/item/{listing_id}` | get_item |
| POST | `/unpublish` | unpublish_item |
| GET | `/my-reports` | get_my_reports |
| PUT | `/listings/{listing_id}` | update_listing |
| GET | `/seller/stats` | get_seller_stats |
| GET | `/leaderboard` | get_leaderboard_data |
| POST | `/publish` | publish_item |
| GET | `/my-listings` | get_my_listings |
| POST | `/report` | submit_report |

---

### payment (routers/payment.py ↔ api/payment_api.py)

#### v1 端点:

| 方法 | 路径 | 函数名 | 认证 |
|------|------|--------|------|
| POST | `/checkout` | create_checkout | 🔒 |
| POST | `/portal` | get_portal | 🔒 |

#### v2 端点:

(无端点)


#### ❌ v2 缺失的端点 (2 个):

| 方法 | 路径 | 函数名 |
|------|------|--------|
| POST | `/portal` | get_portal |
| POST | `/checkout` | create_checkout |

---

### projects (routers/projects.py ↔ api/projects_api.py)

#### v1 端点:

| 方法 | 路径 | 函数名 | 认证 |
|------|------|--------|------|
| GET | `/dashboard` | dashboard_projects | 🔒 |
| GET | `/deleted` | list_deleted_projects | 🔒 |
| GET | `/seller-stats` | get_project_seller_stats | 🔒 |
| GET | `/{project_id}` | get_project | 🔒 |
| PUT | `/{project_id}` | update_project | 🔒 |
| DELETE | `/{project_id}` | delete_project | 🔒 |
| POST | `/{project_id}/restore` | restore_project | 🔒 |
| POST | `/{project_id}/duplicate` | duplicate_project_endpoint | 🔒 |

#### v2 端点:

(无端点)


#### ❌ v2 缺失的端点 (8 个):

| 方法 | 路径 | 函数名 |
|------|------|--------|
| POST | `/{project_id}/restore` | restore_project |
| GET | `/{project_id}` | get_project |
| DELETE | `/{project_id}` | delete_project |
| GET | `/deleted` | list_deleted_projects |
| GET | `/dashboard` | dashboard_projects |
| GET | `/seller-stats` | get_project_seller_stats |
| PUT | `/{project_id}` | update_project |
| POST | `/{project_id}/duplicate` | duplicate_project_endpoint |

---

### resources (routers/resources.py ↔ api/resources_api.py)

#### v1 端点:

(无端点)


#### v2 端点:

(无端点)


---

### support (routers/support.py ↔ api/support_api.py)

#### v1 端点:

| 方法 | 路径 | 函数名 | 认证 |
|------|------|--------|------|
| POST | `/api/support/email` | ticket | 🔒 |
| POST | `/api/contact` | contact | 🔒 |
| POST | `/api/feedback` | feedback | 🔒 |

#### v2 端点:

(无端点)


#### ❌ v2 缺失的端点 (3 个):

| 方法 | 路径 | 函数名 |
|------|------|--------|
| POST | `/api/contact` | contact |
| POST | `/api/feedback` | feedback |
| POST | `/api/support/email` | ticket |

---

### tasks (routers/tasks.py ↔ api/tasks_api.py)

#### v1 端点:

(无端点)


#### v2 端点:

(无端点)


---

### templates (routers/templates.py ↔ api/templates_api.py)

#### v1 端点:

(无端点)


#### v2 端点:

(无端点)


---

### themes (routers/themes.py ↔ api/themes_api.py)

#### v1 端点:

(无端点)


#### v2 端点:

(无端点)


---

### tools (routers/tools.py ↔ api/tools_api.py)

#### v1 端点:

(无端点)


#### v2 端点:

(无端点)


---

### webhooks (routers/webhooks.py ↔ api/webhooks_api.py)

#### v1 端点:

(无端点)


#### v2 端点:

(无端点)


---


## 🎯 下一步行动

### Stage 2: 补全缺失端点 (共 25 个)

#### 优先级划分:
- 🔴 P0 (核心功能): 2 个端点 - **必须先补全**
- 🟠 P1 (高频功能): 19 个端点
- 🟡 P2 (常用功能): 0 个端点
- 🟢 P3 (低频功能): 4 个端点

#### 补全计划:
1. **Day 1-2**: P0 端点 (payment, webhooks, generation)
2. **Day 3-4**: P1 端点 (projects, marketplace, campaigns, templates)
3. **Day 5-7**: P2 + P3 端点 (其余路由)

---

**生成脚本**: scripts/compare_v1_v2_apis.py
**后续步骤**: 查看 docs/tmp/018-phase-9-10-execution-plan.md