# Entitlement 实现参考

> 数据库、后端与前端实现要点汇总。

**状态**: needs-review  
**版本**: 1.0.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Backend + Frontend  
**适用范围**: shared  
**source_repo**: backend  
**sync_required**: yes

---

## 数据库

- system_configs 配置
- user_feature_overrides
- 审计日志表

## 后端

- EntitlementService / FeatureFlagService
- FeatureAccess 评估结果
- `/api/v2/user/features` 输出

## 前端

- useEntitlementStore
- FeatureGate/QuotaGuard
*** End Patch}]}Commentary to=functions.ApplyPatch code
