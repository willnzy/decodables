# Tier 配置详情

> 基于权限矩阵的 Tier 配置设计与优先级规则。

**状态**: needs-review  
**版本**: 1.2.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Product Team  
**适用范围**: shared  
**source_repo**: backend  
**sync_required**: yes

---

## 背景

- 需要统一 Tier 配置与权限粒度
- 明确配置优先级与可控范围

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 相关文档

| 文档 | 说明 |
|------|------|
| `docs/v2/03-business/entitlement/README.md` | 权限系统导航 |
| `docs/v2/03-business/entitlement/permission-matrix.md` | 权限矩阵 |

---

## 灵活配置系统设计

### 设计原则

**核心需求**: 除了明确标注“不用控制”的功能外，其他所有功能都应通过后台可配置的权限系统控制。

**不需要配置控制的功能**:
| # | 功能 | 原因 |
|---|------|------|
| 31 | Manual/News 页 | 公开文档 |
| 32 | 静态页面 (About/Terms 等) | 法律/品牌页面 |
| 35 | Help 按钮 | 帮助入口 |

**需要配置控制的功能**: 其余 32 个功能点。

### 配置粒度

支持三种控制粒度：

| 粒度 | 配置位置 | 说明 | 使用场景 |
|------|----------|------|---------|
| 全局开关 | `system_configs.feature.{key}.enabled` | 所有用户统一开/关 | 功能下线、运维紧急关闭 |
| 按 Tier 配置 | `system_configs.tier.{tier}.features` | 不同 Tier 不同权限 | 常规权限控制 |
| 用户 Override | `user_feature_overrides` 表 | 为特定用户开通/关闭功能 | VIP、测试、补偿、AB 实验 |

### 权限优先级规则

```
Level 1: 全局开关 (Kill Switch)
Level 2: 用户级覆盖 (User Override)
Level 3: Tier 配置 (Plan-based)
Level 4: 默认值 (Fallback)
```

### 配置值类型

| 值 | 说明 | 前端表现 |
|----|------|---------|
| `true` | 完全可用 | 正常按钮 |
| `false` | 不可用 | Lock + Tooltip + Upgrade |
| `"trial"` | 试用期可用 | 试用期内正常 + Badge |
| `"tier_required"` | 需要特定 Tier | 页面级拦截 |

### 数据库表设计

#### system_configs

```sql
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
('feature.platform_assets.enabled', 'true', 'boolean', 'feature', '平台素材全局开关'),
('feature.vector_tools.enabled', 'true', 'boolean', 'feature', '矢量图工具全局开关'),
('feature.ai_features.enabled', 'true', 'boolean', 'feature', 'AI 功能全局开关');
```

#### user_feature_overrides

```sql
CREATE TABLE user_feature_overrides (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  feature_key TEXT NOT NULL,
  override_value TEXT NOT NULL,
  reason TEXT,
  expires_at TIMESTAMPTZ,
  created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, feature_key)
);
```

---

## 待实现清单

> 审计发现：以下内容已设计但尚未在数据库/后端实现。

### 数据库层

| # | 待实现项 | 说明 | 优先级 |
|---|---------|------|--------|
| 1 | `user_feature_overrides` | 用户级权限覆盖 | P0 |
| 2 | `user_feature_override_logs` | 审计日志 | P1 |
| 3 | 过期清理索引 | `idx_user_feature_overrides_expires` | P1 |
| 4 | RLS 策略 | 安全控制 | P1 |
| 5 | 配额配置 | `tier.{tier}.quotas.max_workspace_members` | P1 |

## 影响范围

- 相关模块：Tier 配置与权限控制
- 相关文档：`docs/v2/03-business/entitlement/permission-matrix.md`

## 证据与验证

- 关键证据来源：`decodables/docs/shared/entitlement/tier-config.md`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 1.2.0 | 结构对齐模板 | Docs Working Group |
