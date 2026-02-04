# Marketplace 系统设计

> 市场能力范围、交易规则与内容治理说明。

**状态**: draft  
**版本**: 0.2.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/marketplace/`, `decodables/domains/marketplace/`

---

## 背景

- 需要统一市场能力范围与交易边界
- 需要明确内容举报与治理流程

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 提供内容浏览、筛选与购买能力
- 明确交易规则与权益限制
- 建立举报与合规处理机制

## 能力清单

- 列表与筛选
- 购买与归属管理
- 内容举报与审核联动

## 关键流程

- 浏览 → 筛选 → 详情 → 购买确认
- 举报 → 处理 → 状态反馈

## 规则与护栏

- 交易与退款规则遵循 billing 与权限配置
- 举报入口需鉴权与频控
- 购买与下载需校验资产归属

## 状态与类型

- 交易状态：`pending` / `paid` / `refunded`（以支付系统为准）
- 举报状态：`pending` / `resolved` / `dismissed`（以审核系统为准）

## 数据结构

- Listing：`id` / `title` / `price` / `seller_id` / `status`
- Purchase：`order_id` / `asset_id` / `buyer_id` / `status`

## 前端交互要点

- 筛选/排序与搜索联动
- 购买确认弹窗与购买后权益提示
- 举报入口与处理状态回显

## 实现边界（现状）

- 交易状态与退款规则以支付系统为准

## 影响范围

- 相关模块：Marketplace
- 相关文档：`docs/v2/10-product/user/marketplace/marketplace.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/marketplace/`、`decodables/domains/marketplace/`、`decodables/api/user/marketplace.py`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
| 2026-02-04 | 0.2.0 | 补充 Marketplace 系统设计细节 | Docs Working Group |
