# ADR-0001 使用 DDD 架构

**状态**: active  
**版本**: 1.0.0  
**版本日期**: 2026-01-09  
**最后复核**: 2026-02-04  
**负责人**: Backend Team  
**适用范围**: backend  
**source_repo**: backend  
**sync_required**: no

---

## 决策

采用 DDD 分层架构：

```
api → application → domains ← infrastructure
```

## 影响

- API 只调用 Service
- Repository 通过接口定义
