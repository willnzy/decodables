# Make Decodables - Backend API

> **Version**: 3.0.0 (DDD Architecture)
> **Python**: 3.12+
> **Framework**: FastAPI + Uvicorn
> **Architecture**: Domain-Driven Design (DDD) 三层架构

---

## 🏗️ 架构概览

```
api/ → application/ → domains/ + infrastructure/
                         ↓
                   core/ + shared/
```

### 核心层级

| 层级 | 目录 | 职责 |
|------|------|------|
| **API 层** | `api/` | HTTP 请求处理、DTO 转换 |
| **应用层** | `application/` | 用例编排、Command/Query |
| **领域层** | `domains/` | 业务规则、聚合根、领域服务 |
| **基础设施层** | `infrastructure/` | Repository 实现、第三方集成 |
| **核心层** | `core/` | 框架组件 (auth/cache/db/exceptions) |
| **共享层** | `shared/` | 跨 domain 服务 (ai/payment/storage) |

### 5 个业务领域

- 💰 **billing**: 积分管理、交易记录
- 👤 **identity**: 用户身份、订阅等级
- 📝 **creation**: 项目创作、资产管理
- 🛒 **marketplace**: 市场交易、素材发布
- ⚙️ **platform**: Feature Flags、A/B 实验

---

## 🚀 快速开始

### 本地开发

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 Supabase, Clerk, Stripe 等密钥

# 3. 启动应用
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# 4. 访问 API 文档
open http://localhost:8000/docs
```

### 运行测试

```bash
# 启动烟雾测试 (8 tests)
pytest tests/test_app_startup.py -v

# 集成测试 (billing flow)
pytest tests/integration/test_billing_flow.py -v

# Domain 层测试
pytest tests/domains/ -v

# 完整测试套件
pytest tests/ -v --cov=. --cov-report=html
```

---

## 📚 文档索引

| 文档 | 用途 |
|------|------|
| [后台业务逻辑说明.md](docs/后台业务逻辑说明.md) | 完整架构文档、业务规则 |
| [DDD-Migration-Guide.md](docs/DDD-Migration-Guide.md) | DDD 迁移指南、代码对比 |
| [LEGACY_CODE_CLEANUP_PLAN.md](docs/LEGACY_CODE_CLEANUP_PLAN.md) | 旧代码清理计划 |
| [TEST_COVERAGE_PLAN.md](docs/TEST_COVERAGE_PLAN.md) | 测试覆盖计划 |

---

## ✅ v3.0 迁移完成状态

### Phase 1-2: 新架构创建 ✅
- ✅ Core 框架层 (auth/cache/database/exceptions/middleware/utils)
- ✅ 5 个 Domain (billing/identity/creation/marketplace/platform)
- ✅ Application 层 (commands + queries)
- ✅ Infrastructure 层 (repositories)

### Phase 3: 清理与验证 ✅
- ✅ 删除废弃目录 (`repositories/`, `exceptions/`)
- ✅ 向后兼容层 (`exceptions.py`)
- ✅ 测试覆盖 (34/34 核心测试通过)
- ✅ 文档更新 (3 份完整文档)
- ✅ 旧代码审计 (详细清理计划)

### Phase 4: 旧代码清理 (待执行)
- ⏳ 迁移 `services/ai/` → `shared/ai/`
- ⏳ 迁移 `routers/` → `api/`
- ⏳ 更新引用并删除旧文件

---

## 🧪 测试覆盖

| 测试类型 | 通过 | 总计 | 覆盖率 |
|---------|------|------|--------|
| **启动烟雾** | 8 | 8 | 100% ✅ |
| **集成测试** (billing) | 8 | 8 | 100% ✅ |
| **Domain 层** (marketplace) | 8 | 8 | 100% ✅ |
| **Domain 层** (platform) | 10 | 10 | 100% ✅ |
| **总核心测试** | **34** | **34** | **100%** ✅ |

---

## 🔧 关键技术栈

| 类别 | 技术 |
|------|------|
| Web 框架 | FastAPI, Uvicorn |
| 数据库 | Supabase (PostgreSQL) |
| 缓存 | Redis (主), Memory (降级) |
| 认证 | Clerk JWT |
| 支付 | Stripe |
| AI 服务 | FAL.ai (图像), OpenAI (文本) |
| 任务队列 | Redis Queue (RQ) |
| 测试 | pytest, pytest-asyncio |

---

## 📊 代码统计

```
核心代码结构:
├── core/           ~2,500 lines  (框架层)
├── shared/         ~1,000 lines  (共享服务)
├── domains/        ~3,500 lines  (业务核心)
├── application/    ~1,500 lines  (用例编排)
├── infrastructure/ ~2,000 lines  (技术实现)
├── api/              ~800 lines  (新API层)
└── tests/          ~2,000 lines  (测试覆盖)
─────────────────────────────────
Total:             ~13,300 lines

旧代码 (待清理):
├── services/       ~5,000 lines
└── routers/        ~3,000 lines
```

---

## 🚢 部署

### Railway 部署

```bash
# 推送到 develop 分支会自动触发部署
git push origin develop

# 监控部署日志
railway logs

# 健康检查
curl https://your-app.railway.app/health
```

### 环境变量

必需的环境变量:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `CLERK_SECRET_KEY`
- `STRIPE_SECRET_KEY`
- `REDIS_URL` (可选，不填则用内存缓存)

---

## 👥 团队协作

### Git 工作流

```bash
# 主分支
main     - 生产环境 (Railway production)
develop  - 开发环境 (Railway staging)

# 功能分支
feature/xxx  - 新功能开发
fix/xxx      - Bug 修复
refactor/xxx - 代码重构
```

### Commit 规范

```
feat(billing): add credit refund functionality
fix(auth): resolve JWT token expiration issue
refactor(domains): migrate services to DDD structure
docs(api): update API documentation
test(integration): add billing flow tests
chore(deps): update dependencies
```

---

## 📖 学习资源

- **DDD 入门**: 阅读 [DDD-Migration-Guide.md](docs/DDD-Migration-Guide.md)
- **业务规则**: 阅读 [后台业务逻辑说明.md](docs/后台业务逻辑说明.md)
- **代码示例**: 查看 `domains/billing/` 完整实现
- **测试示例**: 查看 `tests/integration/test_billing_flow.py`

---

## 🆘 故障排查

### 应用无法启动

```bash
# 检查依赖
pip list | grep fastapi

# 检查环境变量
python3 -c "from config import settings; print(settings)"

# 检查数据库连接
python3 -c "from core.database import get_supabase_client; print(get_supabase_client())"
```

### 测试失败

```bash
# 清理缓存
pytest --cache-clear

# 详细错误信息
pytest tests/xxx.py -vv --tb=long

# 单个测试
pytest tests/xxx.py::test_function_name -v
```

---

## 📞 联系方式

- **Issues**: [GitHub Issues](https://github.com/willnzy/decodables/issues)
- **Docs**: [docs/](docs/)

---

**License**: Proprietary
**Maintained by**: Make Decodables Team
**Last Updated**: 2026-01-07
