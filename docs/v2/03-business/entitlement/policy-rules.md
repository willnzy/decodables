# 权限策略与继承规则

> 优先级、继承、用户组与冲突处理。

**状态**: needs-review  
**版本**: 1.0.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Product Team  
**适用范围**: shared  
**source_repo**: backend  
**sync_required**: yes

---

## 背景

- 需要统一权限策略的裁决顺序与继承逻辑
- 明确冲突与版本控制规则

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 优先级规则

```
全局开关 > 用户覆盖 > 用户组 > Workspace > Tier > 默认值
```

## Tier 继承

- 高等级继承低等级基础能力
- 特殊功能以配置为准

## 用户组

- 支持按群组分配权限
- 群组权限可覆盖 Tier

## 配置版本与冲突

- 配置变更需要版本记录
- 冲突时以优先级顺序裁决

## 影响范围

- 相关模块：Entitlement 权限策略
- 相关文档：`docs/v2/03-business/entitlement/permission-matrix.md`

## 证据与验证

- 关键证据来源：`decodables/docs/shared/entitlement/`、`decodables/domains/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 1.0.0 | 结构对齐模板 | Docs Working Group |
