# FAQ 文档模板

> 本模板用于编写 `public/faq/*.md` 中的常见问题文档。
> FAQ 内容同时用于：网站 FAQ 页面 + AI 智能客服知识库

---

## 文档元数据

```yaml
---
title: [分类] 常见问题
status: draft | published
category: general | account | editor | billing | marketplace | troubleshooting
updated: YYYY-MM-DD
questions_count: N
---
```

---

## 问答格式

每个问题使用以下格式：

```markdown
## Q: [问题标题]

**简短回答**：一句话回答，适合 AI 客服快速响应。

**详细说明**：
（2-5 句话的详细解释）

**操作步骤**：（如适用）
1. 步骤一
2. 步骤二
3. 步骤三

**相关链接**：
- [相关 Manual 文档](/manual/xxx)
- [相关 FAQ](/faq/xxx)

**AI 标签**：`#category` `#keyword1` `#keyword2`

---
```

---

## 示例：账单 FAQ

```markdown
---
title: 账单常见问题
status: published
category: billing
updated: 2026-02-05
questions_count: 5
---

# 账单常见问题

## Q: 如何升级套餐？

**简短回答**：在个人中心 > 订阅管理中选择新套餐即可。

**详细说明**：
升级套餐后，系统会按比例计算剩余天数的差价。新套餐的权益立即生效，包括更多的月度积分和高级功能。

**操作步骤**：
1. 登录账号
2. 点击右上角头像 > 个人中心
3. 选择「订阅管理」
4. 点击「升级套餐」
5. 选择目标套餐并完成支付

**相关链接**：
- [套餐与定价](/manual/billing/plans-pricing)
- [管理订阅](/manual/billing/manage-subscription)

**AI 标签**：`#billing` `#upgrade` `#subscription` `#plan`

---

## Q: 积分会过期吗？

**简短回答**：月度积分每月重置，永久积分不过期。

**详细说明**：
我们有两种积分类型：
- **月度积分**：订阅用户每月自动发放，月底清零不累积
- **永久积分**：通过购买或活动获得，永久有效

系统会优先使用月度积分，用完后再使用永久积分。

**相关链接**：
- [积分说明](/manual/billing/credits)

**AI 标签**：`#billing` `#credits` `#expiration` `#monthly` `#permanent`

---

## Q: 如何申请退款？

**简短回答**：订阅后 7 天内可申请全额退款，请联系客服。

**详细说明**：
根据我们的退款政策，首次订阅后 7 天内可申请全额退款。退款后，账号将降级为免费版，已使用的付费功能产出物保留。

**操作步骤**：
1. 确认在 7 天退款期内
2. 发送邮件至 support@makedecodables.com
3. 说明退款原因
4. 等待 3-5 个工作日处理

**相关链接**：
- [账单政策](/legal/billing-policy)

**AI 标签**：`#billing` `#refund` `#cancel` `#policy`

**⚠️ 转人工条件**：用户情绪激动或情况复杂时，建议转人工处理。

---
```

---

## AI 标签分类参考

### 一级分类标签

| 标签 | 说明 |
|------|------|
| `#general` | 常规问题 |
| `#account` | 账号相关 |
| `#editor` | 编辑器相关 |
| `#billing` | 账单相关 |
| `#marketplace` | Marketplace 相关 |
| `#troubleshooting` | 故障排除 |

### 二级关键词标签（示例）

| 分类 | 常用标签 |
|------|----------|
| account | `#login` `#register` `#password` `#profile` `#delete` |
| editor | `#canvas` `#text` `#image` `#ai` `#export` `#shortcut` |
| billing | `#subscription` `#upgrade` `#cancel` `#credits` `#refund` `#invoice` |
| marketplace | `#template` `#purchase` `#sell` `#review` `#payout` |

---

## 转人工触发条件

在 FAQ 条目中标注 `⚠️ 转人工条件` 的场景：

1. **敏感操作**
   - 退款请求
   - 账号删除
   - 订阅取消

2. **复杂情况**
   - 支付失败排查
   - 数据丢失恢复
   - 多次尝试未解决

3. **情绪标识**
   - 用户表达不满
   - 重复询问同一问题
   - 要求与人工沟通

---

## 检查清单

- [ ] 每个问题都有简短回答（1句话）
- [ ] 操作步骤清晰明确（如适用）
- [ ] 相关链接指向正确的 Manual/FAQ
- [ ] AI 标签完整（1个分类 + 2-4个关键词）
- [ ] 敏感问题标注转人工条件
