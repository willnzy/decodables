 # Shared 文档同步索引
 
 > 统一记录 shared 文档的归属、同步状态与变更流程。
 
 **状态**: draft  
 **版本**: 0.1.0  
 **版本日期**: 2026-02-04  
 **最后复核**: 2026-02-04  
 **负责人**: Docs Working Group  
 **适用范围**: shared  
 **source_repo**: both  
 **sync_required**: yes  
 **来源/依据**: `decodables-fe/docs/shared/`、`decodables/docs/shared/`、`decodables/docs/v2/09-reference/feature-coverage-matrix.md`
 
 ---
 
 ## 1. 目标
 
 - 统一 shared 文档的归属与同步规则
 - 提供唯一索引入口，支持双端一致性追踪
 - 避免重复、遗漏、冲突
 
## 1.1 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须以新结构重组表达，仅引用证据来源
- 每条记录必须指向唯一主文档

 ## 2. 同步规则
 
 - shared 文档必须在两端保持同路径与同内容
 - 任一端更新必须同步到另一端
 - 共享文档只在 `docs/v2/` 下维护新版结构
 
 ## 3. 状态字段
 
 - `pending`: 已映射，尚未建立 v2 骨架
 - `needs-review`: 已建立骨架，待结构审查
 - `done`: 内容迁移完成并复核通过
 - `archived`: 停用，仅保留历史
 
 ## 4. 变更流程
 
 1. 在任一端更新 shared 文档
 2. 同步到另一端，保持一致
 3. 在覆盖矩阵更新状态
 
 ## 5. 索引清单
 
> 由覆盖矩阵驱动，所有 shared 文档必须在此登记。

| shared_key | v2_path | status | owner | last_review | source |
| --- | --- | --- | --- | --- | --- |
| `shared-docs-registry` | `docs/v2/09-reference/shared-docs-registry.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/README.md` |
