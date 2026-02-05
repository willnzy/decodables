# 层级权益继承

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **来源**: v1 shared/entitlement/

---

## 概述

高层级自动继承低层级的所有权益。

---

## 继承规则

```
t1 (Free) 的权益
    ↓ 继承
t2 (Starter) 的权益 = t1 权益 + t2 专属
    ↓ 继承
t3 (Pro) 的权益 = t2 权益 + t3 专属
```

---

## 权益矩阵

| 权益 | t1 (Free) | t2 (Starter) | t3 (Pro) |
|------|-----------|--------------|----------|
| 项目数量 | 3 | 10 | 无限 |
| 页面/项目 | 5 | 20 | 无限 |
| 月度积分 | 0 | 100 | 200 |
| 导出分辨率 | 标清 | 高清 | 超高清 |
| 水印 | 有 | 无 | 无 |
| 高级模板 | ❌ | ✅ | ✅ |
| 团队协作 | ❌ | ❌ | ✅ |

---

## 实现

```python
def get_user_entitlements(tier: str) -> dict:
    """获取用户完整权益 (含继承)"""
    base = TIER_ENTITLEMENTS['t1']
    
    if tier in ['t2', 't3']:
        base = {**base, **TIER_ENTITLEMENTS['t2']}
    
    if tier == 't3':
        base = {**base, **TIER_ENTITLEMENTS['t3']}
    
    return base
```

---

## 相关文档

- [Tier 命名系统](../tier-system.md)
- [权益配置](./config.md)
