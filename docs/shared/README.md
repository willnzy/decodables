# docs/shared - 前后端共用文档

**文档总数**: 8 个
**最后整理**: 2026-01-11 (添加用户体验设计文档)
**维护**: Make Decodables 全栈团队

**目录用途**: 系统性文档和业务规范，**前端架构和开发过程中需要关注**

---

## 📚 文档列表

### 🔐 用户与权限系统 (2个)

| 文档 | 大小 | 用途 | 前端关注点 |
|------|------|------|----------|
| [user-id-system.md](user-id-system.md) | ~8KB | ⭐ 用户标识符系统 (user_id vs user_code) | ✅ 用户反馈表单、管理员搜索 UI |
| [tier-naming-system.md](tier-naming-system.md) | ~6KB | ⭐ 会员层级命名规范 (t1/t2/t3 vs Free/Starter/Pro) | ✅ 价格页面显示、升级 UI |

**内容覆盖**:
- **user-id-system.md**:
  - `user_id` (系统内部使用，如 `user_2abc3def4ghi`)
  - `user_code` (用户反馈/管理员搜索，如 26 位格式)
  - 前端在用户反馈表单、支持工单、管理员用户搜索时需要使用 user_code

- **tier-naming-system.md**:
  - 系统代码 (`t1`/`t2`/`t3`) vs 显示名称 (Free Plan/Starter Plan/Pro Plan)
  - 前端价格页面、升级 UI、订阅管理需要使用正确的显示名称
  - 月度积分配置 (0/200/500)

**使用场景**:
- 🎨 设计用户反馈表单 → user-id-system.md
- 💰 实现价格页面 → tier-naming-system.md
- 🔧 管理员用户搜索功能 → user-id-system.md
- 📊 订阅升级流程 → tier-naming-system.md

---

### 💰 定价与计费系统 (1个)

| 文档 | 大小 | 用途 | 前端关注点 |
|------|------|------|----------|
| [pricing-system-design.md](pricing-system-design.md) | ~15KB | ⭐ 定价系统设计 (订阅/积分/折扣) | ✅ 价格展示、购买流程 UI |

**内容覆盖**:
- 订阅计划价格 (t2: $9.9/月, t3: $19.9/月)
- 积分购买档位 (100/500/2000 积分)
- 原价与现价配置
- 折扣展示逻辑

**使用场景**:
- 💳 实现购买流程 UI
- 📊 价格对比表格
- 🎯 促销活动展示

---

### 🎨 Canvas 系统 (1个)

| 文档 | 大小 | 用途 | 前端关注点 |
|------|------|------|----------|
| [canvas-data-schema.md](canvas-data-schema.md) | ~10KB | ⭐ Canvas 数据结构规范 | ✅ 编辑器数据模型、序列化/反序列化 |

**内容覆盖**:
- Canvas 数据结构 (JSON Schema)
- 图层类型定义 (文字/图片/形状等)
- 状态同步规范
- 版本控制字段

**使用场景**:
- 🖼️ 编辑器开发 (Canvas 组件)
- 💾 数据保存与读取
- 🔄 实时协作功能

---

### 📦 素材与内容系统 (1个)

| 文档 | 大小 | 用途 | 前端关注点 |
|------|------|------|----------|
| [asset-category-design.md](asset-category-design.md) | ~25KB | ⭐ 素材分类系统设计 (10 类 + 标签) | ✅ 素材库 UI、分类导航、标签筛选 |

**内容覆盖**:
- 10 个素材分类 (Images/Icons/Illustrations/Patterns/...)
- 层级结构 (父子分类)
- 标签系统
- 搜索与筛选逻辑

**使用场景**:
- 📚 素材库浏览界面
- 🔍 分类导航与筛选
- 🏷️ 标签管理 UI

---

### ⚙️ 功能控制系统 (1个)

| 文档 | 大小 | 用途 | 前端关注点 |
|------|------|------|----------|
| [feature-flag-design.md](feature-flag-design.md) | ~20KB | ⭐ Feature Flag + A/B 测试系统 | ✅ 功能开关、实验分组逻辑 |

**内容覆盖**:
- Feature Flag 开关逻辑
- A/B 测试实验分组
- 用户分组规则
- 前端条件渲染

**使用场景**:
- 🚀 新功能灰度发布
- 🧪 A/B 测试实验
- 🎯 用户分组展示不同 UI

---

### 🎓 用户体验设计 (2个)

| 文档 | 大小 | 用途 | 前端关注点 | 状态 |
|------|------|------|----------|------|
| [onboarding-design.md](onboarding-design.md) | ~15KB | ⭐ 新手引导系统设计 | ✅ Welcome Tour, Editor Tour, Checklist, Feature Spotlights | 🟢 已实现 |
| [theme-system-design.md](theme-system-design.md) | ~12KB | ⭐ 主题系统设计 (Google Doodle 风格) | ✅ 节日主题、纪念日主题展示 | 🟢 已实现 |

**内容覆盖**:
- **onboarding-design.md**:
  - Welcome Tour (产品介绍、核心功能引导)
  - Editor Tour (编辑器功能逐步引导)
  - Getting Started Checklist (任务清单)
  - Feature Spotlights (新功能高亮提示)
  - 量化目标: 7天留存 +15%, 首次创建项目 +30%

- **theme-system-design.md**:
  - Daily Theme 系统 (类似 Google Doodle)
  - 三种主题类型: 固定日期节日、历史人物诞辰、世界纪念日
  - 主题配置: 颜色、徽章、装饰、Banner 样式
  - 前端实时渲染逻辑

