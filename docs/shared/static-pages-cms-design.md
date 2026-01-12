# 静态页面 CMS 系统设计

> **状态**: 📋 设计中
> **版本**: 0.2.0
> **创建日期**: 2026-01-12
> **最后更新**: 2026-01-12
> **关联文档**: [pricing-system-design.md](pricing-system-design.md) (Config 系统)

---

## 1. 概述

### 1.1 需求背景

静态法律/政策页面 (About Us, Contact Us, Privacy Policy, Terms of Service, Billing Policy, Marketplace Guidelines) 目前内容硬编码在前端代码中，每次修改需要重新部署。

**目标**:
1. 页面内容可通过后台 Admin 配置
2. 支持参数引用 (如 `{{company_email}}`), 避免硬编码
3. 页面结构 (布局、样式) 保持代码控制，仅内容动态化

### 1.2 涉及页面

#### 页面类型分类

| 类型 | 说明 | CMS 范围 |
|------|------|----------|
| **Static** (纯静态) | 纯内容展示，无交互逻辑 | 全部内容可 CMS 配置 |
| **Hybrid** (混合型) | 内容展示 + 动态功能 | 静态部分 CMS 配置，动态功能代码控制 |

#### 页面清单

| 页面 | 路由 | 类型 | 内容类型 | CMS 说明 |
|------|------|------|----------|----------|
| About Us | `/about-us` | **Static** | 公司介绍、愿景、特色 | 全部区块可配置 |
| Privacy Policy | `/privacy-policy` | **Static** | 隐私条款 (14 章节) | 全部章节可配置 |
| Terms of Service | `/term-of-service` | **Static** | 服务条款 (18 章节) | 全部章节可配置 |
| Billing Policy | `/billing-policy` | **Static** | 计费政策、订阅规则 | 全部区块可配置 |
| Marketplace Guidelines | `/marketplace-guidelines` | **Static** | 发布规则 (8 章节) | 全部章节可配置 |
| Contact Us | `/contact-us` | **Hybrid** | 联系方式 + 表单 | Hero/联系信息/FAQ 可配置，**表单逻辑代码控制** |

#### Hybrid 页面详细说明

**Contact Us** 页面包含两部分:

| 部分 | 类型 | CMS 配置 | 说明 |
|------|------|----------|------|
| Hero 区块 | 静态内容 | ✅ 可配置 | 标题、描述文案 |
| 联系方式卡片 | 静态内容 | ✅ 可配置 | Email、WhatsApp、社交链接 |
| FAQ 区块 | 静态内容 | ✅ 可配置 | 问答列表 |
| **联系表单** | **动态功能** | ❌ 代码控制 | 表单字段、验证、提交逻辑、API 调用 |

> **设计原则**: 混合型页面的静态内容部分通过 CMS 配置，动态功能部分（表单、状态管理、API 调用）保持代码控制，确保功能稳定性。

### 1.3 设计原则

```
页面结构 (React 组件) = 代码控制 (需重构才改)
页面内容 (文字/链接) = 后台配置 (Admin 可改)
动态参数 (邮箱/电话) = 参数引用 (全局变量)
```

---

## 2. 架构设计

### 2.1 数据存储

**复用现有 Config 系统** (system_configs 表)，新增 `page_content` 配置类型:

