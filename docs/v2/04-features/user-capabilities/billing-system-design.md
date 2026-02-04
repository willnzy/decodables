# 计费与积分系统设计

> 订阅、积分与扣费规则的系统设计说明。

**状态**: draft  
**版本**: 0.1.0  
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
