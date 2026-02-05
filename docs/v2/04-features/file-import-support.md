# 文件格式导入支持设计

**状态**: active  
**版本**: 1.0.0  
**版本日期**: 2026-01-06  
**最后复核**: 2026-02-04  
**负责人**: Frontend Team  
**适用范围**: frontend  
**source_repo**: frontend  
**sync_required**: no

---

## 背景

- 问题或机会: 文件导入类型与流程缺少统一约束
- 目标与非目标: 目标是统一导入能力与校验规则；非目标是覆盖所有文件格式

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 结论/规范/方案

- 文件格式导入能力规划与实现方案
- 导入工作流与兼容策略

## 影响范围

- 相关模块: 文件导入与资源管理
- 相关文档: `docs/v2/04-features/editor-media-properties.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/`、`decodables-fe/@core/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 1.0.0 | 结构对齐与信息补齐 | Docs Working Group |

## 目录

1. [用户场景分析](#1-用户场景分析)
2. [常用软件与格式](#2-常用软件与格式)
3. [格式支持优先级](#3-格式支持优先级)
4. [技术实现方案](#4-技术实现方案)
5. [各格式详细处理](#5-各格式详细处理)
6. [导入工作流设计](#6-导入工作流设计)
7. [实施计划](#7-实施计划)

---

## 1. 用户场景分析

### 1.1 目标用户群体

```
┌─────────────────────────────────────────────────────────────────┐
│                    目标用户与使用场景                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  👩‍🏫 K-12 教师                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  常用软件: Canva, Google Drawings, PowerPoint            │   │
│  │  使用场景: 在其他工具创建插图，导入 Make Decodables       │   │
│  │  典型格式: PNG, JPG, PDF                                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  👨‍👩‍👧 家长/业余创作者                                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  常用软件: Procreate (iPad), Canva, 手机绘图 App          │   │
│  │  使用场景: 手绘插图导入，照片处理后使用                    │   │
│  │  典型格式: PNG, JPG, PSD, HEIC                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  🎨 专业插画师/设计师                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  常用软件: Illustrator, Photoshop, Procreate, Affinity   │   │
│  │  使用场景: 专业插画导入，保持矢量可编辑性                  │   │
│  │  典型格式: SVG, AI, EPS, PSD, PDF                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  📚 出版商/内容团队                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  常用软件: Adobe Creative Suite, Sketch, Figma           │   │
│  │  使用场景: 批量素材导入，保持品牌一致性                    │   │
│  │  典型格式: SVG, AI, PDF, EPS                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 导入需求优先级

| 需求 | 重要性 | 用户比例 |
|------|--------|----------|
| 导入手绘/照片 (PNG/JPG) | 🔴 最高 | 95% |
| 导入矢量图 (SVG) | 🔴 最高 | 60% |
| 导入 PDF 插图 | 🟡 高 | 40% |
| 导入 Procreate 作品 | 🟡 高 | 25% (iPad用户) |
| 导入 PSD 分层文件 | 🟢 中 | 20% |
| 导入 AI/EPS 文件 | 🟢 中 | 15% |
| 导入其他专有格式 | ⚪ 低 | 5% |

---

## 2. 常用软件与格式

### 2.1 美国市场常用绘图软件

