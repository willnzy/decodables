# 架构设计

> **同步范围**: [fullstack]
> **状态**: 🟡 待完善

---

## 目录说明

系统架构设计文档，包括后端、前端、数据库架构。

## 计划文档

| 文档 | 用途 | 同步 | 状态 |
|------|------|------|------|
| `overview.md` | 架构总览 | fullstack | 📋 待创建 |
| `backend.md` | 后端架构（DDD 分层） | backend | 📋 待创建 |
| `frontend.md` | 前端架构（Next.js + Zustand） | frontend | 📋 待创建 |
| `database.md` | 数据库设计 | backend | 📋 待创建 |
| `decisions/` | ADR 决策记录 | fullstack | 📁 目录 |

## 架构原则

- 后端：DDD 分层架构（domains → application → api）
- 前端：三层架构（@core → @shared → @business）
- 数据库：PostgreSQL (Supabase)
