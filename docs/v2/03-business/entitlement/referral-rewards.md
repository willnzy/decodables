# 邀请奖励规则

> 邀请奖励机制、限制与风控规则。

**状态**: active  
**版本**: 2.2.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Product Team  
**适用范围**: shared  
**source_repo**: backend  
**sync_required**: yes

---

## 背景

- 需要统一邀请奖励机制与风控规则
- 明确奖励发放条件与限制

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 奖励机制

| 角色 | 配置 key | 说明 |
|------|----------|------|
| 邀请人 | `referral.referrer_reward` | 完成注册后奖励 |
| 被邀请人 | `referral.referee_reward` | 完成注册后奖励 |

奖励积分 source_type 为 `bonus_referral`。

---

## 邀请流程

1. 用户生成邀请码与邀请链接  
2. 被邀请人通过链接注册  
3. 注册成功后双向奖励发放

---

## 限制与风控

- 同 IP/设备限制
- 单日奖励上限
- 风控延迟发放

---

## 数据结构（摘要）

- `referrals` 邀请记录表  
- `referral_codes` 邀请码表

## 影响范围

- 相关模块：邀请奖励与积分
- 相关文档：`docs/v2/03-business/entitlement/credits-lifecycle.md`

## 证据与验证

- 关键证据来源：`decodables/domains/billing/`、`decodables/api/user/referrals.py`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 2.2.0 | 结构对齐模板 | Docs Working Group |
