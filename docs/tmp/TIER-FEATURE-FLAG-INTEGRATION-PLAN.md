# Feature Flag 扩展：Tier + 用户特征分层筛选

> **版本**: v1.2.0
> **创建日期**: 2026-01-12
> **状态**: ✅ 全部完成 (代码 + 文档)
> **需求来源**: 用户需求 - "先选择 tier 层级，然后再选择用户特征或者分类"
> **实施日期**: 2026-01-12
> **文档更新**: 2026-01-12

---

## 1. 需求理解

### 1.1 业务场景

```
当前 Feature Flag 系统：
- 支持用户黑白名单
- 支持百分比灰度
- 支持定向规则 (email/country/device 等)
- 支持时间窗口
- ❌ 不支持 Tier 条件筛选

目标：
- ✅ 支持 "Tier 优先" 的分层筛选
- ✅ 先选择 Tier 层级 (t1/t2/t3/t4)，再选择用户特征
```

### 1.2 使用示例

| 场景 | Tier 条件 | 用户条件 | 效果 |
|------|-----------|----------|------|
| 新功能内测 | `["t3"]` | 20% 百分比 | 仅对 Pro 用户的 20% 开放 |
| Beta 测试 | `["t2", "t3"]` | 白名单 | 对 Starter/Pro 中的指定用户开放 |
| Enterprise 预览 | `["t4"]` | 100% | 对所有 Enterprise 用户开放 |
| 分层推广 | `["t3"]` → `["t2"]` | 先 100%，再 50% | 先全量 Pro，再 50% Starter |

---

## 2. 技术方案

### 2.1 设计原则

1. **向后兼容**：现有 Flag 配置不受影响
2. **Tier 优先**：Tier 是第一层过滤，用户条件是第二层
3. **复用现有结构**：扩展 `targeting_rules` 字段，不新建表
4. **统一评估引擎**：在 `UnifiedEvaluator` 中添加 Tier 检查步骤

### 2.2 数据结构扩展

#### 方案 A：在 `targeting_rules` 中添加 Tier 条件 (推荐)

```json
{
  "targeting_rules": [
    {
      "id": "rule_pro_beta",
      "priority": 1,
      "tiers": ["t3"],                    // 新增: Tier 筛选
      "conditions": [
        {"attribute": "country", "operator": "in", "value": ["US", "CA"]}
      ],
      "rollout_percentage": 50,           // 规则内百分比
      "variant": "treatment"
    }
  ]
}
```

#### 方案 B：顶层添加 `allowed_tiers` 字段

```json
{
  "allowed_tiers": ["t2", "t3", "t4"],    // 新增: 顶层 Tier 限制
  "targeting_rules": [...],               // 现有规则
  "rollout_percentage": 50
}
```

**选择方案 A + B 混合**：
- 顶层 `allowed_tiers` 作为全局过滤（不在列表中直接返回 disabled）
- 规则级 `tiers` 作为精细控制（不同 Tier 可以有不同规则）

---

## 3. 工作列表

### Phase 1: 数据库 Schema 变更

#### 3.1 修改 `feature_flags` 表

**文件**: `decodables/migrations/v2/02_platform_services.sql`

**变更内容**:
```sql
-- 在 feature_flags 表中添加字段 (约 Line 304 附近)
-- 在 blacklist_user_ids 后添加:
allowed_tiers TEXT[] DEFAULT ARRAY[]::TEXT[],  -- 空数组表示不限制

-- 添加注释
COMMENT ON COLUMN feature_flags.allowed_tiers IS 'v1.2: 允许的 Tier 列表,空数组表示所有 Tier 都允许';
```

**变更位置**: Line 306 附近（在 `blacklist_user_ids` 后）

**回滚方案**:
```sql
ALTER TABLE feature_flags DROP COLUMN IF EXISTS allowed_tiers;
```

---

### Phase 2: 类型系统更新

#### 3.2 更新 `EvaluationContext`

**文件**: `decodables/core/feature_flag/types.py`

**变更内容**:
```python
# Line 87: tier 字段已存在，无需修改
tier: Optional[str] = None  # 用户层级 (t1/t2/t3/t4)
```

**状态**: ✅ 已存在，无需修改

