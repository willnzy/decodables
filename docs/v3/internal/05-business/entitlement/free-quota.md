# 免费配额

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **来源**: v1 shared/entitlement/

---

## 概述

免费用户 (t1) 的配额限制和超额处理。

---

## t1 配额

| 资源 | 限制 |
|------|------|
| 项目数量 | 3 |
| 页面/项目 | 5 |
| 存储空间 | 100 MB |
| 月度积分 | 0 |
| 永久积分 | 100 (注册赠送) |

---

## 超额处理

### 项目超限

```
用户尝试创建第 4 个项目
    ↓
显示升级提示 Modal
    ↓
选择: 升级 / 删除现有项目
```

### 页面超限

```
用户尝试在项目中添加第 6 页
    ↓
显示升级提示 Modal
    ↓
选择: 升级 / 删除现有页面
```

### 存储超限

```
上传时检查累计存储
    ↓
超过 100MB 拒绝上传
    ↓
显示清理建议或升级提示
```

---

## 降级处理

付费用户降级到 t1 后:

| 资源 | 处理 |
|------|------|
| 超额项目 | 保留但变只读 |
| 超额页面 | 保留但不能新增 |
| 超额存储 | 保留但不能上传 |

用户可以:
- 删除内容恢复配额内
- 重新升级解锁

---

## 实现

```python
async def check_project_quota(user_id: str) -> bool:
    """检查用户是否可以创建新项目"""
    user = await get_user(user_id)
    project_count = await count_user_projects(user_id)
    
    limit = TIER_LIMITS[user.tier]['projects']
    
    return project_count < limit
```

---

## 前端处理

```tsx
const CreateProjectButton = () => {
  const { canCreate, upgradeRequired } = useProjectQuota();
  
  if (upgradeRequired) {
    return (
      <UpgradePrompt 
        reason="project_limit"
        currentLimit={3}
      />
    );
  }
  
  return <Button onClick={createProject}>新建项目</Button>;
};
```

---

## 相关文档

- [Tier 权益](../tier-system.md)
- [升级提示组件](../../03-design/components/feedback.md)
