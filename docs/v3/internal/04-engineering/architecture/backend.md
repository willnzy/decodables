# 后端架构

> **同步范围**: [backend]
> **状态**: 🟢 已验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: 代码结构分析, v2/01-architecture/backend-architecture.md

---

## 一、概述

### 1.1 设计理念

三层架构 + 轻量级 DDD 融合：

- **框架层与业务层清晰分离**: core/shared 提供基础能力
- **业务逻辑按领域组织**: domains 按业务域划分
- **规则内聚在聚合内**: Entity + Service 封装业务规则
- **数据访问通过仓储抽象**: Repository 模式隔离数据层

### 1.2 技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| 框架 | FastAPI | >=0.128.0 |
| 语言 | Python | 3.12.7 |
| 数据验证 | Pydantic | >=2.12.5 |
| 数据库 | Supabase (PostgreSQL) | - |
| 缓存 | Redis | >=5.0.0 |
| 任务队列 | RQ | >=1.15.0 |

---

## 二、目录结构

```
decodables/
├── api/                     # HTTP 入口层
│   ├── user/               # 用户端 API (59 files)
│   │   ├── auth.py
│   │   ├── projects.py
│   │   ├── billing.py
│   │   └── ...
│   └── admin/              # 管理端 API
│       ├── users.py
│       ├── analytics.py
│       └── ...
│
├── application/             # 应用层 (用例编排)
│   ├── commands/           # 写操作命令
│   │   ├── billing.py
│   │   ├── creation.py
│   │   └── ...
│   ├── queries/            # 读操作查询
│   │   ├── assets.py
│   │   ├── marketplace.py
│   │   └── ...
│   ├── services/           # 应用服务
│   │   ├── aggregators/    # 数据聚合器
│   │   ├── campaigns/      # 营销活动
│   │   └── metrics/        # 指标计算
│   └── handlers/           # 命令/查询处理器
│       ├── command_bus.py
│       └── query_bus.py
│
├── domains/                 # 领域层 (业务核心, 35 domains)
│   ├── auth/               # 认证领域
│   ├── billing/            # 计费领域
│   ├── creation/           # 创作领域
│   ├── identity/           # 身份领域
│   ├── marketplace/        # 市场领域
│   └── ...                 # 其他领域
│
├── infrastructure/          # 基础设施层
│   ├── repositories/       # 仓储实现 (50+ files)
│   ├── cache/              # 缓存实现
│   ├── monitoring/         # 监控
│   ├── task_queue/         # 任务队列
│   └── websocket/          # WebSocket
│
├── core/                    # 框架层 (业务无关)
│   ├── auth/               # 认证工具
│   ├── cache/              # 缓存抽象
│   ├── database/           # 数据库客户端
│   ├── exceptions/         # 异常定义
│   ├── middleware/         # 中间件
│   ├── feature_flag/       # Feature Flag
│   └── utils/              # 工具函数
│
└── shared/                  # 共享服务 (跨域)
    ├── ai/                 # AI 服务
    ├── payment/            # 支付服务
    ├── storage/            # 存储服务
    └── email/              # 邮件服务
```

---

## 三、分层职责

### 3.1 API 层 (api/)

**职责**: HTTP 入口，参数验证，DTO 转换

```python
# api/user/projects.py
@router.get("/{project_id}")
async def get_project(
    project_id: UUID,
    current_user: AuthUser = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    project = await project_service.get_project(project_id, current_user.id)
    return ProjectResponse.from_entity(project)
```

**规则**:
- 只调用 Application 或 Domain Service
- 不直接访问 Repository
- 负责请求验证和响应格式化

### 3.2 应用层 (application/)

**职责**: 用例编排，跨域协作，事务边界

```python
# application/services/creation_service.py
class CreationApplicationService:
    def __init__(
        self,
        project_service: ProjectService,
        billing_service: BillingService,
    ):
        self.project_service = project_service
        self.billing_service = billing_service
    
    async def create_ai_page(self, user_id: UUID, data: CreateAIPageData):
        # 检查积分
        await self.billing_service.check_credits(user_id, cost=5)
        # 创建页面
        page = await self.project_service.create_page(user_id, data)
        # 扣除积分
        await self.billing_service.deduct_credits(user_id, cost=5)
        return page
```

**规则**:
- 编排多个领域服务
- 管理事务边界
- 不包含业务规则

### 3.3 领域层 (domains/)

**职责**: 业务规则，聚合，领域服务，仓储接口

```python
# domains/creation/aggregates/project.py
class Project:
    id: UUID
    user_id: UUID
    name: str
    pages: List[Page]
    status: ProjectStatus
    
    def add_page(self, page: Page) -> None:
        if len(self.pages) >= MAX_PAGES:
            raise ProjectLimitExceeded()
        self.pages.append(page)

# domains/creation/service.py
class ProjectService:
    def __init__(self, repository: ProjectRepository):
        self.repository = repository
    
    async def create_project(self, user_id: UUID, name: str) -> Project:
        project = Project.create(user_id=user_id, name=name)
        return await self.repository.save(project)
```

**规则**:
- 封装业务规则
- 定义仓储接口（不实现）
- 不依赖 infrastructure

### 3.4 基础设施层 (infrastructure/)

**职责**: 仓储实现，第三方集成，技术实现

