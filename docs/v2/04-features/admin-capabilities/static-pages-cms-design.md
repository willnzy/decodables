 # Static Pages CMS 设计
 
 > 静态页面内容管理与发布机制说明。
 
 **状态**: draft  
 **版本**: 0.1.0  
 **版本日期**: 2026-02-04  
 **最后复核**: 2026-02-04  
 **负责人**: Docs Working Group  
 **适用范围**: shared  
 **source_repo**: both  
 **sync_required**: yes  
 **来源/依据**: `decodables-fe/docs/shared/static-pages-cms-design.md`, `decodables/docs/shared/static-pages-cms-design.md`
 
 ---
 
## 背景

- 需要统一静态内容发布与回滚流程
- 明确页面类型与可配置项

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标
 
 - 统一静态内容发布与回滚流程
 - 明确页面类型与可配置项
 - 约束 SEO 与可访问性要求
 
## 内容模型
 
 - 页面结构与区块
 - 版本与预览
 
## 发布流程
 
 - 草稿 → 审核 → 发布 → 撤回

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
