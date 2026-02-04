# Transaction History 页面体验

> Transaction History 页面体验与关键流程说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/transaction-history/page.tsx`

---

## 背景

- 问题或机会: 需要透明展示积分与订阅相关的交易记录
- 目标与非目标: 目标是查看交易明细；非目标是退款/支付操作

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 旧文档仅作证据参考，需用新结构重写表达
- 必须明确“唯一归属”，避免重复描述

## 结论/规范/方案

- 关键结论与约束: 登录后才可访问；分页加载交易记录
- 必须遵循的规则: 未登录重定向 `/login?redirect=/transaction-history`

## 详细说明

- 页面结构与关键区域:
  - 头部信息（标题/说明/余额）
  - 交易列表表格
  - 空状态与加载态
  - 分页控制
- 关键用户路径与状态:
  - Suspense + PageLoading
  - getCreditHistory(token, page, size) 拉取记录
  - 类型映射与金额展示（支付/退款/取消/积分）
  - 页码切换触发重新加载
- PC/Mobile 差异: 无特定差异，布局自适配

## 影响范围

- 相关模块: user-experience/profile
- 相关文档: `docs/v2/04-features/README.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/transaction-history/page.tsx`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
