# API Reference 补充文档

> 本文档补充了缺失的 41 个 Admin API 端点
> 生成时间: 2026-01-11
> 基于代码版本: v3.30+

---

## 章节编号说明

建议将现有文档的章节编号统一调整为:
- 7.1 → 6.1 用户管理
- 7.2 → 6.2 订阅管理
- 7.3 → 6.3 统计仪表板
- 7.4 → 6.4 AI 洞察
- 7.5 → 6.5 内容审核
- 7.6 → 6.6 通知管理
- 7.7 → 6.7 系统配置
- 6.8 → 6.8 实验管理

以下为新增章节:

---

## 6.4 AI 洞察 `/ai` (补充完整版)

> 当前文档只有标题,缺少所有端点细节

**注意**: AI Insights 模块代码文件不存在 (`ai_insights.py`)，但文档中提到了 4 个端点。
这些端点可能:
1. 已在其他模块实现 (如 `ai.py` 或 `metrics.py`)
2. 计划中但未实现
3. 已废弃

**建议**: 需要确认这些端点的实际实现位置或标记为"计划中"。

---

## 6.6 通知管理 `/notifications` (补充详细文档)

### GET `/notifications`
获取通知列表

**已实现**: ❌ (此端点不存在,请参考下面的实际端点)

### 实际可用端点:

#### POST `/notifications/broadcast`

发送系统广播通知

**限流**: 5 req/min

**请求体**:
```json
{
  "title": "系统维护通知",
  "content": "我们将在周日凌晨 2:00-4:00 进行系统维护",
  "target_group": "all"
}
```

**target_group 可选值**:
- `all` - 所有用户
- `t1` - Free Plan 用户
- `t2` - Starter Plan 用户
- `t3` - Pro Plan 用户
- `free` - 免费用户 (t1)
- `paid` - 付费用户 (t2 + t3)

**响应**:
```json
{
  "success": true,
  "message": "Broadcast sent successfully",
  "sent_count": 1542,
  "target_group": "all"
}
```

**验证规则**:
- title: 1-200 字符
- content: 1-1000 字符
- target_group 必须在有效值列表中

---

#### POST `/notifications/notification/send`

发送通知给单个用户

**限流**: 30 req/min

**请求体**:
```json
{
  "user_id": "user_2abc3def4ghi",
  "title": "欢迎奖励",
  "content": "您已获得 50 积分奖励!",
  "notification_type": "promo"
}
```

**notification_type 可选值**:
- `system` - 系统通知 (默认)
- `announcement` - 公告
- `alert` - 警告
- `promo` - 促销

**响应**:
```json
{
  "success": true,
  "notification_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_2abc3def4ghi",
  "delivered": true
}
```

**错误码**:
- 400: 无效的 user_id 格式或 notification_type
- 404: 用户不存在

---

#### POST `/notifications/notification/batch`

批量发送通知给多个用户

**限流**: 10 req/min

**请求体**:
```json
{
  "user_ids": ["user_2abc", "user_2def", "user_2ghi"],
  "title": "新功能发布",
  "content": "查看我们全新的编辑器功能!",
  "notification_type": "announcement"
}
```

**限制**:
- 单次最多 100 个用户
- user_ids 不能为空

**响应**:
```json
{
  "success": true,
  "sent_count": 2,
  "failed_count": 1,
  "total_users": 3,
  "failed_user_ids": ["user_2def"]
}
```

**注意**: 部分失败不会抛出错误,请检查 `failed_user_ids` 字段

---

#### GET `/notifications/notification/stats`

获取通知统计数据

**限流**: 30 req/min

**响应**:
```json
{
  "total_sent": 15420,
  "sent_today": 245,
  "sent_this_week": 1832,
  "sent_this_month": 7291,
  "by_type": {
    "system": 8500,
    "announcement": 4200,
    "alert": 1800,
    "promo": 920
  },
  "by_target_group": {
    "all": 10500,
    "t1": 2100,
    "t2": 1800,
    "t3": 1020
  },
  "delivery_rate": 99.2,
  "read_rate": 67.5,
  "avg_time_to_read": "4h 32m"
}
```

**字段说明**:
- `delivery_rate`: 成功送达率 (%)
- `read_rate`: 用户阅读率 (%)
- `avg_time_to_read`: 平均阅读时间

---

#### GET `/notifications/notification/history`

获取通知发送历史

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 (1-100) |

