# 营销运营系统设计

> **同步范围**: [backend]
> **状态**: 🟢 已验证 (来源: 代码分析 + v2 文档)
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `api/admin/campaigns.py`, `api/admin/experiments.py`

---

## 一、概述

### 1.1 核心能力

| 模块 | 说明 |
|------|------|
| Campaigns | 营销活动管理 |
| Experiments | A/B 实验管理 |
| AI Analysis | 实验智能分析 |

### 1.2 业务流程

```
创建活动/实验 → 配置参数 → 上线运行 → 监控数据 → 分析结果 → 结束归档
```

---

## 二、Campaigns (营销活动)

### 2.1 API 端点

| 端点 | 方法 | Rate Limit | 说明 |
|------|------|------------|------|
| `/api/v2/admin/campaigns` | GET | 30/min | 活动列表 |
| `/api/v2/admin/campaigns/{id}` | GET | 30/min | 活动详情 |
| `/api/v2/admin/campaigns` | POST | 20/min | 创建活动 |
| `/api/v2/admin/campaigns/{id}` | PUT | 20/min | 更新活动 |
| `/api/v2/admin/campaigns/{id}` | DELETE | 10/min | 删除活动 |
| `/api/v2/admin/campaigns/{id}/activate` | POST | 10/min | 激活活动 |
| `/api/v2/admin/campaigns/{id}/pause` | POST | 10/min | 暂停活动 |
| `/api/v2/admin/campaigns/{id}/stats` | GET | 30/min | 活动统计 |

### 2.2 活动类型

```python
class CampaignType(str, Enum):
    DISCOUNT = "discount"         # 折扣活动
    TRIAL = "trial"              # 试用活动
    CREDIT_BONUS = "credit_bonus" # 积分奖励
    FREE_TIER = "free_tier"      # 免费升级
```

### 2.3 活动状态

```python
class CampaignStatus(str, Enum):
    DRAFT = "draft"              # 草稿
    SCHEDULED = "scheduled"      # 已排期
    ACTIVE = "active"            # 进行中
    ENDED = "ended"              # 已结束
    CANCELLED = "cancelled"      # 已取消
```

### 2.4 数据结构

```python
class Campaign:
    id: UUID
    name: str
    description: str
    type: CampaignType
    status: CampaignStatus
    
    # 配置
    config: CampaignConfig
    
    # 时间
    start_at: datetime
    end_at: Optional[datetime]
    
    # 限制
    usage_limit: Optional[int]       # 总使用次数限制
    per_user_limit: int = 1          # 每用户限制
    target_tiers: List[str]          # 目标 Tier
    
    # 统计
    claimed_count: int
    created_at: datetime

class CampaignConfig:
    # 折扣活动
    discount_percent: Optional[int]
    discount_months: Optional[int]
    
    # 积分奖励
    bonus_credits: Optional[int]
    
    # 试用活动
    trial_days: Optional[int]
    trial_tier: Optional[str]
```

### 2.5 活动统计

```python
class CampaignStats:
    campaign_id: UUID
    claimed_count: int
    conversion_rate: float
    
    by_tier: Dict[str, int]
    by_date: List[DailyCount]
    
    revenue_impact: float
```

---

## 三、Experiments (A/B 实验)

### 3.1 API 端点

| 端点 | 方法 | Rate Limit | 说明 |
|------|------|------------|------|
| `/api/v2/admin/experiments` | GET | 30/min | 实验列表 |
| `/api/v2/admin/experiments` | POST | 20/min | 创建实验 |
| `/api/v2/admin/experiments/{key}` | GET | 30/min | 实验详情 |
| `/api/v2/admin/experiments/{key}` | PUT | 20/min | 更新实验 |
| `/api/v2/admin/experiments/{key}` | DELETE | 10/min | 删除实验 |
| `/api/v2/admin/experiments/{key}/status` | PUT | 20/min | 更新状态 |
| `/api/v2/admin/experiments/{key}/results` | GET | 30/min | 实验结果 |
| `/api/v2/admin/experiments/{key}/aggregate` | POST | 10/min | 聚合数据 |
| `/api/v2/admin/experiments/aggregate-all` | POST | 5/min | 全量聚合 |
| `/api/v2/admin/experiments/cache/clear` | POST | 10/min | 清除缓存 |

### 3.2 AI 分析端点

| 端点 | 方法 | Rate Limit | 说明 |
|------|------|------------|------|
| `/api/v2/admin/experiments/{key}/ai-analysis` | POST | 10/min | AI 分析 |
| `/api/v2/admin/experiments/{key}/quick-recommendation` | GET | 30/min | 快速建议 |
| `/api/v2/admin/experiments/{key}/trend` | GET | 20/min | 趋势数据 |
| `/api/v2/admin/experiments/{key}/hourly-trend` | GET | 20/min | 小时趋势 |

### 3.3 实验类型

```python
class ExperimentType(str, Enum):
    AB = "ab"                    # A/B 测试
    MULTIVARIATE = "multivariate" # 多变量测试
```

### 3.4 实验状态

