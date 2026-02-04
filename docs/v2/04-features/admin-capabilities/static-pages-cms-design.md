 # Static Pages CMS 设计
 
 > 静态页面内容管理与发布机制说明。
 
 **状态**: draft  
**版本**: 0.2.0  
 **版本日期**: 2026-02-04  
 **最后复核**: 2026-02-04  
 **负责人**: Docs Working Group  
 **适用范围**: shared  
 **source_repo**: both  
 **sync_required**: yes  
**来源/依据**: `decodables-fe/app/admin/content/`, `decodables-fe/app/admin/content/_components/StaticPagesPanel.tsx`, `decodables-fe/app/admin/content/_lib/api.ts`, `decodables-fe/app/admin/content/_lib/types.ts`, `decodables/api/admin/static_pages.py`, `decodables/domains/static_pages/`
 
 ---
 
## 背景

- 需要统一静态内容发布与回滚流程
- 需要覆盖 SEO 与合规页面的全生命周期管理
- 需要对外一致的内容展示入口与审核路径

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 统一静态内容发布与回滚流程
- 明确页面类型、模板与 SEO 规则
- 降低错误发布与合规风险

## 能力清单

- 列表/详情/创建/更新/删除
- 发布/撤回（草稿/已发布）
- 页面类型与排序管理
- SEO 字段编辑与预览
- 搜索与分页

## 关键流程

- 列表筛选 → 打开编辑器 → 保存草稿/发布
- 更新内容 → 发布/撤回 → 同步展示

## 规则与护栏

- page_type 限定：`legal` / `company` / `guide` / `other`
- slug/title/content 字段长度与格式校验
- 发布要求：slug + title + content 必填
- 排序权重非负（数值越小越靠前）
- 统一分页：`offset` + `limit`
- 管理员权限、接口限流
- 限流：列表/详情 30/min；写操作 10/min

## 状态与类型

- 发布状态：`draft` / `published`
- 页面类型：`legal` / `company` / `guide` / `other`
- 列表筛选：`page_type` / `include_drafts` / `offset` / `limit`

## 数据结构

- StaticPageSummary：`id` / `slug` / `title` / `subtitle` / `page_type` / `icon` / `is_published` / `last_updated_display`
- StaticPageFull：`content` / `hero_gradient` / `meta_title` / `meta_description` / `schema_data` / `extra_data`
- SEO：`meta_title` / `meta_description` / `schema_data`（JSON-LD）

## 前端交互要点

- 列表：搜索、状态筛选、分页、空状态、刷新
- 编辑器：内容/SEO/设置三页签；Google 预览
- 预览链接：已发布页面可直接跳转 slug

## 实现边界（现状）

- 后端字段为 `page_type`/`subtitle`/`icon`/`hero_gradient`/`schema_data`/`extra_data`
- 前端字段包含 `template`/`robots`/`canonical_url`/`og_image`/`status`，后端未实现
- 前端 `status` 与后端 `is_published` 语义不完全一致
- 前端 `search`/`status` 查询参数未在后端实现

## 影响范围

- 相关模块：静态页面 CMS
- 相关文档：`docs/v2/05-api/admin-endpoints.md`、`docs/v2/05-api/api-reference.md`

## 证据与验证

- 关键证据来源：`decodables/api/admin/static_pages.py`、`decodables/domains/content/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
| 2026-02-04 | 0.2.0 | 补充静态页面 CMS 设计细节 | Docs Working Group |
