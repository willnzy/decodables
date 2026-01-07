# ADR-0002: 数据库驱动的积分配置系统

## Status
Accepted

## Context

### 问题背景
在 DDD 重构过程中，发现 `BillingService` 中的积分消耗配置存在以下问题：

1. **硬编码配置**: 积分消耗值硬编码在代码中
   ```python
   OPERATION_COSTS = {
       "image_generation": 5,
       "text_generation": 1,
       "smart_scan": 10,
       "ocr": 2,
   }
   ```

2. **无法动态调整**: Admin 修改定价需要改代码、重新部署
3. **无法 A/B 测试**: 无法测试不同定价策略对用户行为的影响
4. **配置分散**: 代码中的默认值可能与实际业务需求不一致
5. **缺乏审计**: 无法追踪配置变更历史

### Railway 部署错误
在实现过程中还发现了两个技术问题：
- `ErrorCode.PAYMENT_REQUIRED` 枚举值缺失
- `CreditCost` dataclass 被错误地实例化

## Decision

采用**数据库优先 + Emergency Fallback** 的配置管理策略：

### 架构设计

```
┌──────────────────────────────────────┐
│  BillingService.get_operation_cost() │
└──────────────┬───────────────────────┘
               │
               ▼
       ┌───────────────┐
       │ ConfigService │ (缓存 60s)
       └───────┬───────┘
               │
               ▼
    ┌──────────────────────┐
    │ system_configs 表     │ ← 主要来源 (Admin 可配置)
    │ - credits.cost.*     │
    └──────────────────────┘
               │ (查询失败)
               ▼
    ┌──────────────────────────┐
    │ EMERGENCY_FALLBACK_COSTS │ ← 备用来源 (代码中)
    │ + WARNING 日志           │
    └──────────────────────────┘
```

### 配置优先级
1. **数据库 system_configs 表** (主要来源)
   - Config key 格式: `credits.cost.{operation}`
   - Admin 可通过 API 或直接修改数据库
   - 60 秒缓存 TTL

2. **Emergency Fallback** (备用来源)
   - 代码中的常量 `EMERGENCY_FALLBACK_COSTS`
   - 仅在数据库完全不可用时使用
   - 触发 WARNING 级别日志

### 实现细节

#### 1. BillingService 修改
```python
class BillingService:
    EMERGENCY_FALLBACK_COSTS = {
        "image_generation": 5,
        "text_generation": 1,
        "smart_scan": 10,
        "ocr": 2,
    }

    def __init__(self, repository, config_service=None):
        self._config_service = config_service

    def get_operation_cost(self, operation: str) -> int:
        # 1. Try database first
        if self._config_service:
            config_value = self._config_service.get_config(
                f"credits.cost.{operation}",
                use_cache=True
            )
            if config_value:
                return int(config_value)

        # 2. Use emergency fallback with WARNING
        logger.warning(f"Using EMERGENCY fallback for {operation}")
        return self.EMERGENCY_FALLBACK_COSTS[operation]
```

#### 2. 数据库配置 (ddl.sql)
```sql
INSERT INTO system_configs (key, value, value_type, config_group, description, is_active)
VALUES
  ('credits.cost.image_generation', '5', 'integer', 'credits', 'AI图像生成积分消耗', true),
  ('credits.cost.text_generation', '1', 'integer', 'credits', 'AI文本生成积分消耗', true),
  ('credits.cost.smart_scan', '10', 'integer', 'credits', 'Smart Scan积分消耗', true),
  ('credits.cost.ocr', '2', 'integer', 'credits', 'OCR识别积分消耗', true)
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
```

## Consequences

### Positive
- ✅ **动态配置**: Admin 可实时调整积分消耗，无需重启服务
- ✅ **A/B 测试友好**: 可测试不同定价策略（如限时优惠）
- ✅ **单一真实来源**: 数据库是配置的唯一真实来源 (Single Source of Truth)
- ✅ **可审计**: 通过 `updated_at` 和 `updated_by` 字段追踪变更
- ✅ **性能优化**: 60秒缓存，避免频繁查询数据库
- ✅ **优雅降级**: 数据库不可用时仍能正常工作（使用 fallback）
- ✅ **可观测性**: CRITICAL/WARNING 日志便于监控和告警

### Negative
- ⚠️ **增加数据库依赖**: 如果 system_configs 表数据丢失，会影响业务
- ⚠️ **初始化依赖**: 需要确保数据库有初始配置数据
- ⚠️ **缓存一致性**: 60秒缓存可能导致短暂的配置不一致（可接受）

