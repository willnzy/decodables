# 推荐与返利系统设计

> 推荐与返利能力的系统设计说明。

**状态**: draft  
**版本**: 0.2.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables/domains/referrals/`, `decodables/api/user/referrals.py`

---

## 背景

- 需要统一推荐机制与奖励规则
- 需要明确归因与结算边界

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 定义推荐关系与奖励触发条件
- 规范奖励发放与撤销规则
- 支持活动与渠道扩展

## 能力清单

- 推荐码与分享入口
- 推荐关系追踪
- 奖励发放与统计

## 关键流程

- 分享 → 注册/购买 → 归因 → 发放奖励

## 规则与护栏

- 归因需去重与时效限制
- 奖励发放需校验有效交易
- 异常与作弊需冻结与审计

## 状态与类型

- 归因状态：`pending` / `approved` / `rejected`
- 奖励状态：`earned` / `granted` / `revoked`

## 数据结构

- ReferralCode：`id` / `user_id` / `code` / `status`
- ReferralReward：`referrer_id` / `referred_id` / `amount` / `status`

## 前端交互要点

- 推荐码一键复制与分享
- 归因与奖励列表展示
- 异常状态提示与说明

## 实现边界（现状）

- 归因窗口与奖励规则以后端配置为准

## 影响范围

- 相关模块：推荐与返利
- 相关文档：`docs/v2/03-business/entitlement/referral-rewards.md`

## 证据与验证

- 关键证据来源：`decodables/domains/referrals/`、`decodables/api/user/referrals.py`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
| 2026-02-04 | 0.2.0 | 补充推荐与返利系统设计细节 | Docs Working Group |