```python
class ExperimentStatus(str, Enum):
    DRAFT = "draft"              # 草稿
    RUNNING = "running"          # 运行中
    PAUSED = "paused"            # 已暂停
    COMPLETED = "completed"      # 已完成
    CANCELLED = "cancelled"      # 已取消
```

### 3.5 数据结构

```python
class Experiment:
    id: UUID
    experiment_key: str           # 唯一键
    name: str
    description: str
    type: ExperimentType
    status: ExperimentStatus
    
    # 变体配置
    variants: List[Variant]
    traffic_allocation: float     # 流量占比 (0-100)
    
    # 目标
    primary_metric: str           # 主要指标
    secondary_metrics: List[str]  # 次要指标
    
    # 时间
    start_at: Optional[datetime]
    end_at: Optional[datetime]
    
    # 统计
    total_participants: int
    created_at: datetime

class Variant:
    key: str                      # control, treatment_a, treatment_b
    name: str
    weight: int                   # 权重 (%)
    config: dict                  # 变体配置
```

### 3.6 实验结果

```python
class ExperimentResults:
    experiment_id: UUID
    
    # 各变体数据
    variants: Dict[str, VariantResult]
    
    # 分析结果
    winner: Optional[str]         # 获胜变体
    lift: float                   # 提升比例
    p_value: float               # 统计显著性
    is_significant: bool         # 是否显著
    confidence_interval: Tuple[float, float]
    
    # AI 分析
    ai_summary: Optional[str]
    ai_recommendation: Optional[str]

class VariantResult:
    participants: int
    conversions: int
    conversion_rate: float
    metric_value: float
    confidence: float
```

### 3.7 趋势数据

```python
class ExperimentTrend:
    experiment_key: str
    period: str                   # daily/hourly
    
    data: List[TrendPoint]

class TrendPoint:
    timestamp: datetime
    variants: Dict[str, float]    # 各变体指标值
```

---

## 四、AI 分析

### 4.1 分析请求

```python
class AIAnalysisRequest:
    experiment_key: str
    analysis_type: str            # summary/recommendation/deep_dive
    additional_context: Optional[str]
```

### 4.2 分析结果

```python
class AIAnalysis:
    experiment_key: str
    
    summary: str                  # 实验摘要
    key_findings: List[str]       # 关键发现
    recommendation: str           # 推荐行动
    confidence_score: float       # 置信度
    
    generated_at: datetime
```

### 4.3 快速建议

```python
class QuickRecommendation:
    experiment_key: str
    
    status: str                   # continue/stop/winner_found
    message: str
    suggested_action: str
    
    # 如果有获胜者
    winner_variant: Optional[str]
    expected_lift: Optional[float]
```

---

## 五、安全与护栏

### 5.1 权限控制

- 所有端点需要 Admin 角色
- 删除操作需要二次确认

### 5.2 业务规则

```python
# 活动规则
- 同一用户同一活动只能领取一次
- 活动开始后不能修改核心配置
- 活动结束后不能重新激活

# 实验规则
- 运行中的实验不能修改变体权重
- 实验结束后保留数据 90 天
- 流量分配总和必须等于 100
```

### 5.3 Rate Limiting

| 操作类型 | 限制 |
|----------|------|
| 列表查询 | 30/min |
| 详情查询 | 30/min |
| 创建/更新 | 20/min |
| 删除 | 10/min |
| 全量聚合 | 5/min |
| AI 分析 | 10/min |

---

## 六、前端交互

### 6.1 布局

```
┌─────────────────────────────────────────────────────┐
│  [活动] [实验] [报告]                               │
├─────────────────────────────────────────────────────┤
│                                                     │
│  筛选: [状态▼] [类型▼] [日期范围]                   │
│                                                     │
│  列表 / 详情视图                                    │
│                                                     │
│  实验详情:                                          │
│  - 概览 (参与者、转化率)                            │
│  - 趋势图 (日/小时)                                 │
│  - AI 分析                                          │
│  - 快速建议                                         │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 6.2 实验监控

```
┌─────────────────────────────────────────────────────┐
│  实验: pricing_v2                                   │
│  状态: 🟢 运行中                                    │
├─────────────────────────────────────────────────────┤
│  变体对比                                           │
│  ┌─────────┬────────────┬────────────┬──────────┐ │
│  │ 变体    │ 参与者     │ 转化率     │ 提升     │ │
│  ├─────────┼────────────┼────────────┼──────────┤ │
│  │ control │ 1,234      │ 5.2%       │ -        │ │
│  │ treat_a │ 1,256      │ 6.1%       │ +17.3%   │ │
│  │ treat_b │ 1,198      │ 5.8%       │ +11.5%   │ │
│  └─────────┴────────────┴────────────┴──────────┘ │
│                                                     │
│  📊 [查看趋势] 🤖 [AI 分析] 💡 [快速建议]          │
└─────────────────────────────────────────────────────┘
```

---

## 七、相关文档

- [Admin API 端点](../../api/admin-endpoints.md)
- [Feature Flag 引擎](../../../02-standards/feature-flag-engine.md)
- [Analytics 系统](./analytics-ops.md)

---

**END OF DOCUMENT**
