# 信息架构规范（Admin/User 双树）

> 以可验证的结构保证“完整、准确、合理”，并与代码结构和旧文档双源对齐。

**状态**: active  
**版本**: 1.0.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/`、`decodables-fe/app/admin/`、`decodables/domains/`、`decodables/api/admin/`

---

## 1. 目标

- 建立可验证的文档结构，不依赖记忆或主观穷举。
- 明确 Admin 与 User 的能力体系与页面体验的双树结构。
- 用覆盖矩阵证明“无遗漏、无重复”。

## 2. 顶层目录职责

- `00-governance`: 文档治理与规则
- `01-architecture`: 架构与 ADR
- `02-standards`: 工程规范（含审计/重构）
- `03-business`: 业务规则与数据契约
- `04-features`: 能力体系（Admin/User 双树）
- `10-product`: 页面体验（Admin/User 双树，PC/Mobile 成对）
- `09-reference`: 覆盖矩阵与术语表

## 2.1 跨域 UI 基础设施归属

- 统一 Toast/Modal 等交互规范放在 `02-standards`
- 交互组件与能力实现放在 `04-features/user-capabilities/ui-system`

## 3. Admin/User 双树原则

### 3.1 能力体系（04-features）

- **User 能力树**：用户可见、可操作的功能系统。
- **Admin 能力树**：后台运营与管理能力（配置、审核、分析、内容管理）。
- 二者只共享业务规则与数据契约（`03-business`），不共享正文。

### 3.2 页面体验（10-product）

- **User 体验树**：PC/Mobile 页面成对描述。
- **Admin 体验树**：后台控制台与配置流程体验。
- 页面文档只描述“体验流程”，能力细节留在 `04-features`。

## 4. 结构生成规则

1. **唯一归属**：一个知识点只有一个主文档，其它位置仅引用。
2. **层级规则**：子域文档 ≥ 3 才升级为子目录；每层必须有 README 索引。
3. **稳定优先**：稳定规则前置（治理/架构/标准），高变化内容后置（功能/体验）。

## 4.1 新文档设计原则（强制）

1. **不照搬旧文档**：旧文档只作为证据来源与校验参考，不允许直接复制章节结构或原文段落。
2. **证据驱动重构**：以代码结构与业务规则为主证据，旧文档仅补充缺失信息。
3. **先设计结构，再组织内容**：先明确目标/边界/能力树，再组织内容与图示。
4. **去重与合并**：相同知识点合并为一个主文档，其他位置只引用。

## 4.2 旧文档使用方式

- 只用于“事实核对、术语确认、遗漏补全”
- 禁止原文段落搬运
- 必须用新的结构重新组织表达

## 5. 证据驱动覆盖

结构必须能追溯到证据来源：

- 前端页面与 Admin：`decodables-fe/app/`、`decodables-fe/app/admin/`
- 前端配置系统：`decodables-fe/lib/config/`
- 后端能力域：`decodables/domains/`
- 后端 Admin API：`decodables/api/admin/`

所有能力与页面必须在 `09-reference/feature-coverage-matrix.md` 中标注来源。

## 6. 强制图示规范

- 架构文档：必须包含架构图 + 关键时序图
- 业务规则文档：必须包含业务流程图
- 页面体验文档：必须包含用户流程图

## 7. 覆盖矩阵要求

- 页面清单（含 Admin/PC/Mobile）
- 能力清单（Admin/User 分树）
- 页面 → 能力映射
- 旧文档 → 新归属映射
- 缺口记录与补齐路径
