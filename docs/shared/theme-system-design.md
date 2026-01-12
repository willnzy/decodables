# Theme 主题系统设计 - Daily Doodle 风格

> **版本**: v2.0
> **日期**: 2026-01-12
> **灵感**: Google Doodle - 根据日期自动变化的动态主题
> **更新**: v2.0 增加全站视觉变化、Campaign 联动、Admin 管理、AI 辅助生成

---

## 目录

1. [设计概览](#1-设计概览)
2. [优先级规则](#2-优先级规则)
3. [数据结构设计](#3-数据结构设计)
4. [AI 辅助生成](#4-ai-辅助生成)
5. [后端实现](#5-后端实现)
6. [前端实现](#6-前端实现)
7. [Campaign 联动](#7-campaign-联动)
8. [Admin 管理界面](#8-admin-管理界面)
9. [主题内容规划](#9-主题内容规划)
10. [实施计划](#10-实施计划)

---

## 1. 设计概览

### 1.1 核心理念

```
┌─────────────────────────────────────────────────────────────────┐
│                    Daily Doodle 主题系统 v2.0                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  "每一天都值得纪念，每一个主题都讲述故事"                          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  优先级 1: 世界级节日 (Priority 90-100)                   │   │
│  │  • 新年 (1月1日) - 全球庆祝                               │   │
│  │  • 春节 (农历新年) - 亚洲地区                             │   │
│  │  • 圣诞节 (12月25日) - 西方国家                           │   │
│  │  • 复活节 (动态日期) - 宗教节日                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  优先级 2: 重要纪念日 (Priority 70-89)                    │   │
│  │  • 世界读书日 (4月23日) - 与产品相关                      │   │
│  │  • 地球日 (4月22日) - 环保主题                            │   │
│  │  • 国际妇女节 (3月8日) - 社会意义                         │   │
│  │  • 世界教师日 (10月5日) - 教育主题                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  优先级 3: 伟人/历史纪念 (Priority 50-69)                 │   │
│  │  • 爱因斯坦诞辰 (3月14日) - Pi Day                        │   │
│  │  • 阿波罗11号登月 (7月20日)                               │   │
│  │  • 万维网诞生 (3月12日)                                   │   │
│  │  • 居里夫人诞辰 (11月7日)                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  优先级 4: Campaign 营销活动 (Priority 40-59)             │   │
│  │  • 黑五促销 (11月第4周五)                                 │   │
│  │  • 返校季 (8-9月)                                         │   │
│  │  • 周年庆活动                                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 全站视觉变化范围

```
┌─────────────────────────────────────────────────────────────────┐
│                      全站视觉变化架构                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─ Navbar ─────────────────────────────────────────────────┐  │
│  │  • Logo 装饰 (emoji/图标/动画)                            │  │
│  │  • 背景色/渐变                                            │  │
│  │  • 节日 Badge 展示                                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─ 页面背景 ───────────────────────────────────────────────┐  │
│  │  • 背景色/渐变/图案                                       │  │
│  │  • 装饰动画 (雪花/心形/彩带/烟花)                         │  │
│  │  • 边角装饰图案                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─ 按钮/交互元素 ──────────────────────────────────────────┐  │
│  │  • Primary Button 颜色                                    │  │
│  │  • Hover 效果                                             │  │
│  │  • 链接颜色                                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─ Footer ─────────────────────────────────────────────────┐  │
│  │  • 背景色/图案                                            │  │
│  │  • 节日祝福语                                             │  │
│  │  • 装饰元素                                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─ 编辑器区域 (可选) ───────────────────────────────────────┐  │
│  │  • 侧边栏节日提示                                         │  │
│  │  • 节日模板推荐                                           │  │
│  │  • 保持编辑器核心区域稳定                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 用户体验流程

```
┌─────────────────────────────────────────────────────────────────┐
│                      用户体验流程                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  用户访问网站                                                    │
│       │                                                         │
│       ▼                                                         │
│  检测用户本地时间 + 时区 + 地区                                  │
│       │                                                         │
│       ▼                                                         │
│  查询当日主题 (按优先级)                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. 检查是否有世界级节日 (priority 90+)                  │   │
│  │  2. 检查是否有地区特定节日 (用户时区)                    │   │
│  │  3. 检查是否有重要纪念日 (priority 70-89)                │   │
│  │  4. 检查是否有历史/伟人纪念 (priority 50-69)             │   │
│  │  5. 检查是否有 Campaign 活动 (priority 40-59)            │   │
│  │  6. 使用默认主题                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │                                                         │
│       ▼                                                         │
│  应用全站视觉变化                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • CSS 变量注入 (颜色/间距)                              │   │
│  │  • Logo 装饰渲染                                         │   │
│  │  • 背景效果应用                                          │   │
│  │  • 装饰动画启动                                          │   │
│  │  • 节日 Badge 显示                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │                                                         │
│       ▼                                                         │
│  用户点击 Logo/Badge                                             │
│       │                                                         │
│       ▼                                                         │
│  显示主题详情弹窗                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 今日是什么日子?                                       │   │
│  │  • 相关故事/历史                                         │   │
│  │  • 相关 Campaign 活动 (如有)                             │   │
│  │  • 分享按钮                                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 优先级规则

### 2.1 优先级层级

| 层级 | 优先级范围 | 类型 | 示例 |
|------|------------|------|------|
| **L1** | 95-100 | 世界级节日 | 新年、圣诞节、春节 |
| **L2** | 85-94 | 产品相关纪念日 | 世界读书日、教师节 |
| **L3** | 70-84 | 重要国际日 | 地球日、妇女节 |
| **L4** | 50-69 | 伟人/历史纪念 | 爱因斯坦诞辰、Pi Day |
| **L5** | 40-49 | 营销活动 | 黑五、返校季 |
| **L6** | 0-39 | 轻量级/趣味 | 程序员节、Pi Day |

### 2.2 同日多主题规则

```python
# 规则 1: 优先级最高者胜出
if multiple_themes_same_day:
    active_theme = max(themes, key=lambda t: t.priority)

# 规则 2: 同优先级时，更具体的胜出
if same_priority:
    # 固定日期 > 动态日期 > 范围日期
    active_theme = select_most_specific()

# 规则 3: 地区特定主题优先于全球主题
if same_priority_same_specificity:
    if user_region_theme_exists:
        active_theme = user_region_theme
    else:
        active_theme = global_theme
```

---

## 3. 数据结构设计

### 3.1 数据库表结构

```sql
-- ============================================================
-- daily_themes 表升级 (v2.0)
-- 位置: migrations/v2/02_platform_services.sql
-- ============================================================

-- 在现有 daily_themes 表基础上添加字段:

-- 1. 分类字段
category TEXT NOT NULL DEFAULT 'holiday'
    CHECK (category IN (
        'holiday',      -- 节日 (圣诞、新年、春节)
        'memorial',     -- 纪念日 (地球日、读书日)
        'historical',   -- 历史今日 (登月、WWW诞生)
        'notable',      -- 伟人诞辰 (爱因斯坦、居里夫人)
        'campaign',     -- 营销活动 (黑五、返校季)
        'special'       -- 特殊事件 (一次性)
    )),

-- 2. 多语言支持
name_i18n JSONB DEFAULT '{}',           -- {"zh": "圣诞节", "en": "Christmas"}
slogan TEXT,                             -- 主要标语
slogan_i18n JSONB DEFAULT '{}',          -- {"zh": "圣诞快乐!", "en": "Merry Christmas!"}
description_i18n JSONB DEFAULT '{}',     -- 多语言详细描述

-- 3. Logo 变体配置 (在 theme_config 中)
-- 4. 全站颜色配置 (在 theme_config 中)
-- 5. 背景配置 (在 theme_config 中)
-- 6. 动画配置 (在 theme_config 中)

-- 7. 地区限制
regions TEXT[] DEFAULT ARRAY['global'],  -- 适用地区

-- 8. Campaign 关联 (v2.0 新增)
linked_campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,

-- 9. AI 生成相关 (v2.0 新增)
ai_generated BOOLEAN DEFAULT false,      -- 是否 AI 生成
ai_alternatives JSONB DEFAULT '[]',      -- AI 生成的备选方案
selected_alternative_id TEXT,            -- 选中的备选方案 ID

-- 10. 资源 URL
source_url TEXT,                         -- 参考来源
learn_more_url TEXT,                     -- "了解更多" 链接

-- 添加索引
CREATE INDEX idx_daily_themes_category ON daily_themes (category) WHERE is_deleted = false;
CREATE INDEX idx_daily_themes_regions ON daily_themes USING GIN (regions) WHERE is_deleted = false;
```

### 3.2 theme_config 完整结构

```typescript
interface ThemeConfig {
  // ==================== Logo 变体 ====================
  logo_variant?: {
    type: 'decorated' | 'replaced' | 'animated';
    decorations?: {
      prefix?: string;      // 前缀 emoji/图标
      suffix?: string;      // 后缀 emoji/图标
      overlay_url?: string; // 叠加图层 URL
    };
    custom_logo?: {
      url: string;
      width?: number;
      height?: number;
    };
    animation?: {
      type: 'bounce' | 'pulse' | 'glow' | 'shake' | 'custom';
      duration?: number;
      css?: string;
    };
  };

  // ==================== 全站颜色 (v2.0) ====================
  colors?: {
    primary: string;
    primary_hover: string;
    primary_light: string;
    accent: string;
    accent_hover: string;
    background: string;
    background_secondary: string;
    text: string;
    text_secondary: string;
    text_inverse: string;
    overrides?: {
      navbar?: { background: string; text: string };
      footer?: { background: string; text: string };
      button_primary?: { background: string; text: string };
    };
  };

  // ==================== 背景效果 ====================
  background?: {
    type: 'solid' | 'gradient' | 'image' | 'pattern';
    color?: string;
    gradient?: {
      type: 'linear' | 'radial';
      angle?: number;
      colors: string[];
      positions?: number[];
    };
    image?: {
      url: string;
      position?: string;
      size?: string;
      repeat?: string;
      opacity?: number;
    };
    pattern?: {
      url: string;
      scale?: number;
    };
  };

  // ==================== 装饰动画 ====================
  animations?: Array<{
    id: string;
    type: 'snowflakes' | 'hearts' | 'confetti' | 'fireworks' | 'stars' | 'leaves' | 'bubbles' | 'custom';
    enabled: boolean;
    intensity: 'light' | 'medium' | 'heavy';
    particles?: {
      count: number;
      colors: string[];
      size: { min: number; max: number };
      speed: { min: number; max: number };
      opacity?: { min: number; max: number };
    };
    zones?: ('full' | 'top' | 'bottom' | 'sides')[];
    performance?: {
      mobile_enabled: boolean;
      mobile_intensity: 'light' | 'off';
      reduce_motion_disable: boolean;
    };
  }>;

  // ==================== 徽章配置 ====================
  badge?: {
    text: string;
    text_i18n?: Record<string, string>;
    style?: 'default' | 'festive' | 'minimal';
    position?: 'navbar' | 'logo' | 'banner';
    link_to_detail?: boolean;
  };

  // ==================== 页脚配置 ====================
  footer?: {
    greeting?: string;
    greeting_i18n?: Record<string, string>;
    decorations?: {
      left?: string;
      right?: string;
    };
  };

  // ==================== 弹窗配置 ====================
  detail_modal?: {
    title: string;
    title_i18n?: Record<string, string>;
    content: string;
    content_i18n?: Record<string, string>;
    image_url?: string;
    learn_more_url?: string;
    share_enabled?: boolean;
  };
}
```

### 3.3 日期规则格式

```typescript
interface DateRule {
  type: 'fixed' | 'dynamic' | 'lunar' | 'range';

  // 固定日期: "MM-DD" 格式
  start?: string;
  end?: string;

  // 动态日期
  rule?: string;  // "us_thanksgiving", "mothers_day", etc.
  offset_start?: number;
  offset_end?: number;

  // 农历日期
  lunar_month?: number;
  lunar_day?: number;
  lunar_offset_start?: number;
  lunar_offset_end?: number;

  // 日期范围
  start_month?: number;
  start_day?: number;
  end_month?: number;
  end_day?: number;

  // 通用选项
  years?: number[];
  exclude_years?: number[];
}
```

---

## 4. AI 辅助生成

### 4.1 核心流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI 辅助主题生成流程                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─ Step 1: 触发生成 ───────────────────────────────────────┐  │
│  │  • Admin 点击 "AI 生成建议" 按钮                          │  │
│  │  • 或系统自动在无主题日期前 N 天触发                      │  │
│  │  • 输入: 日期 + 上下文 (产品定位、目标用户)               │  │
│  └──────────────────────────────────────────────────────────┘  │
│       │                                                         │
│       ▼                                                         │
│  ┌─ Step 2: AI 分析日期意义 ────────────────────────────────┐  │
│  │  • 查询历史今日事件                                       │  │
│  │  • 查询国际纪念日                                         │  │
│  │  • 查询伟人诞辰/忌日                                      │  │
│  │  • 分析与教育/儿童/阅读的关联度                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│       │                                                         │
│       ▼                                                         │
│  ┌─ Step 3: 生成 3 个备选方案 ──────────────────────────────┐  │
│  │                                                           │  │
│  │  备选 A: 推荐方案 (最匹配产品定位)                        │  │
│  │  ├─ 主题名称 + 标语                                       │  │
│  │  ├─ Logo 装饰建议                                         │  │
│  │  ├─ 配色方案                                              │  │
│  │  ├─ 动画效果建议                                          │  │
│  │  └─ 详情内容                                              │  │
│  │                                                           │  │
│  │  备选 B: 备选方案 (不同风格)                              │  │
│  │  └─ ...                                                   │  │
│  │                                                           │  │
│  │  备选 C: 创意方案 (独特视角)                              │  │
│  │  └─ ...                                                   │  │
│  │                                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│       │                                                         │
│       ▼                                                         │
│  ┌─ Step 4: Admin 审核选择 ─────────────────────────────────┐  │
│  │  • 预览每个方案的实际效果                                 │  │
│  │  • 选择一个方案                                           │  │
│  │  • 可以微调后发布                                         │  │
│  │  • 或完全拒绝重新生成                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│       │                                                         │
│       ▼                                                         │
│  ┌─ Step 5: 发布主题 ───────────────────────────────────────┐  │
│  │  • 保存选中的方案                                         │  │
│  │  • 记录 AI 生成来源 (ai_generated = true)                 │  │
│  │  • 保存其他备选供参考 (ai_alternatives)                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 AI Prompt 设计

```python
# 主题生成 Prompt

THEME_GENERATION_PROMPT = """
你是 Make Decodables 的主题设计师。Make Decodables 是一个帮助教师为儿童创建可解码小书的平台。

今天的日期是: {date}

请分析这个日期在历史上的重要意义，并生成 3 个主题设计方案。

关于这个日期:
1. 有哪些世界性节日或纪念日?
2. 有哪些著名人物在这一天出生或去世?
3. 历史上这一天发生过什么重大事件?
4. 这些事件与教育、儿童、阅读、学习有什么关联?

请按以下格式返回 3 个备选方案:

```json
{
  "analysis": {
    "date": "YYYY-MM-DD",
    "events": [
      {"type": "holiday|memorial|historical|notable", "name": "...", "relevance_score": 0-100}
    ],
    "recommended_category": "holiday|memorial|historical|notable|special"
  },
  "alternatives": [
    {
      "id": "A",
      "recommendation": "primary",  // primary | secondary | creative
      "name": "主题名称",
      "name_i18n": {"zh": "中文名称", "en": "English Name"},
      "category": "memorial",
      "priority": 75,
      "slogan": "主题标语",
      "slogan_i18n": {"zh": "...", "en": "..."},
      "description": "详细描述 (50-100字)",
      "theme_config": {
        "logo_variant": {
          "type": "decorated",
          "decorations": {
            "prefix": "emoji",
            "suffix": "emoji"
          }
        },
        "colors": {
          "primary": "#hex",
          "accent": "#hex",
          "background": "#hex"
        },
        "animations": [
          {
            "type": "snowflakes|hearts|confetti|fireworks|stars|leaves",
            "intensity": "light|medium"
          }
        ],
        "badge": {
          "text": "🎄 Badge Text"
        }
      },
      "rationale": "为什么推荐这个方案 (50字)"
    },
    // ... 备选 B, C
  ]
}
```

生成方案时请遵循:
1. 方案 A (推荐): 最匹配教育/儿童产品定位
2. 方案 B (备选): 不同的视觉风格
3. 方案 C (创意): 独特或有趣的视角

颜色选择原则:
- 适合儿童的明亮、友好色调
- 避免过于刺眼或阴暗的颜色
- 配色要和谐、舒适

动画选择原则:
- 轻量化，不影响性能
- 有趣但不分散注意力
- 与主题氛围匹配
"""
```

### 4.3 AI 生成 API

```python
# api/admin/themes.py

@router.post("/generate-suggestions")
async def generate_theme_suggestions(
    target_date: str = Query(..., description="目标日期 YYYY-MM-DD"),
    admin_user = Depends(require_admin)
):
    """
    使用 AI 生成主题建议

    返回 3 个备选方案供 Admin 选择
    """
    from shared.ai.openai_service import OpenAIService

    ai_service = OpenAIService()

    # 构建 Prompt
    prompt = THEME_GENERATION_PROMPT.format(date=target_date)

    # 调用 AI
    response = await ai_service.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.7,
        max_tokens=2000
    )

    # 解析结果
    suggestions = json.loads(response.content)

    # 存储到临时表或缓存
    cache_key = f"theme_suggestions:{target_date}"
    await cache_service.set(cache_key, suggestions, ttl=3600)

    return {
        "date": target_date,
        "suggestions": suggestions,
        "expires_in": 3600
    }


@router.post("/apply-suggestion")
async def apply_theme_suggestion(
    target_date: str,
    alternative_id: str,  # "A", "B", or "C"
    modifications: Optional[dict] = None,  # Admin 的修改
    admin_user = Depends(require_admin)
):
    """
    应用 AI 生成的主题建议

    - alternative_id: 选中的备选方案
    - modifications: Admin 的自定义修改
    """
    # 获取缓存的建议
    cache_key = f"theme_suggestions:{target_date}"
    suggestions = await cache_service.get(cache_key)

    if not suggestions:
        raise HTTPException(404, "Suggestions expired, please regenerate")

    # 找到选中的方案
    selected = None
    for alt in suggestions["alternatives"]:
        if alt["id"] == alternative_id:
            selected = alt
            break

    if not selected:
        raise HTTPException(400, f"Alternative {alternative_id} not found")

    # 应用修改
    if modifications:
        selected = {**selected, **modifications}

    # 创建主题
    theme = await themes_service.create_theme(
        name=selected["name"],
        name_i18n=selected.get("name_i18n", {}),
        category=selected["category"],
        priority=selected["priority"],
        date_rule={"type": "fixed", "start": target_date[5:], "end": target_date[5:]},
        theme_config=selected["theme_config"],
        slogan=selected.get("slogan"),
        slogan_i18n=selected.get("slogan_i18n", {}),
        description=selected.get("description"),
        ai_generated=True,
        ai_alternatives=suggestions["alternatives"],
        selected_alternative_id=alternative_id,
        created_by=admin_user.user_id
    )

    return {"theme": theme, "message": "Theme created successfully"}
```

### 4.4 Admin UI - AI 生成界面

```
┌─────────────────────────────────────────────────────────────────┐
│  AI 主题生成                                          [X 关闭] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  目标日期: 2026-03-14 (周六)                                     │
│                                                                 │
│  [正在分析日期意义...]                                           │
│                                                                 │
│  ══════════════════════════════════════════════════════════════ │
│                                                                 │
│  📅 日期分析:                                                    │
│  • π Day (圆周率日) - 国际纪念日                                 │
│  • 爱因斯坦诞辰 (1879) - 伟人纪念                                │
│  • 与教育/科学高度相关 (评分: 95)                                │
│                                                                 │
│  ══════════════════════════════════════════════════════════════ │
│                                                                 │
│  备选方案:                                                       │
│                                                                 │
│  ┌─ 方案 A (推荐) ───────────────────────────────────────────┐ │
│  │  π Pi Day + Einstein Birthday                             │ │
│  │  "Imagination is more important than knowledge"           │ │
│  │                                                           │ │
│  │  预览: [π Make Decodables 🧠]                              │ │
│  │  配色: 蓝色科技风格                                        │ │
│  │  动画: 星星粒子                                            │ │
│  │                                                           │ │
│  │  [实时预览]                              [✓ 选择此方案]   │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─ 方案 B (备选) ───────────────────────────────────────────┐ │
│  │  Math Celebration Day                                      │ │
│  │  "Make learning math fun!"                                 │ │
│  │  ...                                                       │ │
│  │  [实时预览]                              [ ] 选择此方案   │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─ 方案 C (创意) ───────────────────────────────────────────┐ │
│  │  Science Heroes Day                                        │ │
│  │  "Celebrate the minds that changed the world"              │ │
│  │  ...                                                       │ │
│  │  [实时预览]                              [ ] 选择此方案   │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  [重新生成]                              [取消] [应用选中方案] │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.5 自动生成调度

```python
# 定时任务: 每天检查未来 7 天是否有空白日期

async def auto_generate_theme_suggestions():
    """
    自动为未来 7 天无主题的日期生成建议

    运行频率: 每天凌晨 2:00
    """
    today = date.today()

    for i in range(1, 8):
        check_date = today + timedelta(days=i)

        # 检查是否已有主题
        existing = await themes_service.get_theme_for_date(check_date)
        if existing:
            continue

        # 检查是否已有待审核建议
        cache_key = f"theme_suggestions:{check_date.isoformat()}"
        existing_suggestions = await cache_service.get(cache_key)
        if existing_suggestions:
            continue

        # 生成建议
        try:
            suggestions = await ai_service.generate_theme_suggestions(check_date)
            await cache_service.set(cache_key, suggestions, ttl=86400 * 7)

            # 通知 Admin
            await notification_service.notify_admins(
                title="新的主题建议待审核",
                message=f"{check_date.isoformat()} 的主题建议已生成，请登录后台审核",
                link=f"/admin/themes/suggestions?date={check_date.isoformat()}"
            )
        except Exception as e:
            logger.error(f"Failed to generate suggestions for {check_date}: {e}")
```

---

## 5. 后端实现

### 5.1 目录结构

```
domains/themes/
├── __init__.py
├── entity.py                   # ThemeEntity 定义
├── repository.py               # Repository 接口
├── themes_service.py           # 业务逻辑 (已存在，需升级)
└── date_matcher.py             # 日期匹配器 (v2.0 新增)

shared/ai/
└── theme_generator.py          # AI 主题生成服务

infrastructure/repositories/
└── themes_repository.py        # Supabase 实现

api/user/
└── themes.py                   # 用户 API (已存在)

api/admin/
└── themes.py                   # Admin API (v2.0 新增)
```

### 5.2 Theme Service 升级

```python
# domains/themes/themes_service.py (v2.0)

class ThemesService:
    """Theme 服务 - v2.0"""

    async def get_current_theme(
        self,
        check_date: date,
        user_region: str = "global",
        locale: str = "en"
    ) -> Optional[Dict[str, Any]]:
        """获取当前活跃主题"""
        themes = await self.repository.list_active_themes()

        if not themes:
            return None

        matching_themes = []

        for theme in themes:
            if not self._is_theme_active(theme["date_rule"], check_date):
                continue

            regions = theme.get("regions", ["global"])
            is_region_specific = user_region in regions
            is_global = "global" in regions

            if is_region_specific or is_global:
                matching_themes.append({
                    **theme,
                    "_is_region_specific": is_region_specific
                })

        if not matching_themes:
            return None

        # 排序: 地区特定 > 全球 > 优先级高
        matching_themes.sort(
            key=lambda t: (t["_is_region_specific"], t.get("priority", 0)),
            reverse=True
        )

        return self._resolve_i18n(matching_themes[0], locale)
```

---

## 6. 前端实现

### 6.1 目录结构

```
@core/theme/
├── index.ts                    # 导出
├── types.ts                    # 类型定义
├── ThemeProvider.tsx           # 主题上下文 Provider
├── useTheme.ts                 # 主 Hook
├── components/
│   ├── ThemeLogo.tsx           # 主题 Logo
│   ├── ThemeBadge.tsx          # 主题徽章
│   ├── ThemeBackground.tsx     # 背景效果
│   ├── ThemeAnimationLayer.tsx # 动画层
│   ├── ThemeDetailModal.tsx    # 详情弹窗
│   └── ThemeFooter.tsx         # 主题页脚
├── animations/
│   ├── Snowflakes.tsx          # 雪花动画
│   ├── Hearts.tsx              # 心形动画
│   ├── Confetti.tsx            # 彩带动画
│   ├── Fireworks.tsx           # 烟花动画
│   └── Stars.tsx               # 星星动画
└── utils/
    ├── colorUtils.ts           # 颜色工具
    ├── cssVariables.ts         # CSS 变量注入
    └── dateUtils.ts            # 日期工具
```

### 6.2 CSS 变量注入

```typescript
// @core/theme/utils/cssVariables.ts

export function injectCSSVariables(colors: ThemeColors): void {
  const root = document.documentElement;

  root.style.setProperty('--theme-primary', colors.primary);
  root.style.setProperty('--theme-primary-hover', colors.primary_hover);
  root.style.setProperty('--theme-primary-light', colors.primary_light);
  root.style.setProperty('--theme-accent', colors.accent);
  root.style.setProperty('--theme-accent-hover', colors.accent_hover);
  root.style.setProperty('--theme-background', colors.background);
  root.style.setProperty('--theme-background-secondary', colors.background_secondary);
  root.style.setProperty('--theme-text', colors.text);
  root.style.setProperty('--theme-text-secondary', colors.text_secondary);
  root.style.setProperty('--theme-text-inverse', colors.text_inverse);

  // 组件覆盖
  if (colors.overrides?.navbar) {
    root.style.setProperty('--theme-navbar-bg', colors.overrides.navbar.background);
    root.style.setProperty('--theme-navbar-text', colors.overrides.navbar.text);
  }

  if (colors.overrides?.footer) {
    root.style.setProperty('--theme-footer-bg', colors.overrides.footer.background);
    root.style.setProperty('--theme-footer-text', colors.overrides.footer.text);
  }
}
```

---

## 7. Campaign 联动

### 7.1 联动原则

```
Theme 与 Campaign 的关系: 联动但独立

• Theme 控制视觉展示
• Campaign 控制业务逻辑 (积分、折扣)
• 同一节日可以有 Theme 无 Campaign
• Theme 和 Campaign 可以相互关联
```

### 7.2 联动字段

```sql
-- Theme 关联 Campaign
ALTER TABLE daily_themes ADD COLUMN linked_campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL;

-- Campaign 关联 Theme
ALTER TABLE campaigns ADD COLUMN linked_theme_id UUID REFERENCES daily_themes(id) ON DELETE SET NULL;
```

---

## 8. Admin 管理界面

### 8.1 功能概览

```
Admin > Themes 管理

┌─────────────────────────────────────────────────────────────────┐
│  Themes 主题管理                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Tab: 列表视图] [Tab: 日历视图] [Tab: AI 建议] [Tab: 设置]     │
│                                                                 │
│  ┌─ 工具栏 ──────────────────────────────────────────────────┐ │
│  │ [+ 创建主题] [🤖 AI 生成] [导入] [导出]                   │ │
│  │ 筛选: [分类 ▾] [状态 ▾] [地区 ▾]  搜索: [________]       │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─ 主题列表 ────────────────────────────────────────────────┐ │
│  │ ☐ | 名称           | 分类     | 日期规则    | 优先级 | AI │ │
│  │───────────────────────────────────────────────────────────│ │
│  │ ☐ | 🎄 Christmas   | holiday  | 12-20~12-26 | 95    |    │ │
│  │ ☐ | 📚 World Book  | memorial | 04-23       | 85    |    │ │
│  │ ☐ | π Pi Day       | notable  | 03-14       | 55    | 🤖 │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 AI 建议 Tab

```
┌─────────────────────────────────────────────────────────────────┐
│  AI 待审核建议                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  未来 7 天待填充日期:                                            │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ 📅 2026-03-14 (周六)                           [查看建议] │ │
│  │    AI 已生成 3 个备选方案                                 │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ 📅 2026-03-15 (周日)                           [生成建议] │ │
│  │    暂无建议，点击生成                                     │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. 主题内容规划

### 9.1 年度主题日历

| 日期 | 类型 | 主题名称 | 优先级 | 视觉效果 |
|------|------|----------|--------|----------|
| **1月** | | | | |
| 1月1日 | 节日 | 🎊 New Year | 95 | 彩带 + 烟花 |
| 1月第3周一 | 纪念日 | 🦅 MLK Day | 70 | US only |
| 农历正月 | 节日 | 🐲 春节 | 98 | 红色 + 烟花 |
| **2月** | | | | |
| 2月14日 | 节日 | ❤️ Valentine's Day | 60 | 心形动画 |
| **3月** | | | | |
| 3月8日 | 纪念日 | 👩 妇女节 | 75 | 紫色主题 |
| 3月14日 | 伟人 | π Pi Day | 55 | 蓝色科技 |
| **4月** | | | | |
| 4月22日 | 纪念日 | 🌍 地球日 | 80 | 绿色 + 树叶 |
| 4月23日 | 纪念日 | 📚 世界读书日 | 85 | 暖色 + 书本 |
| **5月** | | | | |
| 5月第2周日 | 节日 | 💐 母亲节 | 75 | 粉色 + 花朵 |
| **6月** | | | | |
| 6月第3周日 | 节日 | 👔 父亲节 | 75 | 蓝色稳重 |
| **7月** | | | | |
| 7月20日 | 历史 | 🌙 登月日 | 60 | 星空背景 |
| **9月** | | | | |
| 9月8日 | 纪念日 | ✏️ 扫盲日 | 80 | 教育主题 |
| **10月** | | | | |
| 10月5日 | 纪念日 | 👩‍🏫 教师日 | 85 | 温暖配色 |
| 10月31日 | 节日 | 🎃 万圣节 | 70 | 橙黑 + 蝙蝠 |
| **11月** | | | | |
| 11月第4周四 | 节日 | 🦃 感恩节 | 70 | US only |
| **12月** | | | | |
| 12月20-26日 | 节日 | 🎄 圣诞季 | 95 | 雪花 + 红绿 |

---

## 10. 实施计划

### 10.1 阶段划分

```
Phase 1: 数据库 + 后端 API (P0)
├─ 更新 daily_themes 表结构
├─ 实现 DateMatcher 日期匹配器
├─ 升级 ThemesService
├─ 添加 Admin API
└─ 单元测试

Phase 2: AI 辅助生成 (P0)
├─ AI 主题生成服务
├─ 生成 API 端点
├─ 自动调度任务
└─ 缓存机制

Phase 3: 前端核心组件 (P1)
├─ ThemeProvider 升级
├─ CSS 变量系统
├─ ThemeLogo 组件
├─ ThemeBadge 组件
└─ ThemeDetailModal 组件

Phase 4: 动画效果 (P1)
├─ ThemeAnimationLayer
├─ Snowflakes 动画
├─ Hearts 动画
├─ Confetti 动画
└─ 性能优化

Phase 5: Admin 管理界面 (P2)
├─ 主题列表页
├─ AI 建议审核页
├─ 创建/编辑表单
├─ 日历视图
└─ 预览功能

Phase 6: 内容填充 (P2)
├─ 创建年度主题日历
├─ 配置视觉效果
├─ 多语言支持
└─ 测试验证
```

### 10.2 关键验收标准

| 功能 | 验收标准 |
|------|----------|
| AI 生成 | 能生成 3 个合理的备选方案 |
| 日期匹配 | 固定/动态/农历/范围日期正确 |
| 优先级 | 同日多主题按优先级正确选择 |
| CSS 变量 | 全站颜色正确应用 |
| 动画效果 | 流畅不卡顿 |
| 移动端 | 降级方案正常工作 |
| Admin | AI 建议审核流程顺畅 |

---

## 修订历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-01-06 | 初始版本 |
| v2.0 | 2026-01-12 | 增加全站视觉变化、AI 辅助生成、Campaign 联动、Admin 管理 |

---

**END OF DOCUMENT**