```
┌─────────────────────────────────────────────────────────────────┐
│                    常用绘图软件分析                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📱 移动端 / iPad                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. Procreate          ⭐⭐⭐⭐⭐ (iPad 最流行)            │   │
│  │     原生格式: .procreate                                  │   │
│  │     导出格式: PSD, PNG, JPG, PDF, TIFF                    │   │
│  │                                                          │   │
│  │  2. Procreate Dreams   ⭐⭐⭐ (动画)                       │   │
│  │     导出格式: MP4, GIF, PNG序列                           │   │
│  │                                                          │   │
│  │  3. Tayasui Sketches   ⭐⭐⭐                              │   │
│  │     导出格式: PNG, JPG, PSD                               │   │
│  │                                                          │   │
│  │  4. Adobe Fresco       ⭐⭐⭐                              │   │
│  │     导出格式: PSD, PNG, JPG, PDF                          │   │
│  │                                                          │   │
│  │  5. Concepts           ⭐⭐⭐ (矢量)                       │   │
│  │     导出格式: SVG, PDF, PNG                               │   │
│  │                                                          │   │
│  │  6. Paper by WeTransfer ⭐⭐                               │   │
│  │     导出格式: PNG, JPG, PDF                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  💻 桌面端                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. Adobe Illustrator  ⭐⭐⭐⭐⭐ (矢量标准)               │   │
│  │     原生格式: .ai                                         │   │
│  │     导出格式: SVG, EPS, PDF, PNG                          │   │
│  │                                                          │   │
│  │  2. Adobe Photoshop    ⭐⭐⭐⭐⭐ (位图标准)               │   │
│  │     原生格式: .psd                                        │   │
│  │     导出格式: PNG, JPG, TIFF, PDF                         │   │
│  │                                                          │   │
│  │  3. Affinity Designer  ⭐⭐⭐⭐ (AI 替代品)                │   │
│  │     原生格式: .afdesign                                   │   │
│  │     导出格式: SVG, EPS, PDF, PSD, PNG                     │   │
│  │                                                          │   │
│  │  4. Affinity Photo     ⭐⭐⭐⭐ (PS 替代品)                │   │
│  │     原生格式: .afphoto                                    │   │
│  │     导出格式: PSD, PNG, JPG, TIFF                         │   │
│  │                                                          │   │
│  │  5. CorelDRAW          ⭐⭐⭐ (企业用户)                   │   │
│  │     原生格式: .cdr                                        │   │
│  │     导出格式: SVG, EPS, PDF, AI                           │   │
│  │                                                          │   │
│  │  6. Inkscape           ⭐⭐⭐ (免费开源)                   │   │
│  │     原生格式: .svg                                        │   │
│  │     导出格式: SVG, PDF, EPS, PNG                          │   │
│  │                                                          │   │
│  │  7. Sketch             ⭐⭐⭐ (Mac, UI设计)                │   │
│  │     原生格式: .sketch                                     │   │
│  │     导出格式: SVG, PDF, PNG                               │   │
│  │                                                          │   │
│  │  8. Figma              ⭐⭐⭐⭐ (在线协作)                 │   │
│  │     原生格式: 云端 (.fig)                                 │   │
│  │     导出格式: SVG, PDF, PNG, JPG                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  🌐 在线工具                                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. Canva              ⭐⭐⭐⭐⭐ (教育最流行)             │   │
│  │     导出格式: PNG, JPG, PDF, SVG (Pro)                    │   │
│  │                                                          │   │
│  │  2. Google Drawings    ⭐⭐⭐⭐ (学校常用)                 │   │
│  │     导出格式: SVG, PNG, JPG, PDF                          │   │
│  │                                                          │   │
│  │  3. Microsoft PowerPoint ⭐⭐⭐⭐                          │   │
│  │     导出格式: PNG, JPG, SVG, PDF, EMF                     │   │
│  │                                                          │   │
│  │  4. Pixlr              ⭐⭐⭐                              │   │
│  │     导出格式: PNG, JPG, PXD                               │   │
│  │                                                          │   │
│  │  5. Photopea           ⭐⭐⭐ (在线PS)                     │   │
│  │     导出格式: PSD, PNG, JPG, SVG                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  🖍️ 儿童/教育绘图                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. Tux Paint          ⭐⭐⭐ (K-5)                        │   │
│  │     导出格式: PNG                                         │   │
│  │                                                          │   │
│  │  2. KidPix             ⭐⭐ (经典)                         │   │
│  │     导出格式: PNG, JPG                                    │   │
│  │                                                          │   │
│  │  3. Seesaw             ⭐⭐⭐⭐ (教育平台)                 │   │
│  │     导出格式: PNG, JPG                                    │   │
│  │                                                          │   │
│  │  4. Book Creator       ⭐⭐⭐⭐                            │   │
│  │     导出格式: ePub, PDF, PNG                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 格式类型总结

```
┌─────────────────────────────────────────────────────────────────┐
│                    文件格式分类                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📐 矢量格式 (可缩放，可编辑路径)                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  .svg  - 标准矢量格式，Web 友好               ⭐ 必须支持  │   │
│  │  .ai   - Adobe Illustrator 原生格式          ⭐ 建议支持  │   │
│  │  .eps  - 封装 PostScript，印刷标准           ⭐ 建议支持  │   │
│  │  .pdf  - 可包含矢量内容                      ⭐ 必须支持  │   │
│  │  .emf  - Windows 增强图元文件                  可选支持   │   │
│  │  .wmf  - Windows 图元文件 (旧)                 可选支持   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  🖼️ 位图格式 (像素图像)                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  .png  - 无损压缩，透明支持                  ⭐ 必须支持  │   │
│  │  .jpg  - 有损压缩，照片标准                  ⭐ 必须支持  │   │
│  │  .webp - 现代格式，更小体积                  ⭐ 必须支持  │   │
│  │  .gif  - 动画支持，256色                     ⭐ 建议支持  │   │
│  │  .tiff - 无损，印刷质量                        建议支持   │   │
│  │  .bmp  - Windows 位图                          可选支持   │   │
│  │  .heic - Apple 格式 (iPhone)                 ⭐ 建议支持  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  📦 分层/项目格式 (保留图层结构)                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  .psd  - Photoshop，行业标准                 ⭐ 建议支持  │   │
│  │  .xcf  - GIMP 原生格式                         可选支持   │   │
│  │  .kra  - Krita 原生格式                        可选支持   │   │
│  │  .ora  - OpenRaster，开放标准                  可选支持   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  🔒 专有格式 (需特殊处理)                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  .procreate - Procreate (可读取)             ⭐ 高优先级  │   │
│  │  .sketch    - Sketch (Mac)                     可选支持   │   │
│  │  .afdesign  - Affinity Designer                可选支持   │   │
│  │  .cdr       - CorelDRAW                        可选支持   │   │
│  │  .clip      - Clip Studio Paint                可选支持   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 格式支持优先级

### 3.1 分层优先级

