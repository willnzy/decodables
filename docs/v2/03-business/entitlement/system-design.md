# 权限与功能控制系统设计

> Entitlement + Feature Flag + Merge Layer 的整体架构。

**状态**: active  
**版本**: 4.3.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Product + Backend  
**适用范围**: shared  
**source_repo**: backend  
**sync_required**: yes

---

## 系统职责

| 能力 | 说明 | 负责模块 |
|------|------|---------|
| 用户权限管理 | Tier、试用期、配额、override | EntitlementService |
| 灰度发布 | 按比例放量 | FeatureFlagService |
| A/B 实验 | 多变体实验 | FeatureFlagService |
| 运营授权 | 指定用户越权 | EntitlementService |

## 架构原则

- Entitlement 解决“有没有资格”
- Feature Flag 解决“是否已上线”

---

## 合并层（Merge）

优先级：

```
Kill Switch > Entitlement Override > Tier/Trial > Feature Flag Variant
```

返回结构包含：

- access: full / trial / locked
- variant: flag 评估结果
- reason: 决策来源

---

## 数据流

1. 从 `system_configs` 读取 tier.features 与配额  
2. 评估 Feature Flag  
3. Merge 层合并结果  
4. API 输出 `/api/v2/user/features`
