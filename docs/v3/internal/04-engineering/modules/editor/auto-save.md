# 自动保存机制

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **对应代码**: `decodables-fe/app/create/_hooks/editor/useSaveOperations.ts`

---

## 概述

编辑器的自动保存机制，确保用户数据不丢失。

---

## 保存策略

### 触发时机

| 触发条件 | 延迟 | 说明 |
|----------|------|------|
| 对象修改 | 3s debounce | 防止频繁保存 |
| 页面切换 | 立即 | 保存当前页面 |
| 关闭/离开 | 立即 | beforeunload 触发 |
| 手动保存 | 立即 | Cmd+S 或点击保存 |
| 定时器 | 60s 间隔 | 兜底保存 |

---

## 实现

### Hook 实现

```typescript
const useAutoSave = () => {
  const { projectId, isDirty, markClean } = useEditorStore();
  const debouncedSave = useDebouncedCallback(save, 3000);
  
  // 监听变更
  useEffect(() => {
    if (isDirty) {
      debouncedSave();
    }
  }, [isDirty]);
  
  // 定时保存
  useEffect(() => {
    const interval = setInterval(() => {
      if (isDirty) {
        save();
      }
    }, 60000);
    return () => clearInterval(interval);
  }, [isDirty]);
  
  // 离开页面保存
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        save();
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isDirty]);
  
  return { save, isDirty };
};
```

---

## 保存流程

```
用户操作 → markDirty() → debounce 3s → save()
                                           ↓
                                    序列化画布数据
                                           ↓
                                    POST /api/projects/{id}
                                           ↓
                                    成功: markClean()
                                    失败: 重试 + 提示
```

---

## 数据格式

```typescript
interface SavePayload {
  projectId: string;
  pages: {
    index: number;
    canvasJson: string;  // Fabric.js JSON
    thumbnail?: string;  // base64 缩略图
  }[];
  metadata: {
    name: string;
    updatedAt: string;
  };
}
```

---

## 冲突处理

### 乐观更新

```typescript
const save = async () => {
  const version = currentVersion;
  
  try {
    const result = await api.saveProject(projectId, data, version);
    setCurrentVersion(result.newVersion);
  } catch (error) {
    if (error.code === 'VERSION_CONFLICT') {
      // 显示冲突对话框
      showConflictDialog(error.serverData);
    }
  }
};
```

### 冲突对话框

```
┌─────────────────────────────────────┐
│ ⚠️ 检测到编辑冲突                    │
├─────────────────────────────────────┤
│ 你的更改与服务器版本冲突。           │
│                                     │
│ [保留本地版本]  [使用服务器版本]    │
│            [合并查看]               │
└─────────────────────────────────────┘
```

---

## 离线支持

### IndexedDB 缓存

```typescript
// 保存到 IndexedDB 作为本地备份
const saveToLocal = async (data: SavePayload) => {
  const db = await openDB('editor-cache');
  await db.put('drafts', data, projectId);
};

// 恢复本地草稿
const loadFromLocal = async (projectId: string) => {
  const db = await openDB('editor-cache');
  return db.get('drafts', projectId);
};
```

---

## 保存状态指示

### UI 反馈

| 状态 | 显示 |
|------|------|
| 未修改 | 无提示 |
| 已修改未保存 | "未保存" 标识 |
| 保存中 | "保存中..." + 旋转图标 |
| 已保存 | "✓ 已保存" (2秒后消失) |
| 保存失败 | "保存失败" + 重试按钮 |

---

## 相关文档

- [架构设计](./architecture.md)
- [项目 API](../../../05-business/)