```python
# infrastructure/repositories/project_repository.py
class SupabaseProjectRepository(ProjectRepository):
    def __init__(self, client: AsyncClient):
        self.client = client
    
    async def get_by_id(self, id: UUID) -> Optional[Project]:
        result = await self.client.table("projects")\
            .select("*, pages(*)")\
            .eq("id", str(id))\
            .single()\
            .execute()
        return Project.from_dict(result.data) if result.data else None
```

**规则**:
- 实现领域层定义的接口
- 处理数据库交互
- 封装第三方服务

### 3.5 框架层 (core/)

**职责**: 业务无关的基础能力

| 模块 | 用途 |
|------|------|
| `auth/` | JWT 处理，认证上下文 |
| `cache/` | 缓存抽象（Redis/Memory） |
| `database/` | Supabase 客户端封装 |
| `exceptions/` | 统一异常定义 |
| `middleware/` | HTTP 中间件 |
| `feature_flag/` | Feature Flag 评估 |
| `utils/` | 通用工具函数 |

### 3.6 共享层 (shared/)

**职责**: 跨域共享的业务服务

| 模块 | 用途 |
|------|------|
| `ai/` | OpenAI, FAL.ai 集成 |
| `payment/` | Stripe 集成 |
| `storage/` | Supabase Storage |
| `email/` | Resend 邮件服务 |

---

## 四、领域列表

### 4.1 核心业务域

| 领域 | 职责 | 关键实体 |
|------|------|----------|
| `auth` | 认证授权 | AuthUser, Session |
| `identity` | 用户身份 | UserProfile |
| `billing` | 计费积分 | UserCredits, Payment |
| `subscriptions` | 订阅管理 | Subscription |
| `creation` | 项目创作 | Project, Page |
| `marketplace` | 素材市场 | Listing, Asset |

### 4.2 支撑业务域

| 领域 | 职责 | 关键实体 |
|------|------|----------|
| `generation` | AI 生成 | GenerationHistory |
| `export` | 导出服务 | ExportTask |
| `templates` | 模板管理 | Template |
| `themes` | 主题管理 | Theme |
| `content` | 内容管理 | SystemResource |

### 4.3 平台域

| 领域 | 职责 | 关键实体 |
|------|------|----------|
| `feature_flags` | 功能开关 | FeatureFlag |
| `onboarding` | 新手引导 | OnboardingProgress |
| `events` | 事件追踪 | Event |
| `analytics` | 数据分析 | AnalyticsEvent |

---

## 五、核心模式

### 5.1 Repository 模式

```python
# 接口定义 (domains/creation/repository.py)
class ProjectRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[Project]: ...
    
    @abstractmethod
    async def list_by_user(
        self, user_id: UUID, offset: int = 0, limit: int = 20
    ) -> List[Project]: ...
    
    @abstractmethod
    async def save(self, project: Project) -> Project: ...

# 实现 (infrastructure/repositories/project_repository.py)
class SupabaseProjectRepository(ProjectRepository):
    # ... 具体实现
```

### 5.2 依赖注入

```python
# dependencies.py
def get_project_service(
    db: AsyncClient = Depends(get_supabase_client),
) -> ProjectService:
    repository = SupabaseProjectRepository(db)
    return ProjectService(repository)
```

### 5.3 异常处理

```python
# core/exceptions/base.py
class AppException(Exception):
    error_code: str
    message: str
    http_status: int = 400

# domains/creation/exceptions.py
class ProjectNotFound(AppException):
    error_code = "PROJECT_NOT_FOUND"
    message = "项目不存在"
    http_status = 404
```

---

## 六、命名规范

### 6.1 分页参数

```python
# ✅ 正确
async def list_projects(offset: int = 0, limit: int = 20): ...

# ❌ 错误
async def list_projects(page: int = 1, limit: int = 20): ...
```

### 6.2 返回类型

```python
# ✅ 正确
async def list_projects() -> List[Project]: ...

# ❌ 错误
async def list_projects() -> List[dict]: ...
```

### 6.3 文件命名

| 类型 | 命名 | 示例 |
|------|------|------|
| 实体 | `entity.py` 或 `aggregates/` | `project.py` |
| 服务 | `service.py` 或 `{name}_service.py` | `project_service.py` |
| 仓储接口 | `repository.py` | `repository.py` |
| 仓储实现 | `{name}_repository.py` | `project_repository.py` |
| 异常 | `exceptions.py` | `exceptions.py` |

---

## 七、调用路径

### 7.1 标准路径

```
API Router → Application Service → Domain Service → Repository
```

### 7.2 简单查询路径

```
API Router → Domain Service → Repository
```

### 7.3 示例

```python
# 创建项目流程
1. POST /api/v1/projects
2. api/user/projects.py: create_project()
3. domains/creation/service.py: ProjectService.create_project()
4. infrastructure/repositories/project_repository.py: save()
5. Supabase: INSERT INTO projects
```

---

## 八、测试策略

### 8.1 测试目录

```
tests/
├── unit/                   # 单元测试
│   ├── domains/           # 领域测试
│   └── core/              # 框架测试
├── integration/            # 集成测试
│   ├── api/               # API 测试
│   └── repositories/      # 仓储测试
└── conftest.py            # 共享 fixtures
```

### 8.2 测试覆盖率目标

- 领域层: ≥ 80%
- 应用层: ≥ 70%
- API 层: ≥ 60%
- 整体: ≥ 65%

---

## 九、相关文档

- [架构总览](./overview.md)
- [前端架构](./frontend.md)
- [数据库设计](./database.md)
- [API 参考](../api/)

---

**END OF DOCUMENT**
