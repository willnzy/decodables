# Feature Flag 评估引擎

> **版本**: v2.0
> **日期**: 2026-02-03
> **状态**: 设计完成
> **说明**: 本文档包含 Feature Flag 系统的数据库设计、评估引擎、前后端实现、A/B 实验统计

---

## 目录

1. [系统概述](#一系统概述)
2. [数据库设计](#二数据库设计)
3. [后端实现](#三后端实现)
4. [前端实现](#四前端实现)
5. [A/B 实验](#五ab-实验)
6. [Admin 管理界面](#六admin-管理界面)
7. [迁移计划](#七迁移计划)
8. [修订历史](#八修订历史)

---

## 一、系统概述

### 1.1 核心设计理念

```
┌─────────────────────────────────────────────────────────────────┐
│                      统一架构设计理念                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  "Feature Flag 是 A/B 测试的特例"                                │
│                                                                 │
│  Feature Flag = 2 个变体的实验 (control=off, treatment=on)      │
│  A/B 测试 = N 个变体的实验 + 统计分析                             │
│                                                                 │
│  因此：                                                          │
│  • 共享核心评估引擎                                               │
│  • 共享用户分配算法                                               │
│  • 共享曝光追踪                                                   │
│  • A/B 测试额外需要：指标追踪 + 统计显著性计算                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        Application                               │
│                                                                  │
│   Frontend                           Backend                     │
│   ┌────────────────────┐            ┌────────────────────┐      │
│   │FeatureFlagProvider │ ←──API──→  │FeatureFlagService  │      │
│   │                    │            │                    │      │
│   │ useFeatureFlag()   │            │ is_enabled()       │      │
│   │ useExperiment()    │            │ get_variant()      │      │
│   │ <FeatureFlag>      │            │ track_conversion() │      │
│   └────────────────────┘            └─────────┬──────────┘      │
│                                               │                  │
└───────────────────────────────────────────────┼──────────────────┘
                                                │
                                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Unified Evaluation Engine                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  1. Check enabled                                        │    │
│  │  2. Check prerequisite flags (parent_flags)              │    │
│  │  3. Check time window                                    │    │
│  │  4. Check environment                                    │    │
│  │  5. Check blacklist                                      │    │
│  │  6. Check whitelist                                      │    │
│  │  7. Check allowed_tiers                                  │    │
│  │  8. Evaluate targeting rules                             │    │
│  │  9. Assign variant (deterministic hash)                  │    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────────┘
                                                │
                                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Data Layer                               │
│                                                                  │
│  ┌──────────────┐   ┌───────────────────┐   ┌───────────────┐  │
│  │feature_flags │   │experiment_configs │   │flag_exposures │  │
│  │   (核心表)    │──→│    (扩展表)        │   │  (事件表)     │  │
│  └──────────────┘   └───────────────────┘   └───────────────┘  │
│         │                    │                                   │
│         │                    ▼                                   │
│         │           ┌───────────────────┐                       │
│         │           │experiment_results │                       │
│         │           │   (结果聚合表)     │                       │
│         │           └───────────────────┘                       │
│         │                                                        │
│         └───────────────→ Redis Cache (60s TTL)                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Flag 类型定义

| 类型 | flag_type | 变体数 | 统计分析 | 使用场景 |
|------|-----------|--------|----------|----------|
| **布尔开关** | `boolean` | 2 (on/off) | ❌ | 功能灰度、紧急关闭 |
| **多变体** | `multivariate` | N | ❌ | 配置切换、UI 变体 |
| **A/B 实验** | `experiment` | N | ✅ | 转化优化、假设验证 |

### 1.4 相关文档

| 文档 | 说明 |
|------|------|
| [entitlement-system-design.md](./entitlement-system-design.md) | 系统架构总览 |
| [entitlement-permission-matrix.md](./entitlement-permission-matrix.md) | 功能权限矩阵 |

---

## 二、数据库设计

### 2.1 核心表：feature_flags

```sql
-- ============================================================
-- Feature Flags 核心表
-- 统一存储所有类型的 Flag（功能开关 + A/B 测试）
-- ============================================================
CREATE TABLE feature_flags (
    -- 主键
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(100) NOT NULL UNIQUE,

    -- 基础信息
    name VARCHAR(255) NOT NULL,
    description TEXT,
    flag_type VARCHAR(20) NOT NULL DEFAULT 'boolean',  -- boolean, multivariate, experiment

    -- 状态控制
    enabled BOOLEAN DEFAULT false,
    archived BOOLEAN DEFAULT false,

    -- 环境配置
    environments TEXT[] DEFAULT ARRAY['production', 'staging'],

    -- 时间窗口
    start_at TIMESTAMPTZ,
    end_at TIMESTAMPTZ,

    -- 灰度配置
    rollout_percentage INTEGER DEFAULT 0
        CHECK (rollout_percentage >= 0 AND rollout_percentage <= 100),

    -- 名单控制
    whitelist_user_ids TEXT[] DEFAULT ARRAY[]::TEXT[],
    blacklist_user_ids TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- Tier 分层筛选
    -- 允许的 Tier 列表，空数组表示不限制 (所有 Tier 都允许)
    -- 格式: ["t2", "t3"] 表示仅 Starter 和 Pro 用户可见
    allowed_tiers TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- 定向规则 (JSON)
    -- 格式: [{"id": "rule1", "priority": 1, "tiers": ["t3"], "conditions": [...], "variant": "treatment"}]
    -- 支持规则级 tiers 字段，实现 "先选 Tier，再选用户特征"
    targeting_rules JSONB DEFAULT '[]',

    -- 变体配置 (JSON)
    -- 格式: [{"key": "control", "value": false, "weight": 50}, {"key": "treatment", "value": true, "weight": 50}]
    variants JSONB DEFAULT '[
        {"key": "control", "value": false, "weight": 50},
        {"key": "treatment", "value": true, "weight": 50}
    ]'::JSONB,
    default_variant VARCHAR(100) DEFAULT 'control',

    -- 树状依赖
    -- 父级 Flag keys，子 Flag 仅在所有父级都启用时才生效
    -- 例如: ['editor', 'editor.toolbar'] 表示需要 editor 和 editor.toolbar 都启用
    parent_flags TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- 元数据
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    owner VARCHAR(100),

    -- 审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100),
    updated_by VARCHAR(100),

    -- 约束
    CONSTRAINT valid_flag_type CHECK (flag_type IN ('boolean', 'multivariate', 'experiment'))
);

-- 索引
CREATE INDEX idx_ff_key ON feature_flags(key);
CREATE INDEX idx_ff_enabled ON feature_flags(enabled) WHERE enabled = true AND archived = false;
CREATE INDEX idx_ff_type ON feature_flags(flag_type);
CREATE INDEX idx_ff_tags ON feature_flags USING GIN(tags);

-- 更新时间触发器
CREATE OR REPLACE FUNCTION update_feature_flags_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_ff_updated
    BEFORE UPDATE ON feature_flags
    FOR EACH ROW
    EXECUTE FUNCTION update_feature_flags_timestamp();
```

### 2.2 扩展表：experiment_configs

```sql
-- ============================================================
-- 实验配置表（仅 flag_type = 'experiment' 时需要）
-- ============================================================
CREATE TABLE experiment_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flag_key VARCHAR(100) NOT NULL UNIQUE REFERENCES feature_flags(key) ON DELETE CASCADE,

    -- 实验设计
    hypothesis TEXT,                              -- 假设描述

    -- 指标配置
    primary_metric VARCHAR(100) NOT NULL,         -- 主要指标 (如 'conversion', 'revenue')
    secondary_metrics TEXT[] DEFAULT ARRAY[]::TEXT[],  -- 次要指标

    -- 统计配置
    min_sample_size INTEGER DEFAULT 1000,         -- 最小样本量/每变体
    confidence_level DECIMAL(3,2) DEFAULT 0.95,   -- 置信度 (0.90, 0.95, 0.99)
    min_detectable_effect DECIMAL(5,4),           -- 最小可检测效应 (如 0.05 = 5%)

    -- 时间规划
    planned_duration_days INTEGER,                -- 计划运行天数
    planned_start_date DATE,
    planned_end_date DATE,
    actual_start_date DATE,
    actual_end_date DATE,

    -- 状态管理
    status VARCHAR(20) DEFAULT 'draft',           -- draft, running, paused, completed, stopped

    -- 结论
    winner_variant VARCHAR(100),                  -- 获胜变体
    conclusion TEXT,                              -- 结论描述
    decision VARCHAR(20),                         -- ship_treatment, keep_control, inconclusive
    decided_by VARCHAR(100),
    decided_at TIMESTAMPTZ,

    -- 审计
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_exp_status ON experiment_configs(status);
CREATE INDEX idx_exp_dates ON experiment_configs(planned_start_date, planned_end_date);
```

### 2.3 曝光事件表：flag_exposures

```sql
-- ============================================================
-- 曝光事件表（统一记录所有 Flag 的曝光）
-- ============================================================
CREATE TABLE flag_exposures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Flag 标识
    flag_key VARCHAR(100) NOT NULL,
    flag_type VARCHAR(20) NOT NULL,

    -- 用户标识
    user_id VARCHAR(100),                         -- 登录用户 ID
    anonymous_id VARCHAR(100),                    -- 匿名用户 ID

    -- 分配结果
    variant VARCHAR(100) NOT NULL,
    enabled BOOLEAN NOT NULL,
    reason VARCHAR(50) NOT NULL,                  -- whitelist, blacklist, rule, percentage, default
    rule_id VARCHAR(100),                         -- 命中的规则 ID

    -- 上下文快照
    context JSONB,                                -- 评估时的用户上下文

    -- 环境信息
    environment VARCHAR(50) DEFAULT 'production',

    -- 时间戳
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 索引（优化查询性能）
CREATE INDEX idx_exp_flag_time ON flag_exposures(flag_key, timestamp DESC);
CREATE INDEX idx_exp_user ON flag_exposures(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_exp_time ON flag_exposures(timestamp);
```

### 2.4 实验结果表：experiment_results

```sql
-- ============================================================
-- 实验结果表（每日聚合统计）
-- ============================================================
CREATE TABLE experiment_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Flag 标识
    flag_key VARCHAR(100) NOT NULL REFERENCES feature_flags(key) ON DELETE CASCADE,
    variant VARCHAR(100) NOT NULL,
    metric VARCHAR(100) NOT NULL,

    -- 日期
    date DATE NOT NULL,

    -- 每日统计
    exposures INTEGER DEFAULT 0,                  -- 当日曝光人数
    conversions INTEGER DEFAULT 0,                -- 当日转化人数
    total_value DECIMAL(15,2) DEFAULT 0,          -- 当日总价值 (如收入)

    -- 计算字段
    conversion_rate DECIMAL(10,6),                -- 转化率
    avg_value DECIMAL(10,2),                      -- 平均价值

    -- 累计统计
    cumulative_exposures INTEGER DEFAULT 0,
    cumulative_conversions INTEGER DEFAULT 0,
    cumulative_value DECIMAL(15,2) DEFAULT 0,
    cumulative_rate DECIMAL(10,6),

    -- 统计显著性（与 control 对比）
    relative_lift DECIMAL(10,4),                  -- 相对提升 (如 0.15 = 15%)
    p_value DECIMAL(10,6),
    confidence DECIMAL(5,2),                      -- 置信度百分比
    is_significant BOOLEAN DEFAULT false,

    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(flag_key, variant, metric, date)
);

-- 索引
CREATE INDEX idx_results_flag ON experiment_results(flag_key);
CREATE INDEX idx_results_date ON experiment_results(date DESC);
```

### 2.5 审计日志表：flag_audit_logs

```sql
-- ============================================================
-- 审计日志表（记录所有变更）
-- ============================================================
CREATE TABLE flag_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Flag 标识
    flag_id UUID REFERENCES feature_flags(id) ON DELETE SET NULL,
    flag_key VARCHAR(100) NOT NULL,

    -- 操作信息
    action VARCHAR(50) NOT NULL,                  -- created, updated, enabled, disabled, archived
    changes JSONB,                                -- 变更内容
    previous_value JSONB,                         -- 变更前的值

    -- 操作人
    changed_by VARCHAR(100) NOT NULL,
    reason TEXT,                                  -- 变更原因

    -- 时间戳
    changed_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_audit_flag ON flag_audit_logs(flag_key);
CREATE INDEX idx_audit_time ON flag_audit_logs(changed_at DESC);
```

**审计类型 (action) 详细说明**:

| action | 说明 | 记录内容 |
|--------|------|---------|
| `created` | 创建 Flag | 完整 flag 配置 |
| `updated` | 更新配置 | changes: 变更字段, previous_value: 变更前值 |
| `enabled` | 启用 Flag | enabled: false → true |
| `disabled` | 禁用 Flag (kill switch) | enabled: true → false, reason: 禁用原因 |
| `archived` | 归档 Flag | archived: false → true |
| `unarchived` | 取消归档 | archived: true → false |
| `rollout_changed` | 灰度百分比变更 | rollout_percentage: 旧值 → 新值 |
| `variant_changed` | 变体配置变更 | variants: 变更详情 |
| `rule_added` | 添加定向规则 | targeting_rules: 新增规则 |
| `rule_removed` | 删除定向规则 | targeting_rules: 删除的规则 |
| `whitelist_updated` | 白名单变更 | whitelist_user_ids: 变更详情 |
| `blacklist_updated` | 黑名单变更 | blacklist_user_ids: 变更详情 |
| `experiment_started` | 实验开始 | status: draft → running |
| `experiment_paused` | 实验暂停 | status: running → paused |
| `experiment_stopped` | 实验停止 | status: → stopped, decision |
| `experiment_completed` | 实验完成 | status: → completed, winner_variant |

---

## 三、后端实现

### 3.1 目录结构

```
core/feature_flag/
├── __init__.py              # 导出公共接口 (<50 行)
├── types.py                 # 类型定义 (<100 行)
├── interface.py             # Provider 接口 (<80 行)
├── service.py               # Facade 服务 (<150 行)
├── factory.py               # Provider 工厂 (<80 行)
├── evaluator.py             # 统一评估引擎 (<200 行)
├── hasher.py                # 哈希分配算法 (<50 行)
├── cache.py                 # 缓存管理 (<100 行)
│
├── providers/               # Provider 实现
│   ├── __init__.py
│   ├── self_hosted.py       # 自建实现 (<250 行)
│   ├── growthbook.py        # GrowthBook (<150 行)
│   └── unleash.py           # Unleash (<150 行)
│
└── experiment/              # 实验扩展
    ├── __init__.py
    ├── service.py           # 实验服务 (<200 行)
    ├── statistics.py        # 统计计算 (<150 行)
    └── aggregator.py        # 结果聚合 (<150 行)
```

### 3.2 类型定义

```python
# core/feature_flag/types.py

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime


class FlagType(Enum):
    """Flag 类型"""
    BOOLEAN = "boolean"
    MULTIVARIATE = "multivariate"
    EXPERIMENT = "experiment"


class EvaluationReason(Enum):
    """评估原因"""
    DISABLED = "disabled"
    PARENT_DISABLED = "parent_disabled"  # 父级 Flag 未启用
    TIME_WINDOW = "time_window"
    ENVIRONMENT = "environment"
    TIER_MISMATCH = "tier_mismatch"      # Tier 不匹配
    BLACKLIST = "blacklist"
    WHITELIST = "whitelist"
    RULE = "rule"
    PERCENTAGE = "percentage"
    DEFAULT = "default"
    ERROR = "error"
    NOT_FOUND = "not_found"


@dataclass
class Variant:
    """变体定义"""
    key: str
    value: Any
    weight: int = 50


@dataclass
class EvaluationContext:
    """评估上下文"""
    user_id: Optional[str] = None
    anonymous_id: Optional[str] = None
    email: Optional[str] = None
    tier: Optional[str] = None
    role: Optional[str] = None
    country: Optional[str] = None
    device: Optional[str] = None
    platform: Optional[str] = None
    app_version: Optional[str] = None
    environment: str = "production"
    custom: Dict[str, Any] = field(default_factory=dict)

    @property
    def identifier(self) -> str:
        """获取用户标识（用于哈希分配）"""
        return self.user_id or self.anonymous_id or "anonymous"

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "user_id": self.user_id,
            "anonymous_id": self.anonymous_id,
            "email": self.email,
            "tier": self.tier,
            "role": self.role,
            "country": self.country,
            "device": self.device,
            "platform": self.platform,
            "app_version": self.app_version,
            "environment": self.environment,
        }
        result.update(self.custom)
        return {k: v for k, v in result.items() if v is not None}

    def get(self, key: str, default: Any = None) -> Any:
        if hasattr(self, key) and getattr(self, key) is not None:
            return getattr(self, key)
        return self.custom.get(key, default)


@dataclass
class EvaluationResult:
    """评估结果"""
    enabled: bool
    variant: str = "control"
    value: Any = None
    reason: EvaluationReason = EvaluationReason.DEFAULT
    rule_id: Optional[str] = None
    flag_key: Optional[str] = None
    flag_type: Optional[FlagType] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "variant": self.variant,
            "value": self.value,
            "reason": self.reason.value,
            "rule_id": self.rule_id,
            "flag_key": self.flag_key,
            "flag_type": self.flag_type.value if self.flag_type else None,
        }
```

### 3.3 统一评估引擎

```python
# core/feature_flag/evaluator.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from .types import (
    EvaluationContext,
    EvaluationResult,
    EvaluationReason,
    FlagType,
    Variant,
)
from .hasher import get_hash_bucket

logger = logging.getLogger(__name__)


class UnifiedEvaluator:
    """
    统一评估引擎

    处理所有类型的 Flag：boolean, multivariate, experiment
    使用相同的评估流程，确保一致性
    """

    def evaluate(
        self,
        flag: Dict[str, Any],
        context: EvaluationContext,
        all_flags: Dict[str, Dict] = None,  # 传入所有 flags 用于层级评估
    ) -> EvaluationResult:
        """
        评估 Flag

        评估流程 (9 步):
        1. 检查 enabled (kill switch)
        2. 检查父级 Flag (树状依赖)
        3. 检查时间窗口
        4. 检查环境
        5. 检查黑名单
        6. 检查白名单（命中则立即返回）← 提前到 tier 之前
        7. 检查 Tier 限制 (allowed_tiers)
        8. 评估定向规则 (支持规则级 tiers)
        9. 计算变体分配（百分比灰度）
        """
        flag_key = flag.get("key", "unknown")
        flag_type = FlagType(flag.get("flag_type", "boolean"))

        try:
            # 1. 检查总开关 (kill switch)
            if not flag.get("enabled", False):
                return self._result(flag, False, EvaluationReason.DISABLED)

            # 2. 检查父级 Flag
            if not self._check_parent_flags(flag, context, all_flags):
                return self._result(flag, False, EvaluationReason.PARENT_DISABLED)

            # 3. 检查时间窗口
            if not self._check_time_window(flag):
                return self._result(flag, False, EvaluationReason.TIME_WINDOW)

            # 4. 检查环境
            if not self._check_environment(flag, context):
                return self._result(flag, False, EvaluationReason.ENVIRONMENT)

            # 5. 检查黑名单
            if self._in_blacklist(flag, context):
                return self._result(flag, False, EvaluationReason.BLACKLIST)

            # 6. 检查白名单 (提前到 tier 之前，白名单用户不受 tier 限制)
            if self._in_whitelist(flag, context):
                return self._result(
                    flag, True, EvaluationReason.WHITELIST,
                    variant=self._get_first_treatment_variant(flag)
                )

            # 7. 检查 Tier 限制
            if not self._check_allowed_tiers(flag, context):
                return self._result(flag, False, EvaluationReason.TIER_MISMATCH)

            # 8. 评估定向规则 (支持规则级 tiers)
            rule_result = self._evaluate_rules(flag, context)
            if rule_result:
                return rule_result

            # 9. 计算变体分配
            return self._assign_variant(flag, context)

        except Exception as e:
            logger.error(f"Flag evaluation error: {flag_key}, {e}")
            return self._result(flag, False, EvaluationReason.ERROR)

    # ==================== 层级评估 ====================

    def _check_parent_flags(
        self,
        flag: Dict,
        context: EvaluationContext,
        all_flags: Dict[str, Dict] = None,
    ) -> bool:
        """
        检查父级 Flag 是否都已启用

        树状依赖规则:
        - 子 Flag 仅在所有父级 Flag 都启用时才生效
        - 父级 Flag 的评估是递归的
        - 如果 parent_flags 为空，则无依赖
        """
        parent_keys = flag.get("parent_flags", [])

        if not parent_keys:
            return True

        if all_flags is None:
            logger.warning(f"Cannot check parent flags: all_flags not provided")
            return True

        for parent_key in parent_keys:
            parent_flag = all_flags.get(parent_key)
            if not parent_flag:
                return False
            parent_result = self._evaluate_parent(parent_flag, context, all_flags)
            if not parent_result:
                return False

        return True

    def _evaluate_parent(
        self,
        parent_flag: Dict,
        context: EvaluationContext,
        all_flags: Dict[str, Dict],
    ) -> bool:
        """简化评估父级 Flag (仅检查 enabled 和递归依赖)"""
        if not parent_flag.get("enabled", False):
            return False
        return self._check_parent_flags(parent_flag, context, all_flags)

    # ==================== Tier 分层筛选 ====================

    def _check_allowed_tiers(self, flag: Dict, context: EvaluationContext) -> bool:
        """
        检查 Tier 限制

        - 空数组 = 不限制 Tier
        - 非空数组 = 用户 Tier 必须在列表中
        """
        allowed_tiers = flag.get("allowed_tiers", [])

        if not allowed_tiers:
            return True

        user_tier = context.tier
        if not user_tier:
            return False

        return user_tier.lower() in [t.lower() for t in allowed_tiers]

    # ==================== 其他检查 ====================

    def _check_time_window(self, flag: Dict) -> bool:
        """检查时间窗口"""
        now = datetime.now(timezone.utc)

        start_at = flag.get("start_at")
        if start_at:
            start_time = datetime.fromisoformat(start_at.replace("Z", "+00:00"))
            if now < start_time:
                return False

        end_at = flag.get("end_at")
        if end_at:
            end_time = datetime.fromisoformat(end_at.replace("Z", "+00:00"))
            if now > end_time:
                return False

        return True

    def _check_environment(self, flag: Dict, context: EvaluationContext) -> bool:
        """检查环境"""
        environments = flag.get("environments", [])
        if not environments:
            return True
        return context.environment in environments

    def _in_blacklist(self, flag: Dict, context: EvaluationContext) -> bool:
        """检查黑名单"""
        blacklist = flag.get("blacklist_user_ids", [])
        return context.user_id in blacklist if context.user_id else False

    def _in_whitelist(self, flag: Dict, context: EvaluationContext) -> bool:
        """检查白名单"""
        whitelist = flag.get("whitelist_user_ids", [])
        return context.user_id in whitelist if context.user_id else False

    def _evaluate_rules(
        self,
        flag: Dict,
        context: EvaluationContext
    ) -> Optional[EvaluationResult]:
        """评估定向规则"""
        rules = flag.get("targeting_rules", [])
        if not rules:
            return None

        sorted_rules = sorted(rules, key=lambda r: r.get("priority", 999))

        for rule in sorted_rules:
            if self._match_rule_conditions(rule, context):
                variant_key = rule.get("variant", "treatment")
                variant = self._get_variant_by_key(flag, variant_key)

                rule_percentage = rule.get("rollout_percentage", 100)
                if self._in_rollout(context.identifier, flag["key"], rule_percentage):
                    return self._result(
                        flag,
                        variant.value if variant else True,
                        EvaluationReason.RULE,
                        variant=variant_key,
                        rule_id=rule.get("id")
                    )

        return None

    def _match_rule_conditions(self, rule: Dict, context: EvaluationContext) -> bool:
        """匹配规则条件 (支持规则级 tiers)"""
        # 检查规则级 Tier 限制
        rule_tiers = rule.get("tiers", [])
        if rule_tiers:
            user_tier = context.tier
            if not user_tier:
                return False
            if user_tier.lower() not in [t.lower() for t in rule_tiers]:
                return False

        conditions = rule.get("conditions", [])
        for condition in conditions:
            if not self._match_condition(condition, context):
                return False

        return True

    def _match_condition(self, condition: Dict, context: EvaluationContext) -> bool:
        """匹配单个条件"""
        attribute = condition.get("attribute")
        operator = condition.get("operator")
        expected = condition.get("value")

        actual = context.get(attribute)

        if actual is None:
            return operator == "not_set"

        operators = {
            "eq": lambda a, e: a == e,
            "neq": lambda a, e: a != e,
            "in": lambda a, e: a in e if isinstance(e, list) else a == e,
            "not_in": lambda a, e: a not in e if isinstance(e, list) else a != e,
            "contains": lambda a, e: e in str(a),
            "not_contains": lambda a, e: e not in str(a),
            "starts_with": lambda a, e: str(a).startswith(e),
            "ends_with": lambda a, e: str(a).endswith(e),
            "gt": lambda a, e: float(a) > float(e),
            "gte": lambda a, e: float(a) >= float(e),
            "lt": lambda a, e: float(a) < float(e),
            "lte": lambda a, e: float(a) <= float(e),
            "regex": lambda a, e: bool(__import__('re').match(e, str(a))),
            "not_set": lambda a, e: a is None,
            "is_set": lambda a, e: a is not None,
        }

        try:
            if operator in operators:
                return operators[operator](actual, expected)
            return False
        except Exception:
            return False

    def _assign_variant(self, flag: Dict, context: EvaluationContext) -> EvaluationResult:
        """分配变体（核心算法）"""
        rollout_percentage = flag.get("rollout_percentage", 0)

        if not self._in_rollout(context.identifier, flag["key"], rollout_percentage):
            return self._result(flag, False, EvaluationReason.PERCENTAGE, variant="control")

        variants = flag.get("variants", [])
        if not variants:
            return self._result(flag, True, EvaluationReason.PERCENTAGE, variant="treatment")

        variant = self._select_variant_by_weight(context.identifier, flag["key"], variants)

        return self._result(
            flag,
            variant.get("value", True),
            EvaluationReason.PERCENTAGE,
            variant=variant.get("key", "treatment")
        )

    def _in_rollout(self, identifier: str, flag_key: str, percentage: int) -> bool:
        """判断是否在灰度范围内"""
        if percentage >= 100:
            return True
        if percentage <= 0:
            return False

        bucket = get_hash_bucket(f"{identifier}:{flag_key}")
        return bucket < percentage

    def _select_variant_by_weight(self, identifier: str, flag_key: str, variants: List[Dict]) -> Dict:
        """按权重选择变体"""
        total_weight = sum(v.get("weight", 0) for v in variants)
        if total_weight <= 0:
            return variants[0] if variants else {"key": "control", "value": False}

        bucket = get_hash_bucket(f"{identifier}:{flag_key}:variant")
        variant_bucket = bucket % total_weight

        cumulative = 0
        for variant in variants:
            cumulative += variant.get("weight", 0)
            if variant_bucket < cumulative:
                return variant

        return variants[0]

    def _get_variant_by_key(self, flag: Dict, key: str) -> Optional[Variant]:
        """根据 key 获取变体"""
        variants = flag.get("variants", [])
        for v in variants:
            if v.get("key") == key:
                return Variant(key=v["key"], value=v.get("value"), weight=v.get("weight", 50))
        return None

    def _get_first_treatment_variant(self, flag: Dict) -> str:
        """获取第一个非 control 变体"""
        variants = flag.get("variants", [])
        for v in variants:
            if v.get("key") != "control":
                return v.get("key", "treatment")
        return "treatment"

    def _result(
        self,
        flag: Dict,
        enabled: bool,
        reason: EvaluationReason,
        variant: str = None,
        rule_id: str = None,
    ) -> EvaluationResult:
        """构建评估结果"""
        if variant is None:
            variant = "treatment" if enabled else "control"

        value = enabled
        variants = flag.get("variants", [])
        for v in variants:
            if v.get("key") == variant:
                value = v.get("value", enabled)
                break

        return EvaluationResult(
            enabled=enabled,
            variant=variant,
            value=value,
            reason=reason,
            rule_id=rule_id,
            flag_key=flag.get("key"),
            flag_type=FlagType(flag.get("flag_type", "boolean")),
        )
```

### 3.4 哈希算法

```python
# core/feature_flag/hasher.py

import hashlib


def get_hash_bucket(seed: str, buckets: int = 100) -> int:
    """
    确定性哈希分配

    特点:
    - 同一 seed 始终返回相同 bucket
    - 均匀分布
    - 不可预测

    Args:
        seed: 哈希种子（通常为 user_id:flag_key）
        buckets: 桶数量（默认 100，即百分比）

    Returns:
        0 到 buckets-1 之间的整数
    """
    hash_bytes = hashlib.md5(seed.encode()).digest()
    hash_int = int.from_bytes(hash_bytes[:4], byteorder='big')
    return hash_int % buckets
```

### 3.5 Facade 服务

```python
# core/feature_flag/service.py

from typing import Dict, Optional, Any
from .types import EvaluationContext, EvaluationResult
from .factory import FeatureFlagFactory
from .interface import IFeatureFlagProvider


class FeatureFlagService:
    """Feature Flag 服务 Facade"""

    _instance: Optional['FeatureFlagService'] = None
    _provider: Optional[IFeatureFlagProvider] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._provider is None:
            self._provider = FeatureFlagFactory.create()

    @classmethod
    def configure(cls, provider_type: str = None, **kwargs):
        """配置 Provider（应用启动时调用）"""
        cls._provider = FeatureFlagFactory.create(provider_type, **kwargs)

    # ==================== 主要 API ====================

    def is_enabled(
        self,
        flag_key: str,
        context: Optional[EvaluationContext] = None,
        default: bool = False
    ) -> bool:
        """检查功能是否启用"""
        return self._provider.is_enabled(flag_key, context, default)

    def get_variant(
        self,
        flag_key: str,
        context: Optional[EvaluationContext] = None,
        default: str = "control"
    ) -> str:
        """获取变体 Key"""
        result = self._provider.evaluate(flag_key, context, default)
        return result.variant

    def evaluate(
        self,
        flag_key: str,
        context: Optional[EvaluationContext] = None,
        default: Any = False
    ) -> EvaluationResult:
        """完整评估"""
        return self._provider.evaluate(flag_key, context, default)

    def get_all_flags(self, context: Optional[EvaluationContext] = None) -> Dict[str, bool]:
        """获取所有 Flag 状态"""
        return self._provider.get_all_flags(context)

    def get_all_variants(self, context: Optional[EvaluationContext] = None) -> Dict[str, str]:
        """获取所有 Flag 的变体"""
        return self._provider.get_all_variants(context)

    # ==================== 实验追踪 ====================

    def track_conversion(
        self,
        flag_key: str,
        context: EvaluationContext,
        metric: str = "conversion",
        value: float = 1.0
    ) -> None:
        """追踪转化（用于 A/B 测试）"""
        self._provider.track_conversion(flag_key, context, metric, value)


# 全局单例
feature_service = FeatureFlagService()
```

### 3.6 API 路由

```python
# api/admin/feature_flags_router.py

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from pydantic import BaseModel

from core.feature_flag import feature_service, EvaluationContext
from dependencies import get_current_user, require_admin

router = APIRouter(prefix="/api/admin/feature-flags", tags=["Feature Flags"])


class CreateFlagRequest(BaseModel):
    key: str
    name: str
    description: Optional[str] = None
    flag_type: str = "boolean"
    enabled: bool = False
    environments: List[str] = ["production", "staging"]
    rollout_percentage: int = 0
    variants: Optional[List[dict]] = None
    targeting_rules: Optional[List[dict]] = None
    parent_flags: Optional[List[str]] = None
    allowed_tiers: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class UpdateFlagRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    rollout_percentage: Optional[int] = None
    variants: Optional[List[dict]] = None
    targeting_rules: Optional[List[dict]] = None
    whitelist_user_ids: Optional[List[str]] = None
    blacklist_user_ids: Optional[List[str]] = None
    parent_flags: Optional[List[str]] = None
    allowed_tiers: Optional[List[str]] = None


class TestEvaluationRequest(BaseModel):
    flag_key: str
    user_id: Optional[str] = None
    tier: Optional[str] = None
    email: Optional[str] = None
    environment: str = "production"
    custom: Optional[dict] = None


# ==================== 管理端点 ====================

@router.get("")
async def list_flags(
    flag_type: Optional[str] = None,
    enabled: Optional[bool] = None,
    archived: bool = False,
    page: int = 1,
    limit: int = 20,
    admin = Depends(require_admin)
):
    """获取 Flag 列表"""
    pass


@router.post("")
async def create_flag(request: CreateFlagRequest, admin = Depends(require_admin)):
    """创建 Flag"""
    pass


@router.get("/{key}")
async def get_flag(key: str, admin = Depends(require_admin)):
    """获取单个 Flag 详情"""
    pass


@router.patch("/{key}")
async def update_flag(key: str, request: UpdateFlagRequest, admin = Depends(require_admin)):
    """更新 Flag"""
    pass


@router.post("/{key}/toggle")
async def toggle_flag(key: str, enabled: bool, admin = Depends(require_admin)):
    """开关 Flag"""
    pass


@router.post("/test-evaluation")
async def test_evaluation(request: TestEvaluationRequest, admin = Depends(require_admin)):
    """测试评估"""
    context = EvaluationContext(
        user_id=request.user_id,
        tier=request.tier,
        email=request.email,
        environment=request.environment,
        custom=request.custom or {},
    )
    result = feature_service.evaluate(request.flag_key, context)
    return {"flag_key": request.flag_key, "context": context.to_dict(), "result": result.to_dict()}


# ==================== 客户端端点 ====================

@router.get("/client/flags")
async def get_client_flags(user = Depends(get_current_user)):
    """获取当前用户的所有 Flag 状态"""
    context = EvaluationContext(
        user_id=user.get("id"),
        tier=user.get("tier"),
        email=user.get("email"),
    )
    flags = feature_service.get_all_flags(context)
    variants = feature_service.get_all_variants(context)
    return {"flags": flags, "variants": variants}
```

---

## 四、前端实现

### 4.1 目录结构

```
lib/feature-flags/
├── index.ts                 # 导出 (<30 行)
├── types.ts                 # 类型定义 (<100 行)
├── context.tsx              # Provider + Hooks (<200 行)
├── components.tsx           # 组件 (<150 行)
├── api.ts                   # API 服务 (<80 行)
│
└── providers/               # Provider 实现
    ├── index.ts
    └── self-hosted.ts       # (<150 行)
```

### 4.2 类型定义

```typescript
// lib/feature-flags/types.ts

export type FlagType = 'boolean' | 'multivariate' | 'experiment';

export type EvaluationReason =
  | 'disabled'
  | 'parent_disabled'
  | 'time_window'
  | 'environment'
  | 'tier_mismatch'
  | 'blacklist'
  | 'whitelist'
  | 'rule'
  | 'percentage'
  | 'default'
  | 'error'
  | 'not_found';

export interface EvaluationContext {
  userId?: string;
  anonymousId?: string;
  email?: string;
  tier?: string;
  environment?: string;
  [key: string]: any;
}

export interface EvaluationResult {
  enabled: boolean;
  variant: string;
  value: any;
  reason: EvaluationReason;
  ruleId?: string;
  flagKey?: string;
  flagType?: FlagType;
}

export interface FeatureFlags {
  [key: string]: boolean;
}

export interface FeatureVariants {
  [key: string]: string;
}
```

### 4.3 Context 和 Hooks

```typescript
// lib/feature-flags/context.tsx

"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { useAuthStore } from '@shared/auth/store';
import { EvaluationContext, EvaluationResult, FeatureFlags, FeatureVariants } from './types';

interface FeatureFlagContextType {
  flags: FeatureFlags;
  variants: FeatureVariants;
  isLoading: boolean;
  isReady: boolean;
  isEnabled: (flagKey: string, defaultValue?: boolean) => boolean;
  getVariant: (flagKey: string, defaultValue?: string) => string;
  evaluate: (flagKey: string, defaultValue?: any) => EvaluationResult;
  trackConversion: (flagKey: string, metric?: string, value?: number) => void;
  refresh: () => Promise<void>;
}

const FeatureFlagContext = createContext<FeatureFlagContextType | undefined>(undefined);

export function FeatureFlagProvider({ children, refreshInterval = 60000 }) {
  const { userId, isAuthenticated: isSignedIn } = useAuthStore();

  const [flags, setFlags] = useState<FeatureFlags>({});
  const [variants, setVariants] = useState<FeatureVariants>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isReady, setIsReady] = useState(false);

  // 初始化和刷新逻辑...

  return (
    <FeatureFlagContext.Provider value={value}>
      {children}
    </FeatureFlagContext.Provider>
  );
}

export function useFeatureFlags(): FeatureFlagContextType {
  const context = useContext(FeatureFlagContext);
  if (!context) {
    throw new Error('useFeatureFlags must be used within FeatureFlagProvider');
  }
  return context;
}

export function useFeatureFlag(flagKey: string, defaultValue = false): boolean {
  const { isEnabled, isReady } = useFeatureFlags();
  if (!isReady) return defaultValue;
  return isEnabled(flagKey, defaultValue);
}

export function useVariant(flagKey: string, defaultValue = 'control'): string {
  const { getVariant, isReady } = useFeatureFlags();
  if (!isReady) return defaultValue;
  return getVariant(flagKey, defaultValue);
}

export function useExperiment(flagKey: string) {
  const { getVariant, trackConversion, isReady } = useFeatureFlags();

  return {
    variant: isReady ? getVariant(flagKey) : 'control',
    isReady,
    trackConversion: (metric = 'conversion', value = 1) => {
      trackConversion(flagKey, metric, value);
    },
  };
}
```

### 4.4 组件

```typescript
// lib/feature-flags/components.tsx

"use client";

import React from 'react';
import { useFeatureFlag, useVariant } from './context';

interface FeatureFlagProps {
  flag: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
  defaultEnabled?: boolean;
}

export function FeatureFlag({ flag, children, fallback = null, defaultEnabled = false }: FeatureFlagProps) {
  const enabled = useFeatureFlag(flag, defaultEnabled);
  return enabled ? <>{children}</> : <>{fallback}</>;
}

interface FeatureVariantProps {
  flag: string;
  variants: Record<string, React.ReactNode>;
  default?: React.ReactNode;
}

export function FeatureVariant({ flag, variants, default: defaultContent = null }: FeatureVariantProps) {
  const variant = useVariant(flag);
  return <>{variants[variant] ?? defaultContent}</>;
}
```

---

## 五、A/B 实验

### 5.1 实验数据流

```
1. 创建实验 flag:
   feature_flags 表: key='checkout_v2', flag_type='experiment',
     variants=[{key:'control', weight:50}, {key:'treatment', weight:50}]
   experiment_configs 表: flag_key='checkout_v2', primary_metric='conversion'

2. 曝光:
   用户访问 → evaluate() → 记录到 flag_exposures

3. 转化:
   用户购买 → track_conversion('checkout_v2', 'conversion', 1)

4. 聚合:
   定时任务 → 聚合 flag_exposures → 写入 experiment_results

5. 分析:
   Admin 查看 → 转化率、p-value、置信区间
```

### 5.2 实验统计界面

```
┌─────────────────────────────────────────────────────────────────┐
│  Experiment: checkout_v2                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Status: Running  |  Day 5 of 14  |  Confidence: 87%           │
│                                                                 │
│  ┌──────────────────┬──────────────────┐                       │
│  │     control      │     treatment    │                       │
│  ├──────────────────┼──────────────────┤                       │
│  │ Exposures: 5,234 │ Exposures: 5,189 │                       │
│  │ Conversions: 220 │ Conversions: 249 │                       │
│  │ Rate: 4.20%      │ Rate: 4.80%      │                       │
│  │                  │ Lift: +14.3%     │                       │
│  │                  │ p-value: 0.13    │                       │
│  └──────────────────┴──────────────────┘                       │
│                                                                 │
│  ⚠️ Not yet significant. Need ~3,000 more samples.             │
│                                                                 │
│  [Pause]  [Stop & Ship Control]  [Stop & Ship Treatment]       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 六、Admin 管理界面

### 6.1 功能列表

| 页面 | 功能 |
|------|------|
| **Flag 列表** | 搜索、筛选、排序、快速开关 |
| **Flag 详情** | 查看配置、曝光统计、审计日志 |
| **Flag 编辑** | 基础信息、变体、规则、名单 |
| **实验详情** | 结果图表、统计显著性、决策 |
| **测试工具** | 模拟用户评估 |

### 6.2 界面设计

```
┌─────────────────────────────────────────────────────────────────┐
│  Feature Flags                                    [+ Create]    │
├─────────────────────────────────────────────────────────────────┤
│  [Search...]  [Type: All ▾] [Status: All ▾] [Tags ▾]           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🚩 feat_new_editor                              [ON/OFF] │   │
│  │    New Canvas Editor                                     │   │
│  │    Type: boolean  |  Rollout: 25%  |  Updated: 2h ago   │   │
│  │    Tags: [editor] [beta]                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🧪 exp_checkout_flow                            [ON/OFF] │   │
│  │    Checkout Flow A/B Test                                │   │
│  │    Type: experiment  |  Status: Running  |  Day 5/14    │   │
│  │    Variants: control (50%) | new_flow (50%)              │   │
│  │    [📊 View Results]                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 七、迁移计划

### 7.1 迁移阶段

```
Phase 1: 基础设施 (Day 1-3)
├─ 创建新表结构
├─ 实现评估引擎
├─ 实现 API 路由
└─ 前端 Provider 实现

Phase 2: 新功能试用 (Day 4-5)
├─ 用新系统创建 2-3 个测试 Flag
├─ 前端集成测试
└─ 验证评估逻辑正确性

Phase 3: 数据迁移 (Day 6-7)
├─ 编写迁移脚本
├─ 迁移 experiments → feature_flags
└─ 验证数据完整性

Phase 4: 代码切换 (Day 8-10)
├─ 后端代码切换到新 API
├─ 前端代码切换到新 Hooks
└─ 回归测试

Phase 5: 清理 (Day 11-14)
├─ 观察期（1 周）
├─ 下线旧表（重命名 + 备份）
└─ 删除旧代码
```

### 7.2 迁移脚本示例

```python
# scripts/migrate_experiments_to_feature_flags.py

def migrate_experiments():
    """将 experiments 表数据迁移到 feature_flags + experiment_configs"""
    supabase = get_supabase_client()

    response = supabase.table("experiments").select("*").execute()
    experiments = response.data

    for exp in experiments:
        # 1. 创建 feature_flag 记录
        flag_data = {
            "key": exp["key"],
            "name": exp.get("name", exp["key"]),
            "flag_type": "experiment",
            "enabled": exp.get("status") == "active",
            "rollout_percentage": exp.get("traffic_allocation", 100),
            "variants": convert_variants(exp.get("variants", [])),
        }
        supabase.table("feature_flags").insert(flag_data).execute()

        # 2. 创建 experiment_config 记录
        config_data = {
            "flag_key": exp["key"],
            "primary_metric": exp.get("primary_metric", "conversion"),
            "status": convert_status(exp.get("status")),
        }
        supabase.table("experiment_configs").insert(config_data).execute()
```

### 7.3 回滚方案

```python
# scripts/rollback_feature_flags_migration.py

def rollback():
    """
    回滚迁移（如果需要）
    """
    supabase = get_supabase_client()

    # 1. 删除迁移的数据（根据 created_at 判断）
    migration_start = "2026-01-15T00:00:00Z"

    supabase.table("flag_exposures") \
        .delete() \
        .gte("timestamp", migration_start) \
        .execute()

    supabase.table("experiment_configs") \
        .delete() \
        .gte("created_at", migration_start) \
        .execute()

    supabase.table("feature_flags") \
        .delete() \
        .eq("flag_type", "experiment") \
        .gte("created_at", migration_start) \
        .execute()

    # 2. 恢复旧表名（如果已重命名）
    # ALTER TABLE experiments_deprecated RENAME TO experiments;

    logger.info("Rollback complete")
```

---

## 八、监控与分析

### 8.1 监控指标

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| **评估延迟** | 单次评估耗时 | p99 > 50ms |
| **缓存命中率** | Redis 缓存命中 | < 90% |
| **曝光量** | 每分钟曝光数 | 异常波动 |
| **错误率** | 评估错误比例 | > 0.1% |

### 8.2 分析面板

```
┌─────────────────────────────────────────────────────────────────┐
│  Experiment: exp_checkout_flow                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Status: Running  |  Day 5 of 14  |  Confidence: 87%           │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │            Conversion Rate Over Time                     │   │
│  │     ┌──────────────────────────────────────────────┐    │   │
│  │     │    ──── control (4.2%)                       │    │   │
│  │     │    ──── new_flow (4.8%) ↑14.3%              │    │   │
│  │     └──────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────┬──────────────────┐                       │
│  │     control      │     new_flow     │                       │
│  ├──────────────────┼──────────────────┤                       │
│  │ Exposures: 5,234 │ Exposures: 5,189 │                       │
│  │ Conversions: 220 │ Conversions: 249 │                       │
│  │ Rate: 4.20%      │ Rate: 4.80%      │                       │
│  │                  │ Lift: +14.3%     │                       │
│  │                  │ p-value: 0.13    │                       │
│  └──────────────────┴──────────────────┘                       │
│                                                                 │
│  ⚠️ Not yet significant. Need ~3,000 more samples.             │
│                                                                 │
│  [Pause Experiment]  [Stop & Ship Control]  [Stop & Ship New]  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 九、前端调试组件

### 9.1 FeatureFlagDebugger (开发环境)

```tsx
// components/debug/FeatureFlagDebugger.tsx

/**
 * 调试面板（仅开发环境）
 */
export function FeatureFlagDebugger() {
  const { flags, variants, isLoading, refresh, providerName, isReady } = useFeatureFlags();
  const [isOpen, setIsOpen] = React.useState(false);

  if (process.env.NODE_ENV === 'production') {
    return null;
  }

  return (
    <>
      {/* 触发按钮 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-4 right-4 z-50 p-2 bg-gray-900 text-white rounded-full shadow-lg hover:bg-gray-800"
        title="Feature Flags"
      >
        🚩
      </button>

      {/* 面板 */}
      {isOpen && (
        <div className="fixed bottom-16 right-4 z-50 w-80 max-h-96 overflow-auto bg-gray-900 text-white rounded-lg shadow-xl p-4 text-sm">
          <div className="flex justify-between items-center mb-3">
            <div>
              <h3 className="font-bold">Feature Flags</h3>
              <p className="text-xs text-gray-400">Provider: {providerName}</p>
            </div>
            <button
              onClick={() => refresh()}
              className="text-xs bg-blue-500 hover:bg-blue-600 px-2 py-1 rounded"
              disabled={isLoading}
            >
              {isLoading ? '...' : '↻'}
            </button>
          </div>

          {!isReady ? (
            <p className="text-gray-400">Loading...</p>
          ) : (
            <div className="space-y-2">
              {Object.entries(flags).length === 0 ? (
                <p className="text-gray-400">No flags</p>
              ) : (
                Object.entries(flags).map(([key, enabled]) => (
                  <div key={key} className="flex justify-between items-center py-1 border-b border-gray-700">
                    <div>
                      <span className="text-gray-300">{key}</span>
                      {variants[key] && variants[key] !== 'control' && (
                        <span className="ml-2 text-xs text-purple-400">
                          [{variants[key]}]
                        </span>
                      )}
                    </div>
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      enabled ? 'bg-green-600' : 'bg-red-600'
                    }`}>
                      {enabled ? 'ON' : 'OFF'}
                    </span>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}
    </>
  );
}
```

---

## 十、实施检查清单

### 10.1 Phase 1: 基础设施

| 任务 | 负责人 | 状态 | 验收标准 |
|------|--------|------|----------|
| 创建数据库表 | - | ⬜ | SQL 执行成功 |
| 实现 types.py | - | ⬜ | 类型定义完整 |
| 实现 hasher.py | - | ⬜ | 单元测试通过 |
| 实现 evaluator.py | - | ⬜ | 单元测试通过 |
| 实现 service.py | - | ⬜ | 单元测试通过 |
| 实现 self_hosted.py | - | ⬜ | 集成测试通过 |
| 实现 API 路由 | - | ⬜ | Swagger 可用 |
| 前端 types.ts | - | ⬜ | 类型定义完整 |

### 10.2 Phase 2: 前端集成

| 任务 | 负责人 | 状态 | 验收标准 |
|------|--------|------|----------|
| 实现 FeatureFlagProvider | - | ⬜ | Context 可用 |
| 实现 useFeatureFlag hook | - | ⬜ | 基本功能可用 |
| 实现 useExperiment hook | - | ⬜ | 变体分配正确 |
| 实现 FeatureFlag 组件 | - | ⬜ | 渲染逻辑正确 |
| 实现 FeatureFlagDebugger | - | ⬜ | 开发环境可用 |

### 10.3 Phase 3: 数据迁移

| 任务 | 负责人 | 状态 | 验收标准 |
|------|--------|------|----------|
| 编写迁移脚本 | - | ⬜ | 脚本可执行 |
| 迁移 experiments 数据 | - | ⬜ | 数据完整 |
| 验证数据完整性 | - | ⬜ | 无数据丢失 |
| 准备回滚脚本 | - | ⬜ | 可回滚 |

### 10.4 Phase 4: 监控部署

| 任务 | 负责人 | 状态 | 验收标准 |
|------|--------|------|----------|
| 配置监控指标 | - | ⬜ | Grafana 面板可用 |
| 配置告警规则 | - | ⬜ | 告警可触发 |
| 部署到 staging | - | ⬜ | 功能正常 |
| 部署到 production | - | ⬜ | 功能正常 |

---

## 十一、修订历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-01-06 | 初始版本：Feature Flag + Experiments 统一架构 |
| v1.1 | 2026-01-12 | 添加树状依赖：`parent_flags` 字段 |
| v1.2 | 2026-01-12 | 添加 Tier 分层：`allowed_tiers` 字段 |
| v2.0 | 2026-02-03 | 文档重组：从 feature-flag-design.md 迁移，聚焦引擎实现 |
| v2.1 | 2026-02-03 | 补充遗漏：回滚方案、监控指标、调试组件、operators (not_contains/starts_with/ends_with) |
| v2.2 | 2026-02-03 | 补充遗漏：审计类型详细说明、实施检查清单 |

---

**END OF DOCUMENT**
