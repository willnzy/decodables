# Privacy Policy 页面规格

> **同步范围**: [frontend]
> **状态**: 🟡 待验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05

---

## 一、页面定位

### 1.1 目的

说明平台如何收集、使用、存储和保护用户数据。

### 1.2 合规要求

| 法规 | 适用范围 | 关键要求 |
|------|----------|----------|
| GDPR | 欧盟用户 | 数据主体权利、同意、DPO |
| CCPA | 加州用户 | 数据销售披露、删除权 |
| COPPA | 13岁以下 | 家长同意、数据最小化 |

---

## 二、内容结构

### 2.1 页面布局

```
┌────────────────────────────────────────────────────────────┐
│                        Header                               │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Privacy Policy                                       │ │
│  │  Last Updated: February 5, 2026                       │ │
│  │  Effective Date: February 5, 2026                     │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Table of Contents                                    │ │
│  │  1. Information We Collect                            │ │
│  │  2. How We Use Your Information                       │ │
│  │  3. Information Sharing                               │ │
│  │  4. Data Retention                                    │ │
│  │  5. Data Security                                     │ │
│  │  6. Your Rights                                       │ │
│  │  7. Children's Privacy                                │ │
│  │  8. International Transfers                           │ │
│  │  9. Cookies and Tracking                              │ │
│  │  10. Changes to This Policy                           │ │
│  │  11. Contact Us                                       │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  [Privacy Content - Scrollable]                       │ │
│  │  ...                                                  │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
├────────────────────────────────────────────────────────────┤
│                        Footer                               │
└────────────────────────────────────────────────────────────┘
```

### 2.2 核心章节

| 章节 | 内容要点 |
|------|----------|
| 信息收集 | 收集哪些数据、如何收集 |
| 信息使用 | 数据用途、法律依据 |
| 信息共享 | 第三方、服务提供商 |
| 数据保留 | 保留期限、删除策略 |
| 数据安全 | 安全措施、加密 |
| 用户权利 | 访问、更正、删除、导出 |
| 儿童隐私 | COPPA 合规措施 |

---

## 三、关键内容

### 3.1 信息收集

```markdown
## 1. Information We Collect

### 1.1 Information You Provide
- Account information (email, name)
- Profile information (avatar, preferences)
- Content you create (projects, Mini Books)
- Payment information (processed by Stripe)

### 1.2 Automatically Collected
- Device information (browser, OS)
- Usage data (features used, session duration)
- Log data (IP address, access times)

### 1.3 Third-Party Sources
- OAuth providers (Google, Apple)
- Analytics services
```

### 3.2 信息使用

```markdown
## 2. How We Use Your Information

We use your information to:
- Provide and improve our services
- Process payments and subscriptions
- Send service-related communications
- Analyze usage patterns
- Prevent fraud and abuse
- Comply with legal obligations

Legal Bases (GDPR):
- Contract performance
- Legitimate interests
- Legal compliance
- Consent (where required)
```

### 3.3 第三方服务

```markdown
## 3. Information Sharing

### Service Providers
| Provider | Purpose | Data Shared |
|----------|---------|-------------|
| Supabase | Database | User data |
| Stripe | Payments | Payment info |
| Vercel | Hosting | Access logs |
| OpenAI/FAL | AI Services | Prompts |
| Resend | Email | Email address |

### We Do Not
- Sell your personal information
- Share data for advertising
- Allow third-party tracking for ads
```

### 3.4 用户权利

```markdown
## 6. Your Rights

You have the right to:

### Access
Request a copy of your personal data.

### Correction
Update inaccurate information.

### Deletion
Request deletion of your account and data.
(30-day cool-off period applies)

### Data Portability
Export your data in a machine-readable format.

### Opt-Out
Unsubscribe from marketing communications.

### Withdraw Consent
Withdraw consent where processing is based on consent.

To exercise these rights, contact: privacy@foliaz.com
```

### 3.5 儿童隐私

```markdown
## 7. Children's Privacy

### Age Requirement
Our service is intended for users 13 years and older.
Teachers may use our service to create content for younger students.

### COPPA Compliance
- We do not knowingly collect data from children under 13
- Teachers are responsible for student data they may handle
- If we learn of data collected from a child under 13, 
  we will delete it promptly

### For Schools
If you are using Make Decodables in a school setting, 
please review our [School Privacy Addendum].
```

---

## 四、技术实现

### 4.1 路由

```
/privacy
/legal/privacy (alias)
```

### 4.2 组件

```
app/
└── (marketing)/
    └── privacy/
        └── page.tsx
```

### 4.3 Cookie 同意

```tsx
// Cookie 同意组件
<CookieConsent>
  We use cookies to improve your experience. 
  <Link href="/privacy#cookies">Learn more</Link>
  <Button onClick={acceptAll}>Accept All</Button>
  <Button onClick={customize}>Customize</Button>
</CookieConsent>
```

---

## 五、SEO 考虑

### 5.1 Meta Tags

```html
<title>Privacy Policy - Make Decodables</title>
<meta name="description" content="Learn how Make Decodables 
  collects, uses, and protects your personal information. 
  We are committed to your privacy and data security." />
```

---

## 六、相关文档

- [Terms of Service](./terms.md)
- [数据合规](../../../09-compliance/data-compliance.md)
- [GDPR 合规](../../../09-compliance/gdpr.md)

---

**END OF DOCUMENT**
