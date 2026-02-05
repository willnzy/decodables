# ADR-0002 数据库驱动配置

> **状态**: ✅ Active
> **日期**: 2026-01-09
> **决策者**: Backend Team

---

## 背景

系统中存在大量可配置项:

1. Tier 价格和权益
2. AI 功能成本
3. 限流配置
4. Feature Flags
5. UI 文案

原有方案是将这些配置硬编码在代码中，导致:

- 修改配置需要发布新版本
- 无法追踪配置变更历史
- 不同环境配置管理困难

---

## 决策

采用数据库驱动配置 (Database-Driven Configuration):

1. 系统配置统一存入 `system_configs` 表
2. 通过 Admin API 管理配置
3. 配置变更记录审计日志
4. 支持多级缓存提升性能

---

## 考虑的选项

### 选项 A: 环境变量

- **优点**: 简单，12-factor app 标准
- **缺点**: 修改需要重启，无审计

### 选项 B: 配置文件

- **优点**: 版本控制友好
- **缺点**: 修改需要部署

### 选项 C: 数据库配置 (选中)

- **优点**: 动态修改，可审计，Admin 可管理
- **缺点**: 需要缓存层

### 选项 D: 配置中心 (Consul/etcd)

- **优点**: 专业解决方案
- **缺点**: 额外基础设施，过重

---

## 理由

1. **运营需求**: 需要频繁调整价格、权益等配置
2. **审计需求**: 需要追踪谁在什么时候改了什么
3. **简单性**: 复用现有数据库，无需额外服务
4. **性能**: 通过缓存可以达到接近环境变量的性能

---

## 影响

### 正面影响

- Admin 可以动态调整配置
- 配置变更可追溯
- 支持按环境/Tier 差异化配置
- 可以实现 A/B 测试配置

### 负面影响

- 需要实现缓存层
- 启动时需要加载配置
- 数据库不可用时需要降级策略

### 需要的改动

1. 创建 `system_configs` 表
2. 实现 `ConfigService` 读取和缓存
3. 创建 Admin 配置管理 API
4. 迁移现有硬编码配置

---

## 实现方案

### 数据库表

```sql
CREATE TABLE system_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    value_type VARCHAR(20) NOT NULL,  -- text/json/number/boolean
    config_group VARCHAR(50) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE system_config_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key VARCHAR(100) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    changed_by UUID NOT NULL,
    changed_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 缓存策略

```
┌─────────────────────────────────────┐
│       Application Cache             │
│     (Python dict, 5 min TTL)        │
├─────────────────────────────────────┤
│          Redis Cache                │
│        (30 min TTL)                 │
├─────────────────────────────────────┤
│         Database                    │
│     (system_configs)                │
└─────────────────────────────────────┘
```

### 配置读取

```python
class ConfigService:
    async def get(self, key: str, default: Any = None) -> Any:
        # 1. 检查应用缓存
        if key in self._local_cache:
            return self._local_cache[key]
        
        # 2. 检查 Redis
        value = await self._redis.get(f"config:{key}")
        if value:
            self._local_cache[key] = value
            return value
        
        # 3. 查询数据库
        config = await self._repo.get_by_key(key)
        if config:
            await self._redis.setex(f"config:{key}", 1800, config.value)
            self._local_cache[key] = config.value
            return config.value
        
        return default
```

---

## 相关文档

- [配置系统设计](../../modules/admin/config-ops.md)
- [Admin API 端点](../../api/admin-endpoints.md)
