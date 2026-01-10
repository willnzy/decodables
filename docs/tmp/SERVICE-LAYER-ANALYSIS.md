# Service 层删除历史方法分析报告

**创建时间**: 2026-01-10
**分析范围**: 所有 Domain Service 层

---

## 📊 分析结果

### 找到的删除历史方法 (2 个)

#### 1. ProjectRepository.get_user_deleted_projects()

**文件**: `infrastructure/repositories/project_repository.py:675-698`

**当前实现**:
```python
@retry_on_network_error()
async def get_user_deleted_projects(
    self,
    user_id: str,
    limit: int = 20,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Get user's deleted projects."""
    result = self.client.table("projects").select(
        "id, title, thumbnail_url, deleted_at"
    ).eq("user_id", user_id).eq("is_deleted", True).order(
        "deleted_at", desc=True
    ).range(offset, offset + limit - 1).execute()

    return result.data or []
```

**问题**:
- ❌ 未过滤已过期记录 (缺少 `recovery_expires_at > NOW()`)
- ❌ 未使用 BaseRepository 的 `list_deleted_recoverable()`
- ❌ 返回类型是 `List[Dict]`，非 DDD 风格
- ❌ 未返回 total count (分页信息不完整)

**需要修改**:
- ✅ 使用 `list_deleted_recoverable()` 方法
- ✅ 返回 `tuple[List[Project], int]` (Entity + total)
- ✅ 自动过滤已过期记录

---

#### 2. AssetRepository.get_deleted_assets()

**文件**: `infrastructure/repositories/asset_repository.py:277-291`

**当前实现**:
```python
@retry_on_network_error()
async def get_deleted_assets(self, user_id: str) -> List[Dict[str, Any]]:
    """Get soft-deleted assets (trash)."""
    result = self.client.table("assets").select("*").eq(
        "user_id", user_id
    ).eq("is_deleted", True).order("created_at", desc=True).execute()

    return result.data or []
```

**问题**:
- ❌ 未过滤已过期记录
- ❌ 按 `created_at` 排序 (应该按 `deleted_at`)
- ❌ 未使用 BaseRepository
- ❌ 缺少分页参数

**需要修改**:
- ✅ 使用 `list_deleted_recoverable()`
- ✅ 添加分页参数 (offset, limit)
- ✅ 返回 Entity 和 total count

---

## 🎯 修改计划

### Phase 1: 修改 Repository 层

#### 1.1 ProjectRepository

**删除旧方法**:
- ❌ `get_user_deleted_projects()` (Legacy方法，删除)

**说明**: 不需要自定义方法，直接继承 `BaseRepository.list_deleted_recoverable()`

#### 1.2 AssetRepository

**删除旧方法**:
- ❌ `get_deleted_assets()` (Legacy方法，删除)

**说明**: 同样使用 BaseRepository 的方法

---

### Phase 2: 修改 Service 层

#### 2.1 ProjectService

**文件**: `domains/creation/service.py:458-479`

**修改前**:
```python
async def get_user_deleted_projects(
    self,
    user_id: str,
    limit: int = 20,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Get user's deleted projects (trash)."""
    return await self._repository.get_user_deleted_projects(
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
```

**修改后**:
```python
async def get_user_deleted_projects(
    self,
    user_id: str,
    limit: int = 20,
    offset: int = 0
) -> tuple[List[ProjectDTO], int]:
    """
    Get user's deleted projects (recoverable only).

    Only returns projects within recovery period.
    Expired projects are automatically filtered out.

    Args:
        user_id: User ID
        limit: Max results per page
        offset: Results to skip for pagination

    Returns:
        Tuple of (list of ProjectDTO, total count)
    """
    # 使用 BaseRepository 的方法，自动过滤已过期
    projects, total = await self._repository.list_deleted_recoverable(
        user_id=user_id,
        offset=offset,
        limit=limit
    )

    # 转换为 DTO
    project_dtos = [self._to_dto(p) for p in projects]

    return project_dtos, total
```

#### 2.2 AssetService

**文件**: `domains/assets/assets_service.py:193-203`

**修改前**:
```python
async def get_deleted_assets(self, user_id: str) -> List[Dict[str, Any]]:
    """Get soft-deleted assets (trash)."""
    return await self.repository.get_deleted_assets(user_id)
```

