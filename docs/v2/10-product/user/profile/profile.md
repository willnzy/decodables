# Profile 页面体验

> Profile 页面体验与关键流程说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/profile/page.tsx`

---

## 背景

- 问题或机会: 提供移动端完整的账户/订阅/积分管理入口
- 目标与非目标: 目标是移动端个人中心；非目标是桌面端设置页

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 旧文档仅作证据参考，需用新结构重写表达
- 必须明确“唯一归属”，避免重复描述

## 结论/规范/方案

- 关键结论与约束: 仅移动端展示；桌面端重定向 `/dashboard`
- 必须遵循的规则: 未登录重定向 `/login?redirect=/profile`

## 详细说明

- 页面结构与关键区域:
  - ProfileHeader / UserIdCard
  - CreditsCard / SubscriptionCard
  - QuickActions + SignOut
  - BottomNavbar + Bottom Sheets
- 关键用户路径与状态:
  - auth 未完成显示 Loading
  - 读取 userStore 初始化（tier/credits）
  - 购买积分与订阅管理跳转 Stripe
  - checkout 回调 success/canceled 提示并清理参数
- PC/Mobile 差异: 桌面端直接重定向到 `/dashboard`

## 影响范围

- 相关模块: user-experience/profile
- 相关文档: `docs/v2/04-features/README.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/profile/page.tsx`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
