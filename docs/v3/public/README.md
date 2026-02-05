# Public - 外部公开内容

> **状态**: 🟢 结构完成

---

## 目录说明

面向终端用户的公开内容，用于网站展示和 AI 客服。

---

## 目录索引

| 目录 | 说明 | 输出到 |
|------|------|--------|
| [manual](manual/) | 产品使用手册 | 网站 /manual |
| [faq](faq/) | 常见问题 | 网站 FAQ + AI 客服 |
| [news](news/) | 产品动态 | 网站 /news + 社媒 |
| [legal](legal/) | 法律文档 | 网站法律页面 |
| [ai-knowledge-base](ai-knowledge-base/) | AI 客服知识库 | Help AI 客服 |

---

## 内容来源

public/ 的内容来自 internal/ 的转化：

| internal 来源 | public 输出 |
|---------------|-------------|
| `02-product/features/` | `manual/` |
| `05-business/` | `faq/` |
| `09-compliance/` | `legal/` |
| `06-growth/` | `news/` |
| `manual/` + `faq/` | `ai-knowledge-base/` |

---

## 写作原则

### 用户手册 (manual/)

- 使用简单易懂的语言
- 配图说明操作步骤
- 避免技术术语

### FAQ

- 使用用户提问的语气
- 答案简洁明了
- 提供相关链接

### News

- SEO 友好的标题
- 适合社媒分享
- 包含视觉元素

---

## 模板

详见 `internal/10-governance/templates/`:
- `faq-template.md` - FAQ 模板
- `news-template.md` - News 文章模板