```
┌─────────────────────────────────────────────────────────────────┐
│                    格式支持优先级                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🔴 P0 - 必须支持 (MVP)                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  格式          用途                    技术难度          │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  PNG           基础位图，透明支持      ⭐ (原生支持)      │   │
│  │  JPG/JPEG      照片导入               ⭐ (原生支持)      │   │
│  │  WebP          现代位图               ⭐ (原生支持)      │   │
│  │  SVG           矢量图导入             ⭐⭐ (需解析)       │   │
│  │  GIF           动图/静态              ⭐ (原生支持)      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  🟡 P1 - 高优先级 (Phase 2)                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  格式          用途                    技术难度          │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  PDF           文档/矢量              ⭐⭐⭐ (需库)       │   │
│  │  PSD           Photoshop 分层         ⭐⭐⭐ (需库)       │   │
│  │  HEIC/HEIF     iPhone 照片            ⭐⭐ (需转换)       │   │
│  │  .procreate    Procreate 文件         ⭐⭐⭐⭐ (逆向)     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  🟢 P2 - 中优先级 (Phase 3)                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  格式          用途                    技术难度          │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  AI            Illustrator            ⭐⭐⭐⭐ (复杂)     │   │
│  │  EPS           印刷矢量               ⭐⭐⭐ (需库)       │   │
│  │  TIFF          高质量位图             ⭐⭐ (需库)        │   │
│  │  EMF/WMF       Windows 矢量           ⭐⭐⭐              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ⚪ P3 - 低优先级 (未来)                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  .sketch, .afdesign, .cdr, .xcf, .kra, .ora, .clip      │   │
│  │  建议用户先导出为通用格式 (SVG/PNG/PSD)                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 决策矩阵

| 格式 | 用户需求 | 技术可行性 | 竞品支持 | 优先级 | 工作量 |
|------|----------|------------|----------|--------|--------|
| PNG | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 100% | P0 | 1天 |
| JPG | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 100% | P0 | 1天 |
| SVG | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 90% | P0 | 3天 |
| GIF | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 95% | P0 | 1天 |
| WebP | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 80% | P0 | 1天 |
| PDF | ⭐⭐⭐⭐ | ⭐⭐⭐ | 70% | P1 | 5天 |
| PSD | ⭐⭐⭐⭐ | ⭐⭐⭐ | 50% | P1 | 5天 |
| HEIC | ⭐⭐⭐ | ⭐⭐⭐ | 60% | P1 | 2天 |
| .procreate | ⭐⭐⭐⭐ | ⭐⭐ | 5% | P1 | 7天 |
| AI | ⭐⭐⭐ | ⭐⭐ | 30% | P2 | 7天 |
| EPS | ⭐⭐⭐ | ⭐⭐⭐ | 40% | P2 | 5天 |
| TIFF | ⭐⭐ | ⭐⭐⭐⭐ | 50% | P2 | 2天 |

---

## 4. 技术实现方案

### 4.1 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    文件导入架构                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Import Manager                        │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │  • 格式检测 (Magic Number + Extension)           │    │   │
│  │  │  • 导入器路由                                     │    │   │
│  │  │  • 进度追踪                                       │    │   │
│  │  │  • 错误处理                                       │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│          ┌───────────────────┼───────────────────┐             │
│          │                   │                   │             │
│          ▼                   ▼                   ▼             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐       │
│  │   Raster     │   │   Vector     │   │   Layered    │       │
│  │   Importer   │   │   Importer   │   │   Importer   │       │
│  │              │   │              │   │              │       │
│  │ PNG,JPG,WebP │   │ SVG,PDF,AI   │   │ PSD,Procreate│       │
│  │ GIF,HEIC,BMP │   │ EPS,EMF      │   │ XCF,ORA      │       │
│  └──────────────┘   └──────────────┘   └──────────────┘       │
│          │                   │                   │             │
│          └───────────────────┼───────────────────┘             │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Import Result                          │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │  • 元素数组 (Elements[])                         │    │   │
│  │  │  • 图层信息 (可选)                               │    │   │
│  │  │  • 元数据 (尺寸, DPI, 颜色空间)                  │    │   │
│  │  │  • 警告/转换信息                                 │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Canvas Engine                          │   │
│  │  添加到画布 / 创建新页面 / 替换背景                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 目录结构

```
@core/canvas/import/
├── index.ts                        # 公开 API
├── types.ts                        # 类型定义
│
├── ImportManager.ts                # 导入管理器 (<250 行)
├── FormatDetector.ts               # 格式检测 (<150 行)
│
├── importers/
│   ├── base/
│   │   └── Importer.ts            # 导入器基类 (<100 行)
│   │
│   ├── raster/
│   │   ├── RasterImporter.ts      # 位图导入器 (<150 行)
│   │   ├── PNGImporter.ts         # PNG 处理 (<80 行)
│   │   ├── JPGImporter.ts         # JPG 处理 (<80 行)
│   │   ├── WebPImporter.ts        # WebP 处理 (<80 行)
│   │   ├── GIFImporter.ts         # GIF 处理 (<100 行)
│   │   ├── HEICImporter.ts        # HEIC 转换 (<100 行)
│   │   └── TIFFImporter.ts        # TIFF 处理 (<100 行)
│   │
│   ├── vector/
│   │   ├── VectorImporter.ts      # 矢量导入器 (<200 行)
│   │   ├── SVGImporter.ts         # SVG 解析 (<300 行)
│   │   ├── PDFImporter.ts         # PDF 提取 (<250 行)
│   │   ├── AIImporter.ts          # AI 处理 (<200 行)
│   │   └── EPSImporter.ts         # EPS 处理 (<200 行)
│   │
│   └── layered/
│       ├── LayeredImporter.ts     # 分层导入器 (<150 行)
│       ├── PSDImporter.ts         # PSD 解析 (<300 行)
│       └── ProcreateImporter.ts   # Procreate 解析 (<300 行)
│
├── converters/
│   ├── HEICConverter.ts           # HEIC → JPG (<100 行)
│   ├── ColorSpaceConverter.ts     # 颜色空间转换 (<150 行)
│   └── DPIConverter.ts            # DPI 处理 (<80 行)
│
└── utils/
    ├── magicNumber.ts             # 文件类型检测 (<100 行)
    ├── imageOptimizer.ts          # 图片优化 (<150 行)
    └── svgCleaner.ts              # SVG 清理 (<100 行)
```

### 4.3 依赖库选择

```
┌─────────────────────────────────────────────────────────────────┐
│                    推荐依赖库                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  位图处理:                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  浏览器原生         PNG, JPG, WebP, GIF                   │   │
│  │  heic2any          HEIC → JPG/PNG 转换    (~50KB)        │   │
│  │  utif.js           TIFF 解码              (~30KB)        │   │
│  │  browser-image-    图片压缩优化           (~20KB)        │   │
│  │  compression                                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  矢量处理:                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  @aspect/svg       SVG 解析和操作         (~80KB)        │   │
│  │  svgo              SVG 优化               (~50KB)        │   │
│  │  pdf.js            PDF 渲染和提取         (~500KB)       │   │
│  │  (Mozilla)                                               │   │
│  │  Paper.js          矢量路径操作           (~200KB)       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  分层文件:                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ag-psd            PSD 解析 (完整)        (~150KB)       │   │
│  │  psd.js            PSD 解析 (轻量)        (~50KB)        │   │
│  │  自定义            Procreate 解析         (自研)         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  通用工具:                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  file-type         文件类型检测           (~20KB)        │   │
│  │  iconv-lite        字符编码转换           (~200KB)       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. 各格式详细处理

### 5.1 SVG 导入 (最重要的矢量格式)

