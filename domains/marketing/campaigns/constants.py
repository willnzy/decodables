"""
Campaigns 模块常量定义

@module domains.marketing.campaigns.constants
@version 1.0.0

v1.0.0: 初始创建
- 从 api/admin/campaigns.py 迁移常量 (DDD 架构迁移)
"""

# ==========================================
# Campaign 状态
# ==========================================

# 有效的 Campaign 状态
VALID_CAMPAIGN_STATUSES = {"draft", "active", "paused", "completed", "deleted"}

# Campaign 状态常量
STATUS_DRAFT = "draft"
STATUS_ACTIVE = "active"
STATUS_PAUSED = "paused"
STATUS_COMPLETED = "completed"
STATUS_DELETED = "deleted"

# WS-14: 状态转换矩阵 — 定义每个状态允许转换到哪些状态
VALID_TRANSITIONS = {
    STATUS_DRAFT: {STATUS_ACTIVE, STATUS_DELETED},
    STATUS_ACTIVE: {STATUS_PAUSED, STATUS_COMPLETED, STATUS_DELETED},
    STATUS_PAUSED: {STATUS_ACTIVE, STATUS_DELETED},
    STATUS_COMPLETED: {STATUS_DELETED},  # 已完成只能删除
    STATUS_DELETED: set(),  # 已删除不可转换
}


# ==========================================
# Campaign 类型
# ==========================================

# 有效的 Campaign 类型
VALID_CAMPAIGN_TYPES = {"credits_gift", "credits_discount", "credits_bonus"}

# Campaign 类型常量
TYPE_CREDITS_GIFT = "credits_gift"
TYPE_CREDITS_DISCOUNT = "credits_discount"
TYPE_CREDITS_BONUS = "credits_bonus"


# ==========================================
# Target 类型
# ==========================================

# 有效的 Target 类型
VALID_TARGET_TYPES = {"all", "subscription", "users", "new_users", "inactive_users"}

# Target 类型常量
TARGET_ALL = "all"
TARGET_SUBSCRIPTION = "subscription"
TARGET_USERS = "users"
TARGET_NEW_USERS = "new_users"
TARGET_INACTIVE_USERS = "inactive_users"


# ==========================================
# 参数范围验证
# ==========================================

# 名称长度
NAME_MIN_LENGTH = 1
NAME_MAX_LENGTH = 200

# 描述长度
DESCRIPTION_MAX_LENGTH = 1000

# 使用限制
USAGE_LIMIT_MIN = 1
USAGE_LIMIT_MAX = 1000000

# 每用户使用限制
USAGE_PER_USER_MIN = 1
USAGE_PER_USER_MAX = 100

# 时区字符串长度
TIMEZONE_MAX_LENGTH = 50

# 时间字符串长度
DATETIME_STR_MAX_LENGTH = 50


# ==========================================
# 分页默认值
# ==========================================

DEFAULT_OFFSET = 0
DEFAULT_LIMIT = 20
MAX_LIMIT = 100
