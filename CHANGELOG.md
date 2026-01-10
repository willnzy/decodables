# Changelog

All notable changes to the Make Decodables backend will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.28.0] - 2026-01-11

### Fixed
- **完全重写 test_ai.py - 所有 37 测试通过** (commits: 13f6bac, 30c0347, 5c78220)
  - **问题**：21 个测试失败，16 个通过
    - Mock 了不存在的函数 (`api.admin.ai.get_database_client`)
    - 使用了错误的 mock 路径 (`domains.stats.*` 而非 `api.admin.ai.*`)
    - 认证 mock 无效（`@patch` 在 TestClient 中不生效）
    - Rate limiter 尝试连接 Redis 导致测试失败
    - 缺少 `Path` 导入导致测试无法收集

  - **解决方案**：
    - ✅ 修复 `api/user/tasks.py` 缺失的 `Path` 导入
    - ✅ 添加早期模块 mock (`infrastructure.rate_limiter`, `application.services.ai_reports`)
    - ✅ 实现 FastAPI dependency override 模式用于 admin 认证
    - ✅ 修正所有 mock 路径为 `api.admin.ai.*`
    - ✅ 更新错误断言适配自定义错误格式 (`message`/`detail`)
    - ✅ 修正 `generate_report` 测试使用查询参数而非 JSON body

  - **测试结果**：
    - 之前：21 failed, 16 passed ❌
    - 之后：37 passed, 0 failed ✅
    - 执行时间：~1 秒

  - **新增测试覆盖**：
    - 基础认证测试 (5)
    - 参数验证单元测试 (11)
    - 带 mock 的集成测试 (3)
    - 成功场景测试 (8)
    - 参数验证集成测试 (6)
    - 异常处理测试 (4)
    - 边界情况测试 (6)

### Changed
- **测试基础设施改进**
  - 新增 fixtures：`mock_limiter`, `override_require_admin`
  - 使用 FastAPI 最佳实践的 dependency override 模式
  - 早期模块 mock 防止导入时错误
  - 正确的 mock 路径策略（mock where used, not where defined）

### Technical Details
- **修改的文件**：
  - `api/user/tasks.py` - 添加缺失的 `Path` 导入
  - `tests/api/admin/test_ai.py` - 完全重写 (560 行)
    - 新增早期模块 mock
    - 实现 FastAPI dependency override fixtures
    - 修正所有 domain service mock 路径
    - 修正参数格式和错误断言

- **提交记录**：
  - `13f6bac` - fix(api): add missing Path import to tasks.py
  - `30c0347` - refactor(tests): complete rewrite of test_ai.py - all 37 tests passing
  - `5c78220` - chore(docs): delete Test-AI-Rewrite-TODO.md - task completed

## [3.23.1] - 2026-01-07

### Fixed
- **修复 Platform 域缺失导出** (commit: e3ffe03)
  - 问题：`application/commands/platform.py` 导入的 `TargetType` 和 `ExperimentVariant` 未在 `domains/platform/__init__.py` 中导出
  - 解决：添加 `TargetType` 和 `ExperimentVariant` 到 platform 域的 imports 和 `__all__`

- **修复 DomainException 导入错误** (commit: b01ae31)
  - 问题：`domains/*/exceptions.py` 试图导入不存在的 `DomainException` 类
  - 解决：所有域异常基类改为继承 `AppException`（与 billing 域一致）
  - 影响域：identity, creation, marketplace, platform
  - 异常类现在正确使用 `status_code`, `default_code`, `default_message` 模式

- **修正积分消耗配置值** (commit: 0672827)
  - AI 文本生成设置为 0 积分（当前免费策略）
  - 统一 OCR 和 Smart Scan 为 10 积分（无区分）
  - 修改文件：
    - `ddl.sql`: 更新 system_configs 初始数据
    - `domains/billing/service.py`: 更新 EMERGENCY_FALLBACK_COSTS
    - `docs/后台业务逻辑说明.md`: 更新积分消耗表

## [3.23.0] - 2026-01-07

### Added
- **数据库驱动的积分配置系统** ([ADR-0002](docs/adr/0002-database-driven-config.md))
  - Admin 可通过 `system_configs` 表动态调整积分消耗
  - 支持 A/B 测试不同定价策略
  - 优雅降级：数据库不可用时使用 Emergency Fallback
  - 配置项：
    - `credits.cost.image_generation` (默认: 5)
    - `credits.cost.text_generation` (默认: 0) ✅ 已修正
    - `credits.cost.smart_scan` (默认: 10)
    - `credits.cost.ocr` (默认: 10) ✅ 已修正