```typescript
// @core/canvas/import/importers/vector/SVGImporter.ts

import { Importer, ImportResult, ImportOptions } from '../base/Importer';
import { Element } from '../../../elements/base/Element';
import { PathElement } from '../../../elements/path/PathElement';
import { ImageElement } from '../../../elements/image/ImageElement';
import { TextElement } from '../../../elements/text/TextElement';
import { GroupElement } from '../../../elements/group/GroupElement';

interface SVGImportOptions extends ImportOptions {
  // 是否展开组
  flattenGroups?: boolean;
  
  // 是否转换文本为路径
  convertTextToPath?: boolean;
  
  // 是否保留不支持的元素 (作为图片)
  rasterizeUnsupported?: boolean;
  
  // 是否清理/优化 SVG
  optimize?: boolean;
  
  // 目标尺寸
  targetWidth?: number;
  targetHeight?: number;
}

export class SVGImporter extends Importer {
  readonly supportedFormats = ['svg', 'svgz'];
  
  async import(file: File, options: SVGImportOptions = {}): Promise<ImportResult> {
    const svgText = await this.readAsText(file);
    
    // 1. 清理和优化 SVG
    const cleanedSvg = options.optimize 
      ? await this.optimizeSVG(svgText) 
      : svgText;
    
    // 2. 解析 SVG DOM
    const svgDoc = this.parseSVG(cleanedSvg);
    const svgRoot = svgDoc.documentElement;
    
    // 3. 提取视口和尺寸
    const viewBox = this.parseViewBox(svgRoot);
    const dimensions = this.getDimensions(svgRoot, viewBox);
    
    // 4. 递归转换元素
    const elements = await this.convertElements(
      svgRoot,
      options,
      { x: 0, y: 0 }
    );
    
    // 5. 缩放到目标尺寸
    if (options.targetWidth || options.targetHeight) {
      this.scaleElements(elements, dimensions, options);
    }
    
    return {
      elements,
      metadata: {
        originalWidth: dimensions.width,
        originalHeight: dimensions.height,
        format: 'svg',
        hasText: elements.some(e => e.type === 'text'),
        hasImages: elements.some(e => e.type === 'image'),
      },
      warnings: this.warnings,
    };
  }
  
  private parseSVG(svgText: string): Document {
    const parser = new DOMParser();
    const doc = parser.parseFromString(svgText, 'image/svg+xml');
    
    // 检查解析错误
    const error = doc.querySelector('parsererror');
    if (error) {
      throw new Error(`SVG parse error: ${error.textContent}`);
    }
    
    return doc;
  }
  
  private async convertElements(
    parent: SVGElement,
    options: SVGImportOptions,
    offset: { x: number; y: number }
  ): Promise<Element[]> {
    const elements: Element[] = [];
    
    for (const child of Array.from(parent.children)) {
      const svgChild = child as SVGElement;
      const element = await this.convertElement(svgChild, options, offset);
      
      if (element) {
        if (Array.isArray(element)) {
          elements.push(...element);
        } else {
          elements.push(element);
        }
      }
    }
    
    return elements;
  }
  
  private async convertElement(
    svgElement: SVGElement,
    options: SVGImportOptions,
    offset: { x: number; y: number }
  ): Promise<Element | Element[] | null> {
    const tagName = svgElement.tagName.toLowerCase();
    
    switch (tagName) {
      case 'path':
        return this.convertPath(svgElement as SVGPathElement, offset);
        
      case 'rect':
        return this.convertRect(svgElement as SVGRectElement, offset);
        
      case 'circle':
        return this.convertCircle(svgElement as SVGCircleElement, offset);
        
      case 'ellipse':
        return this.convertEllipse(svgElement as SVGEllipseElement, offset);
        
      case 'line':
        return this.convertLine(svgElement as SVGLineElement, offset);
        
      case 'polyline':
      case 'polygon':
        return this.convertPoly(svgElement, offset);
        
      case 'text':
        if (options.convertTextToPath) {
          return this.convertTextToPath(svgElement as SVGTextElement, offset);
        }
        return this.convertText(svgElement as SVGTextElement, offset);
        
      case 'image':
        return this.convertImage(svgElement as SVGImageElement, offset);
        
      case 'g':
        const children = await this.convertElements(svgElement, options, offset);
        if (options.flattenGroups) {
          return children;
        }
        return this.createGroup(children, svgElement);
        
      case 'use':
        return this.convertUse(svgElement as SVGUseElement, options, offset);
        
      case 'clipPath':
      case 'defs':
      case 'symbol':
        // 跳过定义元素
        return null;
        
      default:
        this.warnings.push(`Unsupported SVG element: <${tagName}>`);
        if (options.rasterizeUnsupported) {
          return this.rasterizeElement(svgElement);
        }
        return null;
    }
  }
  
  private convertPath(path: SVGPathElement, offset: { x: number; y: number }): PathElement {
    const d = path.getAttribute('d') || '';
    const style = this.extractStyle(path);
    const transform = this.extractTransform(path);
    
    const element = new PathElement();
    element.setPathData(d);
    element.setStyle(style);
    element.setTransform({
      x: offset.x + transform.x,
      y: offset.y + transform.y,
      rotation: transform.rotation,
      scaleX: transform.scaleX,
      scaleY: transform.scaleY,
    });
    
    return element;
  }
  
  private extractStyle(svgElement: SVGElement): ElementStyle {
    const computedStyle = window.getComputedStyle(svgElement);
    
    return {
      fill: this.parseColor(
        svgElement.getAttribute('fill') || 
        computedStyle.fill
      ),
      stroke: this.parseColor(
        svgElement.getAttribute('stroke') || 
        computedStyle.stroke
      ),
      strokeWidth: parseFloat(
        svgElement.getAttribute('stroke-width') || 
        computedStyle.strokeWidth || 
        '1'
      ),
      opacity: parseFloat(
        svgElement.getAttribute('opacity') || 
        computedStyle.opacity || 
        '1'
      ),
    };
  }
  
  private async optimizeSVG(svgText: string): Promise<string> {
    // 使用 SVGO 优化
    const { optimize } = await import('svgo');
    
    const result = optimize(svgText, {
      plugins: [
        'removeDoctype',
        'removeXMLProcInst',
        'removeComments',
        'removeMetadata',
        'removeEditorsNSData',
        'cleanupAttrs',
        'mergeStyles',
        'inlineStyles',
        'removeUselessDefs',
        'cleanupNumericValues',
        'convertColors',
        'removeUnknownsAndDefaults',
        'removeNonInheritableGroupAttrs',
        'removeUselessStrokeAndFill',
        'cleanupEnableBackground',
        'removeHiddenElems',
        'removeEmptyText',
        'convertShapeToPath',
        'moveElemsAttrsToGroup',
        'moveGroupAttrsToElems',
        'collapseGroups',
        'convertPathData',
        'convertTransform',
        'removeEmptyAttrs',
        'removeEmptyContainers',
        'mergePaths',
        'removeUnusedNS',
        'sortAttrs',
        'removeTitle',
        'removeDesc',
      ],
    });
    
    return result.data;
  }
  
  // ... 其他转换方法
}
```

### 5.2 PSD 导入 (分层文件)

