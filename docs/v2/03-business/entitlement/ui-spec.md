# 权限 UI 交互规范

> 权限锁定、试用提示与配额交互规范。

**状态**: active  
**版本**: 1.0.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Frontend Team  
**适用范围**: shared  
**source_repo**: frontend  
**sync_required**: yes

---

## 状态映射

- `full`: 正常显示
- `trial`: 试用期标识 + 提示
- `locked`: 锁定 + 升级弹窗

## 交互规范

| 场景 | 交互 |
|------|------|
| 功能锁定 | 锁图标 + Upgrade Modal |
| 配额耗尽 | 按钮置灰 + Tooltip |
| 试用期结束 | Banner + 只读模式 |
