# Manual 列表体验

> Manual 列表页体验与关键流程说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/manual/`

---

## 背景

- 问题或机会: 提供 SEO 友好的帮助中心与教程入口
- 目标与非目标: 目标是展示教程/FAQ/排障内容；非目标是编辑器内帮助

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 旧文档仅作证据参考，需用新结构重写表达
- 必须明确“唯一归属”，避免重复描述

## 结论/规范/方案

- 关键结论与约束: 服务端渲染 + ISR（1h）+ FAQ Schema
- 必须遵循的规则: 文章数据服务端获取；筛选在客户端进行

## 详细说明

- 页面结构与关键区域:
  - 顶部导航 + Hero 区
  - Featured Guides
  - 筛选与列表（ManualFiltersClient）
  - FAQ 与 Troubleshooting 区块
  - CTA + FloatingCTA
- 关键用户路径与状态:
  - ISR 每小时重新验证
  - 点击文章进入 `/manual/[slug]`
  - 筛选在客户端完成，不重新请求
- PC/Mobile 差异: 由组件内部响应式处理

## 影响范围

- 相关模块: user-experience/dashboard
- 相关文档: `docs/v2/04-features/README.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/manual/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