```sql
-- 已存在于 migrations/v2/02_platform_services.sql
CREATE TABLE system_configs (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 配置 Key 命名规范

```
PAGE_{PAGE_NAME}_{SECTION}_{FIELD}
```

**示例**:
| Key | 用途 |
|-----|------|
| `PAGE_ABOUT_US_HERO_TITLE` | About Us 页面 Hero 区块标题 |
| `PAGE_ABOUT_US_HERO_DESCRIPTION` | About Us 页面 Hero 区块描述 |
| `PAGE_ABOUT_US_MISSION_TITLE` | About Us 页面 Mission 区块标题 |
| `PAGE_PRIVACY_SECTION_1_TITLE` | Privacy Policy 第 1 章节标题 |
| `PAGE_PRIVACY_SECTION_1_CONTENT` | Privacy Policy 第 1 章节内容 (Markdown) |

### 2.3 参数引用系统

支持在内容中使用 `{{param_name}}` 语法引用全局参数：

**全局参数 (存储在 Config)**:
| Key | Value | 用途 |
|-----|-------|------|
| `GLOBAL_COMPANY_NAME` | "Make Decodables" | 公司名称 |
| `GLOBAL_COMPANY_EMAIL` | "info@makedecodables.com" | 公司邮箱 |
| `GLOBAL_COMPANY_WHATSAPP` | "+1 (725) 290 0525" | WhatsApp |
| `GLOBAL_COMPANY_ADDRESS` | "..." | 公司地址 |
| `GLOBAL_SUPPORT_EMAIL` | "support@makedecodables.com" | 客服邮箱 |
| `GLOBAL_LAST_UPDATED_PRIVACY` | "January 3, 2025" | 隐私政策更新日期 |
| `GLOBAL_LAST_UPDATED_TERMS` | "January 3, 2025" | 服务条款更新日期 |
| `GLOBAL_LAST_UPDATED_BILLING` | "December 30, 2024" | 计费政策更新日期 |

**内容示例**:
```
如有疑问，请通过 {{GLOBAL_COMPANY_EMAIL}} 联系我们，
或拨打 WhatsApp: {{GLOBAL_COMPANY_WHATSAPP}}。
```

**渲染结果**:
```
如有疑问，请通过 info@makedecodables.com 联系我们，
或拨打 WhatsApp: +1 (725) 290 0525。
```

---

## 3. 数据结构

### 3.1 页面区块配置

每个页面由多个区块 (Section) 组成，每个区块存储为一条 Config:

```typescript
// 单个区块配置 (value 字段的 JSON 结构)
interface PageSectionConfig {
  // 基础信息
  title?: string;           // 区块标题
  subtitle?: string;        // 副标题
  description?: string;     // 描述文本
  content?: string;         // Markdown 内容 (适用于长文本)

  // 可选字段
  items?: SectionItem[];    // 列表项 (如 FAQ、功能列表)
  cta?: CTAConfig;          // 行动号召按钮
  image?: string;           // 图片 URL
  lastUpdated?: string;     // 更新日期

  // 元信息
  enabled?: boolean;        // 是否启用 (默认 true)
  order?: number;           // 排序权重
}

interface SectionItem {
  title: string;
  description?: string;
  icon?: string;            // Lucide 图标名
  link?: string;            // 链接 URL
}

interface CTAConfig {
  text: string;
  href: string;
  variant?: 'primary' | 'secondary' | 'outline';
}
```

### 3.2 配置示例

#### About Us 页面配置

```json
// Key: PAGE_ABOUT_US_HERO
{
  "title": "About {{GLOBAL_COMPANY_NAME}}",
  "subtitle": "Our Mission",
  "description": "We're on a mission to empower educators and parents to create beautiful, personalized reading materials for children.",
  "enabled": true
}

// Key: PAGE_ABOUT_US_FEATURES
{
  "title": "Why Choose Us",
  "items": [
    {
      "title": "Easy to Use",
      "description": "Create professional mini-books in minutes with our intuitive drag-and-drop editor.",
      "icon": "Sparkles"
    },
    {
      "title": "AI-Powered",
      "description": "Generate beautiful illustrations instantly with our advanced AI technology.",
      "icon": "Wand2"
    },
    {
      "title": "Print Ready",
      "description": "Export high-quality PDFs ready for home or professional printing.",
      "icon": "Download"
    },
    {
      "title": "Affordable",
      "description": "Flexible pricing plans designed for educators and families.",
      "icon": "Coins"
    }
  ],
  "enabled": true
}

// Key: PAGE_ABOUT_US_CTA
{
  "title": "Ready to Create?",
  "description": "Join thousands of educators creating engaging reading materials.",
  "cta": {
    "text": "Start Creating Now",
    "href": "/dashboard",
    "variant": "primary"
  },
  "enabled": true
}
```

#### Privacy Policy 章节配置

```json
// Key: PAGE_PRIVACY_SECTION_1
{
  "title": "1. Information We Collect",
  "content": "## Information We Collect\n\nWe collect information you provide directly:\n\n- **Account Information**: Name, email, password when you create an account\n- **Payment Information**: Processed securely through Stripe\n- **Content**: Projects, images, and text you create\n\nWe automatically collect:\n\n- **Usage Data**: Pages visited, features used, time spent\n- **Device Information**: Browser type, IP address, device type\n\nFor questions, contact {{GLOBAL_COMPANY_EMAIL}}.",
  "order": 1,
  "enabled": true
}
```

---

## 4. API 设计

### 4.1 Public API (用户端)

复用现有 Config API，新增页面内容获取端点:

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v2/user/pages/{page_name}` | 获取页面所有区块 |
| GET | `/api/v2/user/pages/{page_name}/{section}` | 获取单个区块 |

