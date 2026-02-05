# 功能下线策略

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **来源**: v1 shared/entitlement/

---

## 概述

功能下线 (Sunset) 的策略和流程。

---

## 下线类型

| 类型 | 说明 | 示例 |
|------|------|------|
| 功能移除 | 完全移除某功能 | 旧版编辑器 |
| 功能降级 | 从免费变为付费 | 高级导出 |
| 功能替换 | 用新功能替代 | 新模板系统 |

---

## 下线流程

### Phase 1: 公告 (提前 30 天)

- 产品公告
- 邮件通知受影响用户
- 应用内提示

### Phase 2: 过渡期 (14 天)

- 功能仍可用但标记"即将下线"
- 提供迁移指南
- 数据导出支持

### Phase 3: 下线

- 移除功能
- 重定向到替代方案
- 保留只读访问 (如适用)

---

## 用户通知模板

```
主题: [重要] {Feature Name} 功能变更通知

Hi {name},

{Feature Name} 将于 {date} 进行以下变更:
- {变更内容}

我们建议您:
- {迁移建议}

如有问题请联系支持团队。

Make Decodables 团队
```

---

## Feature Flag 配置

```python
# 使用 Feature Flag 控制下线
FEATURE_FLAGS = {
    'legacy_editor': {
        'enabled': False,  # 已下线
        'sunset_date': '2026-02-01',
        'redirect_to': '/editor/v2'
    }
}
```

---

## 相关文档

- [Feature Flag 系统](../../04-engineering/modules/config/feature-flags.md)
- [变更公告 (Public)](../../../public/news/announcements/)
