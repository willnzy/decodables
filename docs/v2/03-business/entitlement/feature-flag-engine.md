# Feature Flag 评估引擎

> 灰度发布、A/B 实验与 Kill Switch 机制。

**状态**: active  
**版本**: 1.0.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Backend Team  
**适用范围**: shared  
**source_repo**: backend  
**sync_required**: yes

---

## 核心能力

- 全局开关（Kill Switch）
- 百分比灰度
- A/B 实验变体
- 前置条件（prerequisite）

## 评估优先级

```
Kill Switch > 用户 Override > Tier 权限 > Flag 变体
```

## 输出结构（示例）

```json
{
  "access": "full",
  "variant": "v2",
  "reason": "flag_rollout"
}
```
