# 常见问题 (FAQ)

> **输出到**: 网站 FAQ 页面 + AI 智能客服
> **来源**: 用户反馈 + internal/05-business/

---

## 目录结构

```
faq/
├── README.md              # 本文件
├── general.md             # 常规问题
├── account.md             # 账号相关
├── editor.md              # 编辑器相关
├── billing.md             # 账单相关
├── marketplace.md         # Marketplace 相关
└── troubleshooting.md     # 故障排除
```

---

## 写作规范

### 使用 FAQ 模板

参考 [faq-template.md](../internal/10-governance/templates/faq-template.md)

### 问答格式

```markdown
## Q: [问题标题]

**简短回答**：一句话回答（给 AI 快速响应用）

**详细说明**：
2-5 句话的详细解释

**操作步骤**：（如适用）
1. 步骤一
2. 步骤二

**相关链接**：
- [相关 Manual](/manual/xxx)

**AI 标签**：`#category` `#keyword1` `#keyword2`
```

### AI 标签分类

| 一级标签 | 说明 |
|----------|------|
| `#general` | 常规问题 |
| `#account` | 账号相关 |
| `#editor` | 编辑器相关 |
| `#billing` | 账单相关 |
| `#marketplace` | Marketplace 相关 |
| `#troubleshooting` | 故障排除 |

---

## 各文件内容

### general.md

- 什么是 Make Decodables？
- 支持哪些浏览器？
- 如何联系客服？
- 数据安全吗？

### account.md

- 如何注册？
- 忘记密码怎么办？
- 如何修改邮箱？
- 如何删除账号？

### editor.md

- 如何撤销操作？
- 支持哪些文件格式？
- 如何使用 AI 功能？
- 导出时可以选择什么格式？

### billing.md

- 有哪些套餐？
- 如何升级/降级？
- 积分怎么获得/使用？
- 如何取消订阅？
- 可以退款吗？

### marketplace.md

- 如何购买模板？
- 如何上架我的作品？
- 审核需要多久？
- 如何提现？

### troubleshooting.md

- 页面加载不出来？
- 无法保存项目？
- 导出失败？
- AI 功能不可用？

---

## 转人工触发条件

以下情况建议转人工处理：

1. **敏感操作**
   - 退款请求
   - 账号删除
   - 订阅取消投诉

2. **复杂问题**
   - 支付失败（多次尝试）
   - 数据丢失
   - 账号安全问题

3. **情绪标识**
   - 用户表达不满
   - 重复询问同一问题

---

## 与其他目录的关系

| 目录 | 关系 |
|------|------|
| `manual/` | FAQ 回答疑问，Manual 提供详细教程 |
| `ai-knowledge-base/` | FAQ 是 AI 知识的主要来源 |
| `internal/05-business/` | 业务规则决定 FAQ 答案 |
