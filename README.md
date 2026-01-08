# Make Decodables - Backend API

> **Version**: 3.1.0 (DDD Architecture - Fully Migrated)
> **Python**: 3.12+
> **Framework**: FastAPI + Uvicorn
> **Architecture**: Domain-Driven Design (DDD) 三层架构

---

## 🏗️ 架构概览

```
api/ → application/ → domains/ ← infrastructure/
                         ↓
                   core/ + shared/
```

### 核心层级

| 层级 | 目录 | 文件数 | 代码行数 | 职责 |
|------|------|--------|----------|------|
| **API 层** | `api/` | 58 | 11,242 | HTTP 请求处理、路由、DTO |
| **应用层** | `application/` | 55 | 6,961 | 用例编排、Command/Query、定时任务 |
| **领域层** | `domains/` | 58 | 9,691 | 业务规则、聚合根、领域服务 |
| **基础设施层** | `infrastructure/` | 29 | 7,018 | Repository 实现、日志、任务队列 |
| **核心层** | `core/` | 29 | 3,328 | 框架组件 (auth/cache/db/exceptions) |
| **共享层** | `shared/` | 34 | 7,137 | 跨 domain 服务 (ai/payment/storage) |
| **测试** | `tests/` | 135 | 36,975 | 单元测试、集成测试 |
| **总计** | - | **404** | **~85,000** | - |

### 6 个业务领域

- 💰 **billing**: 积分管理、交易记录、支付服务
- 👤 **identity**: 用户身份、订阅等级
- 📝 **creation**: 项目创作、资产管理
- 🛒 **marketplace**: 市场交易、素材发布
- ⚙️ **platform**: Feature Flags、A/B 实验、配置管理
- 📦 **content**: 系统资源、模板管理

---

## 📁 目录结构

```
decodables/
├── 入口文件
│   ├── app.py              # FastAPI 应用入口
│   ├── config.py           # 环境配置
│   ├── container.py        # 依赖注入容器
│   ├── dependencies.py     # FastAPI 依赖
│   ├── scheduler.py        # APScheduler 定时任务
│   └── worker.py           # RQ Worker 后台任务
│
├── DDD 核心层
│   ├── api/                # API 层 - HTTP 路由
│   │   ├── user/           # 用户端 API (27 个路由)
│   │   ├── admin/          # 管理端 API (16 个路由)
│   │   └── schemas/        # Pydantic 请求/响应模型
│   │
│   ├── application/        # 应用层 - 用例编排
│   │   ├── commands/       # 写操作命令
│   │   ├── queries/        # 读操作查询
│   │   ├── handlers/       # Command/Query 处理器
│   │   └── services/       # 应用服务
│   │       ├── aggregators/    # 统计聚合任务
│   │       ├── campaigns/      # 营销活动调度
│   │       ├── experiments/    # A/B 实验服务
│   │       └── metrics/        # 指标 ETL
│   │
│   ├── domains/            # 领域层 - 业务核心
│   │   ├── billing/        # 积分、支付
│   │   ├── identity/       # 用户身份
│   │   ├── creation/       # 项目创作
│   │   ├── marketplace/    # 素材市场
│   │   ├── platform/       # 平台功能
│   │   ├── content/        # 系统资源
│   │   └── shared/         # 共享领域逻辑
│   │
│   ├── infrastructure/     # 基础设施层
│   │   ├── repositories/   # Supabase 仓储实现
│   │   ├── logging/        # 日志服务
│   │   ├── tasks/          # 后台任务
│   │   ├── task_queue/     # RQ 任务队列
│   │   ├── websocket/      # WebSocket 管理
│   │   └── cache/          # 缓存 key 定义
│   │
│   ├── core/               # 框架层 - 通用组件
│   │   ├── auth/           # JWT 认证
│   │   ├── cache/          # Redis/Memory 缓存
│   │   ├── database/       # Supabase 客户端
│   │   ├── exceptions/     # 异常定义
│   │   ├── middleware/     # CORS、日志中间件
│   │   └── utils/          # 工具函数 (datetime, timezone)
│   │
│   └── shared/             # 共享层 - 跨域服务
│       ├── ai/             # AI 服务 (FAL, OpenAI, Qwen)
│       ├── payment/        # Stripe 支付
│       └── storage/        # Supabase Storage
│
├── 测试和脚本
│   ├── tests/              # 测试文件 (135 个)
│   │   ├── api/            # API 测试
│   │   ├── domains/        # 领域测试
│   │   └── integration/    # 集成测试
│   └── scripts/            # 工具脚本
│       ├── migrations/     # 迁移脚本
│       ├── fixes/          # 修复脚本
│       └── tools/          # 开发工具
│
├── 数据库
│   ├── migrations/         # SQL 迁移文件
│   │   ├── ddl.sql         # 完整数据库 DDL
│   │   └── *.sql           # 增量迁移脚本
│   └── supabase/           # Supabase CLI 配置
│
├── 文档
│   ├── docs/
│   │   ├── 后台业务逻辑说明.md      # 业务规则文档
│   │   ├── BACKEND_ARCHITECTURE_GUIDE.md  # 架构指南
│   │   ├── API_REFERENCE.md        # API 参考
│   │   ├── TEST_COVERAGE_PLAN.md   # 测试计划
│   │   ├── shared/                 # 前后端共用文档
│   │   └── adr/                    # 架构决策记录
│   ├── README.md           # 本文件
│   └── CHANGELOG.md        # 变更日志
│
└── 配置文件
    ├── .env.example        # 环境变量模板
    ├── requirements.txt    # Python 依赖
    ├── pytest.ini          # pytest 配置
    ├── .coveragerc         # 覆盖率配置
    ├── railway.toml        # Railway 部署配置
    └── Procfile            # 进程定义
```

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
# 启动烟雾测试
pytest tests/test_app_startup.py -v

