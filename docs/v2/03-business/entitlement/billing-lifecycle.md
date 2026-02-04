# 订阅与账单生命周期

> 降级、暂停、续费、退款等流程规则。

**状态**: needs-review  
**版本**: 1.0.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Product Team  
**适用范围**: shared  
**source_repo**: backend  
**sync_required**: yes

---

## 背景

- 需要统一订阅与账单生命周期规则
- 明确退款与暂停的权益影响

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 覆盖场景

- Tier 降级
- 订阅暂停
- 账期切换
- 续费提醒
- 发票管理
- 退款处理

## 核心原则

- 权益变更即时生效
- 退款按 FEFO 逆序扣回
- 暂停期积分冻结

## 影响范围

- 相关模块：订阅、账单、退款
- 相关文档：`docs/v2/03-business/entitlement/permission-matrix.md`

## 证据与验证

- 关键证据来源：`decodables/docs/shared/entitlement/`、`decodables/domains/billing/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 1.0.0 | 结构对齐模板 | Docs Working Group |
