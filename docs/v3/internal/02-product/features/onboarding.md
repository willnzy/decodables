# 新手引导功能规格

> **同步范围**: [fullstack]
> **状态**: 🟡 待验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `domains/platform/onboarding/`

---

## 一、概述

### 1.1 功能定位

新手引导帮助新用户快速了解产品核心功能，提高激活率和留存率。

### 1.2 设计目标

| 目标 | 指标 |
|------|------|
| 完成率 | > 60% |
| 激活率提升 | +20% |
| Day 7 留存提升 | +15% |

---

## 二、功能范围

| 功能 | 优先级 | 状态 |
|------|--------|------|
| 欢迎弹窗 | P0 | ✅ |
| 引导步骤 | P0 | 🟡 |
| 进度追踪 | P1 | 🟡 |
| 跳过功能 | P1 | ✅ |
| 重新开始 | P2 | 🔜 |

---

## 三、引导流程

### 3.1 引导步骤

| 步骤 | 名称 | 说明 | 触发条件 |
|------|------|------|----------|
| 1 | welcome | 欢迎页面 | 首次登录 |
| 2 | create_project | 创建项目 | 点击创建 |
| 3 | add_element | 添加元素 | 进入编辑器 |
| 4 | use_ai | 使用 AI | 点击 AI 功能 |
| 5 | export | 导出作品 | 完成编辑 |

### 3.2 流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    新手引导流程                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [首次登录]                                                 │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────┐                                            │
│  │ 1. Welcome  │ ← 欢迎弹窗                                 │
│  │    弹窗     │   介绍产品核心价值                          │
│  └─────────────┘                                            │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────┐                                            │
│  │ 2. Create   │ ← 高亮"创建项目"按钮                       │
│  │    Project  │   引导点击                                  │
│  └─────────────┘                                            │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────┐                                            │
│  │ 3. Add      │ ← 高亮工具栏                               │
│  │    Element  │   引导添加第一个元素                        │
│  └─────────────┘                                            │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────┐                                            │
│  │ 4. Use AI   │ ← 高亮 AI 按钮                             │
│  │             │   引导使用 AI 生图                          │
│  └─────────────┘                                            │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────┐                                            │
│  │ 5. Export   │ ← 高亮导出按钮                             │
│  │             │   引导导出作品                              │
│  └─────────────┘                                            │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────┐                                            │
│  │ 🎉 Complete │ ← 完成弹窗                                 │
│  │    +奖励    │   赠送额外积分                              │
│  └─────────────┘                                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、UI 设计

### 4.1 欢迎弹窗

```
┌────────────────────────────────────────────────────────────┐
│                                                            │
│            🎨 Welcome to Make Decodables!                  │
│                                                            │
│     Create amazing Mini Books with AI assistance.          │
│                                                            │
│     ┌─────────────────────────────────────────────────┐   │
│     │                                                 │   │
│     │            [Product Preview Image]              │   │
│     │                                                 │   │
│     └─────────────────────────────────────────────────┘   │
│                                                            │
│     ✓ Easy drag-and-drop editor                           │
│     ✓ AI-powered image generation                          │
│     ✓ Professional templates                               │
│                                                            │
│     [Skip]                          [Let's Get Started!]   │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 4.2 步骤提示

```
┌─────────────────────────────────────────────────────────────┐
│  Step 2 of 5                                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📝 Create Your First Project                               │
│                                                             │
│  Click the "Create Project" button to start                 │
│  making your first Mini Book!                               │
│                                                             │
│  [←] [Skip this step] [→]                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
         │
         ▼ (指向高亮的按钮)
    ┌─────────────┐
    │ + Create    │ ← 高亮显示
    └─────────────┘
```

### 4.3 完成弹窗

```
┌────────────────────────────────────────────────────────────┐
│                                                            │
│               🎉 Congratulations!                          │
│                                                            │
│     You've completed the getting started guide.            │
│                                                            │
│     🎁 Bonus: 20 credits added to your account!            │
│                                                            │
│     Ready to create more amazing Mini Books?               │
│                                                            │
│                       [Start Creating]                      │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 五、进度追踪

### 5.1 进度存储

```python
@dataclass
class OnboardingProgress:
    user_id: UUID
    steps_completed: List[str]
    current_step: str
    started_at: datetime
    completed_at: Optional[datetime]
    skipped_at: Optional[datetime]
```

### 5.2 进度显示

- Dashboard 顶部显示进度条
- 完成步骤显示勾选
- 当前步骤高亮

---

## 六、跳过与恢复

### 6.1 跳过引导

| 场景 | 处理 |
|------|------|
| 点击跳过 | 记录 skipped_at，不再显示 |
| 关闭弹窗 | 下次登录继续 |
| 完成步骤 | 自动进入下一步 |

### 6.2 重新开始

- Profile 设置中可重置引导
- 重置后从 step 1 开始

---

## 七、奖励机制

### 7.1 完成奖励

| 奖励 | 条件 |
|------|------|
| 20 积分 | 完成全部步骤 |
| 成就徽章 | 首次完成 |

### 7.2 奖励发放

```python
async def on_onboarding_completed(user_id: UUID):
    # 发放奖励积分
    await credits_service.grant(
        user_id,
        amount=20,
        type="onboarding_bonus",
        description="Onboarding completion bonus"
    )
    
    # 发送通知
    await notification_service.create(
        user_id,
        "onboarding_completed",
        {"bonus_credits": 20}
    )
```

---

## 八、API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/onboarding/progress` | GET | 获取进度 |
| `/onboarding/complete-step` | POST | 完成步骤 |
| `/onboarding/skip` | POST | 跳过引导 |
| `/onboarding/reset` | POST | 重置引导 |

---

## 九、埋点追踪

| 事件 | 时机 |
|------|------|
| `onboarding_started` | 开始引导 |
| `onboarding_step_completed` | 完成步骤 |
| `onboarding_skipped` | 跳过引导 |
| `onboarding_completed` | 完成全部 |

---

## 十、相关文档

- [平台服务模块架构](../../04-engineering/modules/platform/architecture.md)
- [用户生命周期](../../05-business/user-system/user-lifecycle.md)

---

**END OF DOCUMENT**
