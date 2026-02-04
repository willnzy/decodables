# t1 试用期过期处理

> 试用期状态检测与过期后的权限处理规则。

**状态**: active  
**版本**: 1.0.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Product Team  
**适用范围**: shared  
**source_repo**: backend  
**sync_required**: yes

---

## 背景

- 需要统一试用期检测与过期处理规则
- 明确 UI 提醒策略

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 试用期状态检测

```typescript
interface TrialStatus {
  isInTrial: boolean;
  trialDays: number;
  daysRemaining: number;
  trialEndDate: Date;
  registeredAt: Date;
}
```

计算逻辑：

- `trial.default_days` 为试用期天数
- `daysRemaining > 0` 则仍在试用期

---

## 过期后的项目处理

| 场景 | 试用期内 | 试用期过期后 | 处理方式 |
|------|:-------:|:-----------:|---------|
| 编辑已有项目 | ✅ | ❌ 只读 | 进入编辑页面时检测 |
| 创建新项目 | ✅ | ❌ | 新建按钮锁定 |
| 复制项目 | ✅ | ❌ | 复制按钮锁定 |
| 删除项目 | ✅ | ✅ | 允许删除 |
| 查看项目列表 | ✅ | ✅ | 保留可见 |
| 发布到商城 | ✅ | ❌ | Publish 锁定 |
| 导出 PDF/ZIP | ✅ | PDF✅/ZIP❌ | ZIP 锁定 |

---

## UI 提醒策略

采用百分比阈值：

| 剩余比例 | 提醒方式 |
|:-------:|---------|
| > 50% | Banner 可关闭 |
| 15% ~ 50% | Banner 不可关闭 |
| 0% ~ 15% | Modal + Banner |
| 已过期 | 持续 Banner + 只读模式 |

配置项：

```sql
('trial.default_days', '7', 'integer', 'trial'),
('trial.warning_threshold', '0.5', 'float', 'trial'),
('trial.urgent_threshold', '0.15', 'float', 'trial'),
('trial.show_modal_on_expire', 'true', 'boolean', 'trial');
```

---

## 备注

- 试用期过期后 `max_custom_assets = 0`
- 已上传素材保留但冻结，需要升级后解锁

## 影响范围

- 相关模块：Trial 机制与权限
- 相关文档：`docs/v2/03-business/entitlement/permission-matrix.md`

## 证据与验证

- 关键证据来源：`decodables/docs/shared/entitlement/11-trial-expiration.md`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 1.0.0 | 结构对齐模板 | Docs Working Group |
