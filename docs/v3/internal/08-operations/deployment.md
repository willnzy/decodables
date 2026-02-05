# 部署流程

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]

---

## 概述

应用部署流程和配置。

---

## 部署环境

| 环境 | 用途 | 平台 |
|------|------|------|
| Production | 生产环境 | Vercel + Railway |
| Staging | 预发布测试 | Vercel + Railway |
| Development | 本地开发 | 本地 |

---

## 部署架构

```
┌─────────────┐     ┌─────────────┐
│   Vercel    │     │   Railway   │
│  (Frontend) │────▶│  (Backend)  │
└─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │   Supabase  │
                    │ (Database)  │
                    └─────────────┘
```

---

## 详细文档

- [部署与扩展](./deployment-scaling.md) - 完整部署和扩展指南

---

## 相关文档

- [监控告警](./monitoring.md)
- [故障处理](./troubleshooting.md)
