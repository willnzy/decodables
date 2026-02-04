# 计费与积分系统设计

> 订阅、积分与扣费规则的系统设计说明。

**状态**: draft  
**版本**: 0.2.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables/domains/billing/`, `decodables/domains/subscriptions/`

---

## 背景

- 需要统一订阅与积分规则
- 需要明确扣费顺序与退款边界

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 统一订阅等级与权益模型
- 明确积分生命周期与扣费顺序
- 规范退款与取消的处理规则

## 能力清单

- 订阅开通/续费/取消
- 月度/永久积分管理
- 交易记录与审计

## 关键流程

- 购买订阅 → 发放月度积分 → 使用扣费
- 充值积分 → 记录交易 → 可追溯

## 规则与护栏

- 扣费顺序：`credits_monthly` → `credits_permanent`
- 订阅变更需记录交易与审计
- 退款需同步积分回滚与状态更新

## 状态与类型

- 订阅状态：`active` / `canceled` / `past_due`（以支付系统为准）
- 积分类型：`monthly` / `permanent`

## 数据结构

- Subscription：`id` / `user_id` / `tier` / `status` / `current_period_end`
- CreditLedger：`user_id` / `amount` / `credit_type` / `reason` / `created_at`

## 前端交互要点

- 交易记录支持筛选与分页
- 订阅与积分卡片状态一致性展示
- 退款或失败需明确提示与引导

## 实现边界（现状）

- 订阅状态与退款规则以支付系统为准

## 影响范围

- 相关模块：计费与积分
- 相关文档：`docs/v2/10-product/user/profile/transaction-history.md`

## 证据与验证

- 关键证据来源：`decodables/domains/billing/`、`decodables/domains/subscriptions/`、`decodables/api/user/billing.py`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
| 2026-02-04 | 0.2.0 | 补充计费与积分系统设计细节 | Docs Working Group |
