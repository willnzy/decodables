# v3 目录重构方案

> **基于**: `classification-principles.md`
> **日期**: 2026-02-05

---

## 一、调整清单

### 1.1 需要移动的文件

| 原位置 | 新位置 | 原因 |
|--------|--------|------|
| `01-architecture/adr/*.md` | `04-engineering/architecture/decisions/` | ADR 是架构决策，属于 engineering |
| `02-standards/testing-guide.md` | `04-engineering/development/testing-guide.md` | 开发规范 |
| `02-standards/integration-testing-guide.md` | `04-engineering/development/integration-testing-guide.md` | 开发规范 |
| `02-standards/logging-standard.md` | `04-engineering/development/logging-standard.md` | 开发规范 |
| `06-operations/*.md` | `08-operations/` | 修正编号冲突 |
| `11-reference/glossary.md` | `01-project/glossary.md` | 项目基础信息 |
| `11-reference/error-codes.md` | `04-engineering/api/error-codes.md` | API 参考 |
| `11-reference/feature-matrix.md` | `05-business/tier-system/feature-matrix.md` | 业务规则 |

### 1.2 需要拆分的文件

| 原文件 | 拆分为 | 原因 |
|--------|--------|------|
| `02-standards/feature-flag-engine.md` | **拆分** | 混合了业务规则和技术实现 |
| | → `05-business/entitlement/policy-rules.md` | 评估优先级（已有，合并） |
| | → `04-engineering/modules/platform/feature-flags.md` | 技术实现细节 |

### 1.3 需要删除的空目录

| 目录 | 原因 |
|------|------|
| `01-architecture/` | 内容移动后删除 |
| `02-standards/` | 内容移动后删除 |
| `06-operations/` | 与 08-operations 重复 |
| `11-reference/` | 内容移动后删除 |

---

## 二、详细执行步骤

### Step 1: 移动 ADR 文件

```bash
# 移动 ADR 到正确位置
mv 01-architecture/adr/0001-use-ddd-architecture.md    04-engineering/architecture/decisions/
mv 01-architecture/adr/0002-database-driven-config.md  04-engineering/architecture/decisions/
mv 01-architecture/adr/0003-dual-credit-model.md       04-engineering/architecture/decisions/
mv 01-architecture/adr/0004-jwt-dual-key-rotation.md   04-engineering/architecture/decisions/
mv 01-architecture/adr/README.md                       04-engineering/architecture/decisions/

# 删除空目录
rm -rf 01-architecture/
```

### Step 2: 移动开发规范

```bash
# 移动测试和日志规范
mv 02-standards/testing-guide.md              04-engineering/development/
mv 02-standards/integration-testing-guide.md  04-engineering/development/
mv 02-standards/logging-standard.md           04-engineering/development/
```

### Step 3: 拆分 feature-flag-engine.md

```
原文件 02-standards/feature-flag-engine.md 包含：
1. 评估优先级规则 → 合并到 05-business/entitlement/policy-rules.md
2. Flag 类型定义 → 新建 04-engineering/modules/platform/feature-flags.md
3. 技术实现细节 → 新建 04-engineering/modules/platform/feature-flags.md

具体操作：
1. 检查 policy-rules.md 是否已包含评估优先级（已包含 ✓）
2. 创建 feature-flags.md 包含技术实现部分
3. 删除原文件
```

### Step 4: 合并 operations

```bash
# 移动内容
mv 06-operations/deployment-scaling.md  08-operations/
mv 06-operations/README.md              08-operations/README.md  # 合并内容

# 删除空目录
rm -rf 06-operations/
```

### Step 5: 移动 reference 内容

```bash
# 术语表 → 项目基础
mv 11-reference/glossary.md       01-project/

# 错误码 → API 参考
mv 11-reference/error-codes.md    04-engineering/api/

# 功能矩阵 → 业务规则
mv 11-reference/feature-matrix.md 05-business/tier-system/

# 删除空目录
rm -rf 11-reference/
```

### Step 6: 删除 02-standards

```bash
# 确认所有文件已移动后删除
rm -rf 02-standards/
```

---

## 三、重构后的目录结构

```
internal/
├── 01-project/                    # ✅ 项目基础
│   ├── README.md
│   ├── vision.md
│   ├── tech-stack.md
│   └── glossary.md                # 新增（从 11-reference 移入）
│
├── 02-product/                    # ✅ 产品规格（不变）
│   ├── features/
│   └── pages/
│
├── 03-design/                     # ✅ 设计系统（不变）
│
├── 04-engineering/                # ✅ 技术实现
│   ├── architecture/
│   │   ├── decisions/             # ADR 移入这里
│   │   │   ├── 0001-use-ddd-architecture.md
│   │   │   ├── 0002-database-driven-config.md
│   │   │   ├── 0003-dual-credit-model.md
│   │   │   ├── 0004-jwt-dual-key-rotation.md
│   │   │   └── README.md
│   │   ├── backend.md
│   │   ├── frontend.md
│   │   └── database.md
│   │
│   ├── api/
│   │   ├── user-endpoints.md
│   │   ├── admin-endpoints.md
│   │   └── error-codes.md         # 新增（从 11-reference 移入）
│   │
│   ├── development/               # 开发规范移入这里
│   │   ├── testing-guide.md
│   │   ├── integration-testing-guide.md
│   │   └── logging-standard.md
│   │
│   └── modules/
│       ├── platform/
│       │   └── feature-flags.md   # 新建（技术实现部分）
│       └── ...
│
├── 05-business/                   # ✅ 业务规则
│   ├── tier-system/
│   │   ├── feature-matrix.md      # 新增（从 11-reference 移入）
│   │   └── ...
│   ├── entitlement/
│   │   ├── policy-rules.md        # 已有，确认包含评估优先级
│   │   └── ...
│   └── ...
│
├── 06-growth/                     # ✅ 运营增长（不变）
│
├── 07-analytics/                  # ✅ 数据分析（不变）
│
├── 08-operations/                 # ✅ 运维
│   ├── README.md
│   └── deployment-scaling.md      # 从 06-operations 移入
│
├── 09-compliance/                 # ✅ 合规（不变）
│
└── 10-governance/                 # ✅ 文档治理
    ├── classification-principles.md  # 新增
    └── ...

删除的目录：
- 01-architecture/  （ADR 移到 04-engineering/architecture/decisions/）
- 02-standards/     （内容移到 04-engineering/development/）
- 06-operations/    （与 08-operations 合并）
- 11-reference/     （内容分散到各领域）
```

---

## 四、需要更新的文件

重构后需要更新内部链接：

| 文件 | 需要更新的链接 |
|------|----------------|
| `01-architecture/adr/*.md` | 相对路径变化 |
| 引用 `02-standards/` 的文件 | 路径变化 |
| 引用 `11-reference/` 的文件 | 路径变化 |
| `documentation-architecture-v4.md` | 添加分类原则引用 |

---

## 五、确认清单

执行前请确认：

- [ ] 理解每个文件移动的原因
- [ ] 同意拆分 feature-flag-engine.md 的方案
- [ ] 同意合并 operations 目录的方案
- [ ] 理解重构后的目录结构

---

**END OF PLAN**
