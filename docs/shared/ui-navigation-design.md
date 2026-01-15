# UI 导航与交互设计规范

> **版本**: v1.0
> **最后更新**: 2026-01-14
> **适用范围**: Make Decodables 全站前端
> **相关文档**: 
>   - 前端开发规范: `docs/main/frontend-development-guide.md` (9.6 章节)
>   - 设计系统: `docs/main/make-decodables-design-system.md`
>   - Dashboard PED: `docs/tmp/refactor/3-Pages/Dashboard/PED.md`

---

## 1. 设计原则

### 1.1 视觉层级分离

**核心理念**: 通过不同的视觉样式明确区分「导航」与「操作」

| 组件类型 | 视觉特征 | 用户心智模型 |
|----------|---------|-------------|
| **主导航** | 文字 + 下划线指示器 | "我在哪个区域/模块" |
| **子级 Tab** | 轻量文字 + 下划线 + 徽章 | "我在筛选/过滤什么" |
| **操作按钮** | 填充/描边按钮 | "我要执行什么动作" |

### 1.2 业界参考

此设计参考了以下产品的导航模式：

| 产品 | 主导航样式 | 子级筛选样式 | 操作按钮样式 |
|------|-----------|-------------|-------------|
| **Notion** | 侧边栏 + 下划线 Tab | Pills/下划线 | 填充按钮 |
| **Figma** | 顶部下划线 Tab | 下拉/Pills | 工具栏按钮 |
| **Linear** | 侧边栏 + 下划线 | 下拉/Pills | 填充按钮 |
| **Vercel** | 顶部下划线 Tab | Pills | 描边/填充按钮 |

---

## 2. 主导航规范 (Level 1)

### 2.1 视觉规范

```
┌─────────────────────────────────────────────────────────────────┐
│  [ Projects ]     [ Assets ]                                     │
│      ═══════                      ← 选中状态: 下划线指示器       │
└─────────────────────────────────────────────────────────────────┘
```

| 元素 | 规范 |
|------|------|
| **容器** | `border-b border-slate-200` |
| **选中态** | `text-indigo-600` + 底部下划线 (`h-0.5 bg-indigo-600`) |
| **未选中** | `text-slate-500 hover:text-slate-700` |
| **间距** | `gap-4` |
| **字号** | `text-lg font-medium` |

### 2.2 代码示例

```tsx
<div className="flex items-center gap-4 border-b border-slate-200 mb-6">
  <button
    onClick={() => setActiveSection('projects')}
    className={cn(
      'pb-3 text-lg font-medium relative',
      activeSection === 'projects'
        ? 'text-indigo-600'
        : 'text-slate-500 hover:text-slate-700'
    )}
  >
    <FileText className="w-5 h-5 inline-block mr-2" />
    Projects
    {activeSection === 'projects' && (
      <span className="absolute bottom-0 left-0 w-full h-0.5 bg-indigo-600" />
    )}
  </button>
</div>
```

### 2.3 锁定功能处理

对于需要特定权限才能访问的导航项，应显示锁定状态而非隐藏：

```tsx
<button
  onClick={() => {
    if (isPro) {
      setActiveSection('assets');
    } else {
      toast.info('Upgrade to Pro to manage your AI-generated assets');
    }
  }}
  className={cn(
    'pb-3 text-lg font-medium relative flex items-center gap-2',
    !isPro && 'opacity-70 cursor-not-allowed'
  )}
>
  <ImageIcon className="w-5 h-5" />
  Assets
  {!isPro && <Lock className="w-4 h-4 text-amber-500" />}
</button>
```

---

## 3. 子级 Tab 规范 (Level 2)

### 3.1 视觉规范

```
┌─────────────────────────────────────────────────────────────────┐
│  [ All Projects (12) ]  [ Bought (3) ]  [ Selling (5) ]          │
│        ═══════════════                 ← 选中状态: 语义色下划线  │
└─────────────────────────────────────────────────────────────────┘
```

| 元素 | 规范 |
|------|------|
| **容器** | `bg-slate-50 rounded-lg p-1` |
| **选中态** | 语义色文字 + 底部下划线 + 浅色徽章 |
| **未选中** | `text-slate-500 hover:text-slate-700 hover:bg-slate-100` |
| **间距** | `gap-1` |
| **字号** | `text-sm font-medium` |

### 3.2 语义色映射

| Tab 类型 | 选中文字色 | 下划线颜色 | 徽章背景 | 使用场景 |
|----------|-----------|-----------|---------|---------|
| **默认/All** | `text-indigo-600` | `bg-indigo-600` | `bg-indigo-100` | 全部内容 |
| **购买/Bought** | `text-blue-600` | `bg-blue-600` | `bg-blue-100` | 已购买内容 |
| **销售/Selling** | `text-emerald-600` | `bg-emerald-600` | `bg-emerald-100` | 正在销售的内容 |

### 3.3 代码示例

