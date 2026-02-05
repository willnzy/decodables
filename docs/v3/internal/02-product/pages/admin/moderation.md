# 内容审核页面

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **对应代码**: `decodables-fe/app/admin/moderation/page.tsx`

---

## 概述

用户提交内容的审核管理。

---

## 页面功能

### 待审核列表
- Marketplace 商品
- 用户举报
- 自动检测违规

### 审核操作
- 通过
- 拒绝（选择原因）
- 标记需修改

### 审核记录
- 审核历史
- 审核员操作日志

---

## 审核流程

```
提交 → 自动检测 → 人工审核 → 通过/拒绝
                         ↓
                    反馈给用户
```

---

## 相关文档

- [Marketplace 功能规格](../../features/marketplace.md)
- [内容规范](../../../../public/legal/content-guidelines.md)
