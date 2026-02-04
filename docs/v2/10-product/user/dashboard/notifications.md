# 通知中心体验

> 通知中心页面体验与关键流程说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/notifications/page.tsx`

---

## 背景

- 问题或机会: 提供统一的通知中心与已读管理
- 目标与非目标: 目标是展示通知与管理已读状态；非目标是编辑器内通知

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 旧文档仅作证据参考，需用新结构重写表达
- 必须明确“唯一归属”，避免重复描述

## 结论/规范/方案

- 关键结论与约束: 页面使用 AuthGate，未登录跳转登录页
- 必须遵循的规则: 支持全量/已读/未读筛选，支持刷新与全已读

## 详细说明

- 页面结构与关键区域:
  - 顶部导航 + 返回 Dashboard
  - 筛选 Tabs（All/Unread/Read）
  - 通知列表 + 未读标记
  - 操作区：刷新、全部已读
- 关键用户路径与状态:
  - 未登录 → 跳转 `/login?redirect=/notifications`
  - 加载中 → `NotificationsLoading`
  - 点击通知 → 标记已读
  - 点击 “Mark all read” → 全部已读
- PC/Mobile 差异: 统一组件布局，移动端遵循 `pb-24` 下边距

## 影响范围

- 相关模块: user-experience/dashboard
- 相关文档: `docs/v2/04-features/README.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/notifications/page.tsx`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
