# 文章管理页面体验

> 文章管理页面体验与关键流程说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/admin/articles/`

---

## 背景

- 问题或机会: 需要统一管理站点与帮助中心文章
- 目标与非目标: 目标是 CMS 管理；非目标是前台阅读体验

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 旧文档仅作证据参考，需用新结构重写表达
- 必须明确“唯一归属”，避免重复描述

## 结论/规范/方案

- 关键结论与约束: 列表 + 编辑对话框
- 必须遵循的规则: 新建文章默认继承 URL 的 category

## 详细说明

- 页面结构与关键区域:
  - ArticleListPanel
  - ArticleEditorDialog
  - Skeleton 加载态
- 管理路径与状态:
  - 点击新建/编辑打开编辑器
  - 关闭编辑器清理编辑状态
  - Suspense 包裹内容
- PC/Mobile 差异: 无特定差异

## 影响范围

- 相关模块: admin-experience/content-management
- 相关文档: `docs/v2/04-features/README.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/admin/articles/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
