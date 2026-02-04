# Dashboard 体验

> Dashboard 页面体验与关键流程说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/dashboard/`

---

## 背景

- 问题或机会: 提供登录后入口，汇总用户项目与关键操作
- 目标与非目标: 目标是展示用户工作区与快捷操作；非目标是编辑器细节

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 旧文档仅作证据参考，需用新结构重写表达
- 必须明确“唯一归属”，避免重复描述

## 结论/规范/方案

- 关键结论与约束: 页面入口通过 AuthGate 控制鉴权
- 必须遵循的规则: AuthGate 未加载时显示 Loading

## 详细说明

- 页面结构与关键区域:
  - `DashboardAuthGate` 处理登录态
  - `DashboardContent` 渲染主界面（由 AuthGate 内部管理）
- 关键用户路径与状态:
  - 未登录 → AuthGate 负责引导登录
  - 已登录 → 渲染 Dashboard 内容
- PC/Mobile 差异: 由内部内容组件负责

## 影响范围

- 相关模块: user-experience/dashboard
- 相关文档: `docs/v2/04-features/README.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/dashboard/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
