# Architecture Decision Records (ADR)

本目录记录了 Make Decodables 后端项目的重要架构决策。

## 什么是 ADR？

ADR (Architecture Decision Record) 用于记录软件架构中的重要决策，包括：
- 决策的背景和动机
- 考虑的替代方案
- 最终决策及理由
- 决策的后果和影响

## ADR 列表

| 编号 | 标题 | 状态 | 日期 |
|------|------|------|------|
| [0001](0001-use-ddd-architecture.md) | 采用 DDD 三层架构 | Accepted | 2026-01-06 |
| [0002](0002-database-driven-config.md) | 数据库驱动的积分配置系统 | Accepted | 2026-01-07 |

## ADR 模板

创建新的 ADR 时，请使用以下模板：

```markdown
# ADR-XXXX: [决策标题]

## Status
[Proposed | Accepted | Deprecated | Superseded]

## Context
[描述需要做出决策的背景和问题]

## Decision
[描述最终决策]

## Consequences
### Positive
- [积极影响]

### Negative
- [消极影响]

## Alternatives Considered
[描述考虑过的其他方案]

## Implementation
- Files: [相关文件]
- Commits: [相关提交]
```

## 贡献指南

1. 重要架构决策必须记录 ADR
2. ADR 编号连续递增
3. ADR 一旦接受（Accepted），不应修改，如需变更应创建新的 ADR 并标记旧的为 Superseded
4. 提交代码时，如果涉及架构变更，必须同时提交对应的 ADR