```typescript
// @core/canvas/import/importers/layered/PSDImporter.ts

import Psd from 'ag-psd';
import { Importer, ImportResult, ImportOptions } from '../base/Importer';
import { Element } from '../../../elements/base/Element';
import { ImageElement } from '../../../elements/image/ImageElement';
import { TextElement } from '../../../elements/text/TextElement';
import { GroupElement } from '../../../elements/group/GroupElement';

interface PSDImportOptions extends ImportOptions {
  // 导入模式
  mode: 'flatten' | 'layers' | 'select';
  
  // 选择的图层 (mode='select' 时)
  selectedLayers?: string[];
  
  // 是否保留隐藏图层
  includeHidden?: boolean;
  
  // 是否保留图层效果
  preserveEffects?: boolean;
  
  // 是否转换智能对象
  rasterizeSmartObjects?: boolean;
}

interface PSDLayer {
  name: string;
  type: 'layer' | 'group' | 'text' | 'shape';
  visible: boolean;
  opacity: number;
  blendMode: string;
  bounds: { left: number; top: number; right: number; bottom: number };
  canvas?: HTMLCanvasElement;
  text?: {
    text: string;
    font: string;
    fontSize: number;
    color: string;
  };
  children?: PSDLayer[];
}

export class PSDImporter extends Importer {
  readonly supportedFormats = ['psd', 'psb'];
  
  async import(file: File, options: PSDImportOptions = { mode: 'flatten' }): Promise<ImportResult> {
    const arrayBuffer = await this.readAsArrayBuffer(file);
    
    // 1. 解析 PSD
    const psd = Psd.readPsd(new Uint8Array(arrayBuffer), {
      skipCompositeImageData: options.mode !== 'flatten',
      skipLayerImageData: options.mode === 'flatten',
      skipThumbnail: true,
    });
    
    // 2. 提取元数据
    const metadata = {
      width: psd.width,
      height: psd.height,
      colorMode: psd.colorMode,
      bitsPerChannel: psd.bitsPerChannel,
      layerCount: this.countLayers(psd.children || []),
    };
    
    // 3. 根据模式处理
    let elements: Element[];
    
    switch (options.mode) {
      case 'flatten':
        elements = await this.importFlattened(psd);
        break;
        
      case 'layers':
        elements = await this.importLayers(psd, options);
        break;
        
      case 'select':
        elements = await this.importSelectedLayers(psd, options);
        break;
        
      default:
        elements = await this.importFlattened(psd);
    }
    
    return {
      elements,
      metadata,
      warnings: this.warnings,
      layerInfo: options.mode !== 'flatten' 
        ? this.extractLayerTree(psd.children || [])
        : undefined,
    };
  }
  
  /**
   * 导入合并后的图像
   */
  private async importFlattened(psd: any): Promise<Element[]> {
    if (!psd.canvas) {
      throw new Error('PSD does not contain composite image data');
    }
    
    const imageData = psd.canvas.toDataURL('image/png');
    const element = new ImageElement();
    await element.loadFromDataURL(imageData);
    
    return [element];
  }
  
  /**
   * 导入所有图层
   */
  private async importLayers(psd: any, options: PSDImportOptions): Promise<Element[]> {
    const elements: Element[] = [];
    
    for (const layer of psd.children || []) {
      const element = await this.convertLayer(layer, options);
      if (element) {
        elements.push(element);
      }
    }
    
    return elements;
  }
  
  /**
   * 导入选中的图层
   */
  private async importSelectedLayers(psd: any, options: PSDImportOptions): Promise<Element[]> {
    const selectedNames = new Set(options.selectedLayers || []);
    const elements: Element[] = [];
    
    const processLayers = async (layers: any[]) => {
      for (const layer of layers) {
        if (selectedNames.has(layer.name)) {
          const element = await this.convertLayer(layer, options);
          if (element) {
            elements.push(element);
          }
        }
        
        if (layer.children) {
          await processLayers(layer.children);
        }
      }
    };
    
    await processLayers(psd.children || []);
    return elements;
  }
  
  /**
   * 转换单个图层
   */
  private async convertLayer(layer: any, options: PSDImportOptions): Promise<Element | null> {
    // 跳过隐藏图层
    if (!layer.hidden === false && !options.includeHidden) {
      return null;
    }
    
    // 组图层
    if (layer.children) {
      const children: Element[] = [];
      for (const child of layer.children) {
        const element = await this.convertLayer(child, options);
        if (element) {
          children.push(element);
        }
      }
      
      if (children.length === 0) return null;
      
      const group = new GroupElement();
      group.setChildren(children);
      group.setName(layer.name);
      return group;
    }
    
    // 文本图层
    if (layer.text) {
      return this.convertTextLayer(layer);
    }
    
    // 普通图层
    if (layer.canvas) {
      return this.convertImageLayer(layer, options);
    }
    
    return null;
  }
  
  /**
   * 转换文本图层
   */
  private convertTextLayer(layer: any): TextElement {
    const element = new TextElement();
    
    element.setText(layer.text.text);
    element.setStyle({
      fontFamily: layer.text.font?.name || 'Arial',
      fontSize: layer.text.fontSize || 24,
      color: this.rgbToHex(layer.text.fillColor),
    });
    
    element.setTransform({
      x: layer.left || 0,
      y: layer.top || 0,
    });
    
    return element;
  }
  
  /**
   * 转换图像图层
   */
  private async convertImageLayer(layer: any, options: PSDImportOptions): Promise<ImageElement> {
    const canvas = layer.canvas as HTMLCanvasElement;
    const imageData = canvas.toDataURL('image/png');
    
    const element = new ImageElement();
    await element.loadFromDataURL(imageData);
    
    element.setTransform({
      x: layer.left || 0,
      y: layer.top || 0,
    });
    
    element.setStyle({
      opacity: (layer.opacity || 255) / 255,
    });
    
    element.setName(layer.name);
    
    return element;
  }
  
  /**
   * 提取图层树结构 (用于 UI 显示)
   */
  private extractLayerTree(layers: any[]): LayerTreeNode[] {
    return layers.map(layer => ({
      name: layer.name,
      type: layer.children ? 'group' : (layer.text ? 'text' : 'layer'),
      visible: !layer.hidden,
      children: layer.children 
        ? this.extractLayerTree(layer.children) 
        : undefined,
    }));
  }
  
  private countLayers(layers: any[]): number {
    let count = 0;
    for (const layer of layers) {
      count++;
      if (layer.children) {
        count += this.countLayers(layer.children);
      }
    }
    return count;
  }
  
  private rgbToHex(color: any): string {
    if (!color) return '#000000';
    const r = Math.round(color.r || 0);
    const g = Math.round(color.g || 0);
    const b = Math.round(color.b || 0);
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
  }
}
```

### 5.3 Procreate 导入 (特殊支持)