```tsx
<div className="flex items-center gap-1 bg-slate-50 rounded-lg p-1">
  {VIEW_TAB_CONFIGS.map(({ value, label }) => {
    const isActive = activeTab === value;
    
    // 语义色映射
    let semanticColorClass = '';
    let semanticBadgeColorClass = '';
    let underlineColor = '';
    
    if (isActive) {
      if (value === 'all') {
        semanticColorClass = 'text-indigo-600';
        semanticBadgeColorClass = 'bg-indigo-100 text-indigo-700';
        underlineColor = 'bg-indigo-600';
      } else if (value === 'bought') {
        semanticColorClass = 'text-blue-600';
        semanticBadgeColorClass = 'bg-blue-100 text-blue-700';
        underlineColor = 'bg-blue-600';
      } else if (value === 'selling') {
        semanticColorClass = 'text-emerald-600';
        semanticBadgeColorClass = 'bg-emerald-100 text-emerald-700';
        underlineColor = 'bg-emerald-600';
      }
    }

    return (
      <button
        key={value}
        onClick={() => onTabChange(value)}
        className={cn(
          'px-3 py-1.5 text-sm font-medium rounded-md transition-all cursor-pointer relative',
          isActive ? semanticColorClass : 'text-slate-500 hover:text-slate-700 hover:bg-slate-100'
        )}
      >
        {label}
        <span className={cn(
          'text-xs px-1.5 py-0.5 rounded-full ml-1.5',
          isActive ? semanticBadgeColorClass : 'bg-slate-100 text-slate-500'
        )}>
          {count}
        </span>
        {isActive && (
          <span className={cn('absolute bottom-0 left-0 w-full h-0.5', underlineColor)} />
        )}
      </button>
    );
  })}
</div>
```

---

## 4. 操作按钮规范 (Actions)

### 4.1 视觉规范

操作按钮保持填充/描边样式，与导航形成明确视觉区分：

```
┌─────────────────────────────────────────────────────────────────┐
│                        [ 🗑️ Trash ] [ + New Project ]           │
│                         ↑ 描边按钮    ↑ 填充按钮                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 代码示例

```tsx
// 次要操作: 描边按钮
<Button variant="outline" className="gap-2">
  <Trash2 className="w-4 h-4" />
  Trash
</Button>

// 主要操作: 填充按钮
<Button className="gap-2">
  <Plus className="w-4 h-4" />
  New Project
</Button>
```

---

## 5. 禁止的样式模式

### 5.1 导航与操作混淆

```tsx
// ❌ 不推荐: 主导航使用填充按钮（会与操作按钮混淆）
<div className="flex gap-2">
  <Button variant={isActive ? 'default' : 'ghost'}>Projects</Button>
  <Button variant={isActive ? 'default' : 'ghost'}>Assets</Button>
</div>

// ✅ 推荐: 主导航使用下划线指示器
<div className="flex gap-4 border-b">
  <button className={cn('pb-3', isActive && 'text-indigo-600 border-b-2 border-indigo-600')}>
    Projects
  </button>
</div>
```

### 5.2 子级 Tab 使用重填充

```tsx
// ❌ 不推荐: 子级 Tab 使用重填充样式（与按钮混淆）
<button className="bg-indigo-600 text-white shadow-sm">All</button>

// ✅ 推荐: 子级 Tab 使用轻量样式
<button className="text-indigo-600 relative">
  All
  <span className="absolute bottom-0 left-0 w-full h-0.5 bg-indigo-600" />
</button>
```

### 5.3 隐藏而非锁定

```tsx
// ❌ 不推荐: 完全隐藏受限功能
{isPro && <button>Assets</button>}

// ✅ 推荐: 显示锁定状态
<button className={cn(!isPro && 'opacity-70')}>
  Assets
  {!isPro && <Lock className="w-4 h-4 text-amber-500" />}
</button>
```

---

## 6. 应用场景

### 6.1 Dashboard 页面

| 区域 | 导航层级 | 样式 |
|------|---------|------|
| Projects / Assets 切换 | Level 1 主导航 | 下划线指示器 |
| All / Bought / Selling | Level 2 子级 Tab | 轻量下划线 + 徽章 |
| Trash / New Project | 操作按钮 | 填充/描边按钮 |

### 6.2 Marketplace 页面

| 区域 | 导航层级 | 样式 |
|------|---------|------|
| Browse / My Purchases / My Sales | Level 1 主导航 | 下划线指示器 |
| All / Templates / Assets | Level 2 子级 Tab | 轻量下划线 + 徽章 |
| Filter / Sort | 操作按钮 | 描边按钮/下拉 |

### 6.3 Editor 页面

| 区域 | 导航层级 | 样式 |
|------|---------|------|
| 媒体库 Tab (System / My Assets) | Level 2 子级 Tab | 轻量下划线 |
| 工具栏按钮 | 操作按钮 | 图标按钮/工具栏按钮 |

---

## 7. 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|---------|
| v1.0 | 2026-01-14 | 初始版本：建立三层导航体系（主导航/子级Tab/操作按钮）；基于业界最佳实践 |

---

**END OF DOCUMENT**