#### 3.3 添加 `EvaluationReason.TIER_MISMATCH`

**文件**: `decodables/core/feature_flag/types.py`

**变更内容** (Line 24-35):
```python
class EvaluationReason(str, Enum):
    """评估原因枚举"""
    DISABLED = "disabled"           # Flag 未启用
    TIME_WINDOW = "time_window"     # 不在时间窗口内
    ENVIRONMENT = "environment"     # 环境不匹配
    TIER_MISMATCH = "tier_mismatch" # 新增: Tier 不匹配
    BLACKLIST = "blacklist"         # 在黑名单中
    WHITELIST = "whitelist"         # 在白名单中
    RULE = "rule"                   # 命中定向规则
    PERCENTAGE = "percentage"       # 百分比灰度
    DEFAULT = "default"             # 默认值
    ERROR = "error"                 # 评估错误
    NOT_FOUND = "not_found"         # Flag 不存在
```

---

### Phase 3: 评估引擎修改

#### 3.4 更新 `UnifiedEvaluator`

**文件**: `decodables/core/feature_flag/evaluator.py`

**变更 1**: 添加 Tier 检查步骤 (在环境检查后，黑名单检查前)

```python
# Line 70-99: evaluate() 方法
def evaluate(
    self,
    flag: Dict[str, Any],
    context: EvaluationContext,
) -> EvaluationResult:
    flag_key = flag.get("key", "unknown")
    flag_type = FlagType(flag.get("flag_type", "boolean"))

    try:
        # 1. 检查总开关
        if not flag.get("enabled", False):
            return self._result(flag, False, EvaluationReason.DISABLED)

        # 2. 检查时间窗口
        if not self._check_time_window(flag):
            return self._result(flag, False, EvaluationReason.TIME_WINDOW)

        # 3. 检查环境
        if not self._check_environment(flag, context):
            return self._result(flag, False, EvaluationReason.ENVIRONMENT)

        # 4. 新增: 检查 Tier 限制 (顶层)
        if not self._check_allowed_tiers(flag, context):
            return self._result(flag, False, EvaluationReason.TIER_MISMATCH)

        # 5. 检查黑名单
        if self._in_blacklist(flag, context):
            return self._result(flag, False, EvaluationReason.BLACKLIST)

        # 6. 检查白名单 (命中则立即返回treatment)
        if self._in_whitelist(flag, context):
            return self._result(
                flag, True, EvaluationReason.WHITELIST,
                variant=self._get_first_treatment_variant(flag)
            )

        # 7. 评估定向规则
        rule_result = self._evaluate_rules(flag, context)
        if rule_result:
            return rule_result

        # 8. 计算变体分配 (百分比灰度)
        return self._assign_variant(flag, context)

    except Exception as e:
        logger.error(f"Flag evaluation error: {flag_key}, {e}", exc_info=True)
        return self._result(flag, False, EvaluationReason.ERROR)
```

**变更 2**: 添加 `_check_allowed_tiers()` 方法

```python
def _check_allowed_tiers(self, flag: Dict, context: EvaluationContext) -> bool:
    """
    检查 Tier 限制 (顶层过滤)

    - 空数组 = 不限制 Tier
    - 非空数组 = 用户 Tier 必须在列表中
    """
    allowed_tiers = flag.get("allowed_tiers", [])

    # 空数组表示不限制
    if not allowed_tiers:
        return True

    user_tier = context.tier
    if not user_tier:
        # 无 Tier 信息时，检查是否允许 "unknown"
        return "unknown" in allowed_tiers or not allowed_tiers

    return user_tier.lower() in [t.lower() for t in allowed_tiers]
```

**变更 3**: 更新 `_match_rule_conditions()` 支持规则级 Tier 条件

```python
def _match_rule_conditions(
    self,
    rule: Dict,
    context: EvaluationContext
) -> bool:
    """匹配规则条件 (所有条件必须满足)"""

    # 新增: 检查规则级 Tier 限制
    rule_tiers = rule.get("tiers", [])
    if rule_tiers:
        user_tier = context.tier
        if not user_tier or user_tier.lower() not in [t.lower() for t in rule_tiers]:
            return False

    # 原有逻辑: 检查 conditions
    conditions = rule.get("conditions", [])
    for condition in conditions:
        if not self._match_condition(condition, context):
            return False

    return True
```