```typescript
// @core/canvas/import/importers/layered/ProcreateImporter.ts

/**
 * Procreate 文件格式说明:
 * 
 * .procreate 文件实际上是一个 ZIP 压缩包，包含:
 * - Document.archive (plist 格式的元数据)
 * - QuickLook/Thumbnail.png (预览图)
 * - 各图层的图像数据 (LZFSE 压缩的原始像素)
 * 
 * 注意: Procreate 格式未公开文档，以下实现基于社区逆向工程
 */

import JSZip from 'jszip';
import plist from 'plist';
import { Importer, ImportResult, ImportOptions } from '../base/Importer';
import { Element } from '../../../elements/base/Element';
import { ImageElement } from '../../../elements/image/ImageElement';

interface ProcreateImportOptions extends ImportOptions {
  mode: 'flatten' | 'layers' | 'thumbnail';
  includeHidden?: boolean;
}

interface ProcreateLayer {
  name: string;
  UUID: string;
  hidden: boolean;
  opacity: number;
  blend: string;
  clipped: boolean;
}

export class ProcreateImporter extends Importer {
  readonly supportedFormats = ['procreate'];
  
  async import(file: File, options: ProcreateImportOptions = { mode: 'flatten' }): Promise<ImportResult> {
    // 1. 解压 ZIP
    const zip = await JSZip.loadAsync(file);
    
    // 2. 读取元数据
    const documentArchive = await zip.file('Document.archive')?.async('arraybuffer');
    if (!documentArchive) {
      throw new Error('Invalid Procreate file: missing Document.archive');
    }
    
    const metadata = this.parseDocumentArchive(documentArchive);
    
    // 3. 根据模式处理
    let elements: Element[];
    
    switch (options.mode) {
      case 'thumbnail':
        elements = await this.importThumbnail(zip);
        break;
        
      case 'flatten':
        elements = await this.importFlattened(zip, metadata);
        break;
        
      case 'layers':
        elements = await this.importLayers(zip, metadata, options);
        break;
        
      default:
        elements = await this.importThumbnail(zip);
    }
    
    return {
      elements,
      metadata: {
        width: metadata.width,
        height: metadata.height,
        layerCount: metadata.layers.length,
        format: 'procreate',
      },
      warnings: this.warnings,
    };
  }
  
  /**
   * 解析 Document.archive (Binary Plist)
   */
  private parseDocumentArchive(buffer: ArrayBuffer): ProcreateMetadata {
    // Binary plist 解析
    // 注意: 需要处理 NSKeyedArchiver 格式
    
    try {
      const data = plist.parse(Buffer.from(buffer));
      
      return {
        width: data.size?.width || data.width || 2048,
        height: data.size?.height || data.height || 2048,
        orientation: data.orientation || 0,
        layers: this.extractLayers(data),
        colorProfile: data.colorProfile,
      };
    } catch (error) {
      this.warnings.push('Could not parse Procreate metadata, using defaults');
      return {
        width: 2048,
        height: 2048,
        orientation: 0,
        layers: [],
      };
    }
  }
  
  /**
   * 导入预览图 (最快)
   */
  private async importThumbnail(zip: JSZip): Promise<Element[]> {
    const thumbnailFile = zip.file('QuickLook/Thumbnail.png');
    
    if (!thumbnailFile) {
      throw new Error('Procreate file does not contain thumbnail');
    }
    
    const blob = await thumbnailFile.async('blob');
    const dataUrl = await this.blobToDataURL(blob);
    
    const element = new ImageElement();
    await element.loadFromDataURL(dataUrl);
    
    return [element];
  }
  
  /**
   * 导入合并后的图像
   */
  private async importFlattened(zip: JSZip, metadata: ProcreateMetadata): Promise<Element[]> {
    // Procreate 没有预合并的图像
    // 需要手动合成所有可见图层
    
    // 创建离屏 canvas
    const canvas = document.createElement('canvas');
    canvas.width = metadata.width;
    canvas.height = metadata.height;
    const ctx = canvas.getContext('2d')!;
    
    // 从底层到顶层绘制
    for (const layer of metadata.layers.reverse()) {
      if (layer.hidden) continue;
      
      try {
        const layerImage = await this.loadLayerImage(zip, layer, metadata);
        if (layerImage) {
          ctx.globalAlpha = layer.opacity;
          ctx.globalCompositeOperation = this.mapBlendMode(layer.blend);
          ctx.drawImage(layerImage, 0, 0);
        }
      } catch (error) {
        this.warnings.push(`Could not load layer: ${layer.name}`);
      }
    }
    
    const dataUrl = canvas.toDataURL('image/png');
    const element = new ImageElement();
    await element.loadFromDataURL(dataUrl);
    
    return [element];
  }
  
  /**
   * 导入各个图层
   */
  private async importLayers(
    zip: JSZip,
    metadata: ProcreateMetadata,
    options: ProcreateImportOptions
  ): Promise<Element[]> {
    const elements: Element[] = [];
    
    for (const layer of metadata.layers) {
      if (layer.hidden && !options.includeHidden) continue;
      
      try {
        const layerImage = await this.loadLayerImage(zip, layer, metadata);
        if (layerImage) {
          const element = new ImageElement();
          await element.loadFromImage(layerImage);
          element.setName(layer.name);
          element.setStyle({ opacity: layer.opacity });
          elements.push(element);
        }
      } catch (error) {
        this.warnings.push(`Could not load layer: ${layer.name}`);
      }
    }
    
    return elements;
  }
  
  /**
   * 加载单个图层图像
   * 
   * Procreate 图层存储格式:
   * - 每个图层以 UUID 命名
   * - 数据使用 LZFSE 压缩 (Apple 专有)
   * - 像素格式为 BGRA
   */
  private async loadLayerImage(
    zip: JSZip,
    layer: ProcreateLayer,
    metadata: ProcreateMetadata
  ): Promise<HTMLImageElement | null> {
    const layerPath = `${layer.UUID}.chunk`;
    const layerFile = zip.file(layerPath);
    
    if (!layerFile) {
      return null;
    }
    
    const compressedData = await layerFile.async('arraybuffer');
    
    // LZFSE 解压 (需要 WebAssembly 实现)
    const pixelData = await this.decompressLZFSE(compressedData);
    
    // 创建 ImageData
    const imageData = new ImageData(
      new Uint8ClampedArray(this.bgraToRgba(pixelData)),
      metadata.width,
      metadata.height
    );
    
    // 转换为图像
    const canvas = document.createElement('canvas');
    canvas.width = metadata.width;
    canvas.height = metadata.height;
    const ctx = canvas.getContext('2d')!;
    ctx.putImageData(imageData, 0, 0);
    
    const img = new Image();
    img.src = canvas.toDataURL('image/png');
    await new Promise(resolve => img.onload = resolve);
    
    return img;
  }
  
  /**
   * LZFSE 解压
   * 需要 WebAssembly 实现或后端支持
   */
  private async decompressLZFSE(data: ArrayBuffer): Promise<Uint8Array> {
    // 方案 1: 使用 WebAssembly 版本的 LZFSE
    // 方案 2: 发送到后端解压
    // 方案 3: 建议用户从 Procreate 导出为 PSD
    
    this.warnings.push(
      'LZFSE decompression requires additional setup. ' +
      'Consider exporting as PSD from Procreate.'
    );
    
    throw new Error('LZFSE decompression not implemented');
  }
  
  /**
   * BGRA 转 RGBA
   */
  private bgraToRgba(bgra: Uint8Array): Uint8Array {
    const rgba = new Uint8Array(bgra.length);
    for (let i = 0; i < bgra.length; i += 4) {
      rgba[i] = bgra[i + 2];     // R <- B
      rgba[i + 1] = bgra[i + 1]; // G
      rgba[i + 2] = bgra[i];     // B <- R
      rgba[i + 3] = bgra[i + 3]; // A
    }
    return rgba;
  }
  
  private mapBlendMode(procreateBlend: string): GlobalCompositeOperation {
    const blendMap: Record<string, GlobalCompositeOperation> = {
      'normal': 'source-over',
      'multiply': 'multiply',
      'screen': 'screen',
      'overlay': 'overlay',
      'darken': 'darken',
      'lighten': 'lighten',
      'colorDodge': 'color-dodge',
      'colorBurn': 'color-burn',
      'hardLight': 'hard-light',
      'softLight': 'soft-light',
      'difference': 'difference',
      'exclusion': 'exclusion',
    };
    
    return blendMap[procreateBlend] || 'source-over';
  }
}
```

