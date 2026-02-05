# Feature Flags 功能规格

> **同步范围**: [fullstack]
> **状态**: 🟡 待验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `domains/platform/feature_flags/`

---

## 一、概述

### 1.1 功能定位

Feature Flags 用于控制功能的发布和灰度，支持 A/B 测试和渐进式发布。

### 1.2 使用场景

| 场景 | 说明 |
|------|------|
| 功能开关 | 快速开启/关闭功能 |
| 灰度发布 | 按比例发布新功能 |
| A/B 测试 | 对比不同方案效果 |
| 用户分群 | 特定用户启用功能 |

---

## 二、功能范围

| 功能 | 优先级 | 状态 |
|------|--------|------|
| Boolean Flag | P0 | ✅ |
| 百分比灰度 | P1 | 🟡 |
| 用户分群 | P1 | 🟡 |
| A/B 实验 | P2 | 🔜 |
| 管理界面 | P2 | 🔜 |

---

## 三、Flag 类型

### 3.1 Boolean Flag

最简单的开关类型，值为 true/false。

```python
# 定义
FLAG_AI_PAGE_GENERATION = FeatureFlag(
    key="ai_page_generation",
    type="boolean",
    default_value=False,
    description="Enable AI page generation feature"
)

# 使用
if await feature_flags.is_enabled("ai_page_generation", user_id):
    # 新功能逻辑
    pass
```

### 3.2 Percentage Flag

按百分比灰度发布。

```python
# 定义
FLAG_NEW_EDITOR = FeatureFlag(
    key="new_editor",
    type="percentage",
    percentage=10,  # 10% 用户启用
    description="New editor experience"
)

# 基于 user_id hash 确定是否启用
```

### 3.3 Segment Flag

按用户分群启用。

```python
# 定义
FLAG_BETA_FEATURES = FeatureFlag(
    key="beta_features",
    type="segment",
    segments=["beta_testers", "internal_users"],
    description="Beta features for selected users"
)
```

---

## 四、Flag 配置

### 4.1 数据结构

```python
@dataclass
class FeatureFlag:
    key: str
    type: str  # boolean | percentage | segment
    default_value: bool = False
    percentage: Optional[int] = None
    segments: Optional[List[str]] = None
    description: str = ""
    enabled: bool = True
    created_at: datetime
    updated_at: datetime
```

### 4.2 配置示例

```json
{
  "key": "ai_page_generation",
  "type": "percentage",
  "default_value": false,
  "percentage": 20,
  "segments": ["t3_users"],
  "description": "AI page generation feature",
  "enabled": true
}
```

---

## 五、评估逻辑

### 5.1 评估流程

```
┌─────────────────────────────────────────────────────────────┐
│                    Flag 评估流程                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [请求评估 Flag]                                            │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────┐                                            │
│  │ Flag 存在?  │                                            │
│  └─────────────┘                                            │
│       │                                                     │
│       ├── 否 ──▶ 返回 default_value                         │
│       │                                                     │
│       ▼ 是                                                  │
│  ┌─────────────┐                                            │
│  │ Flag 启用?  │                                            │
│  └─────────────┘                                            │
│       │                                                     │
│       ├── 否 ──▶ 返回 false                                 │
│       │                                                     │
│       ▼ 是                                                  │
│  ┌─────────────┐                                            │
│  │ 评估类型    │                                            │
│  └─────────────┘                                            │
│       │                                                     │
│       ├── boolean ──▶ 返回 default_value                    │
│       │                                                     │
│       ├── percentage ──▶ hash(user_id) % 100 < percentage?  │
│       │                                                     │
│       └── segment ──▶ user in segments?                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 评估代码

```python
class FeatureFlagService:
    async def is_enabled(self, flag_key: str, user_id: UUID) -> bool:
        flag = await self.get_flag(flag_key)
        
        if not flag or not flag.enabled:
            return False
        
        if flag.type == "boolean":
            return flag.default_value
        
        if flag.type == "percentage":
            # 使用 user_id hash 确保一致性
            hash_value = int(hashlib.md5(str(user_id).encode()).hexdigest(), 16)
            return (hash_value % 100) < flag.percentage
        
        if flag.type == "segment":
            user_segments = await self.get_user_segments(user_id)
            return bool(set(flag.segments) & set(user_segments))
        
        return False
```

---

## 六、当前 Flags

### 6.1 生产环境 Flags

| Flag | 类型 | 状态 | 说明 |
|------|------|------|------|
| `ai_page_generation` | percentage | 100% | AI 生成页面 |
| `ocr_feature` | percentage | 100% | OCR 识别 |
| `new_export` | percentage | 50% | 新导出流程 |
| `beta_templates` | segment | beta | Beta 模板 |

### 6.2 开发环境 Flags

| Flag | 类型 | 状态 | 说明 |
|------|------|------|------|
| `debug_mode` | boolean | true | 调试模式 |
| `mock_ai` | boolean | false | Mock AI 响应 |

---

## 七、管理界面 (计划)

### 7.1 Flag 列表

```
┌────────────────────────────────────────────────────────────┐
│  Feature Flags                              [+ Create Flag] │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │ ai_page_generation                           [ON]  │   │
│  │ Type: percentage | 100%                            │   │
│  │ AI page generation feature                         │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │ new_export                                  [ON]   │   │
│  │ Type: percentage | 50%                             │   │
│  │ New export flow with improved UI                   │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 7.2 Flag 编辑

```
┌────────────────────────────────────────────────────────────┐
│  Edit Feature Flag                                         │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Key: [new_export________________]                         │
│                                                            │
│  Type: [Percentage ▼]                                      │
│                                                            │
│  Percentage: [50]%                                         │
│                                                            │
│  Description:                                              │
│  [New export flow with improved UI_______]                 │
│                                                            │
│  Status: ● Enabled  ○ Disabled                             │
│                                                            │
│  [Cancel]                                     [Save]       │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 八、API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/feature-flags` | GET | 获取所有 Flags (Admin) |
| `/feature-flags/{key}` | GET | 获取单个 Flag |
| `/feature-flags/{key}` | PUT | 更新 Flag (Admin) |
| `/feature-flags/evaluate` | POST | 批量评估 Flags |

### 8.1 批量评估

```json
// POST /feature-flags/evaluate
{
  "flags": ["ai_page_generation", "new_export", "beta_templates"]
}

// Response
{
  "ai_page_generation": true,
  "new_export": false,
  "beta_templates": true
}
```

---

## 九、前端使用

### 9.1 Hook

```typescript
// hooks/useFeatureFlag.ts
function useFeatureFlag(flagKey: string): boolean {
  const { data } = useSWR(`/feature-flags/${flagKey}`);
  return data?.enabled ?? false;
}

// 使用
const isNewExportEnabled = useFeatureFlag('new_export');
```

### 9.2 组件

```tsx
// components/FeatureGate.tsx
function FeatureGate({ flag, children, fallback }) {
  const isEnabled = useFeatureFlag(flag);
  return isEnabled ? children : fallback;
}

// 使用
<FeatureGate flag="new_export" fallback={<OldExport />}>
  <NewExport />
</FeatureGate>
```

---

## 十、相关文档

- [平台服务模块架构](../../04-engineering/modules/platform/architecture.md)
- [系统配置](../../05-business/README.md)

---

**END OF DOCUMENT**
