# docs/shared - 前后端共用文档

**文档总数**: 14 个 (12 个共享 + 2 个前端规划)
**最后整理**: 2026-01-13 (Analytics 统一架构)
**维护**: Make Decodables 全栈团队

**目录用途**: 系统性文档、业务规范、API 详细文档、项目规划，**前后端开发都需要关注**

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

### 📊 数据分析系统 (1个)

| 文档 | 大小 | 用途 | 前端关注点 | 状态 |
|------|------|------|----------|------|
| [analytics-system-design.md](analytics-system-design.md) | ~25KB | ⭐ 统一事件追踪系统设计 (前端批处理 + 后端服务端追踪) | ✅ 前端事件上报 API、事件类型规范 | 🟢 已实现 (v2.0) |

**内容覆盖**:
- **analytics-system-design.md**:
  - 统一的事件追踪系统 (前端批处理 + 后端服务端追踪)
  - DDD 架构设计 (Repository Pattern + Dependency Injection)
  - 标准事件类型定义 (用户行为、AI 生成、支付、项目、市场)
  - 前端批处理 API: `POST /api/v2/user/analytics/events`
  - 数据库表结构: `analytics_events`, `user_events`, `activity_logs`
  - 性能优化策略 (批量写入、Fire-and-Forget)

**使用场景**:
- 📤 实现前端事件批处理上报 → analytics-system-design.md
- 📊 了解标准事件类型规范 → StandardEventTypes 定义
- 🔍 查询事件追踪 API 文档 → API 设计章节
- 🎯 理解事件数据结构 → 数据模型章节

**实现状态** (后端已完成):
- ✅ Analytics API: `api/user/analytics.py` + `domains/analytics/`
- ✅ DDD 架构: Repository Pattern + Entity + Value Objects
- ✅ 前端批处理 API: `POST /api/v2/user/analytics/events`
- ✅ 后端服务端追踪: `track_ai_generation`, `track_payment`, `track_project_action`
- ✅ 数据库表: `analytics_events`, `user_events`, `activity_logs`
- 📋 前端集成: 参考设计文档 "5.1 前端批处理 API" 章节

---

### 🔌 API 详细文档 (2个)

| 文档 | 大小 | 用途 | 前端关注点 | 状态 |
|------|------|------|----------|------|
| [admin-api-review.md](admin-api-review.md) | ~120KB | ⭐ Admin API 完整参考 (142 个端点详细文档) | ✅ 管理后台开发 | 🟢 完整 |
| [user-api-review.md](user-api-review.md) | ~85KB | ⭐ User API 完整参考 (123 个端点详细文档) | ✅ 前端业务逻辑开发 | 🟢 完整 |

**内容覆盖**:
- **admin-api-review.md**:
  - 142 个 Admin API 端点 (实际代码 143 个，1 个待补充)
  - 18 个模块分类: AI Insights、AI Models、Users、Stats、Campaigns、Config、Events、Experiments、Feature Flags 等
  - 每个端点: HTTP 方法、路径、请求参数、请求体、响应格式、限流配置、验证规则
  - DDD 架构合规性说明

- **user-api-review.md**:
  - 123 个 User API 端点 (全部完整)
  - 26 个模块分类: Projects、Templates、Marketplace、Generation、Billing、Payment 等
  - 每个端点: HTTP 方法、路径、请求参数、请求体、响应格式、限流配置、验证规则
  - 测试覆盖率 65%+ 说明

**使用场景**:
- 🔍 查找具体 API 端点的详细信息
- 📝 前端调用 API 的参数参考
- 🧪 编写 API 集成测试
- 📊 了解 API 限流和验证规则
- 🔧 管理后台开发参考

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
| **事件追踪上报** | analytics-system-design.md | 批处理 API + 标准事件类型 |

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
| **API 变更** | admin-api-review.md, user-api-review.md | 新增/修改/删除 API 端点 |
| **按需** | feature-flag-design.md | 新增 Feature Flag 或实验 |
| **功能迭代** | onboarding-design.md, theme-system-design.md | 引导流程或主题系统调整 |

### 同步规则

**🚨 强制要求**: `docs/shared/` 目录下的所有文档必须在**前后端两个项目**中保持完全同步！

```
decodables/docs/shared/          # 后端项目
decodables-fe/docs/shared/       # 前端项目
```

#### 📋 同步流程 (必须遵守)

