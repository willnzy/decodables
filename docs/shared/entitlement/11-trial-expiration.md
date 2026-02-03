# t1 试用期过期处理

> **版本**: v1.0
> **提取自**: entitlement-permission-matrix.md 第八章 8.1 节
> **最后更新**: 2026-02-04

## 概述

本文档描述 t1 用户试用期过期后的处理机制，包括状态检测、项目权限控制、UI 提醒策略和配置项。

---

## 1. 试用期状态检测

### 1.1 TrialStatus 接口定义

```typescript
// lib/entitlement/trial.ts

interface TrialStatus {
  isInTrial: boolean;           // 是否在试用期内
  trialDays: number;            // 总试用天数
  daysRemaining: number;        // 剩余天数 (0 = 已过期)
  trialEndDate: Date;           // 试用期结束日期
  registeredAt: Date;           // 注册时间
}

async function getTrialStatus(userId: string): Promise<TrialStatus> {
  const user = await db.fetch('SELECT created_at FROM profiles WHERE user_id = $1', userId);
  const trialDays = await getConfig('trial.default_days') || 7;

  const registeredAt = new Date(user.created_at);
  const trialEndDate = new Date(registeredAt);
  trialEndDate.setDate(trialEndDate.getDate() + trialDays);

  const now = new Date();
  const daysRemaining = Math.max(0, Math.ceil((trialEndDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)));

  return {
    isInTrial: daysRemaining > 0,
    trialDays,
    daysRemaining,
    trialEndDate,
    registeredAt,
  };
}
```

---

## 2. 试用期过期后的项目处理

### 2.1 权限变化矩阵

| 场景 | 试用期内 | 试用期过期后 | 处理方式 |
|------|:-------:|:----------:|---------|
| **编辑已有项目** | ✅ 可编辑 | ❌ 只读 | 进入编辑页面时检测，过期则显示只读模式 + 升级提示 |
| **创建新项目** | ✅ 可创建 (≤1) | ❌ 不可创建 | 新建按钮带锁，点击弹 UpgradeModal |
| **复制项目** | ✅ 可复制 (≤1) | ❌ 不可复制 | 复制按钮带锁，点击弹 UpgradeModal |
| **删除项目** | ✅ 可删除 | ✅ 可删除 | 允许删除，减少资源占用 |
| **查看项目列表** | ✅ 可查看 | ✅ 可查看 | 允许查看，项目卡片显示 "只读" 标签 |
| **发布到商城** | ✅ 可发布 | ❌ 不可发布 | Publish 按钮带锁 |
| **导出 PDF/ZIP** | ✅ 可导出 | PDF ✅ / ZIP ❌ | PDF 保留，ZIP 锁定 |

### 2.2 编辑器只读模式实现

```typescript
// components/editor/EditorPage.tsx

function EditorPage({ projectId }: { projectId: string }) {
  const { tier, isWithinTrialPeriod } = useEntitlement();
  const [isReadOnly, setIsReadOnly] = useState(false);

  useEffect(() => {
    // t1 试用期过期 → 只读模式
    if (tier === 't1' && !isWithinTrialPeriod) {
      setIsReadOnly(true);
    }
  }, [tier, isWithinTrialPeriod]);

  if (isReadOnly) {
    return (
      <EditorReadOnlyWrapper>
        <TrialExpiredBanner
          message="试用期已结束，项目为只读模式"
          ctaText="升级解锁编辑"
          onUpgrade={() => openUpgradeModal()}
        />
        <Editor readOnly={true} projectId={projectId} />
      </EditorReadOnlyWrapper>
    );
  }

  return <Editor readOnly={false} projectId={projectId} />;
}
```

---

## 3. 试用期状态 UI 提醒

### 3.1 基于百分比的提醒策略

> 使用百分比而非固定天数，以便 `trial.default_days` 配置变更时自动适配。

| 剩余比例 | 提醒方式 | 提醒频率 | 示例 (7天) |
|:-------:|---------|:-------:|:----------:|
| > 50% | 顶部 Banner (可关闭) | 每天首次登录 | 7-4 天 |
| 15% ~ 50% | 顶部 Banner (不可关闭) + 编辑器内提示 | 每次进入 | 3-1 天 |
| 0% ~ 15% | Modal 弹窗 + Banner | 每次进入 | 当天 |
| 已过期 | 持续 Banner + 只读模式 | 持续显示 | - |