---

### Phase 4: 领域层更新

#### 3.5 更新 `FeatureFlagEntity`

**文件**: `decodables/domains/feature_flags/entity.py`

**变更内容**:
```python
# 在 class FeatureFlagEntity 中添加字段 (约 Line 20-60)
@dataclass
class FeatureFlagEntity:
    id: str
    key: str
    name: str
    description: Optional[str]
    flag_type: str
    enabled: bool
    archived: bool
    status: str
    default_value: bool
    environments: List[str]
    start_at: Optional[datetime]
    end_at: Optional[datetime]
    rollout_percentage: int
    whitelist_user_ids: List[str]
    blacklist_user_ids: List[str]
    allowed_tiers: List[str] = field(default_factory=list)  # 新增
    targeting_rules: List[Dict]
    variants: List[Dict]
    default_variant: str
    tags: List[str]
    owner: Optional[str]
    parent_flags: List[str]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]
```

#### 3.6 更新 `FeatureFlagRepository`

**文件**: `decodables/domains/feature_flags/repository.py`

**变更内容**:
- `_to_entity()` 方法添加 `allowed_tiers` 字段映射
- `create()` 方法添加 `allowed_tiers` 参数
- `update()` 方法支持更新 `allowed_tiers`

```python
# _to_entity() 方法 (约 Line 60-100)
def _to_entity(self, data: Dict) -> FeatureFlagEntity:
    return FeatureFlagEntity(
        # ... 现有字段 ...
        blacklist_user_ids=data.get("blacklist_user_ids", []),
        allowed_tiers=data.get("allowed_tiers", []),  # 新增
        targeting_rules=data.get("targeting_rules", []),
        # ... 其他字段 ...
    )
```

---

### Phase 5: API 层更新

#### 3.7 更新 Feature Flag Admin API

**文件**: `decodables/api/admin/feature_flags.py`

**变更 1**: 更新 Request Model

```python
# 创建 Flag 的 Request Model (约 Line 50-100)
class CreateFeatureFlagRequest(BaseModel):
    key: str
    name: str
    description: Optional[str] = None
    flag_type: str = "boolean"
    enabled: bool = False
    environments: List[str] = ["production", "staging"]
    rollout_percentage: int = Field(0, ge=0, le=100)
    whitelist_user_ids: List[str] = []
    blacklist_user_ids: List[str] = []
    allowed_tiers: List[str] = []  # 新增: 空数组表示不限制
    targeting_rules: List[Dict] = []
    variants: List[Dict] = []
    tags: List[str] = []

# 更新 Flag 的 Request Model
class UpdateFeatureFlagRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    environments: Optional[List[str]] = None
    rollout_percentage: Optional[int] = Field(None, ge=0, le=100)
    whitelist_user_ids: Optional[List[str]] = None
    blacklist_user_ids: Optional[List[str]] = None
    allowed_tiers: Optional[List[str]] = None  # 新增
    targeting_rules: Optional[List[Dict]] = None
    variants: Optional[List[Dict]] = None
    tags: Optional[List[str]] = None
```

**变更 2**: 添加 Tier 验证

```python
# 在创建/更新 Flag 时验证 allowed_tiers
VALID_TIERS = {"t1", "t2", "t3", "t4"}

def validate_allowed_tiers(tiers: List[str]) -> None:
    """验证 Tier 列表"""
    if not tiers:
        return  # 空数组是有效的

    invalid = set(t.lower() for t in tiers) - VALID_TIERS
    if invalid:
        raise HTTPException(400, f"Invalid tiers: {invalid}. Valid: {VALID_TIERS}")
```

---

### Phase 6: 前端 Admin UI 更新

#### 3.8 Feature Flag 管理页面

**文件**: `decodables-fe/app/admin/feature-flags/...`

**变更内容**:
1. 添加 "Allowed Tiers" 多选组件
2. 在 targeting_rules 编辑器中添加 "tiers" 字段
3. 更新 Flag 详情展示

