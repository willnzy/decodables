# News 文章模板

> 本模板用于编写 `public/news/` 中的内容文章。
> News 内容用于：网站 News 页面 + SEO/GEO + 社媒运营

---

## 文章类型

| 类型 | 目录 | 用途 | 发布频率 |
|------|------|------|----------|
| **releases** | `news/releases/` | 版本发布公告 | 每次发版 |
| **tutorials** | `news/tutorials/` | 教程文章（SEO） | 每周 1-2 篇 |
| **use-cases** | `news/use-cases/` | 使用案例（SEO） | 每月 2-4 篇 |
| **announcements** | `news/announcements/` | 重要公告 | 按需 |

---

## 通用元数据

```yaml
---
title: 文章标题
slug: url-friendly-slug
type: release | tutorial | use-case | announcement
status: draft | review | published
publish_date: YYYY-MM-DD
author: Make Decodables Team
reading_time: N min
featured_image: /images/news/xxx.jpg

# SEO
seo_title: SEO 标题（60字符内）
seo_description: SEO 描述（160字符内）
seo_keywords: [keyword1, keyword2, keyword3]

# 社媒
social_ready: true
social_image: /images/news/xxx-social.jpg
---
```

---

## 模板 1: 版本发布 (releases)

```markdown
---
title: Make Decodables v2.5 发布：全新 AI 生图功能
slug: v2-5-release-ai-generation
type: release
status: published
publish_date: 2026-02-05
author: Make Decodables Team
reading_time: 3 min
featured_image: /images/news/v2-5-release.jpg

seo_title: Make Decodables v2.5 发布 - 全新 AI 生图功能 | Make Decodables
seo_description: Make Decodables v2.5 版本发布，带来全新 AI 生图功能，一键生成高质量 Decodable 插图。
seo_keywords: [decodable maker, AI illustration, education tool]

social_ready: true
---

# Make Decodables v2.5 发布：全新 AI 生图功能

我们很高兴地宣布 Make Decodables v2.5 版本正式发布！

## 🎨 新功能亮点

### AI 生图功能
（功能介绍...）

### 性能优化
（优化内容...）

## 🔧 改进与修复
- 修复了 xxx 问题
- 优化了 xxx 体验

## 🚀 如何体验
1. 登录 Make Decodables
2. 打开任意项目
3. 点击「AI 生图」按钮

## 📚 相关资源
- [AI 生图使用指南](/manual/editor/ai-features)
- [完整更新日志](/changelog)

---

## 社媒文案

### Twitter (280字符)
🎨 Make Decodables v2.5 is here! 
New AI illustration feature - create stunning decodable images in seconds.
Try it now 👉 [link]
#EdTech #AIEducation #Decodables

### Facebook
🎉 Exciting news! Make Decodables v2.5 is now live!

What's new:
✨ AI-powered illustration generation
⚡ 50% faster loading times
🎯 Improved export quality

Create beautiful decodables faster than ever. Try it free today!
[link]

### LinkedIn
We're thrilled to announce Make Decodables v2.5!

This release introduces our AI illustration feature, designed to help educators create engaging decodable content more efficiently.

Key highlights:
• AI-generated illustrations that match your content
• Significant performance improvements
• Enhanced export options

Learn more: [link]

#EdTech #EducationTechnology #AI #ProductUpdate
```

---

## 模板 2: 教程文章 (tutorials)