#### GET `/pages/{page_name}`

**示例**: `GET /api/v2/user/pages/about-us`

**响应**:
```json
{
  "page": "about-us",
  "sections": {
    "hero": {
      "title": "About Make Decodables",
      "subtitle": "Our Mission",
      "description": "We're on a mission to empower educators...",
      "enabled": true
    },
    "features": {
      "title": "Why Choose Us",
      "items": [...],
      "enabled": true
    },
    "cta": {
      "title": "Ready to Create?",
      "description": "...",
      "cta": {...},
      "enabled": true
    }
  },
  "globals": {
    "company_name": "Make Decodables",
    "company_email": "info@makedecodables.com",
    "company_whatsapp": "+1 (725) 290 0525"
  },
  "lastUpdated": "2026-01-12T10:00:00Z"
}
```

**注意**:
- 参数引用 (`{{...}}`) 在后端已替换为实际值
- 只返回 `enabled: true` 的区块
- 缓存: 60 秒 (页面内容不频繁变化)

### 4.2 Admin API (管理端)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v2/admin/pages` | 列出所有可配置页面 |
| GET | `/api/v2/admin/pages/{page_name}` | 获取页面所有区块 (含未启用) |
| PUT | `/api/v2/admin/pages/{page_name}/{section}` | 更新单个区块 |
| POST | `/api/v2/admin/pages/{page_name}/preview` | 预览页面 (含参数替换) |

---

## 5. 前端集成

### 5.1 数据获取策略

```typescript
// hooks/usePageContent.ts

interface UsePageContentOptions {
  fallbackToLocal?: boolean;  // API 失败时回退本地数据
}

export function usePageContent<T>(
  pageName: string,
  options: UsePageContentOptions = { fallbackToLocal: true }
) {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    async function fetchContent() {
      try {
        const res = await fetch(`/api/v2/user/pages/${pageName}`);
        if (!res.ok) throw new Error('Failed to fetch page content');
        const json = await res.json();
        setData(json);
      } catch (err) {
        setError(err as Error);
        if (options.fallbackToLocal) {
          // 回退到本地硬编码数据
          const localData = await import(`@/data/pages/${pageName}`);
          setData(localData.default);
        }
      } finally {
        setIsLoading(false);
      }
    }
    fetchContent();
  }, [pageName]);

  return { data, isLoading, error };
}
```

### 5.2 组件使用示例

```tsx
// app/about-us/page.tsx
'use client';

import { usePageContent } from '@/hooks/usePageContent';
import { AboutUsPageContent } from '@/types/pages';

export default function AboutUsPage() {
  const { data, isLoading } = usePageContent<AboutUsPageContent>('about-us');

  if (isLoading) return <PageSkeleton />;

  const { sections, globals } = data;

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />

      {/* Hero - 结构固定，内容动态 */}
      {sections.hero.enabled && (
        <HeroSection
          title={sections.hero.title}
          subtitle={sections.hero.subtitle}
          description={sections.hero.description}
        />
      )}

      {/* Features - 结构固定，内容动态 */}
      {sections.features.enabled && (
        <FeaturesSection items={sections.features.items} />
      )}

      {/* CTA - 结构固定，内容动态 */}
      {sections.cta.enabled && (
        <CTASection
          title={sections.cta.title}
          description={sections.cta.description}
          cta={sections.cta.cta}
        />
      )}

      <Footer />
    </div>
  );
}
```

### 5.3 Markdown 渲染 (法律页面)

```tsx
// components/legal/LegalSection.tsx

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface LegalSectionProps {
  title: string;
  content: string;  // Markdown with variables already replaced
  id?: string;
}

export function LegalSection({ title, content, id }: LegalSectionProps) {
  return (
    <section id={id} className="mb-8">
      <h2 className="text-xl font-semibold text-slate-800 mb-4">{title}</h2>
      <div className="prose prose-slate max-w-none">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {content}
        </ReactMarkdown>
      </div>
    </section>
  );
}
```