### 5.4 PDF 导入

```typescript
// @core/canvas/import/importers/vector/PDFImporter.ts

import * as pdfjsLib from 'pdfjs-dist';
import { Importer, ImportResult, ImportOptions } from '../base/Importer';
import { Element } from '../../../elements/base/Element';
import { ImageElement } from '../../../elements/image/ImageElement';

// 设置 PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.js';

interface PDFImportOptions extends ImportOptions {
  // 导入哪些页
  pages?: number[] | 'all' | 'first';
  
  // 渲染质量
  scale?: number;
  
  // 是否提取矢量内容 (实验性)
  extractVectors?: boolean;
  
  // 是否提取图片
  extractImages?: boolean;
}

export class PDFImporter extends Importer {
  readonly supportedFormats = ['pdf'];
  
  async import(file: File, options: PDFImportOptions = {}): Promise<ImportResult> {
    const arrayBuffer = await this.readAsArrayBuffer(file);
    
    // 1. 加载 PDF
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
    
    // 2. 确定要导入的页
    const pageNumbers = this.resolvePageNumbers(
      options.pages || 'first',
      pdf.numPages
    );
    
    // 3. 导入每一页
    const elements: Element[] = [];
    
    for (const pageNum of pageNumbers) {
      const page = await pdf.getPage(pageNum);
      const pageElements = await this.importPage(page, options);
      elements.push(...pageElements);
    }
    
    return {
      elements,
      metadata: {
        pageCount: pdf.numPages,
        importedPages: pageNumbers,
        format: 'pdf',
      },
      warnings: this.warnings,
    };
  }
  
  /**
   * 导入单页
   */
  private async importPage(page: any, options: PDFImportOptions): Promise<Element[]> {
    const scale = options.scale || 2;
    const viewport = page.getViewport({ scale });
    
    // 创建离屏 canvas
    const canvas = document.createElement('canvas');
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    const ctx = canvas.getContext('2d')!;
    
    // 渲染页面
    await page.render({
      canvasContext: ctx,
      viewport,
    }).promise;
    
    // 转换为图像元素
    const dataUrl = canvas.toDataURL('image/png');
    const element = new ImageElement();
    await element.loadFromDataURL(dataUrl);
    
    const elements: Element[] = [element];
    
    // 可选: 提取嵌入的图片
    if (options.extractImages) {
      const images = await this.extractImages(page);
      elements.push(...images);
    }
    
    return elements;
  }
  
  /**
   * 提取 PDF 中嵌入的图片
   */
  private async extractImages(page: any): Promise<ImageElement[]> {
    const elements: ImageElement[] = [];
    
    try {
      const operatorList = await page.getOperatorList();
      
      for (let i = 0; i < operatorList.fnArray.length; i++) {
        // 检查是否是图像操作
        if (operatorList.fnArray[i] === pdfjsLib.OPS.paintImageXObject) {
          const imgIndex = operatorList.argsArray[i][0];
          const img = await page.objs.get(imgIndex);
          
          if (img && img.data) {
            const element = await this.createImageElement(img);
            if (element) {
              elements.push(element);
            }
          }
        }
      }
    } catch (error) {
      this.warnings.push('Could not extract embedded images from PDF');
    }
    
    return elements;
  }
  
  private resolvePageNumbers(pages: number[] | 'all' | 'first', total: number): number[] {
    if (pages === 'first') return [1];
    if (pages === 'all') return Array.from({ length: total }, (_, i) => i + 1);
    return pages.filter(p => p >= 1 && p <= total);
  }
}
```

---

## 6. 导入工作流设计

### 6.1 用户界面

```
┌─────────────────────────────────────────────────────────────────┐
│                    导入文件对话框                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │
│  │     📁 Import Files                              [×]    │
│  │                                                          │
│  │  ┌────────────────────────────────────────────────────┐ │
│  │  │                                                     │ │
│  │  │     Drag and drop files here                       │ │
│  │  │     or click to browse                              │ │
│  │  │                                                     │ │
│  │  │  ┌───────────────────────────────────────────────┐ │ │
│  │  │  │  📷 Images: PNG, JPG, WebP, GIF, HEIC        │ │ │
│  │  │  │  📐 Vectors: SVG, PDF, AI, EPS               │ │ │
│  │  │  │  📦 Projects: PSD, Procreate                 │ │ │
│  │  │  └───────────────────────────────────────────────┘ │ │
│  │  │                                                     │ │
│  │  │                 [Browse Files]                      │ │
│  │  │                                                     │ │
│  │  └────────────────────────────────────────────────────┘ │
│  │                                                          │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ═══════════════════════════════════════════════════════════   │
│                                                                 │
│  检测到分层文件时显示选项:                                        │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │
│  │  📦 my-illustration.psd                                 │
│  │                                                          │
│  │  Import Options:                                         │
│  │                                                          │
│  │  ○ Flatten to single image                              │
│  │  ● Import as separate layers                            │
│  │  ○ Select specific layers                               │
│  │                                                          │
│  │  ┌─ Layer Preview ─────────────────────────────────────┐│
│  │  │  ☑ Background                                       ││
│  │  │  ☑ Character                                        ││
│  │  │    ☑ Head                                           ││
│  │  │    ☑ Body                                           ││
│  │  │  ☐ Sketch (hidden)                                  ││
│  │  │  ☑ Text Layer                                       ││
│  │  └─────────────────────────────────────────────────────┘│
│  │                                                          │
│  │  ☐ Include hidden layers                                │
│  │  ☑ Preserve layer positions                             │
│  │                                                          │
│  │                                                          │
│  │            [Cancel]    [Import]                         │
│  │                                                          │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 导入进度

```
┌─────────────────────────────────────────────────────────────────┐
│                    导入进度                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │
│  │  Importing files...                                      │
│  │                                                          │
│  │  [████████████████████░░░░░░░░░░] 65%                    │
│  │                                                          │
│  │  Processing: my-illustration.psd                         │
│  │  Layer: Character / Head                                 │
│  │                                                          │
│  │  ✅ background.png (completed)                          │
│  │  ✅ icon.svg (completed)                                │
│  │  🔄 my-illustration.psd (in progress)                   │
│  │  ⏳ photo.heic (waiting)                                │
│  │                                                          │
│  │                      [Cancel]                            │
│  │                                                          │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.3 导入结果