**响应**:
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "系统维护",
      "content": "...",
      "notification_type": "system",
      "target_group": "all",
      "user_id": null,
      "user_ids": null,
      "sent_count": 1542,
      "delivered_count": 1538,
      "read_count": 982,
      "created_at": "2026-01-11T10:30:00Z",
      "created_by": "admin_user_123"
    }
  ],
  "pagination": {
    "offset": 0,
    "limit": 50,
    "total": 324
  }
}
```

**注意**:
- 广播通知: `target_group` 有值, `user_id` 和 `user_ids` 为 null
- 单用户通知: `user_id` 有值, `target_group` 和 `user_ids` 为 null
- 批量通知: `user_ids` 有值, `target_group` 和 `user_id` 为 null

---

## 6.7 系统配置 `/config` (补充详细文档)

### 已有端点 (补充细节)

#### GET `/config`

获取所有系统配置

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `category` | string | 可选,按类别筛选 |

**category 可选值**:
- `rate_limit` - 限流配置
- `feature_flags` - 功能开关
- `system` - 系统设置
- `ai` - AI 服务配置
- `storage` - 存储设置
- `payment` - 支付网关设置

**响应**:
```json
{
  "configs": [
    {
      "key": "rate_limit.api.max_requests",
      "value": {"limit": 100, "window": "minute"},
      "category": "rate_limit",
      "description": "API 每分钟最大请求数",
      "is_active": true,
      "updated_at": "2026-01-10T10:30:00Z"
    }
  ],
  "total": 42
}
```

---

#### GET `/config/{config_key}`

获取单个配置

**限流**: 30 req/min

**路径参数**:
- `config_key`: 配置键 (最大 200 字符)

**示例**:
```
GET /api/v2/admin/config/rate_limit.api.max_requests
```

**响应**:
```json
{
  "key": "rate_limit.api.max_requests",
  "value": {
    "limit": 100,
    "window": "minute",
    "enabled": true
  },
  "is_active": true,
  "updated_at": "2026-01-10T10:30:00Z"
}
```

**错误码**:
- 404: 配置键不存在

---

#### PUT `/config` (新增)

更新单个配置

**限流**: 10 req/min

**请求体**:
```json
{
  "config_key": "rate_limit.api.max_requests",
  "config_value": {
    "limit": 150,
    "window": "minute",
    "enabled": true
  }
}
```

**响应**:
```json
{
  "success": true,
  "message": "Configuration updated successfully",
  "config_key": "rate_limit.api.max_requests"
}
```

**审计日志**: 自动记录到 `admin_operations` 表,包含旧值和新值

---

#### PUT `/config/batch` (新增)

批量更新配置

**限流**: 10 req/min

**请求体**:
```json
{
  "updates": [
    {
      "config_key": "feature_flags.new_editor.enabled",
      "config_value": {"enabled": true, "rollout": 100}
    },
    {
      "config_key": "ai.fal.timeout",
      "config_value": {"seconds": 30}
    }
  ]
}
```

**限制**: 单次最多 100 个配置更新

**响应**:
```json
{
  "success": true,
  "results": {
    "feature_flags.new_editor.enabled": true,
    "ai.fal.timeout": true
  },
  "updated_count": 2,
  "failed_count": 0
}
```

**部分失败响应**:
```json
{
  "success": false,
  "results": {
    "valid_key": true,
    "invalid_key": false
  },
  "updated_count": 1,
  "failed_count": 1
}
```

---

### 限流配置 (新增子章节)

#### GET `/config/rate-limits`

获取所有限流配置

**限流**: 30 req/min

**响应**:
```json
{
  "rate_limits": [
    {
      "key": "rate_limit.api.projects.create",
      "limit": 20,
      "window": "minute",
      "enabled": true
    },
    {
      "key": "rate_limit.api.ai.generate",
      "limit": 10,
      "window": "minute",
      "enabled": true
    }
  ],
  "global_enabled": true,
  "total": 15
}
```

---

#### POST `/config/rate-limits/preset`

应用限流预设方案

**限流**: 10 req/min

**请求体**:
```json
{
  "preset": "strict"
}
```

**preset 可选值**:
- `strict` - 严格模式 (限制最严)
- `normal` - 正常模式 (默认)
- `relaxed` - 宽松模式 (开发环境)
- `disabled` - 禁用限流 (仅测试)

**响应**:
```json
{
  "success": true,
  "message": "Rate limit preset 'strict' applied successfully",
  "preset": "strict"
}
```

**审计日志**: 自动记录到 `admin_operations` 表

---

#### GET `/config/rate-limits/presets`

获取所有可用的限流预设

**限流**: 30 req/min

**响应**:
```json
{
  "presets": [
    {
      "name": "strict",
      "description": "严格限流,适用于生产环境高负载",
      "multiplier": 0.5,
      "enabled": null
    },
    {
      "name": "normal",
      "description": "标准限流,默认配置",
      "multiplier": 1.0,
      "enabled": null
    },
    {
      "name": "relaxed",
      "description": "宽松限流,适用于开发环境",
      "multiplier": 2.0,
      "enabled": null
    },
    {
      "name": "disabled",
      "description": "禁用限流,仅测试使用",
      "multiplier": null,
      "enabled": false
    }
  ],
  "total": 4
}
```

---

#### POST `/config/config/cache/clear` (新增)

清空配置缓存

**限流**: 10 req/min

**响应**:
```json
{
  "success": true,
  "message": "Configuration cache cleared successfully"
}
```

**影响**:
- 清空内存中的配置缓存
- 下次请求会重新从数据库加载
- 适用于配置更新后立即生效

**审计日志**: 自动记录到 `admin_operations` 表

---

## 6.8 实验管理 `/experiments` (补充详细文档)

### 基础 CRUD 端点 (补充细节)

#### GET `/experiments`

获取所有实验列表

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `status` | string | - | 按状态筛选 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 (1-100) |

**status 可选值**:
- `draft` - 草稿
- `running` - 运行中
- `paused` - 已暂停
- `completed` - 已完成

**响应**:
```json
{
  "experiments": [
    {
      "id": "uuid-xxx",
      "experiment_key": "new_pricing_page",
      "name": "新定价页面测试",
      "description": "测试新定价页面对转化率的影响",
      "experiment_type": "ab",
      "status": "running",
      "variants": [
        {"key": "control", "name": "原版", "weight": 50},
        {"key": "treatment", "name": "新版", "weight": 50}
      ],
      "traffic_allocation": 100,
      "start_at": "2026-01-01T00:00:00Z",
      "end_at": null,
      "created_at": "2025-12-20T10:00:00Z",
      "created_by": "admin_user_123"
    }
  ],
  "total": 15,
  "offset": 0,
  "limit": 20
}
```

---

#### POST `/experiments`

创建新实验

**限流**: 20 req/min

**请求体**:
```json
{
  "experiment_key": "new_pricing_page",
  "name": "新定价页面测试",
  "description": "测试新定价页面对转化率的影响",
  "experiment_type": "ab",
  "variants": [
    {"key": "control", "name": "原版", "weight": 50},
    {"key": "treatment", "name": "新版", "weight": 50}
  ],
  "targeting": {
    "include_anonymous": true,
    "tiers": ["t2", "t3"]
  },
  "traffic_allocation": 100,
  "metrics": [
    {"key": "conversion", "event": "purchase", "type": "conversion"}
  ],
  "start_at": "2026-01-15T00:00:00Z",
  "end_at": "2026-02-15T00:00:00Z"
}
```

**字段说明**:
- `experiment_key`: 唯一标识符 (2-100 字符)
- `experiment_type`: `ab` | `multivariate` | `feature_flag`
- `variants`: 变体列表,权重总和必须为 100
- `traffic_allocation`: 流量分配百分比 (0-100)
- `targeting`: 目标用户筛选
- `metrics`: 指标定义

**响应**:
```json
{
  "status": "created",
  "experiment": {
    "id": "uuid-xxx",
    "experiment_key": "new_pricing_page",
    ...
  }
}
```

**错误码**:
- 400: 权重总和不为 100 或 experiment_key 已存在

---

#### GET `/experiments/{experiment_key}`

获取实验详情

**限流**: 30 req/min

**响应**:
```json
{
  "experiment": {
    "id": "uuid-xxx",
    "experiment_key": "new_pricing_page",
    "name": "新定价页面测试",
    "description": "...",
    "experiment_type": "ab",
    "status": "running",
    "variants": [...],
    "targeting": {...},
    "traffic_allocation": 100,
    "metrics": [...],
    "start_at": "2026-01-01T00:00:00Z",
    "end_at": null,
    "fallback_variant": "control",
    "winning_variant": null,
    "created_at": "2025-12-20T10:00:00Z",
    "created_by": "admin_user_123",
    "updated_at": "2026-01-05T14:30:00Z"
  }
}
```

**错误码**:
- 404: 实验不存在

---

#### PUT `/experiments/{experiment_key}`

更新实验配置

**限流**: 20 req/min

**请求体** (所有字段可选):
```json
{
  "name": "新定价页面测试 v2",
  "description": "更新后的描述",
  "variants": [
    {"key": "control", "name": "原版", "weight": 40},
    {"key": "treatment", "name": "新版", "weight": 60}
  ],
  "traffic_allocation": 80,
  "end_at": "2026-03-01T00:00:00Z",
  "fallback_variant": "control",
  "winning_variant": "treatment"
}
```

**响应**:
```json
{
  "status": "updated",
  "experiment": {
    ...
  }
}
```

**错误码**:
- 400: 无更新字段或权重总和不为 100
- 404: 实验不存在

---

#### PUT `/experiments/{experiment_key}/status`

更新实验状态

**限流**: 20 req/min

**请求体**:
```json
{
  "status": "paused"
}
```

**status 可选值**: `draft` | `running` | `paused` | `completed`

**响应**:
```json
{
  "status": "updated",
  "new_status": "paused"
}
```

---

#### DELETE `/experiments/{experiment_key}`

删除实验

**限流**: 10 req/min

**限制**: 不能删除正在运行的实验 (status = `running`)

**响应**:
```json
{
  "status": "deleted",
  "experiment_key": "new_pricing_page"
}
```

**审计日志**: 自动记录到 `admin_operations` 表

**错误码**:
- 400: 实验正在运行
- 404: 实验不存在

---

### 结果与分析端点 (新增)

#### GET `/experiments/{experiment_key}/results`

获取实验结果

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `start_date` | string | 开始日期 (YYYY-MM-DD 或 ISO 格式) |
| `end_date` | string | 结束日期 (YYYY-MM-DD 或 ISO 格式) |

**响应**:
```json
{
  "experiment_key": "new_pricing_page",
  "date_range": {
    "start": "2026-01-01T00:00:00Z",
    "end": "2026-01-11T23:59:59Z"
  },
  "variants": {
    "control": {
      "total_exposures": 5420,
      "total_conversions": 542,
      "conversion_rate": 10.0,
      "avg_revenue": 15.30
    },
    "treatment": {
      "total_exposures": 5380,
      "total_conversions": 645,
      "conversion_rate": 12.0,
      "avg_revenue": 17.80,
      "significance": {
        "p_value": 0.002,
        "is_significant": true,
        "confidence_level": 99.8
      }
    }
  },
  "summary": {
    "winner": "treatment",
    "lift": 20.0,
    "confidence": "high"
  }
}
```

**字段说明**:
- `significance`: 统计显著性分析 (相对于 control 组)
- `lift`: 提升百分比
- `confidence`: 置信度级别 (`low` | `medium` | `high`)

---

#### POST `/experiments/{experiment_key}/aggregate`

触发单个实验的结果聚合

**限流**: 10 req/min

**用途**: 手动触发实验结果的重新计算

**响应**:
```json
{
  "status": "aggregated",
  "experiment_key": "new_pricing_page",
  "message": "Aggregation completed successfully"
}
```

---

#### POST `/experiments/aggregate-all`

触发所有运行中实验的结果聚合

**限流**: 5 req/min

**用途**: 批量更新所有 `running` 状态实验的结果

**响应**:
```json
{
  "status": "aggregated",
  "message": "All experiments aggregated successfully"
}
```

---

#### GET `/experiments/{experiment_key}/trend`

获取实验每日趋势数据

**限流**: 20 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `days` | int | 30 | 天数 (1-90) |

**响应**:
```json
{
  "experiment_key": "new_pricing_page",
  "days": 30,
  "data": [
    {
      "date": "2026-01-01",
      "variants": {
        "control": {
          "exposures": 180,
          "conversions": 18,
          "conversion_rate": 10.0
        },
        "treatment": {
          "exposures": 175,
          "conversions": 21,
          "conversion_rate": 12.0
        }
      }
    }
  ]
}
```

---

#### GET `/experiments/{experiment_key}/hourly-trend`

获取实验每小时趋势数据

**限流**: 20 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `hours` | int | 24 | 小时数 (1-168, 即最多 7 天) |

**响应**:
```json
{
  "experiment_key": "new_pricing_page",
  "hours": 24,
  "data": [
    {
      "hour": "2026-01-11T00:00:00Z",
      "variants": {
        "control": {
          "exposures": 12,
          "conversions": 1,
          "conversion_rate": 8.3
        },
        "treatment": {
          "exposures": 14,
          "conversions": 2,
          "conversion_rate": 14.3
        }
      }
    }
  ]
}
```

---

### AI 分析端点 (新增)

#### POST `/experiments/{experiment_key}/ai-analysis`

获取 AI 驱动的实验分析报告

**限流**: 10 req/min

**请求体** (可选):
```json
{
  "additional_context": "我们在 1 月 5 日进行了营销活动推广"
}
```

**响应**:
```json
{
  "success": true,
  "experiment_key": "new_pricing_page",
  "analysis": {
    "summary": "治疗组 (treatment) 在转化率上显著优于对照组,提升 20%",
    "insights": [
      "treatment 变体在所有用户层级都表现更好",
      "转化率提升在付费用户中最为明显 (+35%)",
      "1月5日后流量激增,但转化率保持稳定"
    ],
    "recommendations": [
      "建议将 treatment 变体设为默认版本",
      "可以将流量分配调整为 100% treatment",
      "继续监控 7 天以确保效果稳定"
    ],
    "risks": [
      "样本量偏小,建议再观察 3-5 天",
      "周末流量特征可能与工作日不同"
    ]
  },
  "generated_at": "2026-01-11T10:30:00Z"
}
```

**注意**: 该端点会调用 OpenAI API,可能需要 5-10 秒响应

---

#### GET `/experiments/{experiment_key}/quick-recommendation`

获取快速决策建议 (基于规则,无 AI)

**限流**: 30 req/min

**响应**:
```json
{
  "experiment_key": "new_pricing_page",
  "recommendation": {
    "action": "deploy_winner",
    "winner": "treatment",
    "reason": "treatment 转化率提升 20%,且 p-value < 0.01 (统计显著)",
    "confidence": "high",
    "next_steps": [
      "将 treatment 变体设为默认",
      "标记实验为 completed",
      "监控 7 天以确保无回归"
    ]
  }
}
```

**action 可能值**:
- `deploy_winner` - 部署获胜变体
- `continue_running` - 继续运行实验
- `stop_test` - 停止实验 (无显著差异)

---

### 缓存管理端点 (新增)

#### POST `/experiments/cache/clear`

清空实验缓存

**限流**: 10 req/min

**响应**:
```json
{
  "status": "cache_cleared"
}
```

**影响**:
- 清空内存中的实验配置缓存
- 下次请求会重新从数据库加载
- 不影响结果数据

---

## 6.9 Feature Flags 管理 `/feature-flags` (新增章节)

### GET `/feature-flags`

列出所有 Feature Flags

**限流**: 无限流 (内部工具)

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `flag_type` | string | - | 按类型筛选 |
| `enabled` | bool | - | 按启用状态筛选 |
| `archived` | bool | false | 是否包含已归档 |
| `tags` | string | - | 按标签筛选 (逗号分隔) |
| `search` | string | - | 搜索 key 或 name |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 (1-100) |

**flag_type 可选值**:
- `boolean` - 布尔开关
- `multivariate` - 多变体
- `experiment` - 实验型

**响应**:
```json
{
  "data": [
    {
      "id": "uuid-xxx",
      "key": "new_editor_ui",
      "name": "新编辑器界面",
      "description": "启用重新设计的编辑器界面",
      "flag_type": "boolean",
      "enabled": true,
      "environments": ["production", "staging"],
      "rollout_percentage": 50,
      "variants": null,
      "targeting_rules": [
        {
          "attribute": "tier",
          "operator": "in",
          "values": ["t3"]
        }
      ],
      "whitelist_user_ids": ["user_123"],
      "blacklist_user_ids": [],
      "start_at": null,
      "end_at": null,
      "tags": ["frontend", "beta"],
      "owner": "product_team",
      "created_at": "2025-12-01T10:00:00Z",
      "created_by": "admin_user_123",
      "updated_at": "2026-01-10T15:30:00Z"
    }
  ],
  "pagination": {
    "offset": 0,
    "limit": 20,
    "total": 42
  }
}
```

---

### POST `/feature-flags`

创建新 Feature Flag

**限流**: 无限流 (内部工具)

**请求体**:
```json
{
  "key": "new_editor_ui",
  "name": "新编辑器界面",
  "description": "启用重新设计的编辑器界面",
  "flag_type": "boolean",
  "enabled": false,
  "environments": ["production", "staging"],
  "rollout_percentage": 10,
  "variants": null,
  "targeting_rules": [
    {
      "attribute": "tier",
      "operator": "in",
      "values": ["t3"]
    }
  ],
  "tags": ["frontend", "beta"],
  "owner": "product_team"
}
```

**字段说明**:
- `key`: 唯一标识符 (3-100 字符,字母数字下划线连字符)
- `rollout_percentage`: 灰度发布百分比 (0-100)
- `targeting_rules`: 目标用户规则 (基于用户属性)
- `variants`: 多变体配置 (仅 multivariate 类型)

**响应**:
```json
{
  "success": true,
  "data": {
    "id": "uuid-xxx",
    "key": "new_editor_ui",
    ...
  }
}
```

**错误码**:
- 400: key 已存在或 flag_type 无效

---

### GET `/feature-flags/{key}`

获取 Feature Flag 详情

**限流**: 无限流 (内部工具)

**响应**:
```json
{
  "data": {
    "id": "uuid-xxx",
    "key": "new_editor_ui",
    ...
  }
}
```

**错误码**:
- 404: Flag 不存在

---

### PATCH `/feature-flags/{key}`

更新 Feature Flag

**限流**: 无限流 (内部工具)

**请求体** (所有字段可选):
```json
{
  "name": "新编辑器界面 v2",
  "enabled": true,
  "rollout_percentage": 50,
  "targeting_rules": [
    {
      "attribute": "tier",
      "operator": "in",
      "values": ["t2", "t3"]
    }
  ],
  "tags": ["frontend", "stable"]
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "id": "uuid-xxx",
    "key": "new_editor_ui",
    ...
  }
}
```

**错误码**:
- 400: 无更新字段
- 404: Flag 不存在

---

### POST `/feature-flags/{key}/toggle`

快速切换 Feature Flag 启用状态

**限流**: 无限流 (内部工具)

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `enabled` | bool | 是 | 目标状态 |

**示例**:
```
POST /api/v2/admin/feature-flags/new_editor_ui/toggle?enabled=true
```

**响应**:
```json
{
  "success": true,
  "data": {
    "id": "uuid-xxx",
    "key": "new_editor_ui",
    "enabled": true,
    ...
  }
}
```

**审计日志**: 自动记录到 `admin_operations` 表

---

### DELETE `/feature-flags/{key}`

归档 Feature Flag (软删除)

**限流**: 无限流 (内部工具)

**响应**:
```json
{
  "success": true,
  "message": "Flag 'new_editor_ui' archived successfully"
}
```

**注意**:
- 软删除,不会永久删除数据
- 归档后的 Flag 不会在默认列表中显示
- 可以通过 `archived=true` 参数查看
- 如果 Flag 在活跃实验中使用,会返回 409 错误

**审计日志**: 自动记录到 `admin_operations` 表

**错误码**:
- 404: Flag 不存在
- 409: Flag 正在使用中

---

### POST `/feature-flags/test-evaluation`

测试 Feature Flag 评估逻辑

**限流**: 无限流 (内部工具)

**请求体**:
```json
{
  "flag_key": "new_editor_ui",
  "user_id": "user_123",
  "tier": "t3",
  "email": "test@example.com",
  "environment": "production",
  "custom": {
    "browser": "chrome",
    "country": "US"
  }
}
```

**响应**:
```json
{
  "flag_key": "new_editor_ui",
  "context": {
    "user_id": "user_123",
    "tier": "t3",
    "email": "test@example.com",
    "environment": "production",
    "custom": {
      "browser": "chrome",
      "country": "US"
    }
  },
  "result": {
    "enabled": true,
    "variant": null,
    "reason": "targeting_rule_match",
    "metadata": {
      "matched_rule": "tier in [t3]",
      "rollout_percentage": 50,
      "user_in_rollout": true
    }
  }
}
```

**reason 可能值**:
- `targeting_rule_match` - 匹配目标规则
- `rollout` - 灰度发布命中
- `whitelist` - 白名单用户
- `blacklist` - 黑名单用户
- `default` - 默认值

---

### GET `/feature-flags/{key}/audit`

获取 Feature Flag 审计日志

**限流**: 无限流 (内部工具)

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 (1-100) |

**响应**:
```json
{
  "data": [
    {
      "timestamp": "2026-01-10T15:30:00Z",
      "action": "toggled",
      "admin_id": "admin_user_123",
      "changes": {
        "enabled": {
          "old": false,
          "new": true
        }
      },
      "metadata": {
        "ip": "192.168.1.100",
        "user_agent": "Mozilla/5.0..."
      }
    }
  ],
  "pagination": {
    "offset": 0,
    "limit": 20,
    "total": 47
  }
}
```

**action 可能值**:
- `created` - 创建
- `updated` - 更新
- `toggled` - 切换启用状态
- `archived` - 归档

---

## 6.10 AI Models 管理 `/ai/models` (新增章节)

### GET `/ai/models/config`

获取所有 AI 模型配置

**限流**: 30 req/min

**响应**:
```json
{
  "configs": {
    "text": {
      "model": "gpt-4-turbo",
      "provider": "openai",
      "temperature": 0.7,
      "max_tokens": 2000,
      "enabled": true
    },
    "image": {
      "free": {
        "model": "flux-schnell",
        "provider": "fal",
        "enabled": true
      },
      "pro": {
        "model": "flux-dev",
        "provider": "fal",
        "enabled": true
      }
    },
    "canary": {
      "enabled": false,
      "percentage": 10,
      "target_model": "gpt-4.5-preview"
    }
  }
}
```

**错误处理**: 如果配置加载失败,返回空对象而非 500 错误

---

### PUT `/ai/models/config/text`

更新文本生成模型配置

**限流**: 20 req/min

**请求体**:
```json
{
  "model": "gpt-4-turbo",
  "provider": "openai",
  "temperature": 0.8,
  "max_tokens": 3000
}
```

**字段验证**:
- `temperature`: 0-2
- `max_tokens`: 1-32000
- `provider`: 必须在有效列表中 (openai, anthropic, etc.)

**响应**:
```json
{
  "status": "updated",
  "config": {
    "model": "gpt-4-turbo",
    "provider": "openai",
    "temperature": 0.8,
    "max_tokens": 3000
  }
}
```

---

### PUT `/ai/models/config/image`

更新图片生成模型配置

**限流**: 20 req/min

**请求体**:
```json
{
  "model": "flux-pro",
  "provider": "fal"
}
```

**响应**:
```json
{
  "status": "updated",
  "config": {
    "model": "flux-pro",
    "provider": "fal"
  }
}
```

---

### PUT `/ai/models/config/canary`

更新 Canary 发布配置

**限流**: 10 req/min

**请求体**:
```json
{
  "enabled": true,
  "percentage": 10,
  "target_model": "gpt-4.5-preview"
}
```

**字段说明**:
- `percentage`: 0-100,表示使用新模型的用户百分比
- `target_model`: 目标模型名称 (Canary 模型)

**响应**:
```json
{
  "status": "updated",
  "canary": {
    "enabled": true,
    "percentage": 10,
    "target_model": "gpt-4.5-preview"
  }
}
```

**注意**: Canary 发布用于逐步推出新模型,降低风险

---

### PUT `/ai/models/providers/toggle`

切换 AI 提供商启用状态

**限流**: 10 req/min

**请求体**:
```json
{
  "provider": "openai",
  "enabled": true
}
```

**provider 可选值**: `openai`, `anthropic`, `fal`, `stability`, `replicate`

**响应**:
```json
{
  "status": "updated",
  "provider": "openai",
  "enabled": true
}
```

**影响**:
- 禁用提供商后,系统会回退到其他可用提供商
- 如果没有可用提供商,相关功能会暂时不可用

---

### GET `/ai/models/usage`

获取 AI 使用统计

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `days` | int | 30 | 统计天数 (1-365) |

**响应**:
```json
{
  "usage": {
    "text_generation": {
      "total_requests": 15420,
      "total_tokens": 3250000,
      "avg_tokens_per_request": 210,
      "cost_usd": 32.50
    },
    "image_generation": {
      "total_requests": 8340,
      "cost_usd": 250.20
    },
    "by_model": {
      "gpt-4-turbo": {
        "requests": 12000,
        "tokens": 2500000,
        "cost_usd": 25.00
      },
      "flux-schnell": {
        "requests": 6000,
        "cost_usd": 120.00
      }
    },
    "by_date": [
      {
        "date": "2026-01-11",
        "text_requests": 520,
        "image_requests": 280,
        "cost_usd": 15.30
      }
    ]
  },
  "days": 30
}
```

**错误处理**: 如果统计数据加载失败,返回空对象而非 500 错误

---

### POST `/ai/models/cache/clear`

清空 AI 缓存

**限流**: 5 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `cache_type` | string | all | 缓存类型 |

**cache_type 可选值**:
- `all` - 所有缓存 (默认)
- `text` - 仅文本生成缓存
- `image` - 仅图片生成缓存

**示例**:
```
POST /api/v2/admin/ai/models/cache/clear?cache_type=text
```

**响应**:
```json
{
  "status": "cleared",
  "cache_type": "text"
}
```

---

## 6.11 内容审核 `/moderation` (补充详细文档)

### Marketplace 审核端点

#### GET `/moderation/marketplace/moderation/list`

获取待审核商品列表

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `status` | string | - | 审核状态筛选 |
| `type` | string | - | 资源类型筛选 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 (1-100) |

**status 可选值**:
- `pending` - 待审核
- `approved` - 已批准
- `rejected` - 已拒绝
- `flagged` - 已标记

**type (resource_type) 可选值**:
- `sticker` - 贴纸
- `background` - 背景
- `template` - 模板
- `font` - 字体
- `image` - 图片

**响应**:
```json
{
  "items": [
    {
      "id": "uuid-xxx",
      "listing_id": "listing_123",
      "title": "可爱动物贴纸包",
      "resource_type": "sticker",
      "seller_id": "user_abc",
      "seller_email": "seller@example.com",
      "price": 299,
      "preview_url": "https://...",
      "status": "pending",
      "submitted_at": "2026-01-10T15:00:00Z",
      "flagged_reasons": []
    }
  ],
  "total": 42,
  "offset": 0,
  "limit": 20
}
```

---

#### GET `/moderation/marketplace/moderation/{listing_id}`

获取商品审核详情

**限流**: 30 req/min

**响应**:
```json
{
  "id": "uuid-xxx",
  "listing_id": "listing_123",
  "title": "可爱动物贴纸包",
  "description": "包含 20 个精美动物贴纸",
  "resource_type": "sticker",
  "seller_id": "user_abc",
  "seller_email": "seller@example.com",
  "seller_tier": "t3",
  "price": 299,
  "allowed_tiers": ["t1", "t2", "t3"],
  "preview_url": "https://...",
  "file_url": "https://...",
  "file_size_bytes": 524288,
  "tags": ["animal", "cute", "sticker"],
  "status": "pending",
  "submitted_at": "2026-01-10T15:00:00Z",
  "reviewed_at": null,
  "reviewed_by": null,
  "rejection_reason": null,
  "flagged_reasons": [],
  "download_count": 0
}
```

**错误码**:
- 404: 商品不存在

---

#### POST `/moderation/marketplace/moderation/{listing_id}/approve`

批准商品上架

**限流**: 30 req/min

**响应**:
```json
{
  "status": "approved",
  "listing_id": "listing_123"
}
```

**影响**:
- 商品状态变为 `published`
- 卖家收到通知
- 商品在市场中可见

**错误码**:
- 404: 商品不存在

---

#### POST `/moderation/marketplace/moderation/{listing_id}/reject`

拒绝商品上架

**限流**: 30 req/min

**请求体**:
```json
{
  "reason": "图片质量不符合标准,请重新上传高清图片"
}
```

**字段验证**:
- `reason`: 1-1000 字符,必填

**响应**:
```json
{
  "status": "rejected",
  "listing_id": "listing_123",
  "reason": "图片质量不符合标准,请重新上传高清图片"
}
```

**影响**:
- 商品状态变为 `rejected`
- 卖家收到拒绝通知 (包含原因)
- 卖家可以修改后重新提交

---

#### POST `/moderation/marketplace/moderation/{listing_id}/delete`

软删除商品

**限流**: 30 req/min

**响应**:
```json
{
  "status": "deleted",
  "listing_id": "listing_123"
}
```

**影响**:
- 商品标记为已删除 (软删除)
- 商品在市场中不可见
- 数据不会物理删除,可恢复

---

#### POST `/moderation/marketplace/moderation/{listing_id}/unpublish`

强制下架商品

**限流**: 30 req/min

**响应**:
```json
{
  "status": "unpublished",
  "listing_id": "listing_123"
}
```

**影响**:
- 商品状态变为 `unpublished`
- 商品在市场中不可见
- 卖家收到下架通知

**用途**: 用于处理违规商品或用户举报

---

### 内容举报端点

#### GET `/moderation/reports`

获取所有内容举报

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `status` | string | - | 举报状态筛选 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 (1-100) |

**status 可选值**:
- `pending` - 待处理
- `in_review` - 审查中
- `resolved` - 已解决
- `dismissed` - 已驳回

**响应**:
```json
{
  "items": [
    {
      "id": "report_xxx",
      "resource_type": "listing",
      "resource_id": "listing_123",
      "reporter_id": "user_abc",
      "reason": "inappropriate_content",
      "description": "包含不适宜内容",
      "status": "pending",
      "created_at": "2026-01-10T16:00:00Z",
      "admin_response": null,
      "resolved_at": null
    }
  ],
  "total": 15,
  "offset": 0,
  "limit": 20,
  "has_more": false
}
```

---

#### GET `/moderation/reports/stats`

获取举报统计

**限流**: 30 req/min

**响应**:
```json
{
  "total": 127,
  "by_status": {
    "pending": 15,
    "in_review": 8,
    "resolved": 89,
    "dismissed": 15
  },
  "by_reason": {
    "inappropriate_content": 42,
    "copyright_violation": 28,
    "spam": 35,
    "other": 22
  },
  "avg_resolution_time_hours": 6.5,
  "resolution_rate": 85.7
}
```

**字段说明**:
- `avg_resolution_time_hours`: 平均处理时长 (小时)
- `resolution_rate`: 解决率 (%)

---

#### GET `/moderation/reports/{report_id}`

获取举报详情

**限流**: 30 req/min

**响应**:
```json
{
  "id": "report_xxx",
  "resource_type": "listing",
  "resource_id": "listing_123",
  "resource_title": "可爱动物贴纸包",
  "reporter_id": "user_abc",
  "reporter_email": "reporter@example.com",
  "reason": "inappropriate_content",
  "description": "包含不适宜内容,建议下架",
  "status": "pending",
  "created_at": "2026-01-10T16:00:00Z",
  "admin_response": null,
  "resolved_at": null,
  "resolved_by": null,
  "resource_details": {
    "listing_id": "listing_123",
    "title": "可爱动物贴纸包",
    "seller_id": "user_def",
    "preview_url": "https://..."
  }
}
```

**错误码**:
- 404: 举报不存在

---

#### POST `/moderation/reports/{report_id}/respond`

处理举报

**限流**: 30 req/min

**请求体**:
```json
{
  "status": "resolved",
  "response": "已确认违规,已对商品进行下架处理"
}
```

**status 可选值**: `in_review` | `resolved` | `dismissed`

**响应**:
```json
{
  "status": "resolved",
  "report_id": "report_xxx"
}
```

**影响**:
- 举报状态更新
- 举报者收到处理结果通知 (如果提供了 response)

**错误码**:
- 404: 举报不存在

---

## 6.12 系统管理 `/system` (新增章节)

### 系统配置端点

#### GET `/system/configs`

获取系统配置列表

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `group` | string | - | 按组筛选 |
| `search` | string | - | 搜索关键词 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 50 | 每页数量 (1-100) |

**group 可选值**:
- `general` - 通用配置
- `security` - 安全配置
- `performance` - 性能配置
- `feature` - 功能配置
- `integration` - 集成配置

**响应**:
```json
{
  "configs": [
    {
      "id": "uuid-xxx",
      "key": "system.maintenance_mode",
      "value": "false",
      "value_type": "boolean",
      "config_group": "general",
      "description": "系统维护模式开关",
      "is_active": true,
      "created_at": "2025-12-01T00:00:00Z",
      "updated_at": "2026-01-10T12:00:00Z"
    }
  ],
  "total": 87,
  "offset": 0,
  "limit": 50
}
```

---

#### GET `/system/configs/groups`

获取配置组列表

**限流**: 30 req/min

**响应**:
```json
{
  "groups": [
    {
      "key": "general",
      "name": "通用配置",
      "count": 25
    },
    {
      "key": "security",
      "name": "安全配置",
      "count": 18
    }
  ]
}
```

---

#### POST `/system/configs`

创建系统配置

**限流**: 10 req/min

**请求体**:
```json
{
  "key": "system.new_feature_enabled",
  "value": "true",
  "value_type": "boolean",
  "config_group": "feature",
  "description": "新功能开关"
}
```

**value_type 可选值**:
- `text` - 文本
- `number` - 数字
- `boolean` - 布尔值
- `json` - JSON 对象

**响应**:
```json
{
  "status": "created",
  "config": {
    "id": "uuid-xxx",
    "key": "system.new_feature_enabled",
    ...
  }
}
```

**错误码**:
- 400: key 已存在或 value_type 无效

---

#### PUT `/system/configs/{key:path}`

更新系统配置

**限流**: 10 req/min

**请求体**:
```json
{
  "value": "false",
  "description": "更新后的描述",
  "is_active": true
}
```

**响应**:
```json
{
  "status": "updated",
  "config": {
    ...
  }
}
```

---

#### DELETE `/system/configs/{key:path}`

软删除配置

**限流**: 10 req/min

**响应**:
```json
{
  "status": "deleted",
  "key": "system.old_feature"
}
```

---

#### GET `/system/configs/audit`

获取配置变更审计日志

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `config_key` | string | - | 筛选特定配置 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 50 | 每页数量 (1-100) |

**响应**:
```json
{
  "logs": [
    {
      "id": "uuid-xxx",
      "config_key": "system.maintenance_mode",
      "action": "updated",
      "old_value": "false",
      "new_value": "true",
      "admin_id": "admin_user_123",
      "timestamp": "2026-01-10T12:00:00Z",
      "ip_address": "192.168.1.100"
    }
  ],
  "total": 523,
  "offset": 0,
  "limit": 50
}
```

---

#### POST `/system/configs/cache/invalidate`

清空配置缓存

**限流**: 5 req/min

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `key` | string | 可选,清空特定配置缓存 |

**示例**:
```
POST /api/v2/admin/system/configs/cache/invalidate?key=system.maintenance_mode
```

**响应**:
```json
{
  "status": "invalidated",
  "key": "system.maintenance_mode"
}
```

**如果不提供 key,清空所有配置缓存**:
```json
{
  "status": "invalidated",
  "key": "all"
}
```

---

### 缓存管理端点

#### GET `/system/system/cache/status`

获取 Redis 缓存状态

**限流**: 30 req/min

**响应**:
```json
{
  "connected": true,
  "uptime_seconds": 1234567,
  "memory_used_mb": 128.5,
  "memory_max_mb": 512.0,
  "memory_usage_percent": 25.1,
  "total_keys": 4523,
  "hit_rate": 87.3,
  "evicted_keys": 142,
  "avg_ttl_seconds": 3600
}
```

**字段说明**:
- `hit_rate`: 缓存命中率 (%)
- `evicted_keys`: 被驱逐的键数量

---

#### GET `/system/system/cache/keys`

列出缓存键

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `pattern` | string | * | 键名模式 (支持通配符) |
| `limit` | int | 100 | 最多返回数量 (1-1000) |

**pattern 示例**:
- `*` - 所有键
- `user:*` - 所有 user 相关键
- `config:*` - 所有 config 相关键
- `experiment:*:results` - 实验结果键

**响应**:
```json
{
  "keys": [
    "config:system.maintenance_mode",
    "config:rate_limit.api.max_requests",
    "user:user_123:profile"
  ],
  "total": 3,
  "pattern": "config:*"
}
```

**注意**: pattern 会进行安全验证,只允许字母数字下划线冒号星号连字符点

---

#### DELETE `/system/system/cache/key/{key:path}`

删除单个缓存键

**限流**: 10 req/min

**示例**:
```
DELETE /api/v2/admin/system/system/cache/key/config:system.maintenance_mode
```

**响应**:
```json
{
  "status": "deleted",
  "key": "config:system.maintenance_mode"
}
```

---

#### POST `/system/system/cache/clear-all/confirm`

请求清空所有缓存的确认 Token

**限流**: 1 req / 10 min

**响应**:
```json
{
  "token": "5a2d8f4c1e9b3a7d...",
  "expires_in_seconds": 120,
  "message": "Use this token within 2 minutes to clear all cache"
}
```

**注意**:
- Token 2 分钟后过期
- 一次性使用
- 用于下一步的 clear-all 操作

---

#### POST `/system/system/cache/clear-all`

清空所有缓存 (危险操作,需要确认 Token)

**限流**: 1 req / 10 min

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `confirm_token` | string | 是 | 从 /clear-all/confirm 获取的 Token |

**示例**:
```
POST /api/v2/admin/system/system/cache/clear-all?confirm_token=5a2d8f4c1e9b3a7d...
```

**响应**:
```json
{
  "status": "cleared",
  "message": "All cache has been cleared. Database query load will increase temporarily."
}
```

**审计日志**: 自动记录到 `admin_operations` 表,包含 IP 地址和 User-Agent

**错误码**:
- 403: Token 无效或已过期

**影响**:
- 清空所有 Redis 缓存
- 短期内数据库查询负载会增加
- 缓存会逐步重建

**安全措施** (P0-013):
- 两步确认流程
- Token 有效期 2 分钟
- Token 一次性使用
- 完整审计日志
- 严格限流

---

## 章节编号修正建议

**现有文档章节编号混乱** (7.1-7.7 和 6.8 混用),建议统一调整为:

### 原章节 → 新编号

- 7.1 用户管理 → **6.1 用户管理**
- 7.2 订阅管理 → **6.2 订阅管理**
- 7.3 统计仪表板 → **6.3 统计仪表板**
- 7.4 AI 洞察 → **6.4 AI 洞察** (已补充完整)
- 7.5 内容审核 → **6.5 内容审核** (已补充完整)
- 7.6 通知管理 → **6.6 通知管理** (已补充完整)
- 7.7 系统配置 → **6.7 系统配置** (已补充完整)
- 6.8 实验管理 → **6.8 实验管理** (已补充完整)

### 新增章节

- **6.9 Feature Flags 管理** (全新)
- **6.10 AI Models 管理** (全新)
- **6.11 内容审核** (补充完整)
- **6.12 系统管理** (全新)

---

## 总结

### 补充统计

- **新增端点文档**: 41 个
- **新增章节**: 4 个
- **补充完整的章节**: 4 个

### 模块覆盖

| 模块 | 端点数 | 状态 |
|------|--------|------|
| Notifications | 5 | ✅ 完成 |
| Config | 8 | ✅ 完成 |
| Experiments | 14 | ✅ 完成 |
| Feature Flags | 7 | ✅ 完成 |
| AI Models | 7 | ✅ 完成 |
| Moderation | 10 | ✅ 完成 |
| System | 10 | ✅ 完成 |

**总计**: 61 个端点完整文档

### 待确认事项

1. **AI Insights 模块** (`/ai/insights`) - 代码文件不存在
   - 建议确认这些端点的实际实现位置
   - 或标记为"计划中"

2. **Tasks 模块** - 未找到独立的 `tasks.py` 文件
   - 可能集成在其他模块中
   - 需要确认是否需要单独文档

3. **Events 模块聚合端点** - 可能需要补充
   - 检查是否有遗漏的聚合相关端点

---

**文档生成完成时间**: 2026-01-11
**基于代码版本**: v3.30+ (DDD Migration)