**使用场景**:
- 🎓 实现新用户引导流程 → onboarding-design.md
- 🎨 实现节日主题切换 → theme-system-design.md
- 📊 设计用户任务清单 → onboarding-design.md
- 🎉 设计纪念日主题展示 → theme-system-design.md

**实现状态** (后端已完成):
- ✅ Onboarding API: `api/user/onboarding.py` + `domains/onboarding/`
- ✅ Theme API: `api/user/themes.py` (v3.0.0 DDD) + `domains/themes/`
- ✅ 数据库表: `onboarding_steps`, `user_onboarding_progress`, `daily_themes`
- 📋 前端实现: 待开发 (参考设计文档)

---

## 📖 前端开发快速查找

### 按功能模块查找

| 功能模块 | 推荐文档 | 关键点 |
|----------|----------|--------|
| **用户反馈/支持工单** | user-id-system.md | 使用 user_code (26位) |
| **管理员用户搜索** | user-id-system.md | 支持 user_code 搜索 |
| **价格页面** | tier-naming-system.md + pricing-system-design.md | 显示名称 + 折扣价格 |
| **订阅升级流程** | tier-naming-system.md + pricing-system-design.md | 月度积分 + 价格对比 |
| **Canvas 编辑器** | canvas-data-schema.md | 数据结构 + 序列化 |
| **素材库** | asset-category-design.md | 10 类分类 + 标签系统 |
| **功能开关** | feature-flag-design.md | 条件渲染逻辑 |
| **A/B 测试** | feature-flag-design.md | 用户分组 + 实验跟踪 |
| **新手引导** | onboarding-design.md | Welcome Tour + Editor Tour + Checklist |
| **节日主题** | theme-system-design.md | Daily Theme 切换展示 |

### 按开发阶段查找

| 阶段 | 推荐文档 |
|------|----------|
| **项目初始化** | user-id-system.md → tier-naming-system.md → canvas-data-schema.md |
| **价格页面开发** | tier-naming-system.md → pricing-system-design.md |
| **编辑器开发** | canvas-data-schema.md |
| **素材库开发** | asset-category-design.md |
| **功能开关集成** | feature-flag-design.md |
| **新手引导开发** | onboarding-design.md |
| **主题系统开发** | theme-system-design.md |

---

## 🎯 为什么这些文档在 shared/?

### ✅ 前端需要关注的原因

1. **user-id-system.md** & **tier-naming-system.md**:
   - 前端 UI 需要正确展示用户标识符和会员层级名称
   - 用户反馈表单、支持工单、管理员搜索等功能依赖这些规范

2. **pricing-system-design.md**:
   - 前端价格页面、购买流程需要正确展示价格和折扣
   - 订阅升级 UI 需要与后端价格配置保持一致

3. **canvas-data-schema.md**:
   - 前端编辑器的核心数据模型
   - 序列化/反序列化逻辑必须与后端保持一致

4. **asset-category-design.md**:
   - 前端素材库 UI 的分类导航和筛选逻辑
   - 标签系统的展示和交互

5. **feature-flag-design.md**:
   - 前端功能开关的条件渲染逻辑
   - A/B 测试实验的用户分组和跟踪

6. **onboarding-design.md**:
   - 新用户引导流程的 UI 设计和交互逻辑
   - Welcome Tour、Editor Tour、任务清单的前端实现

7. **theme-system-design.md**:
   - 节日主题的前端渲染和切换逻辑
   - 主题配置的动态加载和应用

---

## 🔄 文档维护规则

### 更新频率

| 频率 | 文档 | 触发条件 |
|------|------|----------|
| **每次价格调整** | tier-naming-system.md, pricing-system-design.md | 价格、折扣、月度积分变更 |
| **每次架构变更** | canvas-data-schema.md | Canvas 数据结构修改 |
| **每次分类调整** | asset-category-design.md | 新增/删除素材分类 |
| **按需** | feature-flag-design.md | 新增 Feature Flag 或实验 |
| **功能迭代** | onboarding-design.md, theme-system-design.md | 引导流程或主题系统调整 |

### 同步规则

**重要**: shared/ 目录下的文档需要在**前后端两个仓库**都保持同步！

```
decodables/docs/shared/          # 后端仓库
decodables-fe/docs/shared/       # 前端仓库
```

**同步时机**:
- ✅ 文档更新后，同时提交到两个仓库
- ✅ 重大变更前，先在团队会议中确认
- ✅ 每周检查一次两边是否同步

---

## 🔗 相关文档目录

- [docs/main/](../main/) - 后端专用文档 (8个) - **前端不需要关注**
- [docs/tmp/](../tmp/) - 临时文档、归档报告 (5个)
- [decodables-fe/docs/](../../../../decodables-fe/docs/) - 前端专用文档
- [.claude/guides/](../../../.claude/guides/) - 开发指南和最佳实践

---

## 📊 文档统计

| 分类 | 文档数 | 占比 |
|------|--------|------|
| 用户与权限系统 | 2 | 25% |
| 定价与计费系统 | 1 | 12.5% |
| Canvas 系统 | 1 | 12.5% |
| 素材与内容系统 | 1 | 12.5% |
| 功能控制系统 | 1 | 12.5% |
| 用户体验设计 | 2 | 25% |
| **总计** | **8** | **100%** |

---

**Last Updated**: 2026-01-11
**Total Documents**: 8
**Status**: 🟢 完整文档库 - 包含业务规范、数据契约、用户体验设计

📚 **前后端协作的桥梁 - 业务规范、数据契约与 UX 设计！**
