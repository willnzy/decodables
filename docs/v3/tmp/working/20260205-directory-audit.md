# v3 目录规划审计报告

> **审计日期**: 2026-02-05
> **审计依据**: `documentation-architecture-v4.md`
> **审计结果**: ❌ 存在多处不一致

---

## 一、发现的问题

### 🔴 问题 1: 编号冲突 - 两个 01 目录

**实际结构**:
```
internal/
├── 01-architecture/   ❌ 设计中没有
│   └── adr/           
└── 01-project/        ✅ 设计中有
```

**设计规范**:
```
internal/
├── 01-project/        # 第一层：项目全局
```

**问题**: 存在两个以 `01-` 开头的目录，编号冲突

**建议**: 
- 将 `01-architecture/adr/` 移动到 `04-engineering/architecture/decisions/`
- 删除 `01-architecture/` 目录

---

### 🔴 问题 2: 重复的 operations 目录

**实际结构**:
```
internal/
├── 06-operations/     ❌ 编号错误，应该是 06-growth
│   ├── deployment-scaling.md
│   └── README.md
└── 08-operations/     ✅ 正确位置，但是空的
    └── README.md
```

**设计规范**:
```
internal/
├── 06-growth/         # 第六层：运营增长
└── 08-operations/     # 第八层：运维保障
```

**问题**: 
1. `06-operations/` 不应该存在（编号被 `06-growth` 占用）
2. `08-operations/` 是正确位置但为空
3. 运维内容分散在两处

**建议**: 
- 将 `06-operations/` 内的文件移动到 `08-operations/`
- 删除 `06-operations/` 目录

---

### 🟡 问题 3: 额外的顶级目录

**实际存在但设计中没有**:
```
internal/
├── 02-standards/      ❌ 设计中没有
│   ├── feature-flag-engine.md
│   ├── integration-testing-guide.md
│   ├── logging-standard.md
│   └── testing-guide.md
│
└── 11-reference/      ❌ 设计中没有
    ├── error-codes.md
    ├── feature-matrix.md
    └── glossary.md
```

**设计规范**:
- 标准/规范应该在 `04-engineering/development/`
- 术语表应该在 `01-project/glossary.md`
- 参考资料应该在 `10-governance/` 或分散到相关目录

**建议**: 
- **方案 A**: 按设计规范重新组织
  - `02-standards/` → `04-engineering/development/`
  - `11-reference/glossary.md` → `01-project/glossary.md`
  - `11-reference/error-codes.md` → `04-engineering/api/error-codes.md`
  - `11-reference/feature-matrix.md` → `05-business/feature-matrix.md`
- **方案 B**: 更新设计规范，保留这两个目录
  - 如果认为分离是合理的，应该更新 `documentation-architecture-v4.md`

---

### 🟡 问题 4: ADR 文件位置不一致

**实际结构**:
```
internal/
├── 01-architecture/adr/           # 有 4 个 ADR 文件
│   ├── 0001-use-ddd-architecture.md
│   ├── 0002-database-driven-config.md
│   ├── 0003-dual-credit-model.md
│   └── 0004-jwt-dual-key-rotation.md
│
└── 04-engineering/architecture/decisions/   # 空的，只有 README
    └── README.md
```

**设计规范**:
```
04-engineering/
└── architecture/
    └── decisions/      # ADR（架构决策记录）
```

**建议**: 将 ADR 文件从 `01-architecture/adr/` 移动到 `04-engineering/architecture/decisions/`

---

### 🟡 问题 5: 设计中有但实际缺失的文件

