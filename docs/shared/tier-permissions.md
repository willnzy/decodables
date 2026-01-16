# Make Decodables 会员权益汇总表

> **版本**: 1.0.0
> **最后更新**: 2026-01-12
> **状态**: ✅ 已确认

---

## 核心权益对比

| 权益 | t1 (Free) | t2 (Starter) | t3 (Pro) | t4 (预留) |
|:-----|:---------:|:------------:|:--------:|:---------:|
| **价格** | 免费 | ~~$9.9~~ **$6.9**/月 | ~~$15.9~~ **$9.9**/月 | 待定 |
| **月度积分** ¹ | 0 | 100 | 200 | 待定 |
| **注册赠送** ² | 100 积分 | - | - | - |
| **项目数** | 1 | 10 | 200 | 待定 |
| **试用期** | 30天全功能 | - | - | - |
| | | | | |
| **📄 导出** | | | | |
| PDF 导出/打印 | ✅ | ✅ | ✅ | ✅ |
| ZIP 批量导出 | 🔶 | ❌ | ✅ | ✅ |
| | | | | |
| **🎨 编辑器** | | | | |
| 基础编辑 | 🔶 | ✅ | ✅ | ✅ |
| 矢量图工具 | 🔶 | ❌ | ✅ | ✅ |
| 手绘工具 | 🔶 | ❌ | ✅ | ✅ |
| 剪贴板粘贴 ³ | 🔶 | ❌ | ✅ | ✅ |
| | | | | |
| **🖼️ 素材** | | | | |
| 平台基础素材 | 🔶 | ✅ | ✅ | ✅ |
| 上传素材 (图片) | 🔶 | ✅ | ✅ | ✅ |
| 上传素材 (SVG/PDF等) ⁴ | 🔶 | ❌ | ✅ | ✅ |
| 保存素材 | 🔶 | ❌ | ✅ | ✅ |
| 历史素材 | 🔶 | ❌ | ✅ | ✅ |
| | | | | |
| **🛒 市场** | | | | |
| 浏览市场 | 🔶 | ✅ | ✅ | ✅ |
| 购买内容 | ❌ | ❌ | ✅ | ✅ |
| 发布内容 | ❌ | ✅ | ✅ | ✅ |
| | | | | |
| **🤖 AI** | | | | |
| AI 生图/生Page/OCR | 🔶 | ✅ | ✅ | ✅ |
| 处理速度 | 🐢 低速 | 🚗 普通 | 🚀 高速 | 🚀 高速 |

---

## 积分充值价格

| 档位 | 积分 | 原价 | 现价 |
|:-----|:----:|:----:|:----:|
| 小包 | 100 | $2.99 | $2.99 |
| 中包 | 500 | $14.95 | $13.46 |
| 大包 | 2000 | $59.80 | $47.84 |

> 💡 **充值积分永久有效，不会过期**

---

## 积分规则

| 积分类型 | 来源 | 有效期 | 扣费优先级 |
|:---------|:-----|:------:|:----------:|
| **月度积分** | 订阅会员每月自动发放 | 每月重置，不累积 | 先扣 |
| **永久积分** | 注册赠送 / 充值购买 | **永久有效** | 后扣 |

---

## AI 消耗 (可配置)

| 功能 | 消耗 |
|:-----|:----:|
| AI 生图 | 5 积分 |
| AI 生 Page | 5 积分 |
| OCR 识别 | 5 积分 |

---

## t1 试用期说明

| 阶段 | 可用功能 |
|:-----|:---------|
| **试用期内 (30天)** | 全功能体验 (同 Pro) + 100 永久积分 |
| **试用期后** | **仅** PDF 导出/打印 |

---

## 升级亮点

| Free → Starter | Starter → Pro |
|:---------------|:--------------|
| +100 月度积分 | +200 月度积分 (翻倍) |
| +10 项目 | +200 项目 |
| +基础编辑功能 | +ZIP 批量导出 |
| +平台基础素材 | +矢量图/手绘工具 |
| +上传图片素材 | +剪贴板粘贴 |
| +浏览/发布市场 | +上传高级格式 (SVG/PDF) |
| +AI 功能 (普通队列) | +保存/历史素材 |
| | +购买市场内容 |
| | +AI 高速队列 |