---

## 6. 后端实现

### 6.1 Service 层

```python
# domains/pages/service.py

class PageContentService:
    """静态页面内容服务"""

    def __init__(self, config_service: ConfigService):
        self.config_service = config_service

    async def get_page_content(self, page_name: str) -> dict:
        """获取页面所有区块内容 (已替换参数)"""
        # 1. 获取所有 PAGE_{page_name}_* 配置
        prefix = f"PAGE_{page_name.upper().replace('-', '_')}_"
        configs = await self.config_service.get_by_prefix(prefix)

        # 2. 获取全局参数
        globals_config = await self._get_global_params()

        # 3. 替换参数引用
        sections = {}
        for key, value in configs.items():
            section_name = key.replace(prefix, '').lower()
            sections[section_name] = self._replace_params(value, globals_config)

        # 4. 过滤已禁用区块
        sections = {k: v for k, v in sections.items() if v.get('enabled', True)}

        return {
            'page': page_name,
            'sections': sections,
            'globals': globals_config,
        }

    async def _get_global_params(self) -> dict:
        """获取全局参数"""
        configs = await self.config_service.get_by_prefix("GLOBAL_")
        return {
            k.replace("GLOBAL_", "").lower(): v
            for k, v in configs.items()
        }

    def _replace_params(self, content: Any, params: dict) -> Any:
        """递归替换 {{param}} 占位符"""
        if isinstance(content, str):
            for key, value in params.items():
                content = content.replace(f"{{{{{key.upper()}}}}}", str(value))
            return content
        elif isinstance(content, dict):
            return {k: self._replace_params(v, params) for k, v in content.items()}
        elif isinstance(content, list):
            return [self._replace_params(item, params) for item in content]
        return content
```

### 6.2 API 路由

```python
# api/user/pages.py

from fastapi import APIRouter, Depends
from domains.pages.service import PageContentService

router = APIRouter(prefix="/pages", tags=["Pages"])

@router.get("/{page_name}")
async def get_page_content(
    page_name: str,
    page_service: PageContentService = Depends()
):
    """获取页面内容 (Public API)"""
    # 验证 page_name 是否合法
    valid_pages = [
        'about-us', 'contact-us', 'privacy-policy',
        'term-of-service', 'billing-policy', 'marketplace-guidelines'
    ]
    if page_name not in valid_pages:
        raise HTTPException(404, "Page not found")

    content = await page_service.get_page_content(page_name)
    return content
```

---

## 7. Admin 界面设计

### 7.1 页面列表

```
┌─────────────────────────────────────────────────────────────────┐
│ Static Pages                                                     │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 📄 About Us                                                  │ │
│ │ /about-us  |  4 sections  |  Last updated: Jan 12, 2026     │ │
│ │                                              [Edit] [Preview]│ │
│ └─────────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 📄 Privacy Policy                                            │ │
│ │ /privacy-policy  |  14 sections  |  Last updated: Jan 3     │ │
│ │                                              [Edit] [Preview]│ │
│ └─────────────────────────────────────────────────────────────┘ │
│ ...                                                              │
├─────────────────────────────────────────────────────────────────┤
│ Global Variables                                      [Manage →]│
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 页面编辑器

```
┌─────────────────────────────────────────────────────────────────┐
│ Edit: About Us                              [Save] [Preview]    │
├─────────────────────────────────────────────────────────────────┤
│ Sections:                                                        │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ ☑ Hero Section                                     [▼ Edit] │ │
│ │   Title: About {{GLOBAL_COMPANY_NAME}}                       │ │
│ │   Subtitle: Our Mission                                      │ │
│ └─────────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ ☑ Features Section                                 [▼ Edit] │ │
│ │   Title: Why Choose Us                                       │ │
│ │   Items: 4 items                                             │ │
│ └─────────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ ☑ CTA Section                                      [▼ Edit] │ │
│ │   Title: Ready to Create?                                    │ │
│ └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ Available Variables:                                             │
│ {{GLOBAL_COMPANY_NAME}} → Make Decodables                       │
│ {{GLOBAL_COMPANY_EMAIL}} → info@makedecodables.com              │
│ {{GLOBAL_COMPANY_WHATSAPP}} → +1 (725) 290 0525                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.3 全局变量管理