- **架构决策记录 (ADR)** 系统
  - 创建 `docs/adr/` 目录记录重要架构决策
  - [ADR-0001](docs/adr/0001-use-ddd-architecture.md): DDD 三层架构
  - [ADR-0002](docs/adr/0002-database-driven-config.md): 数据库驱动配置

### Fixed
- 修复 `ErrorCode.PAYMENT_REQUIRED` 枚举值缺失导致的 Railway 部署错误 (commit: b4ed6ec)
- 修复 `CreditCost` dataclass 初始化错误 (commit: 4bcc7f4)
  - 问题：`CreditCost.__init__()` 被错误地使用 `amount` 和 `operation` 参数实例化
  - 解决：`CreditCost` 是带类级常量的 dataclass，不应实例化
- 修复 `ErrorCode.RESOURCE_NOT_FOUND` 引用错误

### Changed
- **BillingService 配置管理重构**
  - `OPERATION_COSTS` 重命名为 `EMERGENCY_FALLBACK_COSTS` 以明确其用途
  - `get_operation_cost()` 现在从数据库读取配置（通过 ConfigService）
  - 添加 `config_service` 依赖注入支持
  - 使用 fallback 时记录 WARNING 级别日志

### Documentation
- 更新 `docs/后台业务逻辑说明.md`
  - 添加 6.3.1 节：积分消耗配置管理
  - 补充配置来源、优势、Admin 操作指南
- 创建完整的 ADR 文档体系
- 新增 CHANGELOG.md

### Technical Details
- **修改的文件**:
  - `domains/billing/service.py` - 实现数据库驱动配置
  - `ddl.sql` - 添加积分配置初始数据
  - `core/exceptions/base.py` - 添加 PAYMENT_REQUIRED 错误码
  - `domains/billing/exceptions.py` - 修正异常引用

- **提交记录**:
  - `b4ed6ec` - fix: add ErrorCode.PAYMENT_REQUIRED
  - `4bcc7f4` - fix(billing): correct CreditCost usage
  - `f44b06b` - feat(billing): implement database-driven credit cost configuration

---

## [3.22.0] - 2026-01-06

### Added
- **DDD 三层架构重构** ([ADR-0001](docs/adr/0001-use-ddd-architecture.md))
  - Core 层：框架层（100% 复用）
  - Domain 层：业务核心（Aggregates, Value Objects, Domain Services）
  - Infrastructure 层：基础设施（Repositories）
  - Application 层：用例编排（Commands, Queries）
  - API 层：HTTP 接口

- **领域模型实现**:
  - `domains/billing/` - 计费域（UserCredits aggregate）
  - `domains/identity/` - 身份域（UserProfile aggregate）
  - `domains/creation/` - 创作域（Project aggregate）
  - `domains/marketplace/` - 市场域（Listing aggregate）
  - `domains/platform/` - 平台域（FeatureFlag, Experiment）

- **Repository 模式**:
  - `infrastructure/repositories/credit_repository.py` - SupabaseCreditRepository
  - `infrastructure/repositories/user_repository.py` - SupabaseUserRepository
  - `infrastructure/repositories/project_repository.py` - SupabaseProjectRepository
  - `infrastructure/repositories/listing_repository.py` - SupabaseListingRepository

- **CQRS 模式**:
  - `application/commands/` - 写操作处理器
  - `application/queries/` - 读操作处理器

### Changed
- 重构数据访问层：从直接使用 Supabase 客户端改为 Repository 模式
- 业务逻辑从 services 层迁移到 domains 层

### Technical Details
- 40+ 新增测试文件（单元测试、API 测试、集成测试）
- 测试覆盖率从 60% 提升到 80%+

---

## 版本说明

### 版本号规则
遵循语义化版本 (Semantic Versioning):
- **主版本号 (X.0.0)**: 重大架构变更、不兼容改动
- **次版本号 (0.Y.0)**: 新增功能、兼容性改进
- **补丁版本 (0.0.Z)**: Bug 修复、文档更新

### 版本历史
完整版本历史请参见 `docs/后台业务逻辑说明.md` 的版本历史章节。

---

[Unreleased]: https://github.com/willnzy/decodables/compare/v3.23.0...HEAD
[3.23.0]: https://github.com/willnzy/decodables/compare/v3.22.0...v3.23.0
[3.22.0]: https://github.com/willnzy/decodables/releases/tag/v3.22.0
