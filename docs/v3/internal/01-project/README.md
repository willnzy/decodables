# Make Decodables 项目简介

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟢 已验证
> **同步范围**: [fullstack]
> **数据来源**: `CLAUDE.md`

---

## 🎯 AI 上下文入口

> 如果你是 AI 助手，请首先阅读本文档了解项目背景。

---

## 1. 产品概述

**Make Decodables** 是一个在线 Decodable 创作工具，帮助教师和家长创建适合儿童阅读水平的教材。

### 核心功能

| 功能 | 说明 |
|------|------|
| **编辑器** | 在线画布编辑器，支持文字、图片、手绘 |
| **AI 功能** | AI 生图、AI 生成页面、OCR 识别 |
| **模板市场** | 用户可以浏览、购买、出售模板 |
| **订阅体系** | 免费/付费套餐 + 积分系统 |

### 目标用户

- 小学教师
- 家长
- 教育内容创作者

---

## 2. 技术栈

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| Next.js | 16.1.1 | 框架（App Router） |
| React | 19.2.3 | UI 库 |
| TypeScript | 5.9 | 类型系统 |
| Zustand | 5.0.9 | 状态管理 |
| Fabric.js | 5.3.0 | 画布编辑器 |
| Tailwind CSS | - | 样式 |

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | 0.128.0 | API 框架 |
| Python | 3.12.7 | 语言 |
| Pydantic | 2.12.5 | 数据验证 |
| Supabase | - | 数据库（PostgreSQL） |
| JWT | HS256 | 认证 |
| Stripe | - | 支付 |

### AI 服务

| 服务 | 用途 |
|------|------|
| FAL.ai | AI 生图 |
| OpenAI | AI 生成 |
| Vercel AI SDK | 前端 AI 集成 |

### 部署

| 服务 | 用途 |
|------|------|
| Vercel | 前端部署 |
| Railway | 后端部署 |

---

## 3. 架构概览

```
┌─────────────┐     ┌─────────────┐
│   Vercel    │     │   Railway   │
│  (Frontend) │────▶│  (Backend)  │
└─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │   Supabase  │
                    │ (PostgreSQL)│
                    └─────────────┘
```

### 后端架构（DDD）

```
api/          # API 路由层
application/  # 应用服务层（用例编排）
domains/      # 领域层（业务核心）
infrastructure/ # 基础设施层
shared/       # 共享服务（AI/支付/存储）
core/         # 框架层
```

### 前端架构

```
app/          # Next.js 页面
@core/        # 框架层（100% 复用）
@shared/      # 共享层（auth/analytics）
@business/    # 业务层（stores/services/hooks）
```

---

## 4. 业务规则速查

### 用户 ID 系统

| 标识符 | 格式 | 用途 |
|--------|------|------|
| `user_id` | UUID v4 | 数据库主键，API 调用 |
| `user_code` | 26位数字 | 用户反馈，管理员搜索 |

### Tier 体系

| 代码 | 显示名称 | 月度积分 |
|------|----------|----------|
| `t1` | Free Plan | 0 |
| `t2` | Starter Plan | 100 |
| `t3` | Pro Plan | 200 |
| `t4` | (预留) | 待定 |

### 积分规则

| 类型 | 来源 | 有效期 |
|------|------|--------|
| 月度积分 | 订阅发放 | 每月重置 |
| 永久积分 | 充值/活动 | 永久有效 |

**扣费顺序**: 月度积分 → 永久积分

---

## 5. 关键文档索引

| 需求 | 文档位置 |
|------|----------|
| 产品愿景 | [vision.md](vision.md) |
| 技术栈详情 | [tech-stack.md](tech-stack.md) |
| 术语表 | [glossary.md](glossary.md) |
| 决策记录 | [decisions-log.md](decisions-log.md) |
| 业务规则 | [../05-business/](../05-business/) |
| 技术架构 | [../04-engineering/architecture/](../04-engineering/architecture/) |
| 开发规范 | [../04-engineering/development/](../04-engineering/development/) |

---

## 6. 仓库结构

```
AI-WEB/                      # 工作区根目录
├── CLAUDE.md                # Claude Code 配置
├── .claude/                 # Claude Code 文档
│
├── decodables/              # 后端仓库
│   ├── docs/v3/             # 文档（本目录）
│   ├── api/                 # API 路由
│   ├── application/         # 应用层
│   ├── domains/             # 领域层
│   └── ...
│
└── decodables-fe/           # 前端仓库
    ├── docs/v3/             # 文档（镜像）
    ├── app/                 # Next.js 页面
    ├── @core/               # 框架层
    ├── @business/           # 业务层
    └── ...
```

---

## 7. 开发环境

### 后端

```bash
cd decodables
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### 前端

```bash
cd decodables-fe
npm install
npm run dev
```

---

## 变更历史

| 日期 | 变更 |
|------|------|
| 2026-02-05 | 初始版本 |
