# Marketplace 主页体验

> Marketplace 页面体验与关键流程说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/marketplace/`

---

## 背景

- 问题或机会: 提供可筛选的素材/模板市场入口
- 目标与非目标: 目标是浏览/购买内容；非目标是发布流程

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 旧文档仅作证据参考，需用新结构重写表达
- 必须明确“唯一归属”，避免重复描述

## 结论/规范/方案

- 关键结论与约束: AuthGate + 用户数据初始化后渲染
- 必须遵循的规则: 未登录重定向 `/login?redirect=/marketplace`

## 详细说明

- 页面结构与关键区域:
  - 顶部导航 + ContentGuidelines
  - Tabs + 搜索 + FilterSidebar
  - 列表/虚拟列表 + 详情预览
  - 购买确认/举报弹窗
- 关键用户路径与状态:
  - filters 与 URL 同步（防抖搜索）
  - 购买流程：确认 → executePurchase → 标记 is_owned
  - 举报流程：ReportDialog 提交
  - 排行榜 tab 使用 LeaderboardSection
- PC/Mobile 差异: 移动端使用 MobileFilterSheet 与无限滚动

## 影响范围

- 相关模块: user-experience/marketplace
- 相关文档: `docs/v2/04-features/README.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/marketplace/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
