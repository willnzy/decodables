# 服务条款页面体验

> 服务条款页面体验与关键流程说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/terms-of-service/`

---

## 背景

- 问题或机会: 需要明确平台使用条款与法律约束
- 目标与非目标: 目标是展示可动态更新的服务条款；非目标是条款编辑

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 旧文档仅作证据参考，需用新结构重写表达
- 必须明确“唯一归属”，避免重复描述

## 结论/规范/方案

- 关键结论与约束: StaticPageLayout + StaticPageRenderer；ISR 1 小时
- 必须遵循的规则: 内容从服务端获取，API 失败时使用 fallback

## 详细说明

- 页面结构与关键区域:
  - 统一静态页面布局（标题/副标题/徽标/更新时间）
  - Markdown 正文渲染（支持模板变量）
- 关键用户路径与状态:
  - 并行获取 pageData 与 template context
  - 取 pageData 或 fallback 内容
  - 依据 last_updated_display 展示更新时间
- PC/Mobile 差异: 由 StaticPageLayout 内部响应式控制

## 影响范围

- 相关模块: user-experience/dashboard
- 相关文档: `docs/v2/04-features/README.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/terms-of-service/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
