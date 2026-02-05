# 发票管理

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **来源**: v1 shared/entitlement/

---

## 概述

发票生成、查看和下载的管理。

---

## 发票类型

| 类型 | 触发 | 说明 |
|------|------|------|
| 订阅发票 | 订阅支付成功 | 月度/年度订阅 |
| 积分发票 | 积分包购买 | 一次性购买 |
| 退款发票 | 退款成功 | 负数发票 |

---

## 发票字段

```typescript
interface Invoice {
  id: string;
  invoice_number: string;     // INV-2026-001234
  user_id: string;
  amount: number;             // 金额 (美分)
  currency: 'usd';
  status: 'paid' | 'refunded' | 'void';
  created_at: string;         // UTC 时间
  
  // Stripe 关联
  stripe_invoice_id: string;
  stripe_hosted_url: string;  // Stripe 托管发票页
  pdf_url: string;            // PDF 下载链接
  
  // 明细
  items: InvoiceItem[];
}
```

---

## 用户操作

### 查看发票列表

```
设置 → 账单 → 发票历史
```

显示:
- 发票号
- 日期
- 金额
- 状态
- 下载 PDF

### 下载发票

点击"下载"跳转 Stripe 托管 PDF。

---

## API

```
GET /api/billing/invoices
GET /api/billing/invoices/{id}
GET /api/billing/invoices/{id}/pdf  # 重定向到 Stripe PDF
```

---

## Stripe 集成

```python
async def get_user_invoices(user_id: str) -> list[Invoice]:
    """获取用户发票列表"""
    customer_id = await get_stripe_customer_id(user_id)
    
    # 从 Stripe 获取
    invoices = stripe.Invoice.list(customer=customer_id)
    
    return [map_stripe_invoice(inv) for inv in invoices]
```

---

## 相关文档

- [Stripe 集成](../../04-engineering/modules/billing/stripe-integration.md)
- [账单设置页](../../02-product/pages/user/settings.md)
