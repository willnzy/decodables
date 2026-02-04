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
