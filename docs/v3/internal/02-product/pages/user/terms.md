# Terms of Service 页面规格

> **同步范围**: [frontend]
> **状态**: 🟡 待验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05

---

## 一、页面定位

### 1.1 目的

规定用户使用服务的条款和条件，保护平台和用户权益。

### 1.2 法律要求

- GDPR 合规
- CCPA 合规
- COPPA 合规 (针对 K-5 教育)

---

## 二、内容结构

### 2.1 页面布局

```
┌────────────────────────────────────────────────────────────┐
│                        Header                               │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Terms of Service                                     │ │
│  │  Last Updated: February 5, 2026                       │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Table of Contents                                    │ │
│  │  1. Acceptance of Terms                               │ │
│  │  2. Description of Service                            │ │
│  │  3. User Accounts                                     │ │
│  │  4. Subscription and Billing                          │ │
│  │  5. User Content                                      │ │
│  │  6. Intellectual Property                             │ │
│  │  7. Prohibited Uses                                   │ │
│  │  8. Termination                                       │ │
│  │  9. Disclaimers                                       │ │
│  │  10. Limitation of Liability                          │ │
│  │  11. Changes to Terms                                 │ │
│  │  12. Contact Information                              │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  [Terms Content - Scrollable]                         │ │
│  │                                                       │ │
│  │  1. Acceptance of Terms                               │ │
│  │  By accessing or using Make Decodables...             │ │
│  │                                                       │ │
│  │  2. Description of Service                            │ │
│  │  Make Decodables provides an AI-powered...            │ │
│  │  ...                                                  │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
├────────────────────────────────────────────────────────────┤
│                        Footer                               │
└────────────────────────────────────────────────────────────┘
```

### 2.2 核心条款

| 章节 | 要点 |
|------|------|
| 服务描述 | AI Mini Book 创作平台 |
| 用户账户 | 注册要求、账户安全 |
| 订阅计费 | 付款条款、退款政策 |
| 用户内容 | 内容所有权、授权使用 |
| 知识产权 | 平台 IP、用户 IP |
| 禁止行为 | 滥用、违法使用 |
| 终止条款 | 账户终止条件 |
| 责任限制 | 服务责任边界 |

---

## 三、关键条款内容

### 3.1 订阅和计费

```markdown
## 4. Subscription and Billing

### 4.1 Free Plan
- Limited features and credits
- No payment required

### 4.2 Paid Subscriptions
- Billed monthly
- Auto-renewal unless cancelled
- Price changes with 30-day notice

### 4.3 Refunds
- No refunds for partial months
- Prorated refunds for annual plans
- 7-day money-back guarantee for new subscriptions

### 4.4 Credits
- Monthly credits reset each billing cycle
- Purchased credits never expire
- Credits are non-transferable
```

### 3.2 用户内容

```markdown
## 5. User Content

### 5.1 Ownership
You retain ownership of content you create.

### 5.2 License to Us
You grant us a license to host and display your content.

### 5.3 AI-Generated Content
AI-generated images are subject to our AI provider's terms.

### 5.4 Responsibility
You are responsible for the content you create and share.
```

### 3.3 禁止行为

```markdown
## 7. Prohibited Uses

You may not:
- Generate harmful or illegal content
- Share access credentials
- Attempt to bypass usage limits
- Use for commercial purposes without authorization
- Violate any applicable laws
```

---

## 四、技术实现

### 4.1 路由

```
/terms
/legal/terms (alias)
```

### 4.2 组件

```
app/
└── (marketing)/
    └── terms/
        └── page.tsx
```

### 4.3 静态内容

- Markdown 源文件
- Build 时静态生成
- 版本历史追踪

---

## 五、SEO 考虑

### 5.1 Meta Tags

```html
<title>Terms of Service - Make Decodables</title>
<meta name="description" content="Read the Terms of Service for 
  Make Decodables. Learn about your rights and responsibilities 
  when using our AI-powered educational platform." />
```

---

## 六、相关文档

- [Privacy Policy](./privacy.md)
- [合规文档](../../../09-compliance/README.md)

---

**END OF DOCUMENT**
