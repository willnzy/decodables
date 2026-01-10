# Make Decodables V3.0.0 升级路线图

**目标版本**: v3.0.0
**当前状态**: 部分模块已升级
**剩余工作**: 4 个模块待升级

---

## 📋 升级概述

### V3.0.0 标准

V3.0.0 引入了 **Container Pattern** 统一依赖注入：

```python
# ❌ V2.x (Inline Handler)
handler = GetResourcesHandler(content_service)  # Inline 创建
result = await handler.handle(query)

# ✅ V3.0.0 (Container Pattern)
container = get_container()
handler = container.get_resources_handler  # 从 Container 获取
result = await handler.handle(query)
```

### 核心改进

| 改进点 | V2.x | V3.0.0 | 收益 |
|--------|------|--------|------|
| **依赖注入** | FastAPI Depends() | Container Property | 统一管理 |
| **Handler 创建** | Inline 创建 | Container 注册 | 可测试性 |
| **Result 对象** | 部分有 | 完整 | 类型安全 |
| **Service 层** | 直接注入 | Container 管理 | 解耦 |

---

## 📊 升级状态

### 已升级模块 (✅ V3.0.0)

| 模块 | 当前版本 | 升级时间 | 状态 |
|------|----------|----------|------|
| Experiments | v3.31 | 2025-12 | ✅ 完成 |
| Generations | v3.0.0 | 2025-12 | ✅ 完成 |
| Export | v3.0.0 | 2025-12 | ✅ 完成 |
| Marketplace | v3.0.0 | 2025-12 | ✅ 完成 |

### 待升级模块 (⏳ V2.x)

| 模块 | 当前版本 | 预计工时 | 优先级 |
|------|----------|----------|--------|
| **Resources** (System + User) | v2.1.0 | 8h | P0 |
| **Templates** | v2.x | 6h | P1 |
| **Assets** | v2.x | 6h | P1 |
| **System Resources** | v2.1.0 | 4h | P2 |

**总工时**: 24 小时

---

## 🎯 优先级 P0: Resources 模块升级

### 模块范围

1. **System Resources** - 系统资源管理
2. **User Assets** - 用户资源管理

### 当前架构 (v2.1.0)

**特点**: 已使用 Query Handlers，但未使用 Container

```python
# api/user/resources.py
@router.get("/resources")
async def get_resources(
    content_service: ContentService = Depends(get_content_service)
):
    # ❌ Inline 创建 Handler
    handler = GetResourcesHandler(content_service)
    query = GetResourcesQuery(user_id=user_id)
    result = await handler.handle(query)
    return result.to_dict()
```

### 目标架构 (v3.0.0)

```python
# api/user/resources.py
@router.get("/resources")
async def get_resources(
    user_id: str = Depends(get_current_user_id)
):
    # ✅ 从 Container 获取 Handler
    container = get_container()
    handler = container.get_resources_handler

    query = GetResourcesQuery(user_id=user_id)
    result: GetResourcesResult = await handler.handle(query)

    return result.to_dict()
```

### 升级步骤

#### Step 1: 添加 Result 对象 (2h)

为所有 Query 创建对应的 Result 对象：

```python
# application/resources/queries.py

@dataclass
class GetResourcesResult:
    """资源查询结果."""
    resources: List[Dict[str, Any]]
    total: int
    categories: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resources": self.resources,
            "total": self.total,
            "categories": self.categories
        }
```

**需要添加**:
- [x] GetResourcesResult
- [x] GetResourcesByCategoryResult
- [x] SearchResourcesResult
- [x] GetResourceDetailsResult

#### Step 2: 注册到 Container (2h)

```python
# infrastructure/container.py

class Container:
    @property
    def content_service(self) -> ContentService:
        """Content Service 单例."""
        if not hasattr(self, '_content_service'):
            self._content_service = ContentService(
                repository=self.content_repository
            )
        return self._content_service

    @property
    def get_resources_handler(self) -> GetResourcesHandler:
        """GetResourcesHandler 工厂方法."""
        return GetResourcesHandler(
            content_service=self.content_service
        )

    @property
    def search_resources_handler(self) -> SearchResourcesHandler:
        """SearchResourcesHandler 工厂方法."""
        return SearchResourcesHandler(
            content_service=self.content_service
        )
```

#### Step 3: 更新 API 层 (2h)

移除所有 Depends()，使用 Container：

```python
# api/user/resources.py

from infrastructure.container import get_container

@router.get("/resources")
async def get_resources(
    category: Optional[str] = None,
    user_id: str = Depends(get_current_user_id)  # 保留认证
):
    container = get_container()

    if category:
        handler = container.get_resources_by_category_handler
        query = GetResourcesByCategoryQuery(
            category=category,
            user_id=user_id
        )
    else:
        handler = container.get_resources_handler
        query = GetResourcesQuery(user_id=user_id)

    result = await handler.handle(query)
    return result.to_dict()
```

#### Step 4: 更新测试 (2h)

使用 Mock Container：

```python
# tests/api/user/test_resources.py

@pytest.fixture
def mock_container():
    container = Mock()
    container.get_resources_handler = Mock(
        return_value=Mock(
            handle=AsyncMock(
                return_value=GetResourcesResult(
                    resources=[...],
                    total=10,
                    categories=["cat1", "cat2"]
                )
            )
        )
    )
    return container

async def test_get_resources(mock_container):
    # 注入 Mock Container
    with patch('api.user.resources.get_container', return_value=mock_container):
        response = await client.get("/api/user/resources")
        assert response.status_code == 200
```

