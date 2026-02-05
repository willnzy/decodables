# 前端架构

> **同步范围**: [frontend]
> **状态**: 🟢 已验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: 代码结构分析, tsconfig.json, package.json

---

## 一、概述

### 1.1 设计理念

- **页面组件化**: 页面由可复用组件组合而成
- **状态分离**: 服务端状态与客户端状态分离管理
- **关注点分离**: 业务逻辑与 UI 渲染分离
- **类型安全**: TypeScript 提供编译时类型检查

### 1.2 技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| 框架 | Next.js | 16.1.1 |
| UI 库 | React | 19.2.3 |
| 语言 | TypeScript | 5.9+ |
| 状态管理 | Zustand | 5.0.9 |
| 服务端状态 | TanStack Query | 5.90.19 |
| 编辑器 | Fabric.js | 5.3.0 |
| 样式 | Tailwind CSS | 4.x |

---

## 二、目录结构

```
decodables-fe/
├── app/                     # Next.js App Router (673 files)
│   ├── (user)/             # 用户端路由组
│   │   ├── page.tsx        # 首页
│   │   ├── create/         # 编辑器
│   │   ├── dashboard/      # 仪表盘
│   │   ├── marketplace/    # 素材市场
│   │   └── profile/        # 个人中心
│   ├── (admin)/            # 管理端路由组
│   │   └── admin/
│   ├── (auth)/             # 认证路由组
│   │   ├── login/
│   │   └── signup/
│   ├── api/                # API 路由 (BFF)
│   └── layout.tsx          # 根布局
│
├── components/              # UI 组件库 (168 files)
│   ├── ui/                 # 基础 UI 组件 (Button, Dialog, etc.)
│   ├── editor/             # 编辑器组件
│   ├── dashboard/          # 仪表盘组件
│   ├── marketplace/        # 素材市场组件
│   └── shared/             # 共享业务组件
│
├── hooks/                   # 自定义 Hooks (17 files)
│   ├── useAnalytics.ts     # 数据分析
│   ├── useApiCall.ts       # API 调用
│   ├── useCredits.ts       # 积分管理
│   ├── useIsMobile.ts      # 设备检测
│   ├── useProjects.ts      # 项目管理
│   └── ...
│
├── lib/                     # 工具库和服务
│   ├── auth/               # 认证模块
│   │   ├── authApi.ts
│   │   ├── AuthProvider.tsx
│   │   ├── authStore.ts
│   │   └── useAuth.ts
│   ├── config/             # 配置管理
│   │   ├── store/
│   │   ├── hooks/
│   │   └── providers/
│   ├── fonts/              # 字体服务
│   ├── textEffects/        # 文字效果
│   ├── textPath/           # 文字路径
│   ├── textTemplates/      # 文字模板
│   ├── analytics.ts        # 数据分析
│   ├── logger.ts           # 日志服务
│   └── utils.ts            # 工具函数
│
├── services/                # API 服务层 (20 files)
│   ├── api.ts              # API 基础配置
│   ├── projectService.ts   # 项目服务
│   ├── marketplaceService.ts # 素材市场服务
│   ├── paymentService.ts   # 支付服务
│   └── ...
│
├── e2e/                     # E2E 测试
│   └── flows/              # 测试流程
│
├── __tests__/               # 单元测试 (87 files)
│
└── public/                  # 静态资源
    ├── fonts/              # 字体文件
    └── images/             # 图片资源
```

---

## 三、分层职责

### 3.1 页面层 (app/)

**职责**: 路由定义，页面组合，数据获取

```typescript
// app/(user)/dashboard/page.tsx
export default async function DashboardPage() {
  // 服务端数据获取
  const projects = await getProjects();
  
  return (
    <DashboardLayout>
      <ProjectList initialData={projects} />
    </DashboardLayout>
  );
}
```

**规则**:
- 使用 App Router 约定
- 服务端组件优先
- 页面只负责组合，不包含业务逻辑

### 3.2 组件层 (components/)

**职责**: UI 渲染，用户交互

```typescript
// components/dashboard/ProjectCard.tsx
interface ProjectCardProps {
  project: Project;
  onEdit: () => void;
  onDelete: () => void;
}

export function ProjectCard({ project, onEdit, onDelete }: ProjectCardProps) {
  return (
    <Card>
      <CardHeader>{project.name}</CardHeader>
      <CardContent>
        <Thumbnail src={project.thumbnail} />
      </CardContent>
      <CardFooter>
        <Button onClick={onEdit}>编辑</Button>
        <Button onClick={onDelete}>删除</Button>
      </CardFooter>
    </Card>
  );
}
```

**分类**:
| 目录 | 说明 |
|------|------|
| `ui/` | 基础组件 (Radix UI 封装) |
| `editor/` | 编辑器相关组件 |
| `dashboard/` | 仪表盘组件 |
| `marketplace/` | 素材市场组件 |
| `shared/` | 跨模块共享组件 |

### 3.3 Hooks 层 (hooks/)

**职责**: 状态逻辑复用，副作用管理

```typescript
// hooks/useProjects.ts
export function useProjects() {
  const queryClient = useQueryClient();
  
  const { data: projects, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectService.listProjects(),
  });
  
  const createProject = useMutation({
    mutationFn: projectService.createProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
  
  return { projects, isLoading, createProject };
}
```

### 3.4 服务层 (services/)

**职责**: API 调用封装

