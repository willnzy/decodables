 # Articles 系统设计
 
 > 后台文章系统的结构、流程与运营能力。
 
 **状态**: draft  
**版本**: 0.2.0  
 **版本日期**: 2026-02-04  
 **最后复核**: 2026-02-04  
 **负责人**: Docs Working Group  
 **适用范围**: shared  
 **source_repo**: both  
 **sync_required**: yes  
**来源/依据**: `decodables-fe/app/admin/articles/`, `decodables-fe/app/admin/articles/_lib/api.ts`, `decodables-fe/app/admin/articles/_lib/types.ts`, `decodables/api/admin/articles.py`
 
 ---
 
## 背景

- 管理后台需要统一维护站内/帮助中心内容
- 需要覆盖草稿/发布的全生命周期管理
- 需要支撑 SEO 与运营审计

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 统一文章管理能力与运营流程
- 明确内容结构、分类与发布机制
- 支持 SEO 与排序控制
- 降低内容发布风险与误操作成本

## 能力清单

- 列表/详情/创建/更新/删除
- 发布/撤回（草稿/已发布）
- 分类、标签与排序管理
- Slug 生成/校验与预览链接
- SEO 字段编辑（meta/canonical/noindex）

## 关键流程

- 列表筛选 → 打开编辑器 → 保存草稿/发布
- 更新内容 → 发布/撤回 → 同步展示

## 规则与护栏

- 分类限定：`manual` / `news` / `changelog` / `faq` / `troubleshooting`
- 标题/摘要/slug 字段长度与格式校验
- 标签数量上限与去重（前端 10 个）
- 发布要求：标题 + slug + 正文必填
- 排序权重非负（数值越小越靠前）
- 统一分页：`offset` + `limit`
- 管理员权限、接口限流与审计日志
- 限流：列表/详情 30/min；写操作 10/min

## 状态与类型

- 文章状态：`draft` / `published`
- 分类：`manual` / `news` / `changelog` / `faq` / `troubleshooting`
- 列表筛选：`category` / `search` / `status` / `sort_by` / `sort_order`
- URL 分页：`page` → `offset` 映射

## 数据结构

- ArticleSummary：`id` / `slug` / `title` / `summary` / `category` / `tags` / `is_published` / `published_at` / `view_count`
- ArticleFull：`content` / `cover_image` / `author_id` / `sort_order` / `seo`
- SEO：`meta_title` / `meta_description` / `og_image` / `canonical_url` / `noindex`

## 前端交互要点

- 列表：分类 Tabs、搜索、分页、空状态、失败重试、刷新
- 编辑器：弹窗式编辑，支持标题/slug/分类/标签/摘要/正文/排序/SEO
- 预览链接：`news/changelog` → `/news/[slug]`，其他 → `/manual/[slug]`

## 实现边界（现状）

- 列表接口仅支持 `category` / `include_drafts` / `offset` / `limit`
- `search` / `status` / `sort_by` / `sort_order` 为前端占位参数
- `check-slug` 与 `stats` 接口仅在前端定义，后端未实现

## 接口清单（Admin）

- `GET /api/v2/admin/articles`
- `GET /api/v2/admin/articles/{id}`
- `POST /api/v2/admin/articles`
- `PUT /api/v2/admin/articles/{id}`
- `DELETE /api/v2/admin/articles/{id}`
- `POST /api/v2/admin/articles/{id}/publish`
- `POST /api/v2/admin/articles/{id}/unpublish`

## 影响范围

- 相关模块：Articles 系统
- 相关文档：`docs/v2/05-api/admin-endpoints.md`、`docs/v2/05-api/api-reference.md`

## 证据与验证

- 关键证据来源：`decodables/api/admin/articles.py`、`decodables/domains/content/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
| 2026-02-04 | 0.2.0 | 补充后台文章系统设计细节 | Docs Working Group |