### 验收标准

- [x] 所有 Query 有对应 Result 对象
- [x] 所有 Handler 注册到 Container
- [x] API 层移除 Inline Handler 创建
- [x] 测试用例更新并通过
- [x] 文档更新

---

## 📋 优先级 P1: Templates 模块升级

### 当前状态

**架构**: V2.x (Service 直接注入)

```python
# api/admin/templates.py
@router.post("/templates")
async def create_template(
    data: CreateTemplateRequest,
    template_service: TemplateService = Depends(get_template_service)
):
    template = await template_service.create(data)
    return template.to_dict()
```

### 升级计划

#### Step 1: 创建 Command/Query 对象 (2h)

```python
# application/templates/commands.py

@dataclass
class CreateTemplateCommand:
    name: str
    category: str
    content: Dict[str, Any]
    user_id: str

@dataclass
class CreateTemplateResult:
    template_id: str
    name: str
    created_at: datetime
```

#### Step 2: 创建 Handler (2h)

```python
# application/templates/handlers.py

class CreateTemplateHandler:
    def __init__(self, template_service: TemplateService):
        self.template_service = template_service

    async def handle(
        self, command: CreateTemplateCommand
    ) -> CreateTemplateResult:
        template = await self.template_service.create(
            name=command.name,
            category=command.category,
            content=command.content,
            user_id=command.user_id
        )
        return CreateTemplateResult(
            template_id=template.id,
            name=template.name,
            created_at=template.created_at
        )
```

#### Step 3: 注册到 Container (1h)

```python
# infrastructure/container.py

@property
def create_template_handler(self) -> CreateTemplateHandler:
    return CreateTemplateHandler(
        template_service=self.template_service
    )
```

#### Step 4: 更新 API (1h)

```python
# api/admin/templates.py

@router.post("/templates")
async def create_template(
    data: CreateTemplateRequest,
    user_id: str = Depends(get_current_user_id)
):
    container = get_container()
    handler = container.create_template_handler

    command = CreateTemplateCommand(
        name=data.name,
        category=data.category,
        content=data.content,
        user_id=user_id
    )

    result = await handler.handle(command)
    return result.to_dict()
```

---

## 📋 优先级 P1: Assets 模块升级

### 升级范围

- User Assets (用户资源上传/管理)
- Asset Versions (资源版本)
- Asset Categories (资源分类)

### 升级步骤

类似 Templates 模块：
1. 创建 Command/Query + Result 对象 (2h)
2. 创建 Handler (2h)
3. 注册到 Container (1h)
4. 更新 API + 测试 (1h)

**总工时**: 6 小时

---

## 📋 优先级 P2: System Resources 模块升级

### 升级范围

- System Assets (系统资源)
- Resource Templates (资源模板)

### 升级步骤

类似 Templates 模块，工时较少因为业务逻辑简单。

**总工时**: 4 小时

---

## 📅 实施时间线

### Week 1: Resources 模块 (8h)

| 任务 | 工时 | 负责人 |
|------|------|--------|
| 添加 Result 对象 | 2h | Backend Team |
| 注册到 Container | 2h | Backend Team |
| 更新 API 层 | 2h | Backend Team |
| 更新测试 | 2h | Backend Team |

### Week 2: Templates 模块 (6h)

| 任务 | 工时 | 负责人 |
|------|------|--------|
| Command/Query + Result | 2h | Backend Team |
| Handler 实现 | 2h | Backend Team |
| Container + API 更新 | 2h | Backend Team |

### Week 3: Assets 模块 (6h)

| 任务 | 工时 | 负责人 |
|------|------|--------|
| Command/Query + Result | 2h | Backend Team |
| Handler 实现 | 2h | Backend Team |
| Container + API 更新 | 2h | Backend Team |

### Week 4: System Resources 模块 (4h)

| 任务 | 工时 | 负责人 |
|------|------|--------|
| 完整升级 | 4h | Backend Team |

**总计**: 24 小时 (约 1 个月)

---

## ✅ 验收标准

### 代码质量

- [ ] 所有 API 使用 Container Pattern
- [ ] 所有 Query/Command 有对应 Result 对象
- [ ] 移除所有 Inline Handler 创建
- [ ] 移除所有 Service Depends() (保留认证 Depends)

### 测试覆盖

- [ ] 测试用例更新并通过
- [ ] Mock Container 正确使用
- [ ] 集成测试覆盖所有 API

### 文档完善

- [ ] API 文档更新
- [ ] 架构文档更新
- [ ] 示例代码更新

---

## 📚 参考资料

### 成功案例

- **Experiments v3.31** - 完整的 Container Pattern 实现
- **Generations v3.0.0** - Query/Command + Result 模式
- **Export v3.0.0** - Handler 注册示例

### 详细升级计划

| 文档 | 位置 |
|------|------|
| RESOURCES-UPGRADE-v3.0.0-PLAN.md | docs/tmp/ |
| SYSTEM-RESOURCES-V3.0.0-PLAN.md | docs/tmp/ |
| USER-ASSETS-V3.0.0-PLAN.md | docs/tmp/ |
| TEMPLATES-V3.0.0-PLAN.md | docs/tmp/ |

---

**最后更新**: 2026-01-10
**维护者**: Make Decodables 后端团队
