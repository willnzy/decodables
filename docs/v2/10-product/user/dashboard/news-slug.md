# News 详情体验

> News 详情页体验与关键流程说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/news/[slug]/page.tsx`

---

## 背景

- 问题或机会: 提供 SEO 友好的新闻详情页
- 目标与非目标: 目标是展示文章与关联推荐；非目标是文章编辑

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 旧文档仅作证据参考，需用新结构重写表达
- 必须明确“唯一归属”，避免重复描述

## 结论/规范/方案

- 关键结论与约束: SSG 参数生成 + ISR（1h）+ NewsArticle Schema
- 必须遵循的规则: 文章不存在返回 404；动态 metadata 依据文章内容

## 详细说明

- 页面结构与关键区域:
  - 返回 News 列表
  - 文章标题/标签/元信息
  - 封面图（可选）
  - Markdown 内容
  - 分享按钮与关联文章
  - CTA + FloatingCTA
- 关键用户路径与状态:
  - 通过 `generateStaticParams` 预渲染全部 slug
  - `generateMetadata` 根据文章生成 SEO 元数据
  - 文章不存在调用 `notFound()`
- PC/Mobile 差异: 由组件内部响应式处理

## 影响范围

- 相关模块: user-experience/dashboard
- 相关文档: `docs/v2/04-features/README.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/news/[slug]/page.tsx`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