### Mitigation (缓解措施)
1. **数据备份**: system_configs 表随数据库自动备份
2. **初始化脚本**: ddl.sql 包含初始配置，确保部署后立即可用
3. **Fallback 保护**: 代码中的 Emergency Fallback 确保关键流程不中断
4. **监控告警**: 使用 fallback 时记录 WARNING，可配置 Sentry 告警

## Alternatives Considered

### 方案 A: 保持硬编码 + 环境变量覆盖
```python
CREDITS_PER_IMAGE = int(os.getenv("CREDITS_PER_IMAGE", "5"))
```
- **优点**: 实现简单，通过环境变量可调整
- **缺点**:
  - 需要重启服务才能生效
  - 无法做 A/B 测试
  - 无审计记录
- **结论**: ❌ 不满足动态配置需求

### 方案 B: 应用启动时从数据库加载 (无 fallback)
```python
@app.on_event("startup")
async def load_configs():
    # 从数据库加载所有配置到内存
    global OPERATION_COSTS
    OPERATION_COSTS = await load_credit_costs_from_db()
```
- **优点**: 性能最好（纯内存访问）
- **缺点**:
  - 数据库配置缺失时应用无法启动（fail-fast）
  - 修改配置需要重启应用
  - 无动态调整能力
- **结论**: ❌ 不符合实时调整需求

### 方案 C: 数据库优先 + Emergency Fallback (选中)
- **优点**:
  - 数据库是主要来源，满足动态配置
  - Fallback 保证高可用性
  - 有缓存优化性能
- **缺点**: 实现稍复杂
- **结论**: ✅ 最佳平衡

### 方案 D: 完全无 fallback (强制数据库)
```python
def get_operation_cost(self, operation: str) -> int:
    if not self._config_service:
        raise RuntimeError("ConfigService not available")
    cost = self._config_service.get_config(f"credits.cost.{operation}")
    if cost is None:
        raise RuntimeError(f"Config not found: {operation}")
    return int(cost)
```
- **优点**: 最纯粹的 Single Source of Truth
- **缺点**:
  - 数据库故障时功能完全不可用
  - 运维风险高
- **结论**: ❌ 可用性优先于纯粹性

## Implementation

### 修改的文件
1. `domains/billing/service.py`
   - 添加 `config_service` 依赖注入
   - 重命名 `OPERATION_COSTS` → `EMERGENCY_FALLBACK_COSTS`
   - 实现数据库优先的 `get_operation_cost()` 方法
   - 添加日志记录

2. `ddl.sql`
   - 添加 4 个积分配置到 system_configs 表
   - 使用 `ON CONFLICT DO UPDATE` 确保幂等性

3. `core/exceptions/base.py`
   - 添加 `ErrorCode.PAYMENT_REQUIRED` 枚举值

4. `domains/billing/exceptions.py`
   - 修正 `ErrorCode.RESOURCE_NOT_FOUND` 引用

### 相关提交
- `b4ed6ec` - 修复 ErrorCode.PAYMENT_REQUIRED 缺失
- `4bcc7f4` - 修复 CreditCost 初始化错误
- `f44b06b` - 实现数据库驱动配置系统

### 测试验证
1. **正常流程**: 数据库有配置 → 返回数据库值
2. **Fallback 流程**: 数据库无配置 → 返回 fallback 值 + WARNING 日志
3. **ConfigService 缺失**: 直接使用 fallback
4. **缓存测试**: 60秒内不重复查询数据库

## Admin 使用指南

### 修改积分配置

**方式 1: 通过 SQL**
```sql
UPDATE system_configs
SET value = '8', updated_by = 'admin@example.com'
WHERE key = 'credits.cost.image_generation';
```

**方式 2: 通过 Admin API** (待实现)
```bash
POST /api/v2/admin/configs
{
  "key": "credits.cost.image_generation",
  "value": "8"
}
```

### 监控配置使用情况

查看是否使用了 fallback（应该收到告警）：
```bash
# 查看日志中的 WARNING
grep "Using EMERGENCY fallback" logs/app.log

# Sentry 中应该有 WARNING 级别事件
```

## Future Enhancements

1. **版本控制**: 记录配置变更历史到 `config_audit_logs` 表
2. **灰度发布**: 支持按用户等级/地区应用不同配置
3. **Admin UI**: 可视化配置管理界面
4. **实时生效**: 使用 Redis Pub/Sub 立即刷新缓存（而非等待 60 秒）
5. **配置验证**: 添加配置值范围校验（如积分不能为负数）

## Notes

此决策解决了 Railway 部署错误，同时建立了可扩展的配置管理体系。未来所有需要动态配置的业务参数都可以采用相同模式。
