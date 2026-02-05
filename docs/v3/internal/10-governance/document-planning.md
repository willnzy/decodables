# 文档规划清单

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **用途**: 列出所有计划文档及其大纲结构

---

## 优先级说明

| 优先级 | 说明 |
|--------|------|
| P0 | 核心文档，优先创建 |
| P1 | 重要文档，次优先 |
| P2 | 补充文档，按需创建 |

---

## 一、01-project/ 项目总览

### 1.1 README.md (P0) ✅ 已存在

### 1.2 vision.md (P1)
```
# 产品愿景
## 一、产品定位
## 二、目标用户
## 三、核心价值主张
## 四、差异化优势
## 五、长期目标
```

### 1.3 tech-stack.md (P0)
```
# 技术栈
## 一、概述
## 二、前端技术栈
  - 框架、UI 库、状态管理、构建工具
## 三、后端技术栈
  - 框架、数据库、缓存、队列
## 四、第三方服务
  - 支付、AI、存储、邮件
## 五、开发工具
  - IDE、版本控制、CI/CD
## 六、部署环境
  - 生产、测试环境
```

---

## 二、02-product/features/ 功能规格

### 2.1 editor.md (P0)
```
# 编辑器功能规格
## 一、概述
## 二、功能范围
  - Canvas 画布
  - 媒体元素（图片、文字、形状）
  - 工具栏
  - 属性面板
  - 图层管理
## 三、用户故事
## 四、功能详情
  - 4.1 Canvas 操作
  - 4.2 图片处理
  - 4.3 文字编辑
  - 4.4 形状绘制
  - 4.5 AI 功能
  - 4.6 导出功能
## 五、UI/交互
## 六、技术约束
## 七、依赖关系
## 八、验收标准
```

### 2.2 dashboard.md (P1)
```
# 仪表盘功能规格
## 一、概述
## 二、功能范围
  - 作品列表
  - 文件夹管理
  - 搜索筛选
  - 批量操作
## 三、用户故事
## 四、功能详情
## 五、UI/交互
## 六、技术约束
## 七、验收标准
```

### 2.3 marketplace.md (P1)
```
# 素材市场功能规格
## 一、概述
## 二、功能范围
  - 素材浏览
  - 分类筛选
  - 素材详情
  - 收藏功能
## 三、用户故事
## 四、功能详情
## 五、UI/交互
## 六、验收标准
```

### 2.4 ai-generation.md (P1)
```
# AI 生成功能规格
## 一、概述
## 二、功能范围
  - AI 生图
  - AI 生成 Page
  - OCR 识别
## 三、用户故事
## 四、功能详情
  - 4.1 AI 生图
  - 4.2 AI 生成 Page
  - 4.3 OCR 识别
## 五、积分消耗
## 六、技术约束
## 七、验收标准
```

### 2.5 subscription.md (P1)
```
# 订阅功能规格
## 一、概述
## 二、功能范围
  - 订阅计划展示
  - 订阅购买
  - 订阅管理
  - 积分充值
## 三、用户故事
## 四、功能详情
## 五、支付流程
## 六、验收标准
```

---

## 三、04-engineering/architecture/ 架构文档

### 3.1 overview.md (P0)
```
# 架构总览
## 一、设计目标
## 二、架构原则
  - DDD、分层、依赖倒置
## 三、系统架构图
## 四、技术选型
## 五、部署架构
```

### 3.2 backend.md (P0)
```
# 后端架构
## 一、概述
## 二、分层架构
  - API 层
  - Application 层
  - Domain 层
  - Infrastructure 层
## 三、目录结构
## 四、依赖关系
## 五、核心模式
  - Repository 模式
  - Service 模式
  - Entity 设计
## 六、错误处理
## 七、日志规范
```

### 3.3 frontend.md (P0)
```
# 前端架构
## 一、概述
## 二、三层架构
  - @core 层
  - @shared 层
  - @business 层
## 三、目录结构
## 四、状态管理
  - Store 拆分策略
  - 状态同步
## 五、路由设计
## 六、组件设计
## 七、性能优化
```

### 3.4 database.md (P0)
```
# 数据库设计
## 一、概述
## 二、Schema 文件结构
  - 01_core_business.sql
  - 02_platform_services.sql
  - 03_infrastructure.sql
## 三、核心表设计
## 四、索引策略
## 五、RPC 函数
## 六、迁移管理
```

---

## 四、04-engineering/modules/ 模块文档

### 4.1 editor/architecture.md (P0)
```
# 编辑器模块架构
## 一、模块概述
## 二、代码结构
  - 后端（creation, templates, export）
  - 前端（app/create, stores/editor）
## 三、Canvas 架构
  - Fabric.js 集成
  - 对象模型
  - 事件系统
## 四、媒体管理
  - 图片、文字、形状
  - 属性系统
## 五、状态管理
  - Editor Store
  - History Store
## 六、数据流
## 七、性能优化
```

### 4.2 billing/architecture.md (P0)
```
# 计费模块架构
## 一、模块概述
## 二、代码结构
## 三、订阅管理
  - Stripe 集成
  - 订阅生命周期
## 四、积分管理
  - 积分类型
  - 扣费逻辑
## 五、Webhook 处理
## 六、数据流
```

### 4.3 auth/architecture.md (P0)
```
# 认证模块架构
## 一、模块概述
## 二、代码结构
## 三、认证流程
  - 登录流程
  - 注册流程
  - OTP 验证
## 四、JWT 管理
  - Token 生成
  - Token 刷新
  - Token 验证
## 五、会话管理
## 六、安全措施
```