```typescript
// 组件示例
<MultiSelect
  label="Allowed Tiers"
  options={[
    { value: "t1", label: "Free (t1)" },
    { value: "t2", label: "Starter (t2)" },
    { value: "t3", label: "Pro (t3)" },
    { value: "t4", label: "Enterprise (t4)" },
  ]}
  value={flag.allowed_tiers}
  onChange={(tiers) => updateFlag({ allowed_tiers: tiers })}
  placeholder="All tiers (no restriction)"
/>
```

---

### Phase 7: 测试

#### 3.9 单元测试

**文件**: `decodables/tests/core/feature_flag/test_evaluator.py`

**新增测试用例**:
```python
class TestTierFiltering:
    """Tier 过滤测试"""

    def test_allowed_tiers_empty_allows_all(self):
        """空 allowed_tiers 允许所有用户"""
        flag = {"key": "test", "enabled": True, "allowed_tiers": []}
        context = EvaluationContext(user_id="u1", tier="t1")
        result = evaluator.evaluate(flag, context)
        assert result.reason != EvaluationReason.TIER_MISMATCH

    def test_allowed_tiers_filters_out_non_matching(self):
        """allowed_tiers 过滤不匹配的 Tier"""
        flag = {"key": "test", "enabled": True, "allowed_tiers": ["t3"]}
        context = EvaluationContext(user_id="u1", tier="t1")
        result = evaluator.evaluate(flag, context)
        assert result.reason == EvaluationReason.TIER_MISMATCH
        assert result.enabled == False

    def test_allowed_tiers_allows_matching(self):
        """allowed_tiers 允许匹配的 Tier"""
        flag = {"key": "test", "enabled": True, "allowed_tiers": ["t2", "t3"]}
        context = EvaluationContext(user_id="u1", tier="t3")
        result = evaluator.evaluate(flag, context)
        assert result.reason != EvaluationReason.TIER_MISMATCH

    def test_rule_level_tiers(self):
        """规则级 Tier 条件"""
        flag = {
            "key": "test",
            "enabled": True,
            "allowed_tiers": [],  # 顶层不限制
            "targeting_rules": [
                {
                    "id": "r1",
                    "tiers": ["t3"],  # 规则级限制
                    "conditions": [],
                    "variant": "treatment"
                }
            ]
        }
        # t3 用户命中规则
        ctx_t3 = EvaluationContext(user_id="u1", tier="t3")
        result_t3 = evaluator.evaluate(flag, ctx_t3)
        assert result_t3.reason == EvaluationReason.RULE

        # t1 用户不命中规则，进入百分比分配
        ctx_t1 = EvaluationContext(user_id="u2", tier="t1")
        result_t1 = evaluator.evaluate(flag, ctx_t1)
        assert result_t1.reason in [EvaluationReason.PERCENTAGE, EvaluationReason.DEFAULT]
```

#### 3.10 集成测试

**文件**: `decodables/tests/integration/test_feature_flag_tier.py`

**测试场景**:
1. API 创建带 `allowed_tiers` 的 Flag
2. API 更新 `allowed_tiers`
3. 评估服务正确过滤 Tier
4. 前端正确展示 Tier 配置

---

### Phase 8: 文档更新

#### 3.11 更新设计文档

**文件**: `decodables/docs/shared/feature-flag-design.md` (如存在)

**新增内容**:
- Tier 分层筛选功能说明
- `allowed_tiers` 字段说明
- 规则级 `tiers` 字段说明
- 评估流程更新 (8 步 → 包含 Tier 检查)

#### 3.12 更新 API 文档

**文件**: `decodables/docs/main/api-reference.md`

**新增内容**:
- Feature Flag API 的 `allowed_tiers` 参数说明
- targeting_rules 中的 `tiers` 字段说明

---

## 4. 实施顺序

| 序号 | 任务 | 文件 | 预计改动 | 依赖 |
|------|------|------|----------|------|
| 1 | Schema 变更 | `migrations/v2/02_platform_services.sql` | +3 行 | 无 |
| 2 | 类型更新 | `core/feature_flag/types.py` | +1 行 | 无 |
| 3 | 评估引擎 | `core/feature_flag/evaluator.py` | +30 行 | 2 |
| 4 | Entity | `domains/feature_flags/entity.py` | +2 行 | 1 |
| 5 | Repository | `domains/feature_flags/repository.py` | +10 行 | 4 |
| 6 | Admin API | `api/admin/feature_flags.py` | +20 行 | 5 |
| 7 | 单元测试 | `tests/core/feature_flag/test_evaluator.py` | +60 行 | 3 |
| 8 | 集成测试 | `tests/integration/test_feature_flag_tier.py` | 新文件 | 6 |
| 9 | 前端 UI | `decodables-fe/app/admin/feature-flags/...` | +50 行 | 6 |
| 10 | 文档更新 | `docs/...` | +100 行 | 全部 |

