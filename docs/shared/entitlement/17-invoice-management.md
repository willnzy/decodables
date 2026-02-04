# 发票与收据管理

> **版本**: v2.0
> **日期**: 2026-02-04
> **状态**: 产品确认

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [README.md](./README.md) | 文档导航索引 |
| [14-billing-cycle-switch.md](./14-billing-cycle-switch.md) | 计费周期切换 |
| [18-refund-processing.md](./18-refund-processing.md) | 退款处理 |

---

## 一、文档类型

### 1.1 类型定义

| 类型 | 说明 | 生成时机 |
|------|------|----------|
| **Receipt (收据)** | 付款成功凭证 | 付款成功后自动生成 |
| **Invoice (发票)** | 正式税务发票 | 用户申请后生成 |
| **Credit Note** | 退款凭证 | 退款成功后自动生成 |

### 1.2 支持的付款类型

| 付款类型 | 自动生成收据 | 可申请发票 |
|----------|-------------|------------|
| 订阅付款 | ✅ | ✅ |
| 积分充值 | ✅ | ✅ |
| 一次性购买 | ✅ | ✅ |
| 退款 | ✅ (Credit Note) | ❌ |

---

## 二、收据管理

### 2.1 自动生成规则

```
付款成功 (Stripe webhook: payment_intent.succeeded)
    ↓
自动生成收据
    ↓
发送收据邮件 (PDF 附件)
    ↓
收据可在 Transaction History 页面下载
```

### 2.2 收据内容

```
┌─────────────────────────────────┐
│ RECEIPT                         │
│ Make Decodables                 │
│                                 │
│ Receipt #: REC-2026020401234    │
│ Date: February 4, 2026          │
│                                 │
│ Bill To:                        │
│ John Doe                        │
│ john@example.com                │
│                                 │
│ ─────────────────────────────── │
│ Item          Qty     Amount    │
│ Pro Plan       1      $9.90     │
│ (Monthly)                       │
│ ─────────────────────────────── │
│ Total                  $9.90    │
│                                 │
│ Payment Method: Visa ****1234   │
│ Status: Paid                    │
│                                 │
│ Thank you for your purchase!    │
└─────────────────────────────────┘
```

---

## 三、发票申请

### 3.1 申请条件

| 条件 | 要求 |
|------|------|
| 付款状态 | 已成功 |
| 申请时间 | 付款后 90 天内 |
| 发票信息 | 需填写完整 |

### 3.2 发票信息

```
必填项:
- 公司名称 / 个人姓名
- 税号 (企业用户)
- 账单地址
- 联系邮箱

可选项:
- 采购订单号 (PO Number)
- 额外备注
```

### 3.3 申请流程

```
1. 进入 Transaction History
2. 找到目标交易记录
3. 点击 "申请发票"
4. 填写发票信息
5. 提交申请
6. 系统生成发票 (1-3 个工作日)
7. 发送发票至邮箱
```

---

## 四、文档存储

### 4.1 存储策略

| 文档类型 | 存储位置 | 保留期限 |
|----------|----------|----------|
| 收据 PDF | Supabase Storage | 7 年 |
| 发票 PDF | Supabase Storage | 7 年 |
| Credit Note | Supabase Storage | 7 年 |

### 4.2 数据结构

```sql
CREATE TABLE IF NOT EXISTS billing_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    transaction_id UUID REFERENCES transactions(id),
    document_type VARCHAR(20) NOT NULL, -- receipt, invoice, credit_note
    document_number VARCHAR(50) NOT NULL UNIQUE,
    storage_path TEXT NOT NULL, -- Supabase Storage 路径
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    billing_info JSONB, -- 发票信息
    status VARCHAR(20) DEFAULT 'generated', -- generated, sent, downloaded
    created_at TIMESTAMPTZ DEFAULT NOW(),
    sent_at TIMESTAMPTZ
);

-- 索引
CREATE INDEX idx_billing_documents_user ON billing_documents(user_id, created_at DESC);
CREATE INDEX idx_billing_documents_number ON billing_documents(document_number);
```

---

## 五、用户界面

### 5.1 Transaction History 页面

```
┌─────────────────────────────────────────────────────┐
│ Transaction History                                  │
│                                                      │
│ Date        Description      Amount    Documents     │
│ ─────────────────────────────────────────────────── │
│ Feb 4, 2026 Pro Plan (Month) $9.90    [📄][📑]      │
│ Jan 4, 2026 Pro Plan (Month) $9.90    [📄][📑]      │
│ Dec 15, 2025 Credits 500     $13.46   [📄][📑]      │
│                                                      │
│ [📄] = Download Receipt                             │
│ [📑] = Request Invoice                              │
└─────────────────────────────────────────────────────┘
```

### 5.2 发票申请弹窗

```
┌─────────────────────────────────┐
│ Request Invoice                 │
│                                 │
│ Company Name *                  │
│ [________________________]      │
│                                 │
│ Tax ID (Optional)               │
│ [________________________]      │
│                                 │
│ Billing Address *               │
│ [________________________]      │
│ [________________________]      │
│                                 │
│ Email *                         │
│ [________________________]      │
│                                 │
│ PO Number (Optional)            │
│ [________________________]      │
│                                 │
│ [Submit Request]  [Cancel]      │
└─────────────────────────────────┘
```

---

## 六、API 接口

```python
# 获取交易历史
GET /api/v1/billing/transactions?limit=20&offset=0

# 下载收据
GET /api/v1/billing/documents/{document_id}/download

# 申请发票
POST /api/v1/billing/documents/invoice
{
    "transaction_id": "uuid",
    "billing_info": {
        "company_name": "Acme Inc",
        "tax_id": "12-3456789",
        "address": "123 Main St",
        "email": "billing@acme.com",
        "po_number": "PO-2026-001"
    }
}

# 获取用户的所有文档
GET /api/v1/billing/documents?type=invoice
```

---

## 七、通知策略

| 事件 | 通知方式 | 内容 |
|------|----------|------|
| 收据生成 | 邮件 (PDF 附件) | 付款确认 + 收据 |
| 发票生成 | 邮件 (PDF 附件) | 发票已生成 |
| Credit Note | 邮件 (PDF 附件) | 退款确认 |

---

**END OF DOCUMENT**
