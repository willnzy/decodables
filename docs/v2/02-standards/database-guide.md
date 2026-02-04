# 数据库开发规范（摘要版）

**状态**: active  
**版本**: 2.0.0  
**版本日期**: 2026-01-11  
**最后复核**: 2026-02-04  
**负责人**: Backend Team  
**适用范围**: backend  
**source_repo**: backend  
**sync_required**: no

---

## Schema 管理

- 仅修改 `migrations/v2/01|02|03` 三个主文件
- 不创建临时迁移脚本

## RPC 与索引

- RPC 放在主文件末尾
- 索引使用部分索引（按需要）
