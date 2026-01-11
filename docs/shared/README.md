# docs/shared - 前后端共用文档

**文档总数**: 6 个
**最后整理**: 2026-01-11 (文档重组)
**维护**: Make Decodables 全栈团队

**目录用途**: 系统性文档和业务规范，**前端架构和开发过程中需要关注**

---

## 📚 文档列表

### 🔐 用户与权限系统 (2个)

| 文档 | 大小 | 用途 | 前端关注点 |
|------|------|------|----------|
| [USER-ID-SYSTEM.md](USER-ID-SYSTEM.md) | ~8KB | ⭐ 用户标识符系统 (user_id vs user_code) | ✅ 用户反馈表单、管理员搜索 UI |
| [TIER-NAMING-SYSTEM.md](TIER-NAMING-SYSTEM.md) | ~6KB | ⭐ 会员层级命名规范 (t1/t2/t3 vs Free/Starter/Pro) | ✅ 价格页面显示、升级 UI |

**内容覆盖**:
- **USER-ID-SYSTEM.md**:
  - `user_id` (系统内部使用，如 `user_2abc3def4ghi`)
  - `user_code` (用户反馈/管理员搜索，如 26 位格式)
  - 前端在用户反馈表单、支持工单、管理员用户搜索时需要使用 user_code

- **TIER-NAMING-SYSTEM.md**:
  - 系统代码 (`t1`/`t2`/`t3`) vs 显示名称 (Free Plan/Starter Plan/Pro Plan)
  - 前端价格页面、升级 UI、订阅管理需要使用正确的显示名称
  - 月度积分配置 (0/200/500)

**使用场景**:
- 🎨 设计用户反馈表单 → USER-ID-SYSTEM.md
- 💰 实现价格页面 → TIER-NAMING-SYSTEM.md
- 🔧 管理员用户搜索功能 → USER-ID-SYSTEM.md
- 📊 订阅升级流程 → TIER-NAMING-SYSTEM.md

---

### 💰 定价与计费系统 (1个)

| 文档 | 大小 | 用途 | 前端关注点 |
|------|------|------|----------|
| [PRICING-SYSTEM-DESIGN.md](PRICING-SYSTEM-DESIGN.md) | ~15KB | ⭐ 定价系统设计 (订阅/积分/折扣) | ✅ 价格展示、购买流程 UI |

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
| [Canvas-Data-Schema.md](Canvas-Data-Schema.md) | ~10KB | ⭐ Canvas 数据结构规范 | ✅ 编辑器数据模型、序列化/反序列化 |

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
| [[重构后]Asset-Category-System-Design.md]([重构后]Asset-Category-System-Design.md) | ~25KB | ⭐ 素材分类系统设计 (10 类 + 标签) | ✅ 素材库 UI、分类导航、标签筛选 |

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
| [[重构后]Feature-Flag-Experiments-Unified-Design.md]([重构后]Feature-Flag-Experiments-Unified-Design.md) | ~20KB | ⭐ Feature Flag + A/B 测试系统 | ✅ 功能开关、实验分组逻辑 |

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

## 📖 前端开发快速查找

### 按功能模块查找

| 功能模块 | 推荐文档 | 关键点 |
|----------|----------|--------|
| **用户反馈/支持工单** | USER-ID-SYSTEM.md | 使用 user_code (26位) |
| **管理员用户搜索** | USER-ID-SYSTEM.md | 支持 user_code 搜索 |
| **价格页面** | TIER-NAMING-SYSTEM.md + PRICING-SYSTEM-DESIGN.md | 显示名称 + 折扣价格 |
| **订阅升级流程** | TIER-NAMING-SYSTEM.md + PRICING-SYSTEM-DESIGN.md | 月度积分 + 价格对比 |
| **Canvas 编辑器** | Canvas-Data-Schema.md | 数据结构 + 序列化 |
| **素材库** | Asset-Category-System-Design.md | 10 类分类 + 标签系统 |
| **功能开关** | Feature-Flag-Experiments-Unified-Design.md | 条件渲染逻辑 |
| **A/B 测试** | Feature-Flag-Experiments-Unified-Design.md | 用户分组 + 实验跟踪 |

### 按开发阶段查找

| 阶段 | 推荐文档 |
|------|----------|
| **项目初始化** | USER-ID-SYSTEM.md → TIER-NAMING-SYSTEM.md → Canvas-Data-Schema.md |
| **价格页面开发** | TIER-NAMING-SYSTEM.md → PRICING-SYSTEM-DESIGN.md |
| **编辑器开发** | Canvas-Data-Schema.md |
| **素材库开发** | Asset-Category-System-Design.md |
| **功能开关集成** | Feature-Flag-Experiments-Unified-Design.md |

---

## 🎯 为什么这些文档在 shared/?

### ✅ 前端需要关注的原因

1. **USER-ID-SYSTEM.md** & **TIER-NAMING-SYSTEM.md**:
   - 前端 UI 需要正确展示用户标识符和会员层级名称
   - 用户反馈表单、支持工单、管理员搜索等功能依赖这些规范

2. **PRICING-SYSTEM-DESIGN.md**:
   - 前端价格页面、购买流程需要正确展示价格和折扣
   - 订阅升级 UI 需要与后端价格配置保持一致

3. **Canvas-Data-Schema.md**:
   - 前端编辑器的核心数据模型
   - 序列化/反序列化逻辑必须与后端保持一致

4. **Asset-Category-System-Design.md**:
   - 前端素材库 UI 的分类导航和筛选逻辑
   - 标签系统的展示和交互

5. **Feature-Flag-Experiments-Unified-Design.md**:
   - 前端功能开关的条件渲染逻辑
   - A/B 测试实验的用户分组和跟踪

---

## 🔄 文档维护规则

### 更新频率

| 频率 | 文档 | 触发条件 |
|------|------|----------|
| **每次价格调整** | TIER-NAMING-SYSTEM.md, PRICING-SYSTEM-DESIGN.md | 价格、折扣、月度积分变更 |
| **每次架构变更** | Canvas-Data-Schema.md | Canvas 数据结构修改 |
| **每次分类调整** | Asset-Category-System-Design.md | 新增/删除素材分类 |
| **按需** | Feature-Flag-Experiments-Unified-Design.md | 新增 Feature Flag 或实验 |

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
- [docs/tmp/](../tmp/) - 临时文档、待执行任务 (9个)
- [decodables-fe/docs/](../../../../decodables-fe/docs/) - 前端专用文档
- [.claude/guides/](../../../.claude/guides/) - 开发指南和最佳实践

---

## 📊 文档统计

| 分类 | 文档数 | 占比 |
|------|--------|------|
| 用户与权限系统 | 2 | 33% |
| 定价与计费系统 | 1 | 17% |
| Canvas 系统 | 1 | 17% |
| 素材与内容系统 | 1 | 17% |
| 功能控制系统 | 1 | 17% |
| **总计** | **6** | **100%** |

---

**Last Updated**: 2026-01-11
**Total Documents**: 6
**Status**: 🟢 重组完成 - 只保留前端需要关注的系统性文档

📚 **前后端协作的桥梁 - 业务规范与数据契约！**
