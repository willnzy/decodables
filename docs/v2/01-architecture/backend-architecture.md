# 后端架构总览（摘要版）

**状态**: active  
**版本**: 1.0.0  
**版本日期**: 2026-01-09  
**最后复核**: 2026-02-04  
**负责人**: Backend Team  
**适用范围**: backend  
**source_repo**: backend  
**sync_required**: no

---

## 架构分层

```
api → application → domains ← infrastructure
```

## 核心原则

- API 层不直接访问 Repository
- Repository 实现必须符合 Interface
- 分页统一使用 offset + limit
