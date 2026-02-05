# About Us 页面规格

> **同步范围**: [frontend]
> **状态**: 🟡 待验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05

---

## 一、页面定位

### 1.1 目的

展示公司/产品故事，建立用户信任，传达品牌价值观。

### 1.2 目标用户

- 潜在用户了解产品背景
- 教育工作者评估产品可信度
- 合作伙伴了解公司情况

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
│  │  "Empowering Teachers to Create                      │ │
│  │   Engaging Learning Materials"                        │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │                    Our Story                          │ │
│  │  产品起源、解决的问题、愿景                           │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │                    Our Mission                        │ │
│  │  - Make education engaging                            │ │
│  │  - Empower teachers with AI                          │ │
│  │  - Simplify content creation                          │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │                    Our Values                         │ │
│  │  🎯 简单易用                                          │ │
│  │  🚀 创新驱动                                          │ │
│  │  ❤️ 教育为先                                          │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │                    Contact CTA                        │ │
│  │  "Have questions? Get in touch!"                      │ │
│  │  [Contact Us]                                         │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
├────────────────────────────────────────────────────────────┤
│                        Footer                               │
└────────────────────────────────────────────────────────────┘
```

### 2.2 内容要点

| 区块 | 内容 |
|------|------|
| Hero | 品牌口号，突出教育赋能 |
| Our Story | 产品诞生背景，创始人动机 |
| Our Mission | 3-4 个核心使命点 |
| Our Values | 公司价值观（简洁、创新、教育） |
| Contact CTA | 引导联系我们 |

---

## 三、SEO 考虑

### 3.1 Meta Tags

```html
<title>About Us - Make Decodables | AI-Powered Mini Book Creator</title>
<meta name="description" content="Learn about Make Decodables, 
  the AI-powered platform helping K-5 teachers create engaging 
  educational Mini Books for their students." />
```

### 3.2 关键词

- Make Decodables
- Educational tool
- AI Mini Book creator
- K-5 teachers
- Decodable books

---

## 四、技术实现

### 4.1 路由

```
/about
```

### 4.2 组件

```
app/
└── (marketing)/
    └── about/
        └── page.tsx
```

### 4.3 静态生成

- 使用 Next.js Static Generation
- 无需 API 调用
- CDN 缓存

---

## 五、相关文档

- [Contact Us 页面](./contact-us.md)
- [品牌规范](../../03-design/tokens/README.md)

---

**END OF DOCUMENT**