**修改后**:
```python
async def get_deleted_assets(
    self,
    user_id: str,
    limit: int = 20,
    offset: int = 0
) -> tuple[List[AssetDTO], int]:
    """
    Get user's deleted assets (recoverable only).

    Only returns assets within recovery period.

    Args:
        user_id: User ID
        limit: Max results per page
        offset: Results to skip for pagination

    Returns:
        Tuple of (list of AssetDTO, total count)
    """
    # 使用 BaseRepository 的方法
    assets, total = await self.repository.list_deleted_recoverable(
        user_id=user_id,
        offset=offset,
        limit=limit
    )

    # 转换为 DTO
    asset_dtos = [self._to_dto(a) for a in assets]

    return asset_dtos, total
```

---

### Phase 3: 更新 DTO

#### 3.1 ProjectDTO

**文件**: `domains/creation/dto.py` (需要确认)

**添加计算属性**:
```python
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, computed_field

class ProjectDTO(BaseModel):
    id: str
    title: str
    thumbnail_url: Optional[str] = None
    user_id: str

    # 软删除字段
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    recovery_expires_at: Optional[datetime] = None

    # 🆕 计算属性: 距离永久删除的天数
    @computed_field
    @property
    def days_until_permanent_delete(self) -> Optional[int]:
        """
        Calculate days until permanent deletion.

        Returns:
            - None if not deleted or already expired
            - int: remaining days (≥ 0)
        """
        if not self.is_deleted or not self.recovery_expires_at:
            return None

        now = datetime.now(timezone.utc)
        if self.recovery_expires_at <= now:
            return None  # Already expired

        delta = self.recovery_expires_at - now
        return delta.days

    # 🆕 计算属性: 是否即将过期
    @computed_field
    @property
    def is_expiring_soon(self) -> bool:
        """Whether recovery period expires within 3 days."""
        days = self.days_until_permanent_delete
        return days is not None and days <= 3

    class Config:
        from_attributes = True
```

#### 3.2 AssetDTO

**文件**: `domains/assets/dto.py` (需要确认)

**添加相同的计算属性** (同上)

---

## 📊 影响分析

### Repository 层变化

| Repository | 删除方法 | 新方法 | 说明 |
|-----------|---------|--------|------|
| ProjectRepository | `get_user_deleted_projects()` | 继承 `list_deleted_recoverable()` | BaseRepository 提供 |
| AssetRepository | `get_deleted_assets()` | 继承 `list_deleted_recoverable()` | BaseRepository 提供 |

### Service 层变化

| Service | 方法 | 返回类型变化 | 说明 |
|---------|------|-------------|------|
| ProjectService | `get_user_deleted_projects()` | `List[Dict]` → `tuple[List[ProjectDTO], int]` | 添加 total count |
| AssetService | `get_deleted_assets()` | `List[Dict]` → `tuple[List[AssetDTO], int]` | 添加分页参数 |

### API 层变化

| API | 影响 | 说明 |
|-----|------|------|
| `GET /projects/deleted` | 响应结构变化 | 需要更新返回值解包 |
| `GET /assets/deleted` | 响应结构变化 + 添加分页 | 需要更新 API 签名 |

---

## ✅ 验收标准

### Repository 层
- [ ] 删除 `get_user_deleted_projects()` 方法
- [ ] 删除 `get_deleted_assets()` 方法
- [ ] 使用 `list_deleted_recoverable()` 替代

### Service 层
- [ ] 修改返回类型为 `tuple[List[DTO], int]`
- [ ] 自动过滤已过期记录
- [ ] 添加完整的分页支持

### DTO 层
- [ ] 添加 `days_until_permanent_delete` 计算属性
- [ ] 添加 `is_expiring_soon` 计算属性

### 测试层
- [ ] 更新 Service 测试
- [ ] 验证自动过滤已过期记录
- [ ] 测试覆盖率 ≥ 80%

---

## 🚀 实施顺序

1. ✅ **Step 1**: 修改 ProjectService (1h)
2. ✅ **Step 2**: 修改 AssetService (0.5h)
3. ✅ **Step 3**: 删除 Repository 旧方法 (0.5h)
4. ✅ **Step 4**: 更新 ProjectDTO (1h)
5. ✅ **Step 5**: 更新 AssetDTO (0.5h)
6. ✅ **Step 6**: 更新测试 (0.5h)

**总工时**: 4h

---

**创建时间**: 2026-01-10
**分析人**: Claude
**状态**: ✅ 分析完成，准备实施
