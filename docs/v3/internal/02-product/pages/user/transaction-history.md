# 交易记录页面

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **对应代码**: `decodables-fe/app/transaction-history/page.tsx`

---

## 概述

用户的交易历史记录页面。

---

## 页面功能

### 交易列表
- 日期筛选
- 类型筛选
- 搜索

### 交易详情
- 交易 ID
- 金额
- 状态
- 发票链接

---

## 交易类型

| 类型 | 说明 |
|------|------|
| subscription | 订阅付款 |
| credits | 积分充值 |
| purchase | 素材购买 |
| sale | 素材销售收入 |
| refund | 退款 |

---

## 相关文档

- [计费模块技术设计](../../../04-engineering/modules/billing/)
- [计费功能规格](../../features/billing.md)