---

## 备注

| 编号 | 说明 |
|:----:|:-----|
| ¹ | **月度积分**: 每月自动发放，月底重置归零，不累积到下月 |
| ² | **永久积分**: 注册赠送和充值获得的积分，永久有效不过期 |
| ³ | **剪贴板粘贴**: 支持从剪贴板粘贴图片、文字、截图到 Page |
| ⁴ | **高级格式上传**: 包括 SVG、PDF、AI 等矢量格式 |

---

## 图例

| 符号 | 含义 |
|:----:|:-----|
| ✅ | 可用 |
| ❌ | 不可用 |
| 🔶 | 试用期内可用，试用期后不可用 |

---

## 技术实现

### 数据库配置 (system_configs)

所有权益配置存储在 `system_configs` 表中，支持通过 Admin 页面动态调整。

#### 配置 Key 命名规范

```
tier.{tier_code}.{config_name}
credits.cost.{operation_name}
credits.topup.{package_name}
```

#### 完整配置列表

```sql
-- ==========================================
-- Tier 基础配置
-- ==========================================

-- 显示名称
('tier.t1.display_name', 'Free Plan', 'text', 'tier'),
('tier.t2.display_name', 'Starter Plan', 'text', 'tier'),
('tier.t3.display_name', 'Pro Plan', 'text', 'tier'),
('tier.t4.display_name', 'Enterprise Plan', 'text', 'tier'),

-- 是否启用 (t4 暂不启用)
('tier.t1.enabled', 'true', 'boolean', 'tier'),
('tier.t2.enabled', 'true', 'boolean', 'tier'),
('tier.t3.enabled', 'true', 'boolean', 'tier'),
('tier.t4.enabled', 'false', 'boolean', 'tier'),

-- 月度积分
('tier.t1.monthly_credits', '0', 'integer', 'tier'),
('tier.t2.monthly_credits', '100', 'integer', 'tier'),
('tier.t3.monthly_credits', '200', 'integer', 'tier'),
('tier.t4.monthly_credits', '500', 'integer', 'tier'),

-- 项目限制
('tier.t1.max_projects', '1', 'integer', 'tier'),
('tier.t2.max_projects', '10', 'integer', 'tier'),
('tier.t3.max_projects', '200', 'integer', 'tier'),
('tier.t4.max_projects', '1000', 'integer', 'tier'),

-- 价格配置 (原价)
('tier.t1.price_original', '0', 'decimal', 'tier'),
('tier.t2.price_original', '9.9', 'decimal', 'tier'),
('tier.t3.price_original', '15.9', 'decimal', 'tier'),
('tier.t4.price_original', '49.9', 'decimal', 'tier'),

-- 价格配置 (现价)
('tier.t1.price_current', '0', 'decimal', 'tier'),
('tier.t2.price_current', '6.9', 'decimal', 'tier'),
('tier.t3.price_current', '9.9', 'decimal', 'tier'),
('tier.t4.price_current', '39.9', 'decimal', 'tier'),

-- AI 队列优先级
('tier.t1.ai_queue_priority', 'low', 'text', 'tier'),
('tier.t2.ai_queue_priority', 'normal', 'text', 'tier'),
('tier.t3.ai_queue_priority', 'high', 'text', 'tier'),
('tier.t4.ai_queue_priority', 'high', 'text', 'tier'),

-- 充值折扣 (已取消 t3 折扣)
('tier.t1.topup_discount', '1.0', 'decimal', 'tier'),
('tier.t2.topup_discount', '1.0', 'decimal', 'tier'),
('tier.t3.topup_discount', '1.0', 'decimal', 'tier'),
('tier.t4.topup_discount', '1.0', 'decimal', 'tier'),

-- ==========================================
-- 功能权限 (JSON 格式)
-- ==========================================

('tier.t1.features', '{
  "pdf_export": true,
  "zip_export": "trial",
  "basic_editor": "trial",
  "vector_tools": "trial",
  "freehand_tools": "trial",
  "clipboard_paste": "trial",
  "platform_assets": "trial",
  "upload_image": "trial",
  "upload_advanced": "trial",
  "save_assets": "trial",
  "history_assets": "trial",
  "browse_marketplace": "trial",
  "purchase_marketplace": false,
  "publish_marketplace": false,
  "ai_features": "trial"
}', 'json', 'tier'),

('tier.t2.features', '{
  "pdf_export": true,
  "zip_export": false,
  "basic_editor": true,
  "vector_tools": false,
  "freehand_tools": false,
  "clipboard_paste": false,
  "platform_assets": true,
  "upload_image": true,
  "upload_advanced": false,
  "save_assets": false,
  "history_assets": false,
  "browse_marketplace": true,
  "purchase_marketplace": false,
  "publish_marketplace": true,
  "ai_features": true
}', 'json', 'tier'),

('tier.t3.features', '{
  "pdf_export": true,
  "zip_export": true,
  "basic_editor": true,
  "vector_tools": true,
  "freehand_tools": true,
  "clipboard_paste": true,
  "platform_assets": true,
  "upload_image": true,
  "upload_advanced": true,
  "save_assets": true,
  "history_assets": true,
  "browse_marketplace": true,
  "purchase_marketplace": true,
  "publish_marketplace": true,
  "ai_features": true
}', 'json', 'tier'),

('tier.t4.features', '{
  "pdf_export": true,
  "zip_export": true,
  "basic_editor": true,
  "vector_tools": true,
  "freehand_tools": true,
  "clipboard_paste": true,
  "platform_assets": true,
  "upload_image": true,
  "upload_advanced": true,
  "save_assets": true,
  "history_assets": true,
  "browse_marketplace": true,
  "purchase_marketplace": true,
  "publish_marketplace": true,
  "ai_features": true,
  "priority_support": true,
  "api_access": true
}', 'json', 'tier'),

-- ==========================================
-- AI 功能成本配置
-- ==========================================

('credits.cost.image_generation', '5', 'integer', 'credits'),
('credits.cost.page_generation', '5', 'integer', 'credits'),
('credits.cost.ocr', '5', 'integer', 'credits'),
('credits.cost.smart_scan', '5', 'integer', 'credits'),
('credits.cost.text_generation', '0', 'integer', 'credits'),

-- ==========================================
-- 充值包配置
-- ==========================================

('credits.topup.small.credits', '100', 'integer', 'credits'),
('credits.topup.small.price_original', '2.99', 'decimal', 'credits'),
('credits.topup.small.price_current', '2.99', 'decimal', 'credits'),

('credits.topup.medium.credits', '500', 'integer', 'credits'),
('credits.topup.medium.price_original', '14.95', 'decimal', 'credits'),
('credits.topup.medium.price_current', '13.46', 'decimal', 'credits'),

('credits.topup.large.credits', '2000', 'integer', 'credits'),
('credits.topup.large.price_original', '59.80', 'decimal', 'credits'),
('credits.topup.large.price_current', '47.84', 'decimal', 'credits'),

-- ==========================================
-- 其他配置
-- ==========================================

('credits.signup_bonus', '100', 'integer', 'credits'),
('tier.trial_duration_days', '30', 'integer', 'tier'),
```

### 功能权限值说明

| 值 | 含义 |
|:---|:-----|
| `true` | 功能可用 |
| `false` | 功能不可用 |
| `"trial"` | 试用期内可用，试用期后不可用 |

### API 接口

#### 公开 API (无需登录)

```
GET /api/v2/config/tiers
```

返回所有启用的 Tier 配置供前端使用。

#### Admin API

```
GET  /api/v2/admin/tier-permissions           # 获取所有 Tier 权限配置
PUT  /api/v2/admin/tier-permissions/{tier}    # 更新 Tier 权限配置
GET  /api/v2/admin/credit-costs               # 获取积分成本配置
PUT  /api/v2/admin/credit-costs               # 更新积分成本配置
GET  /api/v2/admin/topup-packages             # 获取充值包配置
PUT  /api/v2/admin/topup-packages             # 更新充值包配置
```

---

## 修订历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0.0 | 2026-01-12 | 初始版本，基于用户确认的权益表 |

---

**END OF DOCUMENT**
