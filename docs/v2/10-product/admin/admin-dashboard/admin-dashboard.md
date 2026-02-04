# Admin 主页体验

> Admin 主页体验与关键流程说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/admin/page.tsx`

---

## 背景

- 问题或机会: 提供统一的管理员入口与多模块导航
- 目标与非目标: 目标是管理面板入口；非目标是移动端访问

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 旧文档仅作证据参考，需用新结构重写表达
- 必须明确“唯一归属”，避免重复描述

## 结论/规范/方案

- 关键结论与约束: AuthGate + URL 驱动 tab；非管理员显示拒绝
- 必须遵循的规则: 未登录重定向 `/login?redirect=/admin`

## 详细说明

- 页面结构与关键区域:
  - Header + AdminTabs
  - 主区渲染当前 tab 内容
  - AdminPanels 底部面板
- 管理路径与状态:
  - 加载态：AdminLoading
  - 未登录跳转登录
  - role 非 admin 显示 AccessDenied
  - tab 通过 `?tab=` 切换
- PC/Mobile 差异: 移动端返回 MobileBlocker

## 影响范围

- 相关模块: admin-experience/admin-dashboard
- 相关文档: `docs/v2/04-features/README.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/admin/page.tsx`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