```
┌─────────────────────────────────────────────────────────────────┐
│ Global Variables                                    [+ Add New] │
├─────────────────────────────────────────────────────────────────┤
│ Variable Name              │ Value                   │ Action   │
│ ─────────────────────────────────────────────────────────────── │
│ GLOBAL_COMPANY_NAME        │ Make Decodables         │ [Edit]   │
│ GLOBAL_COMPANY_EMAIL       │ info@makedecodables.com │ [Edit]   │
│ GLOBAL_COMPANY_WHATSAPP    │ +1 (725) 290 0525       │ [Edit]   │
│ GLOBAL_SUPPORT_EMAIL       │ support@makedecodables..│ [Edit]   │
│ GLOBAL_LAST_UPDATED_PRIVACY│ January 3, 2025         │ [Edit]   │
│ GLOBAL_LAST_UPDATED_TERMS  │ January 3, 2025         │ [Edit]   │
│ GLOBAL_LAST_UPDATED_BILLING│ December 30, 2024       │ [Edit]   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. 迁移计划

### 8.1 实施步骤

| 步骤 | 内容 | 优先级 |
|------|------|--------|
| 1 | 创建 PageContentService | P1 |
| 2 | 创建 User API `/pages/{name}` | P1 |
| 3 | 创建 Admin API 管理端点 | P2 |
| 4 | 迁移 About Us 页面 (试点) | P1 |
| 5 | 迁移其他静态页面 | P2 |
| 6 | 创建 Admin UI 编辑器 | P3 |

### 8.2 页面迁移清单

| 页面 | 区块数 | 迁移复杂度 | 状态 |
|------|--------|------------|------|
| About Us | 4 | 低 | 🔲 待迁移 |
| Contact Us | 3 | 低 | 🔲 待迁移 |
| Privacy Policy | 14 | 中 | 🔲 待迁移 |
| Terms of Service | 18 | 中 | 🔲 待迁移 |
| Billing Policy | 8 | 中 | 🔲 待迁移 |
| Marketplace Guidelines | 8 | 中 | 🔲 待迁移 |

### 8.3 全局变量初始化

```sql
-- 初始化全局变量
INSERT INTO system_configs (key, value, category, description, is_public) VALUES
('GLOBAL_COMPANY_NAME', '"Make Decodables"', 'global', 'Company name', true),
('GLOBAL_COMPANY_EMAIL', '"info@makedecodables.com"', 'global', 'Contact email', true),
('GLOBAL_COMPANY_WHATSAPP', '"+1 (725) 290 0525"', 'global', 'WhatsApp number', true),
('GLOBAL_SUPPORT_EMAIL', '"support@makedecodables.com"', 'global', 'Support email', true),
('GLOBAL_COMPANY_ADDRESS', '"..."', 'global', 'Company address', true),
('GLOBAL_LAST_UPDATED_PRIVACY', '"January 3, 2025"', 'global', 'Privacy policy last updated', true),
('GLOBAL_LAST_UPDATED_TERMS', '"January 3, 2025"', 'global', 'Terms of service last updated', true),
('GLOBAL_LAST_UPDATED_BILLING', '"December 30, 2024"', 'global', 'Billing policy last updated', true),
('GLOBAL_LAST_UPDATED_MARKETPLACE', '"December 30, 2024"', 'global', 'Marketplace guidelines last updated', true);
```

---

## 9. 与现有系统的关系

### 9.1 对比

| 系统 | 用途 | 数据特点 |
|------|------|----------|
| **Config** | 功能开关、价格配置 | Key-Value, 短文本 |
| **Articles** | 动态内容 (Manual, News) | 完整文章, Markdown |
| **Pages** (本设计) | 静态页面内容 | 结构化区块, 参数引用 |

### 9.2 数据存储

```
system_configs 表
├── PRICING_*           → 价格配置
├── FEATURE_*           → Feature Flags
├── GLOBAL_*            → 全局变量 (新增)
└── PAGE_*              → 页面区块内容 (新增)
```

---

## 10. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 0.1.0 | 2026-01-12 | 初始设计 |
| **0.2.0** | **2026-01-12** | **页面分类**: 新增 1.2 节页面类型分类 (Static/Hybrid)；明确 Contact Us 为混合型页面；详细说明 Hybrid 页面各部分的 CMS 配置范围 |

---

**END OF DESIGN**
