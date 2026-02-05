# 垃圾箱系统

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **对应代码**: `decodables-fe/app/dashboard/_hooks/useTrashActions.ts`

---

## 概述

垃圾箱系统实现软删除功能，支持还原和永久删除。

---

## 软删除机制

### 数据库字段

```sql
-- 项目表添加软删除字段
ALTER TABLE projects ADD COLUMN deleted_at TIMESTAMPTZ;
ALTER TABLE projects ADD COLUMN deleted_by UUID REFERENCES users(id);

-- 素材表添加软删除字段
ALTER TABLE assets ADD COLUMN deleted_at TIMESTAMPTZ;
ALTER TABLE assets ADD COLUMN deleted_by UUID REFERENCES users(id);
```

### 查询过滤

```sql
-- 正常列表排除已删除项
SELECT * FROM projects 
WHERE user_id = $1 AND deleted_at IS NULL;

-- 垃圾箱列表只显示已删除项
SELECT * FROM projects 
WHERE user_id = $1 AND deleted_at IS NOT NULL;
```

---

## API 设计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/trash` | 获取垃圾箱内容 |
| POST | `/api/projects/{id}/trash` | 移到垃圾箱 |
| POST | `/api/projects/{id}/restore` | 从垃圾箱还原 |
| DELETE | `/api/projects/{id}/permanent` | 永久删除 |
| DELETE | `/api/trash/empty` | 清空垃圾箱 |

---

## 前端实现

### useTrashActions Hook

```typescript
const useTrashActions = () => {
  const moveToTrash = useMutation({
    mutationFn: (id: string) => api.post(`/api/projects/${id}/trash`),
    onSuccess: () => {
      queryClient.invalidateQueries(['projects']);
      queryClient.invalidateQueries(['trash']);
      toast.success('已移到垃圾箱');
    },
  });
  
  const restore = useMutation({
    mutationFn: ({ id, targetFolderId }) => 
      api.post(`/api/projects/${id}/restore`, { targetFolderId }),
    onSuccess: () => {
      queryClient.invalidateQueries(['projects']);
      queryClient.invalidateQueries(['trash']);
      toast.success('已还原');
    },
  });
  
  const permanentDelete = useMutation({
    mutationFn: (id: string) => api.delete(`/api/projects/${id}/permanent`),
    onSuccess: () => {
      queryClient.invalidateQueries(['trash']);
      toast.success('已永久删除');
    },
  });
  
  const emptyTrash = useMutation({
    mutationFn: () => api.delete('/api/trash/empty'),
    onSuccess: () => {
      queryClient.invalidateQueries(['trash']);
      toast.success('垃圾箱已清空');
    },
  });
  
  return { moveToTrash, restore, permanentDelete, emptyTrash };
};
```

---

## 自动清理

### 定时任务

```python
# 每天运行，删除超过 30 天的软删除项目
async def cleanup_expired_soft_deletes():
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    
    # 永久删除
    await db.execute("""
        DELETE FROM projects 
        WHERE deleted_at IS NOT NULL 
        AND deleted_at < $1
    """, cutoff)
```

### 显示剩余天数

```typescript
const getRemainingDays = (deletedAt: Date) => {
  const expiresAt = addDays(deletedAt, 30);
  return differenceInDays(expiresAt, new Date());
};

// UI 显示
// "将在 15 天后永久删除"
```

---

## 还原位置选择

### 原位置存在

直接还原到原文件夹。

### 原位置不存在

```
┌─────────────────────────────────────┐
│ 选择还原位置                        │
├─────────────────────────────────────┤
│ 原文件夹 "工作项目" 已被删除。       │
│                                     │
│ 请选择新的位置:                     │
│                                     │
│ ○ 根目录                            │
│ ○ 文件夹 A                          │
│ ○ 文件夹 B                          │
│                                     │
│        [取消]  [还原]               │
└─────────────────────────────────────┘
```

---

## 批量操作

### 批量删除

```typescript
const batchMoveToTrash = useMutation({
  mutationFn: (ids: string[]) => 
    api.post('/api/projects/batch-trash', { ids }),
});
```

### 批量还原

```typescript
const batchRestore = useMutation({
  mutationFn: (ids: string[]) =>
    api.post('/api/projects/batch-restore', { ids }),
});
```

---

## 相关文档

- [架构设计](./architecture.md)
- [项目管理页面](../../../02-product/pages/user/dashboard/projects.md)