```markdown
---
title: 如何用 Make Decodables 创建你的第一个 Decodable
slug: how-to-create-first-decodable
type: tutorial
status: published
publish_date: 2026-02-05
author: Make Decodables Team
reading_time: 5 min
featured_image: /images/news/tutorial-first-decodable.jpg

seo_title: 如何创建 Decodable - 新手教程 | Make Decodables
seo_description: 5 分钟学会使用 Make Decodables 创建专业的 Decodable 教材，适合教师和家长。
seo_keywords: [create decodable, decodable tutorial, how to make decodable, reading instruction]

social_ready: true
---

# 如何用 Make Decodables 创建你的第一个 Decodable

> 预计阅读时间：5 分钟
> 难度：初级

## 什么是 Decodable？

（简要介绍...）

## 准备工作

在开始之前，你需要：
- [ ] 注册 Make Decodables 账号（免费）
- [ ] 准备好你的故事内容

## 步骤 1：创建新项目

（详细步骤 + 截图...）

## 步骤 2：添加文字

（详细步骤 + 截图...）

## 步骤 3：添加图片

（详细步骤 + 截图...）

## 步骤 4：导出分享

（详细步骤 + 截图...）

## 小技巧

💡 **提示 1**：xxx
💡 **提示 2**：xxx

## 下一步

- [进阶教程：使用 AI 功能](/news/tutorials/ai-features-guide)
- [查看模板库获取灵感](/marketplace)

## 常见问题

**Q: 免费账号可以创建几个项目？**
A: 免费账号可以创建无限数量的项目。

---

## 社媒文案

### Twitter
📚 New tutorial: Create your first decodable in 5 minutes!
Perfect for teachers and parents getting started.
Step-by-step guide 👉 [link]
#Literacy #TeacherTools #Decodables

### Facebook
Want to create professional decodables but don't know where to start?

Our new step-by-step tutorial shows you how to:
✅ Set up your first project
✅ Add text and images
✅ Export and share

No design skills needed! Read the full guide: [link]

### Pinterest (图片描述)
How to Create a Decodable in 5 Minutes - Step by Step Tutorial for Teachers and Parents | Make Decodables
```

---

## 模板 3: 使用案例 (use-cases)

```markdown
---
title: 教师 Sarah 如何用 Make Decodables 改变她的阅读课堂
slug: teacher-sarah-classroom-story
type: use-case
status: published
publish_date: 2026-02-05
author: Make Decodables Team
reading_time: 4 min
featured_image: /images/news/case-study-sarah.jpg

seo_title: 教师成功案例：Make Decodables 改变阅读教学 | Make Decodables
seo_description: 了解教师 Sarah 如何使用 Make Decodables 为学生创建个性化 Decodable，提升阅读教学效果。
seo_keywords: [teacher success story, decodable classroom, reading instruction, phonics teaching]

social_ready: true
---

# 教师 Sarah 如何用 Make Decodables 改变她的阅读课堂

> "Make Decodables 让我能够为每个学生创建适合他们水平的阅读材料。" —— Sarah M., 小学教师

## 背景

Sarah 是一位有 8 年教龄的小学教师...（故事背景）

## 挑战

（描述她面临的问题）

## 解决方案

（她如何使用 Make Decodables）

## 成果

- 📈 学生阅读参与度提升 40%
- ⏱️ 备课时间减少 60%
- 🎯 个性化教学成为可能

## Sarah 的使用技巧

1. **技巧一**：xxx
2. **技巧二**：xxx
3. **技巧三**：xxx

## 立即开始

想要像 Sarah 一样改变你的课堂？[免费注册 Make Decodables](/signup)

---

## 社媒文案

### Twitter
📖 "Make Decodables changed how I teach reading." 
See how teacher Sarah boosted student engagement by 40%.
Read her story 👉 [link]
#TeacherStories #EdTech #ReadingInstruction

### Facebook
Meet Sarah, a teacher who transformed her reading classroom with Make Decodables.

Her results:
📈 40% increase in student engagement
⏱️ 60% less prep time
🎯 Personalized learning for every student

Read her full story and discover how you can do the same: [link]

### LinkedIn
Case Study: How one teacher revolutionized her reading instruction

Sarah M., an elementary school teacher with 8 years of experience, faced a common challenge: creating engaging, level-appropriate reading materials for her diverse classroom.

After adopting Make Decodables, she saw remarkable results:
• 40% increase in student reading engagement
• 60% reduction in preparation time
• Ability to personalize content for each student's needs

Read the full case study: [link]

#EdTech #CaseStudy #ReadingInstruction #TeacherSuccess
```

---

## SEO 检查清单

- [ ] 标题包含主要关键词
- [ ] URL slug 简洁且包含关键词
- [ ] Meta description 在 160 字符内且包含 CTA
- [ ] 文章长度 ≥ 800 字（教程）或 ≥ 500 字（案例）
- [ ] 包含 2-3 个内部链接
- [ ] 包含 1 个外部权威链接（如适用）
- [ ] 图片有 alt 文本
- [ ] H1/H2/H3 结构清晰

## 社媒检查清单

- [ ] Twitter 文案 ≤ 280 字符
- [ ] Facebook 文案 150-300 字
- [ ] LinkedIn 文案 200-400 字
- [ ] 包含 CTA 和链接
- [ ] 包含 2-4 个相关 hashtag
- [ ] 社媒图片尺寸正确（1200x630 推荐）