---

## 5. 文件变更汇总

### 后端文件 (8 个)

| 文件路径 | 变更类型 | 变更说明 |
|----------|----------|----------|
| `migrations/v2/02_platform_services.sql` | 修改 | 添加 `allowed_tiers` 字段 |
| `core/feature_flag/types.py` | 修改 | 添加 `TIER_MISMATCH` 枚举 |
| `core/feature_flag/evaluator.py` | 修改 | 添加 Tier 检查逻辑 |
| `domains/feature_flags/entity.py` | 修改 | 添加 `allowed_tiers` 字段 |
| `domains/feature_flags/repository.py` | 修改 | 支持 `allowed_tiers` CRUD |
| `api/admin/feature_flags.py` | 修改 | 添加 `allowed_tiers` 参数验证 |
| `tests/core/feature_flag/test_evaluator.py` | 修改 | 添加 Tier 测试用例 |
| `tests/integration/test_feature_flag_tier.py` | 新增 | 集成测试 |

### 前端文件 (待确认具体路径)

| 文件路径 | 变更类型 | 变更说明 |
|----------|----------|----------|
| `app/admin/feature-flags/[key]/page.tsx` | 修改 | 添加 Tier 配置 UI |
| `app/admin/feature-flags/create/page.tsx` | 修改 | 添加 Tier 选择组件 |
| `components/admin/FeatureFlagForm.tsx` | 修改 | 添加 Tier 字段 |

### 文档文件 (2 个)

| 文件路径 | 变更类型 | 变更说明 |
|----------|----------|----------|
| `docs/shared/feature-flag-design.md` | 修改 | 添加 Tier 筛选说明 |
| `docs/main/api-reference.md` | 修改 | 更新 API 参数说明 |

---

## 6. 评估流程变更

### 变更前 (7 步)

```
1. enabled 检查
2. 时间窗口检查
3. 环境检查
4. 黑名单检查
5. 白名单检查
6. 定向规则评估
7. 百分比分配
```

### 变更后 (8 步)

```
1. enabled 检查
2. 时间窗口检查
3. 环境检查
4. ⭐ Tier 检查 (新增)
5. 黑名单检查
6. 白名单检查
7. 定向规则评估 (支持规则级 Tier)
8. 百分比分配
```

---

## 7. 回滚方案

### 数据库回滚

```sql
-- 移除 allowed_tiers 字段
ALTER TABLE feature_flags DROP COLUMN IF EXISTS allowed_tiers;
```

### 代码回滚

```bash
# 回滚到实施前的 commit
git revert <commit-hash>
```

---

## 8. 风险评估

| 风险 | 级别 | 缓解措施 |
|------|------|----------|
| 现有 Flag 评估受影响 | 低 | `allowed_tiers` 默认空数组，不影响现有 Flag |
| 性能下降 | 低 | Tier 检查是 O(1) 操作 |
| 前端兼容性 | 中 | 前端需同步更新，否则无法配置新字段 |
| 数据迁移 | 无 | 新字段有默认值，无需迁移现有数据 |

---

## 9. 验收标准

### 功能验收

- [ ] 创建 Flag 时可以设置 `allowed_tiers`
- [ ] 更新 Flag 时可以修改 `allowed_tiers`
- [ ] 评估时正确过滤不匹配 Tier 的用户
- [ ] targeting_rules 中支持 `tiers` 字段
- [ ] Admin UI 可以配置 Tier 限制

### 测试验收

- [ ] 单元测试覆盖率 ≥ 80%
- [ ] 所有现有测试通过
- [ ] 新增测试用例全部通过

### 文档验收

- [ ] API 文档已更新
- [ ] 设计文档已更新
- [ ] 变更日志已记录

---

**END OF DOCUMENT**