# 集成测试 (billing flow)
pytest tests/integration/test_billing_flow.py -v

# 完整测试套件
pytest tests/ -v --cov=. --cov-report=html
```

---

## 📚 文档索引

| 文档 | 用途 |
|------|------|
| [后台业务逻辑说明.md](docs/后台业务逻辑说明.md) | 完整架构文档、业务规则、数据库设计 |
| [BACKEND_ARCHITECTURE_GUIDE.md](docs/BACKEND_ARCHITECTURE_GUIDE.md) | DDD 架构设计指南 |
| [API_REFERENCE.md](docs/API_REFERENCE.md) | API 端点参考 |
| [TEST_COVERAGE_PLAN.md](docs/TEST_COVERAGE_PLAN.md) | 测试覆盖计划 |
| [DDD-Migration-Guide.md](docs/DDD-Migration-Guide.md) | DDD 迁移指南 |

---

## ✅ DDD 迁移状态

### 已完成 ✅

- ✅ Core 框架层 (auth/cache/database/exceptions/middleware/utils)
- ✅ 6 个 Domain (billing/identity/creation/marketplace/platform/content)
- ✅ Application 层 (commands + queries + services)
- ✅ Infrastructure 层 (repositories + logging + tasks)
- ✅ API 层重构 (api/user/ + api/admin/)
- ✅ Schemas 迁移 (api/schemas/)
- ✅ 定时任务迁移 (application/services/)
- ✅ 测试覆盖 (135 个测试文件)
- ✅ 旧代码清理 (schemas/, scheduled_tasks/, routers/)

### DDD 合规性: ~98%

---

## 🔧 关键技术栈

| 类别 | 技术 |
|------|------|
| Web 框架 | FastAPI, Uvicorn |
| 数据库 | Supabase (PostgreSQL) |
| 缓存 | Redis (主), Memory (降级) |
| 认证 | Clerk JWT |
| 支付 | Stripe |
| AI 服务 | FAL.ai (图像), OpenAI (文本), Qwen |
| 任务队列 | Redis Queue (RQ) |
| 定时任务 | APScheduler |
| 测试 | pytest, pytest-asyncio, pytest-cov |

---

## 🚢 部署

### Railway 部署

```bash
# 推送到 develop 分支会自动触发部署
git push origin develop

# 健康检查
curl https://your-app.railway.app/health
```

### 环境变量

必需的环境变量:
- `SUPABASE_URL` - Supabase 项目 URL
- `SUPABASE_KEY` - Supabase service role key
- `CLERK_SECRET_KEY` - Clerk 密钥
- `STRIPE_SECRET_KEY` - Stripe 密钥
- `REDIS_URL` - Redis 连接 (可选，不填则用内存缓存)

---

## 📞 联系方式

- **Issues**: [GitHub Issues](https://github.com/willnzy/decodables/issues)
- **Docs**: [docs/](docs/)

---

**License**: Proprietary
**Maintained by**: Make Decodables Team
**Last Updated**: 2026-01-08
