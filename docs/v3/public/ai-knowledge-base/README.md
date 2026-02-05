# AI 客服知识库

> **输出到**: Help 页面的 AI 智能客服
> **来源**: public/manual/ + public/faq/

---

## 目录结构

```
ai-knowledge-base/
├── README.md              # 本文件
│
├── intents/               # 意图分类
│   ├── account.md         # 账号相关意图
│   ├── billing.md         # 账单相关意图
│   ├── editor.md          # 编辑器相关意图
│   └── general.md         # 通用意图
│
├── responses/             # 标准回复
│   ├── account.md         # 账号相关回复
│   ├── billing.md         # 账单相关回复
│   ├── editor.md          # 编辑器相关回复
│   └── escalation.md      # 转人工条件
│
└── context/               # 上下文信息
    ├── product-summary.md # 产品信息摘要
    ├── pricing-summary.md # 定价信息摘要
    └── policy-summary.md  # 政策摘要
```

---

## intents/ 意图分类

定义用户可能的意图，用于 AI 理解用户问题。

### 意图格式

```markdown
## intent_name

**描述**: 用户想要做什么
**触发词**: [关键词列表]
**示例问句**:
- "xxx?"
- "xxx?"

**关联回复**: responses/{category}.md#{response_id}
```

### 示例

```markdown
## upgrade_plan

**描述**: 用户想要升级套餐
**触发词**: [升级, 套餐, 高级, Pro, upgrade, plan]
**示例问句**:
- "怎么升级套餐？"
- "我想升级到 Pro"
- "How do I upgrade my plan?"

**关联回复**: responses/billing.md#upgrade
```

---

## responses/ 标准回复

定义 AI 的标准回复内容。

### 回复格式

```markdown
## {response_id}

**简短回复**: 一句话回答

**详细回复**:
（2-5 句话的详细解释）

**操作引导**: （如适用）
1. 步骤一
2. 步骤二

**相关链接**:
- [Manual 链接](/manual/xxx)
- [FAQ 链接](/faq/xxx)

**追问检测**: （用户可能的追问）
- "xxx" → 关联 intent
```

---

## context/ 上下文信息

提供 AI 需要的背景知识。

### product-summary.md

```markdown
## 产品简介
Make Decodables 是一个在线 Decodable 创作工具...

## 核心功能
- 编辑器：在线画布...
- AI 功能：AI 生图...
- 模板市场：浏览、购买...

## 目标用户
- 教师
- 家长
- 教育内容创作者
```

### pricing-summary.md

```markdown
## 套餐

| 套餐 | 价格 | 积分 |
|------|------|------|
| Free | $0 | 0 |
| Starter | $6.9/月 | 100 |
| Pro | $9.9/月 | 200 |

## 积分
- 月度积分：每月发放，月底清零
- 永久积分：购买获得，永久有效

## AI 功能消耗
- AI 生图：5 积分
- AI 生成页面：5 积分
```

### policy-summary.md

```markdown
## 退款政策
首次订阅后 7 天内可申请全额退款

## 取消订阅
随时可取消，当前周期结束后生效

## 数据安全
所有数据加密存储...
```

---

## escalation.md 转人工条件

```markdown
## 必须转人工

1. **敏感操作**
   - 退款请求
   - 账号删除
   - 支付纠纷

2. **复杂问题**
   - 支付失败（尝试 2+ 次）
   - 数据丢失
   - 账号安全

## 建议转人工

1. **情绪标识**
   - 用户表达不满
   - 重复询问同一问题
   - 明确要求人工

2. **超出知识库**
   - AI 无法回答
   - 需要查询用户数据

## 转人工话术

"抱歉，这个问题需要我们的客服团队来处理。我已经为您转接人工客服，请稍等..."
```

---

## 更新流程

```
Manual/FAQ 更新 → 提取变更 → 更新 intents/ → 更新 responses/ → 更新 context/
```

---

## 与其他目录的关系

| 目录 | 关系 |
|------|------|
| `manual/` | 知识来源（详细教程） |
| `faq/` | 知识来源（问答对） |
| `internal/06-growth/support/ai-customer-service.md` | AI 客服设计策略 |
