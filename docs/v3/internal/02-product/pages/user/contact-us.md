# Contact Us 页面规格

> **同步范围**: [frontend]
> **状态**: 🟡 待验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05

---

## 一、页面定位

### 1.1 目的

提供用户联系渠道，收集用户反馈和合作意向。

### 1.2 联系类型

| 类型 | 说明 |
|------|------|
| 一般咨询 | 产品功能、使用问题 |
| 技术支持 | Bug 报告、技术问题 |
| 商务合作 | 企业合作、批量授权 |
| 反馈建议 | 功能建议、改进意见 |

---

## 二、页面内容

### 2.1 内容结构

```
┌────────────────────────────────────────────────────────────┐
│                        Header                               │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │                    Hero Section                       │ │
│  │  "We'd Love to Hear From You"                        │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌────────────────────┬─────────────────────────────────┐ │
│  │                    │                                 │ │
│  │  Contact Form      │   Contact Info                  │ │
│  │                    │                                 │ │
│  │  [Name        ]    │   📧 Email                      │ │
│  │  [Email       ]    │   info@foliaz.com    │ │
│  │  [Subject  ▼  ]    │                                 │ │
│  │  [Message     ]    │   🕐 Response Time              │ │
│  │  [            ]    │   Within 24-48 hours            │ │
│  │  [            ]    │                                 │ │
│  │  [Send Message]    │   💬 Live Chat                  │ │
│  │                    │   Available in Help Center      │ │
│  └────────────────────┴─────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │                    FAQ Quick Links                    │ │
│  │  Before contacting us, check our FAQ                 │ │
│  │  [View FAQ]                                          │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
├────────────────────────────────────────────────────────────┤
│                        Footer                               │
└────────────────────────────────────────────────────────────┘
```

### 2.2 表单字段

| 字段 | 类型 | 必填 | 验证 |
|------|------|------|------|
| Name | text | ✅ | 2-100 字符 |
| Email | email | ✅ | 有效邮箱格式 |
| Subject | select | ✅ | 预设选项 |
| Message | textarea | ✅ | 10-2000 字符 |

### 2.3 Subject 选项

```
- General Inquiry
- Technical Support
- Bug Report
- Feature Request
- Business Partnership
- Billing Question
- Other
```

---

## 三、技术实现

### 3.1 路由

```
/contact
```

### 3.2 组件

```
app/
└── (marketing)/
    └── contact/
        └── page.tsx
```

### 3.3 表单提交

```typescript
// 表单提交逻辑
async function handleSubmit(data: ContactFormData) {
  // 1. 验证数据
  const validated = contactSchema.parse(data);
  
  // 2. 发送到后端
  await api.post('/contact', validated);
  
  // 3. 显示成功消息
  toast.success('Message sent! We will reply within 24-48 hours.');
}
```

### 3.4 后端处理

```python
# 发送邮件通知
async def handle_contact_form(data: ContactFormData):
    # 1. 保存到数据库 (可选)
    await db.insert('contact_submissions', data)
    
    # 2. 发送邮件给 support
    await email_service.send(
        to='info@foliaz.com',
        subject=f'[Contact Form] {data.subject}',
        body=format_contact_email(data)
    )
    
    # 3. 发送确认邮件给用户
    await email_service.send(
        to=data.email,
        template='contact_confirmation',
        data={'name': data.name}
    )
```

---

## 四、SEO 考虑

### 4.1 Meta Tags

```html
<title>Contact Us - Make Decodables</title>
<meta name="description" content="Get in touch with the Make Decodables 
  team. We're here to help with questions, support, and feedback." />
```

---

## 五、相关文档

- [About Us 页面](./about-us.md)
- [帮助中心](../../../06-growth/user-support/help-center.md)

---

**END OF DOCUMENT**