**无论在哪个项目更新了 `docs/shared/` 下的文件，都必须同步到另一个项目！**

```
步骤 1: 更新文档 (在任意项目中)
  ├─ decodables/docs/shared/xxx.md
  └─ 或 decodables-fe/docs/shared/xxx.md

步骤 2: 复制到另一个项目
  └─ 使用 cp 命令或手动复制确保内容一致

步骤 3: 验证同步
  └─ diff -q decodables/docs/shared/ decodables-fe/docs/shared/

步骤 4: 提交到两个项目
  ├─ cd decodables && git add docs/shared/ && git commit && git push
  └─ cd decodables-fe && git add docs/shared/ && git commit && git push
```

#### ⚡ 快速同步命令

```bash
# 从后端同步到前端
cp -f decodables/docs/shared/*.md decodables-fe/docs/shared/

# 从前端同步到后端
cp -f decodables-fe/docs/shared/*.md decodables/docs/shared/

# 验证两边是否一致
diff -q decodables/docs/shared/ decodables-fe/docs/shared/
```

#### 🎯 同步时机

| 场景 | 操作 |
|------|------|
| 📝 **新增文档** | 立即复制到另一个项目，双方同时提交 |
| 🔄 **更新文档** | 立即复制到另一个项目，双方同时提交 |
| 🗑️ **删除文档** | 立即删除另一个项目的对应文件，双方同时提交 |
| 📊 **重大变更** | 先在团队会议中确认，再执行同步 |
| ✅ **每周检查** | 运行 `diff` 命令确保两边完全一致 |

#### ⚠️ 注意事项

- **不要**只在一个项目中更新而忘记同步
- **不要**等到"有空再同步"，必须立即同步
- **不要**假设别人会帮你同步，更新者必须自己负责同步
- **验证**每次同步后运行 `diff` 命令确认无差异

---

## 🔗 相关文档目录

- [docs/main/](../main/) - 后端专用文档 (8个) - **前端不需要关注**
- [docs/tmp/](../tmp/) - 临时文档、归档报告 (7个)
- [decodables-fe/docs/](../../../../decodables-fe/docs/) - 前端专用文档
- [.claude/guides/](../../../.claude/guides/) - 开发指南和最佳实践

---

## 📋 项目规划文档 (2个)

| 文档 | 大小 | 用途 | 维护责任 |
|------|------|------|----------|
| [project-implementation-plan.md](project-implementation-plan.md) | ~49KB | ⭐ 项目实施计划 (时间线/里程碑/技术栈) | 前端+产品 |
| [system-refactoring-proposal-v2.md](system-refactoring-proposal-v2.md) | ~26KB | ⭐ 系统重构方案 v2 (三层架构+DDD) | 前端+后端 |

**内容覆盖**:
- **project-implementation-plan.md**:
  - 平台优先级 (PC → 手机 → PWA)
  - 总体工时估算 (22-26 周)
  - 甘特图时间线和里程碑
  - 技术栈清单和依赖分析
  - 风险矩阵

- **system-refactoring-proposal-v2.md**:
  - 三层架构 + 轻量级 DDD 设计
  - 前后端目录结构规范
  - 领域划分 (6 大业务领域)
  - 代码迁移映射表

**使用场景**:
- 📅 项目进度规划 → project-implementation-plan.md
- 🏗️ 架构理解与开发 → system-refactoring-proposal-v2.md
- 🔄 代码迁移参考 → system-refactoring-proposal-v2.md

---

## 📊 文档统计

| 分类 | 文档数 | 占比 |
|------|--------|------|
| 用户与权限系统 | 2 | 14% |
| 定价与计费系统 | 1 | 7% |
| Canvas 系统 | 1 | 7% |
| 素材与内容系统 | 1 | 7% |
| 功能控制系统 | 1 | 7% |
| 用户体验设计 | 2 | 14% |
| 数据分析系统 | 1 | 7% |
| API 详细文档 | 2 | 14% |
| 项目规划文档 | 2 | 14% |
| 导航索引 | 1 | 7% |
| **总计** | **14** | **100%** |

---

**Last Updated**: 2026-01-13
**Total Documents**: 14
**Status**: 🟢 完整文档库 - 包含业务规范、数据契约、用户体验设计、数据分析、项目规划

📚 **前后端协作的桥梁 - 业务规范、数据契约、UX 设计与项目规划！**
