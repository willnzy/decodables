# 素材分类系统技术设计

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **来源**: v1 shared/asset-category-design.md

---

## 概述

素材分类系统的技术设计，支持 10 种素材类型。

---

## 分类定义

| 代码 | 显示名称 | 说明 |
|------|----------|------|
| backgrounds | 背景 | 背景图案、纹理 |
| borders | 边框 | 装饰边框、相框 |
| characters | 人物/角色 | 人物、动物、卡通角色 |
| clipart | 剪贴画 | 通用剪贴画 |
| decorations | 装饰 | 装饰元素、点缀 |
| icons | 图标 | 图标、符号 |
| patterns | 图案 | 重复图案、平铺纹理 |
| shapes | 形状 | 基础形状、几何图形 |
| stickers | 贴纸 | 贴纸、标签 |
| text-effects | 文字效果 | 艺术字、文字装饰 |

---

## 数据模型

```typescript
interface AssetCategory {
  code: string;        // 系统代码，不变
  name: string;        // 显示名称，可配置
  icon: string;        // 图标
  sort_order: number;  // 排序
  is_active: boolean;  // 是否启用
}

interface Asset {
  id: string;
  category: string;    // 分类代码
  name: string;
  thumbnail_url: string;
  file_url: string;
  is_premium: boolean; // 付费素材
  tags: string[];
  created_at: Date;
}
```

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/assets/categories | 分类列表 |
| GET | /api/assets | 素材列表 (支持分类筛选) |
| POST | /api/admin/assets | 上传素材 |

---

## 相关文档

- [Admin 内容管理页面](../../../02-product/pages/admin/content.md)
- [Marketplace 功能规格](../../../02-product/features/marketplace.md)
