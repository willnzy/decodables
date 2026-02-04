# ADR-0002 数据库驱动配置

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

系统配置统一存入数据库 `system_configs`，避免硬编码。

## 影响

- Admin 可动态配置
- 配置变更可审计
