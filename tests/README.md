# 测试套件

## 概述

本测试套件基于**测试驱动设计**原则，依据 `后台业务逻辑说明.md` 设计测试用例，而非迎合业务代码跑通测试。

**核心原则**: 如果测试失败，应该检查代码是否符合业务规则，而不是修改测试。

## 目录结构

```
tests/
├── conftest.py                    # 共享 fixtures 和 mock 配置
├── README.md                      # 本文档
│
├── business_rules/                # 纯业务逻辑测试（无外部依赖）
│   ├── test_user_tier_rules.py    # 用户等级与会员规则 (Section 2)
│   ├── test_trial_period.py       # 30天试用期规则 (Section 2.3)
│   ├── test_credit_rules.py       # 积分扣费、重置规则 (Section 3)
│   ├── test_permission_matrix.py  # 功能权限矩阵 (Section 4)
│   └── test_marketplace_rules.py  # 市场购买、发布、分成规则 (Section 6)
│
├── services/                      # 服务层集成测试
│   ├── test_access_control.py     # 访问控制服务
│   ├── test_credit_service.py     # 积分服务
│   ├── test_marketplace_service.py # 市场服务
│   ├── test_payment_service.py    # 支付服务
│   ├── test_cache_service.py      # 缓存服务
│   ├── test_analytics_service.py  # 分析服务
│   ├── test_experiment_service.py # A/B 测试服务
│   └── test_resource_service.py   # 资源服务
│
├── api/                           # API 端点测试
│   ├── test_projects_api.py       # 项目 CRUD
│   ├── test_generation_api.py     # AI 生成
│   ├── test_export_api.py         # 导出功能
│   ├── test_upload_api.py         # 文件上传
│   └── test_user_api.py           # 用户相关
│
└── edge_cases/                    # 边界条件测试
    ├── test_trial_boundaries.py   # 试用期边界（30天）
    ├── test_credit_boundaries.py  # 积分边界
    └── test_project_limit_boundaries.py  # 项目限制边界
```

## 运行测试

```bash
# 运行所有测试
pytest

# 运行特定目录
pytest tests/business_rules/
pytest tests/services/
pytest tests/api/
pytest tests/edge_cases/

# 运行特定文件
pytest tests/business_rules/test_trial_period.py

# 详细输出
pytest -v

# 覆盖率报告
pytest --cov=. --cov-report=html
```

## 业务规则参考

测试用例基于以下业务规则设计：

### 用户等级 (Section 2)
- **Free**: 无订阅，30天试用期
- **Starter**: $14.9/月，500月度积分
- **Pro**: $24.9/月，1000月度积分

### 试用期 (Section 2.3)
- 时长：**30 天**（从注册日期开始）
- 试用期内 Free 用户可体验所有功能
- 试用期后功能"上锁"，需升级解锁

### 积分系统 (Section 3)
- 扣费优先级：**先月度，后永久**
- 月度重置：**覆盖**，不累加，不结转
- AI 图像生成：5 积分/张
- OCR/Smart Scan：5 积分/次

### 项目限制 (Section 7.1)
- Free: 1 个项目
- Starter: 20 个项目
- Pro: 200 个项目

### 市场分成 (Section 6.3)
- 卖家：90%（永久积分）
- 平台：10%

## 测试设计原则

1. **业务驱动**: 测试设计基于业务规则文档，而非代码实现
2. **独立性**: 每个测试可独立运行
3. **可读性**: 测试名称清晰描述测试目的
4. **边界覆盖**: 专门测试边界条件
5. **Mock 隔离**: 服务测试使用 mock 隔离外部依赖

## 注意事项

- `business_rules/` 目录下的测试**不应该**依赖任何外部服务或数据库
- 修改业务规则时，**先更新测试**，再修改代码
- 新功能开发时，先编写测试用例

---

*文档版本: v3.24 | 最后更新: 2026-01-06*
