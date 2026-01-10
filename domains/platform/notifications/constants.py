"""
Notifications 模块常量定义

@module domains.platform.notifications.constants
@version 1.0.0

v1.0.0: 初始创建
- 从 api/admin/notifications.py 迁移常量 (DDD 架构迁移)
"""

# ==========================================
# Target Groups (目标用户组)
# ==========================================

# 有效的目标用户组
VALID_TARGET_GROUPS = {"all", "t1", "t2", "t3"}

# Target Group 常量
TARGET_GROUP_ALL = "all"
TARGET_GROUP_FREE = "t1"
TARGET_GROUP_STARTER = "t2"
TARGET_GROUP_PRO = "t3"


# ==========================================
# Notification Types (通知类型)
# ==========================================

# 有效的通知类型
VALID_NOTIFICATION_TYPES = {"system", "marketing", "alert", "update", "promotion"}

# Notification Type 常量
TYPE_SYSTEM = "system"
TYPE_MARKETING = "marketing"
TYPE_ALERT = "alert"
TYPE_UPDATE = "update"
TYPE_PROMOTION = "promotion"


# ==========================================
# 参数范围验证
# ==========================================

# 标题长度
TITLE_MIN_LENGTH = 1
TITLE_MAX_LENGTH = 200

# 内容长度
CONTENT_MIN_LENGTH = 1
CONTENT_MAX_LENGTH = 5000

# User ID 长度
USER_ID_MIN_LENGTH = 1
USER_ID_MAX_LENGTH = 100

# 字段最大长度
FIELD_MAX_LENGTH = 20

# 批量发送最大用户数
BATCH_MAX_USERS = 100


# ==========================================
# 分页默认值
# ==========================================

DEFAULT_OFFSET = 0
DEFAULT_LIMIT = 50
MAX_LIMIT = 100
