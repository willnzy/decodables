# Theme 主题系统设计 - Daily Doodle 风格

> **版本**: v1.0  
> **日期**: 2026-01-06  
> **灵感**: Google Doodle - 根据日期自动变化的动态主题

---

## 目录

1. [设计概览](#1-设计概览)
2. [数据结构设计](#2-数据结构设计)
3. [后端实现](#3-后端实现)
4. [前端实现](#4-前端实现)
5. [主题内容规划](#5-主题内容规划)
6. [实施计划](#6-实施计划)

---

## 1. 设计概览

### 1.1 核心理念

```
┌─────────────────────────────────────────────────────────────────┐
│                    Daily Doodle 主题系统                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  "每一天都值得纪念，每一个主题都讲述故事"                          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  类型 1: 固定日期事件                                    │   │
│  │  • 新年 (1月1日)                                         │   │
│  │  • 春节 (农历新年)                                       │   │
│  │  • 教师节 (各国不同)                                     │   │
│  │  • 圣诞节 (12月25日)                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  类型 2: 伟人纪念日                                      │   │
│  │  • 爱因斯坦诞辰 (3月14日)                                │   │
│  │  • 居里夫人诞辰 (11月7日)                                │   │
│  │  • 马丁·路德·金纪念日 (1月第三个周一)                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  类型 3: 世界纪念日                                      │   │
│  │  • 世界读书日 (4月23日)                                  │   │
│  │  • 地球日 (4月22日)                                      │   │
│  │  • 国际妇女节 (3月8日)                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  类型 4: 历史今日                                        │   │
│  │  • 阿波罗11号登月 (7月20日)                              │   │
│  │  • 万维网诞生 (3月12日)                                  │   │
│  │  • 第一张照片 (某日)                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 用户体验流程

```
┌─────────────────────────────────────────────────────────────────┐
│                      用户体验流程                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  用户访问网站                                                    │
│       │                                                         │
│       ▼                                                         │
│  检测用户本地时间 + 时区                                         │
│       │                                                         │
│       ▼                                                         │
│  查询当日主题 (按优先级)                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. 检查是否有该用户时区的节日                           │   │
│  │  2. 检查是否有全球通用的纪念日                           │   │
│  │  3. 检查是否有历史今日事件                               │   │
│  │  4. 使用默认主题                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │                                                         │
│       ▼                                                         │
│  应用主题                                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • Logo 变化 (Doodle 风格)                               │   │
│  │  • 背景色/背景图变化                                     │   │
│  │  • Slogan 显示                                           │   │
│  │  • 可选: 动画效果                                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │                                                         │
│       ▼                                                         │
│  用户点击 Logo/Slogan                                           │
│       │                                                         │
│       ▼                                                         │
│  显示主题详情弹窗 (今日是什么日子?)                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 主题效果示例

```
┌─────────────────────────────────────────────────────────────────┐
│                      主题效果示例                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  默认主题                                                │   │
│  │  Logo: Make Decodables (标准)                           │   │
│  │  Slogan: "Create magical mini-books in 30 seconds"      │   │
│  │  背景: 白色                                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  圣诞节 (12月25日)                                       │   │
│  │  Logo: 🎄 Make Decodables ❄️ (带圣诞装饰)                │   │
│  │  Slogan: "Merry Christmas! Create holiday stories 🎁"   │   │
│  │  背景: 淡红色 + 雪花动画                                  │   │
│  │  动画: 雪花飘落效果                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  世界读书日 (4月23日)                                    │   │
│  │  Logo: 📚 Make Decodables 📖 (书本装饰)                  │   │
│  │  Slogan: "World Book Day - Every child deserves a story"│   │
│  │  背景: 温暖的米色                                        │   │
│  │  动画: 翻书页效果                                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  爱因斯坦诞辰 (3月14日)                                  │   │
│  │  Logo: ⚛️ Make Decodables 🧠 (科学元素)                  │   │
│  │  Slogan: "Happy Birthday Einstein! Imagination > Knowledge"│
│  │  背景: 星空蓝                                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 数据结构设计

### 2.1 数据库表结构

```sql
-- ============================================================
-- 主题定义表
-- ============================================================
CREATE TABLE themes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 基础信息
    key VARCHAR(100) NOT NULL UNIQUE,           -- 唯一标识 (如 christmas_2026)
    name VARCHAR(255) NOT NULL,                 -- 显示名称
    name_i18n JSONB DEFAULT '{}',               -- 多语言名称 {"zh": "圣诞节", "en": "Christmas"}
    
    -- 分类
    category VARCHAR(50) NOT NULL,              -- holiday, memorial, history, special
    
    -- 日期规则
    date_rule JSONB NOT NULL,                   -- 日期规则 (见下方详解)
    
    -- 主题内容
    slogan VARCHAR(500),                        -- 标语
    slogan_i18n JSONB DEFAULT '{}',             -- 多语言标语
    description TEXT,                           -- 详细描述
    description_i18n JSONB DEFAULT '{}',        -- 多语言描述
    
    -- 视觉效果
    logo_variant JSONB,                         -- Logo 变体配置
    colors JSONB NOT NULL,                      -- 颜色配置
    background JSONB,                           -- 背景配置
    animations JSONB DEFAULT '[]',              -- 动画效果列表
    
    -- 适用范围
    regions TEXT[] DEFAULT ARRAY['global'],     -- 适用地区 ['global', 'CN', 'US', ...]
    
    -- 优先级 (同一天多个主题时)
    priority INTEGER DEFAULT 50,                -- 0-100, 越高越优先
    
    -- 状态
    enabled BOOLEAN DEFAULT true,
    archived BOOLEAN DEFAULT false,
    
    -- 元数据
    source_url VARCHAR(500),                    -- 参考来源
    created_by VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 主题资源表 (Logo 变体、背景图等)
-- ============================================================
CREATE TABLE theme_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    theme_id UUID REFERENCES themes(id) ON DELETE CASCADE,
    
    asset_type VARCHAR(50) NOT NULL,            -- logo, background, icon, animation
    file_url VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),                      -- svg, png, lottie, css
    
    -- 变体
    variant VARCHAR(50) DEFAULT 'default',      -- default, dark, mobile
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 主题展示日志 (分析用)
-- ============================================================
CREATE TABLE theme_impressions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    theme_id UUID REFERENCES themes(id),
    theme_key VARCHAR(100) NOT NULL,
    
    user_id VARCHAR(100),
    user_timezone VARCHAR(50),
    user_region VARCHAR(10),
    local_date DATE NOT NULL,
    
    -- 交互
    clicked BOOLEAN DEFAULT false,
    
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_themes_enabled ON themes(enabled) WHERE enabled = true;
CREATE INDEX idx_themes_category ON themes(category);
CREATE INDEX idx_impressions_date ON theme_impressions(local_date);
```

### 2.2 日期规则 (date_rule) 格式

```typescript
// 日期规则类型定义
interface DateRule {
  type: 'fixed' | 'lunar' | 'relative' | 'range';
  
  // 固定日期 (type: 'fixed')
  // 每年的固定日期
  month?: number;      // 1-12
  day?: number;        // 1-31
  
  // 农历日期 (type: 'lunar')
  // 用于春节等农历节日
  lunarMonth?: number;
  lunarDay?: number;
  
  // 相对日期 (type: 'relative')
  // 如: 1月第三个周一 (马丁·路德·金纪念日)
  weekOfMonth?: number;  // 1-5, -1 表示最后一周
  dayOfWeek?: number;    // 0-6, 0=周日
  
  // 日期范围 (type: 'range')
  // 用于持续多天的节日
  startMonth?: number;
  startDay?: number;
  endMonth?: number;
  endDay?: number;
  
  // 可选: 特定年份
  years?: number[];     // 仅在特定年份生效
  excludeYears?: number[]; // 排除特定年份
}

// 示例
const examples = {
  // 圣诞节: 每年12月25日
  christmas: {
    type: 'fixed',
    month: 12,
    day: 25
  },
  
  // 春节: 农历正月初一
  chineseNewYear: {
    type: 'lunar',
    lunarMonth: 1,
    lunarDay: 1
  },
  
  // 马丁·路德·金纪念日: 1月第三个周一
  mlkDay: {
    type: 'relative',
    month: 1,
    weekOfMonth: 3,
    dayOfWeek: 1  // 周一
  },
  
  // 感恩节: 11月第四个周四
  thanksgiving: {
    type: 'relative',
    month: 11,
    weekOfMonth: 4,
    dayOfWeek: 4  // 周四
  },
  
  // 圣诞季: 12月20日-26日
  christmasSeason: {
    type: 'range',
    startMonth: 12,
    startDay: 20,
    endMonth: 12,
    endDay: 26
  }
};
```

### 2.3 颜色配置 (colors) 格式

```typescript
interface ThemeColors {
  // 主色调
  primary: string;
  primaryHover: string;
  primaryLight: string;
  
  // 背景色
  background: string;
  backgroundSecondary: string;
  
  // 文字色
  text: string;
  textSecondary: string;
  
  // 强调色
  accent: string;
  
  // 可选: 覆盖特定组件
  overrides?: {
    navbar?: { background: string; text: string };
    footer?: { background: string; text: string };
    button?: { background: string; text: string };
  };
}

// 示例: 圣诞主题
const christmasColors: ThemeColors = {
  primary: '#C41E3A',      // 圣诞红
  primaryHover: '#A01830',
  primaryLight: '#FFE4E8',
  
  background: '#FFF9F9',   // 淡红白
  backgroundSecondary: '#FFE4E8',
  
  text: '#2D3748',
  textSecondary: '#718096',
  
  accent: '#165B33',       // 圣诞绿
  
  overrides: {
    navbar: {
      background: '#165B33',
      text: '#FFFFFF'
    }
  }
};
```

### 2.4 Logo 变体 (logo_variant) 格式

```typescript
interface LogoVariant {
  // 类型
  type: 'decorated' | 'replaced' | 'animated';
  
  // 装饰模式 (在原 Logo 基础上添加装饰)
  decorations?: {
    prefix?: string;    // Logo 前缀 (如 emoji)
    suffix?: string;    // Logo 后缀
    overlay?: string;   // 叠加图层 URL
  };
  
  // 替换模式 (使用自定义 Logo)
  customLogo?: {
    url: string;
    width?: number;
    height?: number;
  };
  
  // 动画模式
  animation?: {
    type: 'bounce' | 'shake' | 'glow' | 'custom';
    duration?: number;
    customCss?: string;
  };
}

// 示例
const christmasLogo: LogoVariant = {
  type: 'decorated',
  decorations: {
    prefix: '🎄',
    suffix: '❄️'
  },
  animation: {
    type: 'glow',
    duration: 2000
  }
};
```

### 2.5 背景配置 (background) 格式

```typescript
interface ThemeBackground {
  // 背景类型
  type: 'solid' | 'gradient' | 'image' | 'pattern';
  
  // 纯色
  color?: string;
  
  // 渐变
  gradient?: {
    type: 'linear' | 'radial';
    angle?: number;
    colors: string[];
  };
  
  // 图片
  image?: {
    url: string;
    position?: string;
    size?: string;
    repeat?: string;
    opacity?: number;
  };
  
  // 图案
  pattern?: {
    url: string;
    scale?: number;
  };
}
```

### 2.6 动画效果 (animations) 格式

```typescript
interface ThemeAnimation {
  id: string;
  type: 'snowfall' | 'confetti' | 'fireworks' | 'particles' | 'custom';
  
  // 通用配置
  enabled: boolean;
  intensity?: number;       // 0-100
  duration?: number;        // 持续时间 (ms), 0=无限
  
  // 粒子配置 (snowfall, confetti, particles)
  particles?: {
    count: number;
    color: string | string[];
    size: { min: number; max: number };
    speed: { min: number; max: number };
  };
  
  // 自定义动画
  customCss?: string;
  customJs?: string;        // 仅限受信任的预定义动画
}

// 示例: 雪花效果
const snowfallAnimation: ThemeAnimation = {
  id: 'christmas_snow',
  type: 'snowfall',
  enabled: true,
  intensity: 50,
  particles: {
    count: 50,
    color: '#FFFFFF',
    size: { min: 5, max: 15 },
    speed: { min: 1, max: 3 }
  }
};
```

---

## 3. 后端实现

### 3.1 目录结构

```
core/theme/
├── __init__.py
├── types.py                    # 类型定义 (<150 行)
├── date_matcher.py             # 日期匹配器 (<200 行)
├── service.py                  # 主题服务 (<200 行)
├── repository.py               # 仓储接口 (<80 行)
└── lunar_calendar.py           # 农历转换 (<150 行)

infrastructure/repositories/
└── supabase_theme_repo.py      # 仓储实现 (<200 行)

api/routers/
└── themes.py                   # API 路由 (<150 行)
```

### 3.2 日期匹配器

```python
# core/theme/date_matcher.py

from datetime import date, datetime
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum

from .lunar_calendar import lunar_to_solar


class DateRuleType(Enum):
    FIXED = "fixed"
    LUNAR = "lunar"
    RELATIVE = "relative"
    RANGE = "range"


@dataclass
class DateRule:
    type: DateRuleType
    month: Optional[int] = None
    day: Optional[int] = None
    lunar_month: Optional[int] = None
    lunar_day: Optional[int] = None
    week_of_month: Optional[int] = None
    day_of_week: Optional[int] = None
    start_month: Optional[int] = None
    start_day: Optional[int] = None
    end_month: Optional[int] = None
    end_day: Optional[int] = None
    years: Optional[List[int]] = None
    exclude_years: Optional[List[int]] = None


class DateMatcher:
    """日期匹配器 - 判断某个日期是否匹配规则"""
    
    def matches(self, rule: DateRule, target_date: date) -> bool:
        """检查目标日期是否匹配规则"""
        
        # 检查年份限制
        if rule.years and target_date.year not in rule.years:
            return False
        if rule.exclude_years and target_date.year in rule.exclude_years:
            return False
        
        if rule.type == DateRuleType.FIXED:
            return self._match_fixed(rule, target_date)
        elif rule.type == DateRuleType.LUNAR:
            return self._match_lunar(rule, target_date)
        elif rule.type == DateRuleType.RELATIVE:
            return self._match_relative(rule, target_date)
        elif rule.type == DateRuleType.RANGE:
            return self._match_range(rule, target_date)
        
        return False
    
    def _match_fixed(self, rule: DateRule, target_date: date) -> bool:
        """固定日期匹配"""
        return target_date.month == rule.month and target_date.day == rule.day
    
    def _match_lunar(self, rule: DateRule, target_date: date) -> bool:
        """农历日期匹配"""
        # 将农历转换为公历
        solar_date = lunar_to_solar(
            target_date.year,
            rule.lunar_month,
            rule.lunar_day
        )
        return target_date == solar_date
    
    def _match_relative(self, rule: DateRule, target_date: date) -> bool:
        """相对日期匹配 (如: 第三个周一)"""
        if target_date.month != rule.month:
            return False
        
        if target_date.weekday() != rule.day_of_week:
            return False
        
        # 计算是第几周
        day = target_date.day
        week = (day - 1) // 7 + 1
        
        if rule.week_of_month == -1:
            # 最后一周
            next_week_day = day + 7
            if next_week_day > self._days_in_month(target_date.year, target_date.month):
                return True
        else:
            return week == rule.week_of_month
        
        return False
    
    def _match_range(self, rule: DateRule, target_date: date) -> bool:
        """日期范围匹配"""
        start = date(target_date.year, rule.start_month, rule.start_day)
        end = date(target_date.year, rule.end_month, rule.end_day)
        
        # 处理跨年情况 (如 12月-1月)
        if end < start:
            return target_date >= start or target_date <= end
        
        return start <= target_date <= end
    
    def _days_in_month(self, year: int, month: int) -> int:
        """获取某月的天数"""
        if month in [1, 3, 5, 7, 8, 10, 12]:
            return 31
        elif month in [4, 6, 9, 11]:
            return 30
        elif month == 2:
            if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
                return 29
            return 28
```

### 3.3 主题服务

```python
# core/theme/service.py

from datetime import date, datetime
from typing import Optional, List
from dataclasses import dataclass

from .types import Theme, ThemeColors, ThemeBackground
from .date_matcher import DateMatcher, DateRule
from .repository import IThemeRepository
from core.cache import cache_service


@dataclass
class ResolvedTheme:
    """解析后的主题 (用于前端)"""
    key: str
    name: str
    slogan: str
    description: Optional[str]
    colors: ThemeColors
    logo_variant: Optional[dict]
    background: Optional[ThemeBackground]
    animations: List[dict]
    is_default: bool = False


class ThemeService:
    """主题服务"""
    
    CACHE_TTL = 3600  # 1 小时缓存
    DEFAULT_THEME_KEY = "default"
    
    def __init__(self, repository: IThemeRepository):
        self._repository = repository
        self._matcher = DateMatcher()
    
    async def get_theme_for_date(
        self,
        target_date: date,
        user_timezone: str = "UTC",
        user_region: str = "global",
        locale: str = "en"
    ) -> ResolvedTheme:
        """
        获取指定日期的主题
        
        Args:
            target_date: 目标日期 (用户本地日期)
            user_timezone: 用户时区
            user_region: 用户地区 (用于地区特定节日)
            locale: 语言偏好
        
        Returns:
            ResolvedTheme: 解析后的主题
        """
        cache_key = f"theme:{target_date}:{user_region}:{locale}"
        
        # 尝试从缓存获取
        cached = await cache_service.get(cache_key)
        if cached:
            return ResolvedTheme(**cached)
        
        # 获取所有启用的主题
        themes = await self._repository.get_enabled_themes()
        
        # 筛选匹配的主题
        matching_themes = []
        for theme in themes:
            # 检查地区
            if not self._region_matches(theme.regions, user_region):
                continue
            
            # 检查日期
            rule = DateRule(**theme.date_rule)
            if self._matcher.matches(rule, target_date):
                matching_themes.append(theme)
        
        # 按优先级排序
        matching_themes.sort(key=lambda t: t.priority, reverse=True)
        
        # 选择最高优先级的主题
        if matching_themes:
            theme = matching_themes[0]
            resolved = self._resolve_theme(theme, locale)
        else:
            # 使用默认主题
            default_theme = await self._repository.get_by_key(self.DEFAULT_THEME_KEY)
            resolved = self._resolve_theme(default_theme, locale)
            resolved.is_default = True
        
        # 缓存
        await cache_service.set(cache_key, resolved.__dict__, self.CACHE_TTL)
        
        return resolved
    
    def _region_matches(self, theme_regions: List[str], user_region: str) -> bool:
        """检查地区是否匹配"""
        if "global" in theme_regions:
            return True
        return user_region in theme_regions
    
    def _resolve_theme(self, theme: Theme, locale: str) -> ResolvedTheme:
        """解析主题 (处理多语言)"""
        return ResolvedTheme(
            key=theme.key,
            name=theme.name_i18n.get(locale, theme.name),
            slogan=theme.slogan_i18n.get(locale, theme.slogan or ""),
            description=theme.description_i18n.get(locale, theme.description),
            colors=ThemeColors(**theme.colors),
            logo_variant=theme.logo_variant,
            background=ThemeBackground(**theme.background) if theme.background else None,
            animations=theme.animations or [],
        )
    
    async def get_upcoming_themes(
        self,
        start_date: date,
        days: int = 30,
        user_region: str = "global"
    ) -> List[dict]:
        """获取未来几天的主题预览"""
        themes = await self._repository.get_enabled_themes()
        upcoming = []
        
        for i in range(days):
            check_date = date(
                start_date.year,
                start_date.month,
                start_date.day
            )
            check_date = check_date.replace(day=start_date.day + i)
            
            for theme in themes:
                if not self._region_matches(theme.regions, user_region):
                    continue
                
                rule = DateRule(**theme.date_rule)
                if self._matcher.matches(rule, check_date):
                    upcoming.append({
                        "date": check_date.isoformat(),
                        "theme_key": theme.key,
                        "theme_name": theme.name,
                    })
        
        return upcoming
```

### 3.4 API 路由

```python
# api/routers/themes.py

from fastapi import APIRouter, Query
from datetime import date, datetime
from typing import Optional

from core.theme.service import ThemeService
from dependencies import get_theme_service

router = APIRouter(prefix="/api/themes", tags=["Themes"])


@router.get("/current")
async def get_current_theme(
    timezone: str = Query("UTC", description="用户时区"),
    region: str = Query("global", description="用户地区"),
    locale: str = Query("en", description="语言"),
    theme_service: ThemeService = Depends(get_theme_service)
):
    """
    获取当前主题
    
    根据用户的本地时间、地区返回适合的主题
    """
    # 计算用户本地日期
    from datetime import timezone as tz
    import pytz
    
    user_tz = pytz.timezone(timezone)
    user_now = datetime.now(user_tz)
    user_date = user_now.date()
    
    theme = await theme_service.get_theme_for_date(
        target_date=user_date,
        user_timezone=timezone,
        user_region=region,
        locale=locale
    )
    
    return {
        "theme": theme.__dict__,
        "user_date": user_date.isoformat(),
        "user_timezone": timezone,
    }


@router.get("/upcoming")
async def get_upcoming_themes(
    days: int = Query(30, ge=1, le=365),
    region: str = Query("global"),
    theme_service: ThemeService = Depends(get_theme_service)
):
    """获取未来的主题预览"""
    today = date.today()
    upcoming = await theme_service.get_upcoming_themes(today, days, region)
    return {"upcoming": upcoming}


@router.get("/{theme_key}")
async def get_theme_detail(
    theme_key: str,
    locale: str = Query("en"),
    theme_service: ThemeService = Depends(get_theme_service)
):
    """获取主题详情"""
    theme = await theme_service.get_theme_by_key(theme_key, locale)
    return {"theme": theme}
```

---

## 4. 前端实现

### 4.1 目录结构

```
@core/theme/
├── index.ts                    # 导出
├── types.ts                    # 类型定义 (<150 行)
├── context.tsx                 # ThemeProvider (<250 行)
├── hooks.ts                    # Hooks (<100 行)
├── components/
│   ├── ThemeLogo.tsx          # 主题 Logo (<150 行)
│   ├── ThemeSlogan.tsx        # 主题标语 (<80 行)
│   ├── ThemeBackground.tsx    # 背景效果 (<100 行)
│   ├── ThemeAnimations.tsx    # 动画效果 (<200 行)
│   └── ThemeDetailModal.tsx   # 详情弹窗 (<150 行)
├── animations/
│   ├── Snowfall.tsx           # 雪花动画 (<100 行)
│   ├── Confetti.tsx           # 彩带动画 (<100 行)
│   └── Particles.tsx          # 粒子动画 (<100 行)
└── utils.ts                    # 工具函数 (<80 行)
```

### 4.2 ThemeProvider

```typescript
// @core/theme/context.tsx

"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useMemo,
  useCallback,
} from 'react';

import { ResolvedTheme, ThemeColors } from './types';
import { applyThemeToDOM, getUserTimezone, getUserRegion } from './utils';

interface ThemeContextType {
  theme: ResolvedTheme | null;
  isLoading: boolean;
  isDefault: boolean;
  showDetailModal: () => void;
  refresh: () => Promise<void>;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const DEFAULT_THEME: ResolvedTheme = {
  key: 'default',
  name: 'Make Decodables',
  slogan: 'Create magical mini-books in 30 seconds',
  description: null,
  colors: {
    primary: '#4F46E5',
    primaryHover: '#4338CA',
    primaryLight: '#EEF2FF',
    background: '#FFFFFF',
    backgroundSecondary: '#F8FAFC',
    text: '#1E293B',
    textSecondary: '#64748B',
    accent: '#4F46E5',
  },
  logo_variant: null,
  background: null,
  animations: [],
  is_default: true,
};

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<ResolvedTheme | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  
  const fetchTheme = useCallback(async () => {
    setIsLoading(true);
    try {
      const timezone = getUserTimezone();
      const region = getUserRegion();
      const locale = navigator.language.split('-')[0] || 'en';
      
      const response = await fetch(
        `/api/themes/current?timezone=${encodeURIComponent(timezone)}&region=${region}&locale=${locale}`
      );
      
      if (response.ok) {
        const data = await response.json();
        setTheme(data.theme);
        applyThemeToDOM(data.theme.colors);
      } else {
        setTheme(DEFAULT_THEME);
        applyThemeToDOM(DEFAULT_THEME.colors);
      }
    } catch (error) {
      console.error('Failed to fetch theme:', error);
      setTheme(DEFAULT_THEME);
      applyThemeToDOM(DEFAULT_THEME.colors);
    } finally {
      setIsLoading(false);
    }
  }, []);
  
  useEffect(() => {
    fetchTheme();
    
    // 每小时检查一次 (处理跨天)
    const interval = setInterval(fetchTheme, 3600000);
    return () => clearInterval(interval);
  }, [fetchTheme]);
  
  const value = useMemo<ThemeContextType>(() => ({
    theme,
    isLoading,
    isDefault: theme?.is_default ?? true,
    showDetailModal: () => setShowModal(true),
    refresh: fetchTheme,
  }), [theme, isLoading, fetchTheme]);
  
  return (
    <ThemeContext.Provider value={value}>
      {children}
      {showModal && theme && !theme.is_default && (
        <ThemeDetailModal
          theme={theme}
          onClose={() => setShowModal(false)}
        />
      )}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}
```

### 4.3 主题 Logo 组件

```typescript
// @core/theme/components/ThemeLogo.tsx

"use client";

import React from 'react';
import { useTheme } from '../context';
import { cn } from '@core/utils';

interface ThemeLogoProps {
  className?: string;
  onClick?: () => void;
}

export function ThemeLogo({ className, onClick }: ThemeLogoProps) {
  const { theme, isDefault, showDetailModal } = useTheme();
  
  if (!theme) return null;
  
  const logoVariant = theme.logo_variant;
  const hasVariant = logoVariant && !isDefault;
  
  const handleClick = () => {
    if (hasVariant) {
      showDetailModal();
    }
    onClick?.();
  };
  
  // 动画类
  const animationClass = hasVariant && logoVariant.animation
    ? getAnimationClass(logoVariant.animation.type)
    : '';
  
  return (
    <div
      className={cn(
        "flex items-center gap-1 cursor-pointer transition-transform hover:scale-105",
        hasVariant && "cursor-pointer",
        animationClass,
        className
      )}
      onClick={handleClick}
      title={hasVariant ? "Click to learn more about today" : undefined}
    >
      {/* 前缀装饰 */}
      {hasVariant && logoVariant.decorations?.prefix && (
        <span className="text-2xl">{logoVariant.decorations.prefix}</span>
      )}
      
      {/* Logo */}
      {hasVariant && logoVariant.customLogo ? (
        <img
          src={logoVariant.customLogo.url}
          alt="Make Decodables"
          width={logoVariant.customLogo.width || 150}
          height={logoVariant.customLogo.height || 40}
        />
      ) : (
        <span className="font-bold text-xl text-primary">
          Make Decodables
        </span>
      )}
      
      {/* 后缀装饰 */}
      {hasVariant && logoVariant.decorations?.suffix && (
        <span className="text-2xl">{logoVariant.decorations.suffix}</span>
      )}
    </div>
  );
}

function getAnimationClass(type: string): string {
  const animations: Record<string, string> = {
    bounce: 'animate-bounce',
    shake: 'animate-pulse',
    glow: 'animate-glow',
  };
  return animations[type] || '';
}
```

### 4.4 雪花动画组件

```typescript
// @core/theme/animations/Snowfall.tsx

"use client";

import React, { useEffect, useRef } from 'react';

interface SnowfallProps {
  intensity?: number;  // 0-100
  particleCount?: number;
  colors?: string[];
}

export function Snowfall({
  intensity = 50,
  particleCount = 50,
  colors = ['#FFFFFF', '#E8E8E8'],
}: SnowfallProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // 设置画布大小
    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    
    // 创建雪花
    const actualCount = Math.floor(particleCount * (intensity / 100));
    const snowflakes = Array.from({ length: actualCount }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      radius: Math.random() * 3 + 2,
      speed: Math.random() * 2 + 1,
      wind: Math.random() * 0.5 - 0.25,
      color: colors[Math.floor(Math.random() * colors.length)],
    }));
    
    // 动画循环
    let animationId: number;
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      snowflakes.forEach(flake => {
        // 绘制雪花
        ctx.beginPath();
        ctx.arc(flake.x, flake.y, flake.radius, 0, Math.PI * 2);
        ctx.fillStyle = flake.color;
        ctx.fill();
        
        // 更新位置
        flake.y += flake.speed;
        flake.x += flake.wind;
        
        // 重置到顶部
        if (flake.y > canvas.height) {
          flake.y = -flake.radius;
          flake.x = Math.random() * canvas.width;
        }
        
        // 水平循环
        if (flake.x > canvas.width) flake.x = 0;
        if (flake.x < 0) flake.x = canvas.width;
      });
      
      animationId = requestAnimationFrame(animate);
    };
    
    animate();
    
    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', resizeCanvas);
    };
  }, [intensity, particleCount, colors]);
  
  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none z-50"
      style={{ opacity: 0.8 }}
    />
  );
}
```

---

## 5. 主题内容规划

### 5.1 年度主题日历

| 日期 | 类型 | 主题名称 | 优先级 |
|------|------|----------|--------|
| **1月** | | | |
| 1月1日 | 节日 | 新年 New Year | 90 |
| 1月第3周一 | 纪念日 | 马丁·路德·金日 | 70 |
| 农历正月初一 | 节日 | 春节 Chinese New Year | 95 |
| **2月** | | | |
| 2月14日 | 节日 | 情人节 Valentine's Day | 60 |
| **3月** | | | |
| 3月8日 | 纪念日 | 国际妇女节 | 75 |
| 3月12日 | 历史 | 万维网诞生 (1989) | 50 |
| 3月14日 | 伟人 | 爱因斯坦诞辰 / Pi Day | 70 |
| **4月** | | | |
| 4月22日 | 纪念日 | 地球日 Earth Day | 80 |
| 4月23日 | 纪念日 | 世界读书日 | 85 |
| **5月** | | | |
| 5月第2周日 | 节日 | 母亲节 | 75 |
| **6月** | | | |
| 6月第3周日 | 节日 | 父亲节 | 75 |
| **7月** | | | |
| 7月20日 | 历史 | 阿波罗11号登月 (1969) | 60 |
| **8月** | | | |
| - | - | - | - |
| **9月** | | | |
| 9月8日 | 纪念日 | 国际扫盲日 | 80 |
| **10月** | | | |
| 10月5日 | 纪念日 | 世界教师日 | 85 |
| 10月31日 | 节日 | 万圣节 Halloween | 70 |
| **11月** | | | |
| 11月7日 | 伟人 | 居里夫人诞辰 | 60 |
| 11月第4周四 | 节日 | 感恩节 (US) | 70 |
| **12月** | | | |
| 12月20-26日 | 节日 | 圣诞季 Christmas | 90 |

### 5.2 伟人纪念日列表

| 日期 | 人物 | Slogan 示例 |
|------|------|-------------|
| 1月15日 | 马丁·路德·金 | "I have a dream..." |
| 3月14日 | 爱因斯坦 | "Imagination is more important than knowledge" |
| 4月15日 | 达·芬奇 | "Learning never exhausts the mind" |
| 7月18日 | 曼德拉 | "Education is the most powerful weapon" |
| 11月7日 | 居里夫人 | "Nothing in life is to be feared, only understood" |
| 12月5日 | 沃尔特·迪士尼 | "All our dreams can come true..." |

### 5.3 世界纪念日列表

| 日期 | 纪念日 | Slogan 示例 |
|------|--------|-------------|
| 2月21日 | 国际母语日 | "Every language tells a story" |
| 3月8日 | 国际妇女节 | "Empowering women, empowering the world" |
| 4月22日 | 世界地球日 | "There is no Planet B" |
| 4月23日 | 世界读书日 | "A book is a dream you hold in your hand" |
| 5月15日 | 国际家庭日 | "Family: Where life begins and love never ends" |
| 9月8日 | 国际扫盲日 | "Literacy lights up life" |
| 10月5日 | 世界教师日 | "Teachers: Lighting the way to the future" |
| 11月20日 | 世界儿童日 | "Every child deserves a childhood" |

---

## 6. 实施计划

### 6.1 阶段划分

```
Phase 1: 基础设施 (3 天)
├─ 数据库表创建
├─ 后端服务实现
├─ API 路由
└─ 前端 ThemeProvider

Phase 2: 核心功能 (3 天)
├─ 日期匹配器 (含农历)
├─ Logo 组件
├─ 背景效果
└─ Slogan 显示

Phase 3: 动画效果 (2 天)
├─ 雪花动画
├─ 彩带动画
├─ 粒子效果
└─ 详情弹窗

Phase 4: 内容填充 (2 天)
├─ 默认主题
├─ 主要节日主题 (5-10个)
├─ 测试验证
└─ 文档

总计: ~10 天
```

### 6.2 检查清单

| 任务 | 验收标准 |
|------|----------|
| 日期匹配 | 固定/农历/相对日期正确 |
| 时区处理 | 用户本地时间正确 |
| Logo 变化 | 装饰/替换/动画正常 |
| 背景效果 | 颜色/渐变/图片正常 |
| 动画效果 | 雪花/彩带流畅 |
| 多语言 | 中英文切换正常 |
| 详情弹窗 | 点击显示正常 |
| 缓存 | 1小时缓存有效 |

---

**主题系统设计完成！接下来我会继续设计 Onboarding 和 Editor Media Library。**