| 设计要求 | 实际状态 | 说明 |
|----------|----------|------|
| `01-project/glossary.md` | ❌ 缺失 | 在 `11-reference/` |
| `01-project/decisions-log.md` | ❌ 缺失 | ADR 分散在其他位置 |
| `03-design/tokens.md` | ❌ 缺失 | 拆分成 `colors.md`, `typography.md` |
| `03-design/components.md` | ❌ 缺失 | 拆分成多个文件 |
| `03-design/brand.md` | ❌ 缺失 | 未创建 |
| `04-engineering/development/backend.md` | ❌ 缺失 | 只有 README |
| `04-engineering/development/frontend.md` | ❌ 缺失 | 只有 README |
| `04-engineering/development/api-guide.md` | ❌ 缺失 | - |
| `04-engineering/development/database.md` | ❌ 缺失 | 在 `architecture/database.md` |
| `04-engineering/development/testing.md` | ❌ 缺失 | 在 `02-standards/testing-guide.md` |
| `04-engineering/data/schema.md` | ❌ 缺失 | - |
| `04-engineering/data/entities.md` | ❌ 缺失 | - |
| `08-operations/deployment.md` | ❌ 缺失 | 在 `06-operations/deployment-scaling.md` |
| `08-operations/monitoring.md` | ❌ 缺失 | - |
| `08-operations/troubleshooting.md` | ❌ 缺失 | - |

---

## 二、设计 vs 实际对照表

| 编号 | 设计规范 | 实际实现 | 状态 |
|------|----------|----------|------|
| 01 | `01-project/` | `01-project/` + `01-architecture/` | ⚠️ 冲突 |
| 02 | `02-product/` | `02-product/` + `02-standards/` | ⚠️ 额外 |
| 03 | `03-design/` | `03-design/` | ✅ |
| 04 | `04-engineering/` | `04-engineering/` | ✅ 但内部缺文件 |
| 05 | `05-business/` | `05-business/` | ✅ |
| 06 | `06-growth/` | `06-growth/` + `06-operations/` | ⚠️ 冲突 |
| 07 | `07-analytics/` | `07-analytics/` | ✅ 但空的 |
| 08 | `08-operations/` | `08-operations/` | ⚠️ 空的，内容在 06 |
| 09 | `09-compliance/` | `09-compliance/` | ✅ 但空的 |
| 10 | `10-governance/` | `10-governance/` | ✅ |
| 11 | (无) | `11-reference/` | ⚠️ 额外 |

---

## 三、建议的修正方案

### 方案 A: 完全按设计规范调整（推荐）

```bash
# 1. 移动 ADR 文件
mv internal/01-architecture/adr/*.md internal/04-engineering/architecture/decisions/
rm -rf internal/01-architecture/

# 2. 合并 operations
mv internal/06-operations/*.md internal/08-operations/
rm -rf internal/06-operations/

# 3. 整合 standards
mv internal/02-standards/*.md internal/04-engineering/development/
rm -rf internal/02-standards/

# 4. 整合 reference
mv internal/11-reference/glossary.md internal/01-project/
mv internal/11-reference/error-codes.md internal/04-engineering/api/
mv internal/11-reference/feature-matrix.md internal/05-business/
rm -rf internal/11-reference/
```

### 方案 B: 更新设计规范以适应实际

如果认为当前结构更合理，则更新 `documentation-architecture-v4.md` 添加：
- `02-standards/` - 开发规范（与 product 分开）
- `11-reference/` - 参考资料（术语、错误码）

并在设计中说明 ADR 可以放在 `01-architecture/adr/` 或 `04-engineering/architecture/decisions/`

---

## 四、优先级建议

| 优先级 | 任务 | 影响 |
|--------|------|------|
| **P0** | 解决 06-operations 重复 | 目录混乱 |
| **P0** | 解决 01-architecture 冲突 | 编号冲突 |
| **P1** | 决定 02-standards 去留 | 结构一致性 |
| **P1** | 决定 11-reference 去留 | 结构一致性 |
| **P2** | 补充缺失的文件 | 内容完整性 |

---

## 五、结论

**目录规划存在以下问题**:

1. ❌ **编号冲突**: 两个 `01-*` 目录，两个运维目录
2. ❌ **额外目录**: `02-standards/` 和 `11-reference/` 未在设计中定义
3. ⚠️ **内容分散**: ADR 和 operations 内容位置不一致
4. ⚠️ **空目录**: 部分目录只有 README 或 .gitkeep

**建议决策**:
请确认是按设计规范调整实际目录（方案 A），还是更新设计规范以适应实际结构（方案 B）？

---

**END OF AUDIT**
