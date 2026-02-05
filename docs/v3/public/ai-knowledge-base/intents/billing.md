# 计费相关意图

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充

---

## 意图列表

### intent_billing_plans

**触发词**: 套餐、价格、多少钱、plans

**回复模板**: `responses/billing.md#plans`

---

### intent_billing_upgrade

**触发词**: 升级、upgrade

**回复模板**: `responses/billing.md#upgrade`

---

### intent_billing_downgrade

**触发词**: 降级、downgrade

**回复模板**: `responses/billing.md#downgrade`

---

### intent_billing_cancel

**触发词**: 取消订阅、退订、cancel

**回复模板**: `responses/billing.md#cancel`

**升级标识**: 敏感操作，可能需要转人工

---

### intent_billing_refund

**触发词**: 退款、refund

**回复模板**: `responses/billing.md#refund`

**升级标识**: 高敏感操作，建议转人工

---

### intent_billing_credits

**触发词**: 积分、credits、点数

**回复模板**: `responses/billing.md#credits`

---

### intent_billing_invoice

**触发词**: 发票、invoice、账单

**回复模板**: `responses/billing.md#invoice`