### 3.2 TrialStatusBanner 组件

```typescript
// components/trial/TrialStatusBanner.tsx

interface TrialBannerProps {
  daysRemaining: number;
  totalTrialDays: number;       // 从配置获取
  warningThreshold?: number;    // 默认 0.5 (50%)
  urgentThreshold?: number;     // 默认 0.15 (15%)
  onUpgrade: () => void;
  onDismiss?: () => void;
}

function TrialStatusBanner({
  daysRemaining,
  totalTrialDays,
  warningThreshold = 0.5,
  urgentThreshold = 0.15,
  onUpgrade,
  onDismiss
}: TrialBannerProps) {
  const remainingRatio = daysRemaining / totalTrialDays;

  // 基于百分比判断样式
  const variant = useMemo(() => {
    if (daysRemaining <= 0) return 'expired';
    if (remainingRatio <= urgentThreshold) return 'urgent';
    if (remainingRatio <= warningThreshold) return 'warning';
    return 'info';
  }, [daysRemaining, remainingRatio, warningThreshold, urgentThreshold]);

  const canDismiss = remainingRatio > warningThreshold;

  const messages = {
    urgent: `试用期今天结束！升级后继续使用所有功能`,
    warning: `试用期还剩 ${daysRemaining} 天`,
    info: `试用期还剩 ${daysRemaining} 天，探索所有功能`,
    expired: `试用期已结束，项目已变为只读模式`,
  };

  return (
    <Banner variant={variant} dismissible={canDismiss} onDismiss={onDismiss}>
      <span>{messages[variant]}</span>
      <Button size="sm" onClick={onUpgrade}>
        {daysRemaining <= 0 ? '升级解锁' : daysRemaining <= 1 ? '立即升级' : '查看套餐'}
      </Button>
    </Banner>
  );
}
```

### 3.3 TrialExpiredModal 组件

```typescript
// components/trial/TrialExpiredModal.tsx

function TrialExpiredModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <ModalHeader>
        <Icon name="clock" className="text-amber-500" />
        试用期已结束
      </ModalHeader>
      <ModalBody>
        <p>您的 7 天免费试用已结束。</p>
        <p className="mt-2">升级后可以：</p>
        <ul className="list-disc ml-4 mt-2">
          <li>继续编辑您的项目</li>
          <li>创建更多项目和文件夹</li>
          <li>使用 AI 生成功能</li>
          <li>导出 ZIP 文件</li>
        </ul>
      </ModalBody>
      <ModalFooter>
        <Button variant="ghost" onClick={onClose}>以后再说</Button>
        <Button variant="primary" onClick={() => openUpgradeModal()}>查看套餐</Button>
      </ModalFooter>
    </Modal>
  );
}
```

---

## 4. 试用期配置 Key

### 4.1 system_configs 配置项

```sql
-- system_configs 配置项 (使用百分比阈值，适应不同试用期长度)
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
('trial.default_days', '7', 'integer', 'trial', '默认试用天数'),
('trial.warning_threshold', '0.5', 'float', 'trial', 'warning 样式阈值 (剩余比例 ≤ 50%)'),
('trial.urgent_threshold', '0.15', 'float', 'trial', 'urgent 样式阈值 (剩余比例 ≤ 15%)'),
('trial.show_modal_on_expire', 'true', 'boolean', 'trial', '过期当天是否弹窗');
```

### 4.2 阈值计算示例

| 试用期长度 | warning 阈值 (≤50%) | urgent 阈值 (≤15%) |
|:--------:|:------------------:|:-----------------:|
| 7 天 | 剩余 ≤ 3.5 天 | 剩余 ≤ 1 天 |
| 14 天 | 剩余 ≤ 7 天 | 剩余 ≤ 2 天 |
| 30 天 | 剩余 ≤ 15 天 | 剩余 ≤ 4.5 天 |

---

## 相关文档

- [01-permission-matrix.md](./01-permission-matrix.md) - 权限矩阵总览
- [02-tier-config.md](./02-tier-config.md) - Tier 配置详情
- [05-ui-spec.md](./05-ui-spec.md) - UI 规范 (Banner/Modal 样式)
- [12-tier-downgrade.md](./12-tier-downgrade.md) - Tier 降级处理 (待创建)

---

**注意**: t1 试用期过期后 `max_custom_assets = 0`，但已上传的素材仍可在项目中使用。