---

## 五、05-business/ 业务规则

### 5.1 user-system/user-lifecycle.md (P1)
```
# 用户生命周期
## 一、概述
## 二、用户状态
  - 未注册、已注册、已订阅、已流失
## 三、状态流转
## 四、关键事件
  - 注册、首次订阅、取消订阅、回归
## 五、数据处理
  - 数据保留
  - 数据删除
```

### 5.2 tier-system/tier-benefits.md (P0)
```
# Tier 权益详情
## 一、概述
## 二、各等级权益
  - t1 权益
  - t2 权益
  - t3 权益
  - t4 权益（预留）
## 三、权益对比表
## 四、权益变更规则
```

### 5.3 credits-system/credits-flow.md (P0)
```
# 积分流转规则
## 一、概述
## 二、积分获取
  - 注册赠送
  - 月度发放
  - 充值购买
## 三、积分消费
  - AI 功能消耗
  - 扣费顺序
## 四、积分过期
  - 月度积分重置
  - 永久积分不过期
## 五、积分查询
```

### 5.4 pricing/pricing-strategy.md (P1)
```
# 定价策略
## 一、概述
## 二、订阅定价
  - 价格表
  - 定价逻辑
## 三、积分定价
  - 价格表
  - 折扣逻辑
## 四、促销策略
## 五、价格调整流程
```

---

## 六、03-design/ 设计系统

### 6.1 tokens/colors.md (P1)
```
# 颜色系统
## 一、概述
## 二、品牌色
## 三、语义色
  - Primary、Secondary
  - Success、Warning、Error
  - Neutral
## 四、深色模式
## 五、代码对照
  - CSS 变量
  - Tailwind 类
```

### 6.2 tokens/typography.md (P1)
```
# 字体系统
## 一、概述
## 二、字体族
## 三、字号规范
## 四、行高规范
## 五、字重规范
## 六、代码对照
```

### 6.3 components/buttons.md (P1)
```
# 按钮组件
## 一、概述
## 二、按钮变体
  - Primary、Secondary、Ghost、Link
## 三、按钮尺寸
  - sm、md、lg
## 四、按钮状态
  - Default、Hover、Active、Disabled、Loading
## 五、使用指南
## 六、代码示例
```

---

## 七、11-reference/ 参考资料

### 7.1 glossary.md (P1)
```
# 术语表
## 一、产品术语
## 二、技术术语
## 三、业务术语
## 四、缩写列表
```

### 7.2 feature-matrix.md (P1)
```
# 功能覆盖矩阵
## 一、功能列表
## 二、Tier 权限矩阵
## 三、实现状态矩阵
## 四、测试覆盖矩阵
```

### 7.3 error-codes.md (P1)
```
# 错误码速查
## 一、错误码规范
## 二、认证错误 (AUTH_xxx)
## 三、业务错误 (BIZ_xxx)
## 四、系统错误 (SYS_xxx)
## 五、处理建议
```

---

## 八、public/ 用户文档

### 8.1 manual/getting-started/index.md (P0)
```
# 快速入门
## 欢迎使用 Make Decodables
## 第一步：创建账号
## 第二步：创建第一个项目
## 第三步：基础编辑
## 第四步：保存和导出
## 下一步
```

### 8.2 manual/editor/index.md (P0)
```
# 编辑器使用指南
## 编辑器概览
## 工具栏介绍
## 画布操作
## 属性面板
## 快捷键
```

### 8.3 faq/general.md (P1)
```
# 常见问题
## 账户相关
  - 如何注册？
  - 忘记密码？
## 功能相关
  - 如何创建项目？
  - 如何使用 AI 功能？
## 订阅相关
  - 订阅计划有哪些？
  - 如何取消订阅？
## 其他
  - 联系客服
```

---

## 创建优先级

### P0 - 核心文档（优先创建）

| 文档 | 位置 |
|------|------|
| tech-stack.md | 01-project/ |
| editor.md | 02-product/features/ |
| overview.md | 04-engineering/architecture/ |
| backend.md | 04-engineering/architecture/ |
| frontend.md | 04-engineering/architecture/ |
| database.md | 04-engineering/architecture/ |
| editor/architecture.md | 04-engineering/modules/ |
| billing/architecture.md | 04-engineering/modules/ |
| auth/architecture.md | 04-engineering/modules/ |
| tier-benefits.md | 05-business/tier-system/ |
| credits-flow.md | 05-business/credits-system/ |
| getting-started/index.md | public/manual/ |
| editor/index.md | public/manual/ |

### P1 - 重要文档（次优先）

| 文档 | 位置 |
|------|------|
| vision.md | 01-project/ |
| dashboard.md | 02-product/features/ |
| marketplace.md | 02-product/features/ |
| ai-generation.md | 02-product/features/ |
| subscription.md | 02-product/features/ |
| colors.md | 03-design/tokens/ |
| typography.md | 03-design/tokens/ |
| buttons.md | 03-design/components/ |
| user-lifecycle.md | 05-business/user-system/ |
| pricing-strategy.md | 05-business/pricing/ |
| glossary.md | 11-reference/ |
| feature-matrix.md | 11-reference/ |
| error-codes.md | 11-reference/ |
| general.md | public/faq/ |

---

**END OF DOCUMENT**
