# 04 - 静态页面 CMS + 资产分类 审计报告

> 审计时间: 2026-02-12 ~ 2026-02-13 | 后端: static_pages.py, asset_categories.py | 前端: /admin/content

---

## A. 静态页面 CMS (Static Pages)

### 问题清单

| 编号 | 优先级 | 问题 | 审计维度 |
|------|--------|------|---------|
| - | 🟡 P1 | PageStatus 定义包含 archived 但后端不支持；筛选用 status 但后端用 include_drafts | D17 |
| - | 🟡 P1 | 前端 types 定义了 9 个后端未实现字段: template/content_format/robots/canonical_url/og_image/author_id/author_email/view_count | D10 |
| - | 🟢 P2 | v3 文档需同步 v2 设计详情 | D2 |

### 总评

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 文档一致性 | ⚠️ | v2 详细(17字段+SEO)，v3 过于简化 |
| 文档→API | ✅ | 7 个端点 100% 覆盖 |
| API→前端 | ⚠️ | 参数映射问题 + 前端定义了后端未实现的字段 |
| DDD 合规 | ✅ | 架构合规 |
| 安全加固 | ✅ | 速率限制已配置 |

**总体评分**: 🟡 7/10 — 核心 CRUD 完整，类型定义有偏差

---

## B. 资产分类 (Asset Categories)

### 问题清单

| 编号 | 优先级 | 问题 | 审计维度 |
|------|--------|------|---------|
| - | 🔴 P0 | **标识符错误** — 后端用 slug 标识资源，前端用 id，所有操作路径错误 | D17 |
| - | 🔴 P0 | **HTTP 方法错误** — updateCategory 前端用 PUT，后端实际是 PATCH | D17 |
| - | 🔴 P0 | **字段名不匹配** — 前端 type vs 后端 asset_type; 前端 is_active vs 后端 is_visible/is_featured | D10 |
| - | 🟡 P1 | 前端缺失 2 个 API 调用: GET /tree (树形查询), GET /{slug}/resources (资源查询) | D9 |
| - | 🟡 P1 | parent_id 应为 parent_slug (创建时) | D17 |
| M1 | 🟢 P2 | **AssetCategoriesPanel.tsx 超大文件** — 985 行 (超标 3.3x)，需拆分 | D13 / CL-3.16 |
| - | 🟢 P2 | v2/v3 文档方向不一致，需澄清当前使用哪个版本 | D2 |

### 总评

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 文档一致性 | ❌ | v2 设计为通用树形系统，v3 硬编码 10 个分类，严重不一致 |
| 文档→API | ✅ | 7 个端点 100% 覆盖 |
| API→前端 | 🔴 | 路径标识符/HTTP 方法/字段名三重错误 |
| DDD 合规 | ✅ | 通过 Container DI |
| 安全加固 | ✅ | 速率限制已配置 |

**总体评分**: 🔴 4/10 — 前端实现与后端严重脱节

---

## C. 跨层审计 (D17-D25) 复核

✅ 无 v2.0 新增发现。M1 (AssetCategoriesPanel 超大文件) 和 asset_categories 字段不一致属于 v1.0 已识别问题。