```
┌─────────────────────────────────────────────────────────────────┐
│                    导入完成                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │
│  │  ✅ Import Complete                                      │
│  │                                                          │
│  │  4 files imported successfully                           │
│  │                                                          │
│  │  ┌───────────────────────────────────────────────────┐  │
│  │  │  📷 background.png             → Page 1           │  │
│  │  │  📐 icon.svg                   → Page 1 (3 paths) │  │
│  │  │  📦 my-illustration.psd        → Page 1 (5 layers)│  │
│  │  │  📷 photo.heic                 → Page 2           │  │
│  │  └───────────────────────────────────────────────────┘  │
│  │                                                          │
│  │  ⚠️ Warnings:                                           │
│  │  • HEIC converted to PNG (original format not supported)│
│  │  • Some SVG filters were simplified                     │
│  │                                                          │
│  │                           [Done]                         │
│  │                                                          │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. 实施计划

### 7.1 阶段规划

```
┌─────────────────────────────────────────────────────────────────┐
│                    实施计划                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Phase 1: 基础格式 (1 周)                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • Import Manager 框架                                    │   │
│  │  • 格式检测 (Magic Number)                                │   │
│  │  • PNG/JPG/WebP/GIF 导入 (原生)                          │   │
│  │  • 基础 UI (拖放上传)                                     │   │
│  │  时间: 5 天                                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Phase 2: SVG 支持 (1 周)                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • SVG 解析和转换                                         │   │
│  │  • 路径/形状/文本支持                                     │   │
│  │  • 样式和变换处理                                         │   │
│  │  • SVG 优化 (SVGO)                                        │   │
│  │  时间: 5 天                                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Phase 3: PDF/HEIC (1 周)                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • PDF.js 集成                                            │   │
│  │  • PDF 页面渲染                                           │   │
│  │  • HEIC 转换 (heic2any)                                  │   │
│  │  • 图片提取                                               │   │
│  │  时间: 5 天                                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Phase 4: PSD 支持 (1 周)                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • ag-psd 集成                                            │   │
│  │  • 图层解析                                               │   │
│  │  • 导入选项 UI                                            │   │
│  │  • 图层选择器                                             │   │
│  │  时间: 5 天                                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Phase 5: Procreate 支持 (1 周)                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • ZIP 解析                                               │   │
│  │  • 元数据提取                                             │   │
│  │  • 预览图导入                                             │   │
│  │  • (可选) LZFSE 解压                                      │   │
│  │  时间: 5 天                                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Phase 6: AI/EPS 支持 (1 周)                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • AI 格式解析 (PDF 兼容部分)                             │   │
│  │  • EPS 处理                                               │   │
│  │  • 后端转换服务 (可选)                                    │   │
│  │  时间: 5 天                                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  总计: 6 周                                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 依赖库汇总

```json
{
  "dependencies": {
    "pdfjs-dist": "^3.11.174",
    "ag-psd": "^16.0.0",
    "heic2any": "^0.0.4",
    "svgo": "^3.0.2",
    "jszip": "^3.10.1",
    "file-type": "^18.5.0",
    "plist": "^3.1.0"
  }
}
```

### 7.3 功能检查清单

| 格式 | 导入 | 预览 | 图层 | 矢量 | 优先级 |
|------|------|------|------|------|--------|
| PNG | ✅ | ✅ | - | - | P0 |
| JPG | ✅ | ✅ | - | - | P0 |
| WebP | ✅ | ✅ | - | - | P0 |
| GIF | ✅ | ✅ | - | - | P0 |
| SVG | ✅ | ✅ | - | ✅ | P0 |
| HEIC | ✅ | ✅ | - | - | P1 |
| PDF | ✅ | ✅ | - | 部分 | P1 |
| PSD | ✅ | ✅ | ✅ | - | P1 |
| Procreate | ✅ | ✅ | 部分 | - | P1 |
| AI | ✅ | ✅ | - | 部分 | P2 |
| EPS | ✅ | ✅ | - | 部分 | P2 |
| TIFF | ✅ | ✅ | - | - | P2 |

---

## 附录：格式兼容性说明页面

建议在帮助文档中添加格式兼容性说明：

```
┌─────────────────────────────────────────────────────────────────┐
│                    Supported File Formats                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Full Support ✅                                                 │
│  • PNG, JPG, WebP, GIF - Images                                 │
│  • SVG - Vector graphics (editable paths)                       │
│                                                                 │
│  Good Support 🟢                                                 │
│  • PDF - Rendered as images (vectors preserved where possible)  │
│  • PSD - Photoshop files with layers                           │
│  • HEIC - iPhone photos (converted to PNG)                      │
│                                                                 │
│  Basic Support 🟡                                                │
│  • Procreate - Preview and flattened export                    │
│  • AI/EPS - Converted via PDF compatibility                    │
│                                                                 │
│  Recommendations:                                                │
│  • From Procreate: Export as PSD for best results              │
│  • From Illustrator: Export as SVG for editable vectors        │
│  • From Photoshop: Use PSD for layers, PNG for single image    │
│  • From Canva: Export as PNG (transparent) or SVG              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

**文件格式导入支持设计完成！**