```typescript
// services/projectService.ts
class ProjectService {
  async listProjects(): Promise<Project[]> {
    const response = await api.get('/projects');
    return response.data;
  }
  
  async createProject(data: CreateProjectData): Promise<Project> {
    const response = await api.post('/projects', data);
    return response.data;
  }
}

export const projectService = new ProjectService();
```

### 3.5 工具层 (lib/)

**职责**: 通用工具，配置管理

| 模块 | 职责 |
|------|------|
| `auth/` | 认证状态管理 |
| `config/` | 应用配置管理 |
| `fonts/` | 字体加载服务 |
| `logger.ts` | 日志服务 |
| `analytics.ts` | 数据分析 |

---

## 四、状态管理

### 4.1 状态分类

| 类型 | 工具 | 示例 |
|------|------|------|
| **服务端状态** | TanStack Query | 项目列表，用户信息 |
| **客户端状态** | Zustand | 编辑器状态，UI 状态 |
| **URL 状态** | Next.js Router | 路由参数，查询参数 |
| **表单状态** | React State | 输入值，验证状态 |

### 4.2 Zustand Store 示例

```typescript
// lib/auth/authStore.ts
interface AuthState {
  user: User | null;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: true,
  setUser: (user) => set({ user, isLoading: false }),
  logout: () => set({ user: null }),
}));
```

### 4.3 TanStack Query 示例

```typescript
// hooks/useCredits.ts
export function useCredits() {
  return useQuery({
    queryKey: ['credits'],
    queryFn: () => api.get('/billing/credits'),
    staleTime: 30 * 1000, // 30 秒
    refetchOnWindowFocus: true,
  });
}
```

---

## 五、路由设计

### 5.1 路由组结构

```
app/
├── (user)/              # 用户端 (需要认证)
│   ├── page.tsx         # / 首页
│   ├── create/          # /create/* 编辑器
│   ├── dashboard/       # /dashboard/* 仪表盘
│   ├── marketplace/     # /marketplace/* 素材市场
│   └── profile/         # /profile/* 个人中心
│
├── (admin)/             # 管理端 (需要管理员权限)
│   └── admin/           # /admin/*
│
├── (auth)/              # 认证页面 (公开)
│   ├── login/           # /login
│   └── signup/          # /signup
│
├── (public)/            # 公开页面
│   ├── about/           # /about
│   ├── help/            # /help
│   └── news/            # /news
│
└── api/                 # API 路由 (BFF)
    └── auth/            # /api/auth/*
```

### 5.2 路由保护

```typescript
// app/(user)/layout.tsx
export default async function UserLayout({ children }) {
  const session = await getServerSession();
  
  if (!session) {
    redirect('/login');
  }
  
  return (
    <AuthProvider session={session}>
      <UserNav />
      {children}
    </AuthProvider>
  );
}
```

---

## 六、响应式设计

### 6.1 断点定义

| 断点 | 宽度 | 设备 |
|------|------|------|
| `sm` | 640px | 手机横屏 |
| `md` | 768px | 平板 |
| `lg` | 1024px | 小桌面 |
| `xl` | 1280px | 桌面 |
| `2xl` | 1536px | 大桌面 |

### 6.2 Mobile-First 原则

```tsx
// 默认样式 = 移动端，md: = 桌面增强
<div className="flex flex-col md:flex-row">
  <Sidebar className="w-full md:w-64" />
  <Main className="flex-1" />
</div>
```

### 6.3 响应式组件

```tsx
// 使用 Sheet (移动) / Dialog (桌面)
<ResponsiveModal>
  <ModalContent />
</ResponsiveModal>
```

---

## 七、测试策略

### 7.1 测试类型

| 类型 | 工具 | 目录 |
|------|------|------|
| 单元测试 | Jest + Testing Library | `__tests__/` |
| E2E 测试 | Playwright | `e2e/` |

### 7.2 测试覆盖率目标

- 组件: ≥ 60%
- Hooks: ≥ 70%
- 服务: ≥ 80%
- 整体: ≥ 60%

### 7.3 E2E 测试流程

```
e2e/flows/
├── editor.spec.ts           # 编辑器流程
├── dashboard.spec.ts        # 仪表盘流程
├── marketplace.spec.ts      # 素材市场流程
├── payment.spec.ts          # 支付流程
└── user-registration.spec.ts # 用户注册
```

---

## 八、性能优化

### 8.1 代码分割

```typescript
// 动态导入
const Editor = dynamic(() => import('@/components/editor/Editor'), {
  loading: () => <EditorSkeleton />,
  ssr: false,
});
```

### 8.2 图片优化

```tsx
// 使用 Next.js Image
import Image from 'next/image';

<Image
  src={project.thumbnail}
  alt={project.name}
  width={300}
  height={200}
  placeholder="blur"
/>
```

### 8.3 缓存策略

```typescript
// TanStack Query 缓存
useQuery({
  queryKey: ['projects'],
  staleTime: 5 * 60 * 1000, // 5 分钟
  cacheTime: 30 * 60 * 1000, // 30 分钟
});
```

---

## 九、路径别名

```json
// tsconfig.json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

**使用示例**:
```typescript
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/auth';
import { projectService } from '@/services/projectService';
```

---

## 十、相关文档

- [架构总览](./overview.md)
- [后端架构](./backend.md)
- [设计系统](../../03-design/)
- [响应式设计指南](../../../decodables-fe/docs/main/responsive-design-guide.md)

---

**END OF DOCUMENT**
