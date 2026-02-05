# Dashboard 模块架构

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `domains/creation/`, `app/(protected)/dashboard/`

---

## 一、模块概述

### 1.1 职责

Dashboard 模块负责用户项目的管理，包括创建、查看、编辑和删除项目。

### 1.2 核心功能

| 功能 | 说明 |
|------|------|
| 项目列表 | 展示用户所有项目 |
| 创建项目 | 从模板或空白创建 |
| 文件夹 | 项目分组管理 |
| 搜索过滤 | 按名称、日期筛选 |
| 批量操作 | 批量删除、移动 |

---

## 二、系统架构

### 2.1 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    Dashboard Module                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │   Frontend  │────▶│     API     │────▶│   Domain    │   │
│  │   (Next.js) │◀────│  (FastAPI)  │◀────│  (Creation) │   │
│  └─────────────┘     └─────────────┘     └─────────────┘   │
│                             │                    │          │
│                             │                    │          │
│                             ▼                    ▼          │
│                      ┌─────────────┐     ┌─────────────┐   │
│                      │   Storage   │     │  PostgreSQL │   │
│                      │  (Supabase) │     │  (Supabase) │   │
│                      └─────────────┘     └─────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、后端架构

### 3.1 目录结构

```
domains/creation/
├── entities.py          # Project, Folder 实体
├── repository.py        # 数据访问接口
├── service.py           # 业务逻辑服务
└── value_objects.py     # 值对象

api/user/
├── projects.py          # 项目 API
└── folders.py           # 文件夹 API
```

### 3.2 核心实体

**Project 实体**:

```python
@dataclass
class Project:
    id: UUID
    user_id: UUID
    name: str
    folder_id: Optional[UUID]
    thumbnail_url: Optional[str]
    page_count: int
    created_at: datetime
    updated_at: datetime
```

**Folder 实体**:

```python
@dataclass
class Folder:
    id: UUID
    user_id: UUID
    name: str
    parent_id: Optional[UUID]
    created_at: datetime
```

### 3.3 服务层

```python
class CreationService:
    # 项目管理
    async def create_project(self, user_id, name, template_id) -> Project
    async def list_projects(self, user_id, folder_id, offset, limit) -> List[Project]
    async def update_project(self, project_id, name) -> Project
    async def delete_project(self, project_id) -> None
    
    # 文件夹管理
    async def create_folder(self, user_id, name, parent_id) -> Folder
    async def list_folders(self, user_id, parent_id) -> List[Folder]
    async def move_to_folder(self, project_id, folder_id) -> None
```

---

## 四、前端架构

### 4.1 目录结构

```
app/(protected)/dashboard/
├── page.tsx             # 主页面
├── _components/
│   ├── ProjectGrid.tsx  # 项目网格
│   ├── ProjectCard.tsx  # 项目卡片
│   ├── FolderList.tsx   # 文件夹列表
│   └── CreateModal.tsx  # 创建弹窗
└── _hooks/
    ├── useProjects.ts   # 项目数据 Hook
    └── useFolders.ts    # 文件夹 Hook
```

### 4.2 状态管理

```typescript
// stores/dashboard/projectStore.ts
interface ProjectState {
  projects: Project[];
  folders: Folder[];
  currentFolder: string | null;
  loading: boolean;
  
  // Actions
  fetchProjects: (folderId?: string) => Promise<void>;
  createProject: (name: string, templateId?: string) => Promise<Project>;
  deleteProject: (id: string) => Promise<void>;
}
```

### 4.3 页面布局

```
┌────────────────────────────────────────────────────────────┐
│  Dashboard                                      [+ Create] │
├─────────────┬──────────────────────────────────────────────┤
│             │                                              │
│  📁 All     │  Search: [______________] [Filter ▼]        │
│  📁 My Work │                                              │
│  📁 Archive │  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐         │
│             │  │     │  │     │  │     │  │     │         │
│             │  │ Proj│  │ Proj│  │ Proj│  │ Proj│         │
│  [+ Folder] │  │     │  │     │  │     │  │     │         │
│             │  └─────┘  └─────┘  └─────┘  └─────┘         │
│             │                                              │
└─────────────┴──────────────────────────────────────────────┘
```

---

## 五、API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/projects` | GET | 项目列表 |
| `/projects` | POST | 创建项目 |
| `/projects/{id}` | GET | 项目详情 |
| `/projects/{id}` | PUT | 更新项目 |
| `/projects/{id}` | DELETE | 删除项目 |
| `/folders` | GET | 文件夹列表 |
| `/folders` | POST | 创建文件夹 |
| `/folders/{id}` | DELETE | 删除文件夹 |

---

## 六、数据库设计

### 6.1 表结构

```sql
-- 项目表
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    name VARCHAR(255) NOT NULL,
    folder_id UUID REFERENCES folders(id),
    thumbnail_url TEXT,
    page_count INTEGER DEFAULT 8,
    data JSONB,  -- 项目数据
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 文件夹表
CREATE TABLE folders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    name VARCHAR(100) NOT NULL,
    parent_id UUID REFERENCES folders(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 6.2 索引

```sql
CREATE INDEX idx_projects_user ON projects(user_id);
CREATE INDEX idx_projects_folder ON projects(folder_id);
CREATE INDEX idx_folders_user ON folders(user_id);
```

---

## 七、配额管理

### 7.1 项目数量限制

| Tier | 限制 |
|------|------|
| t1 (Free) | 3 个项目 |
| t2 (Starter) | 50 个项目 |
| t3 (Pro) | 无限 |

### 7.2 限制检查

```python
async def check_project_quota(user_id: UUID, tier: str) -> bool:
    current_count = await project_repo.count_by_user(user_id)
    max_count = TIER_PROJECT_LIMITS[tier]
    return current_count < max_count
```

---

## 八、相关文档

- [Dashboard 功能规格](../../02-product/features/dashboard.md)
- [编辑器模块架构](../editor/architecture.md)

---

**END OF DOCUMENT**
