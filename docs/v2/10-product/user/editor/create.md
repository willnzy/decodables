# 编辑器页面体验

> 编辑器页面体验与关键流程说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/create/page.tsx`

---

## 背景

- 问题或机会: 提供受控的编辑器入口，避免未登录调用 API
- 目标与非目标: 目标是加载编辑器；非目标是营销入口页

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 旧文档仅作证据参考，需用新结构重写表达
- 必须明确“唯一归属”，避免重复描述

## 结论/规范/方案

- 关键结论与约束: AuthGate + Suspense + Skeleton
- 必须遵循的规则: 未登录重定向 `/login?redirect=/create`

## 详细说明

- 页面结构与关键区域:
  - EditorAuthGate
  - EditorSkeleton
  - EditorContent
- 关键用户路径与状态:
  - auth 未完成显示 skeleton
  - 未登录跳转登录
  - 等待 userStore 初始化后渲染 EditorContent
- PC/Mobile 差异: 由编辑器内部布局决定

## 影响范围

- 相关模块: user-experience/editor
- 相关文档: `docs/v2/04-features/README.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/create/page.tsx`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
