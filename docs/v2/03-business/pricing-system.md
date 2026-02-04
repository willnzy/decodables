# 定价系统设计

> 价格配置系统的统一设计与治理。

**状态**: needs-review  
**版本**: 1.1.0  
**版本日期**: 2026-01-12  
**最后复核**: 2026-02-04  
**负责人**: Backend Team  
**适用范围**: shared  
**source_repo**: backend  
**sync_required**: yes

---

## 背景

- 需要统一价格配置与治理方式
- 明确价格优先级与审计要求

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 核心原则

- 价格配置数据库化
- 支持原价/现价双定价
- 保留历史版本与审计

---

## 核心表设计（摘要）

### pricing_plans

- plan_code / plan_type / price_cents / original_price_cents
- subscription 与 credits 两类

### pricing_history

- 记录每次价格变更

### user_price_overrides

- 用户级价格覆盖

---

## 使用优先级

```
1. user_price_overrides
2. pricing_plans
3. system_configs (旧配置 fallback)
4. constants (最终 fallback)
```

---

## 相关文档

- `docs/v2/03-business/entitlement/permission-matrix.md`

## 影响范围

- 相关模块：定价系统、订阅与积分
- 相关文档：`docs/v2/03-business/entitlement/permission-matrix.md`

## 证据与验证

- 关键证据来源：`decodables/domains/billing/`、`decodables/infrastructure/repositories/payment_repository.py`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 1.1.0 | 结构对齐模板 | Docs Working Group |
