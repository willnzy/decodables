"""
Database Field Mappings - Single Source of Truth

This module defines the mappings between database table columns and domain object attributes.
All repository implementations MUST use these mappings to ensure consistency.

@module infrastructure.repositories.field_mappings
@version 1.0.0
@created 2026-01-10
"""

from typing import Dict, Any, List
from dataclasses import asdict, is_dataclass

# ============================================================
# profiles 表 → UserProfile 聚合根
# ============================================================
PROFILES_DB_TO_DOMAIN: Dict[str, str] = {
    # 数据库字段 → 领域对象属性路径
    'id': 'user_id',                          # TEXT (Clerk ID) → user_id
    'email': 'email',                         # TEXT
    'tier': 'tier',                           # TEXT (t1/t2/t3) → UserTier enum
    'credits_monthly': 'credits_monthly',     # INTEGER
    'credits_permanent': 'credits_permanent', # INTEGER
    'stripe_customer_id': 'stripe_customer_id',    # TEXT
    'stripe_subscription_id': 'stripe_subscription_id',  # TEXT
    'onboarding_step': 'onboarding_step',     # TEXT → OnboardingStep enum
    'preferences': 'preferences',             # JSONB → UserPreferences
    'display_name': 'display_name',           # TEXT
    'avatar_url': 'avatar_url',               # TEXT
    'is_deleted': 'is_deleted',               # BOOLEAN
    'deleted_at': 'deleted_at',               # TIMESTAMPTZ
    'created_at': 'created_at',               # TIMESTAMPTZ
    'updated_at': 'updated_at',               # TIMESTAMPTZ
}

# ============================================================
# credit_transactions 表 → CreditTransaction 值对象
# ============================================================
CREDIT_TX_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'transaction_id',                   # UUID
    'user_id': 'user_id',                     # TEXT (FK to profiles.id)
    'transaction_type': 'tx_type',            # TEXT → TransactionType enum
    'bucket': 'bucket',                       # TEXT → CreditBucket enum
    'amount': 'amount',                       # INTEGER
    'balance_monthly_after': 'balance_monthly_after',      # INTEGER
    'balance_permanent_after': 'balance_permanent_after',  # INTEGER
    'description': 'description',             # TEXT
    'idempotency_key': 'idempotency_key',     # TEXT (UNIQUE)
    'metadata': 'metadata',                   # JSONB → dict
    'created_at': 'created_at',               # TIMESTAMPTZ
}

# ============================================================
# projects 表 → Project 聚合根
# ============================================================
PROJECTS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'project_id',                       # UUID
    'user_id': 'user_id',                     # TEXT (FK to profiles.id)
    'title': 'title',                         # TEXT
    'description': 'description',             # TEXT
    'paper_size': 'paper_size',               # TEXT → PaperSize enum
    'orientation': 'orientation',             # TEXT → Orientation enum
    'num_pages': 'num_pages',                 # INTEGER
    'is_public': 'is_public',                 # BOOLEAN
    'marketplace_listing_id': 'listing_id',   # UUID (nullable)
    'source_listing_id': 'source_listing_id', # UUID (nullable) - 购买来源
    'is_purchased': 'is_purchased',           # BOOLEAN
    'origin_owner_id': 'origin_owner_id',     # TEXT (nullable) - 原作者
    'contains_locked_elements': 'contains_locked_elements',  # BOOLEAN
    'is_deleted': 'is_deleted',               # BOOLEAN
    'is_permanently_deleted': 'is_permanently_deleted',  # BOOLEAN
    'deleted_at': 'deleted_at',               # TIMESTAMPTZ
    'created_at': 'created_at',               # TIMESTAMPTZ
    'updated_at': 'updated_at',               # TIMESTAMPTZ
}

# ============================================================
# marketplace_listings 表 → Listing 聚合根
# ============================================================
LISTINGS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'listing_id',                       # UUID
    'project_id': 'project_id',               # UUID (FK to projects.id)
    'seller_id': 'seller_id',                 # TEXT (FK to profiles.id)
    'title': 'title',                         # TEXT
    'description': 'description',             # TEXT
    'price_usd': 'price_usd',                 # NUMERIC(10,2)
    'price_credits': 'price_credits',         # INTEGER
    'preview_image_url': 'preview_image_url', # TEXT
    'tags': 'tags',                           # TEXT[]
    'category': 'category',                   # TEXT → AssetCategory enum
    'total_purchases': 'total_purchases',     # INTEGER
    'total_favorites': 'total_favorites',     # INTEGER
    'avg_rating': 'avg_rating',               # NUMERIC(3,2)
    'moderation_status': 'moderation_status', # TEXT → ModerationStatus enum
    'is_featured': 'is_featured',             # BOOLEAN
    'is_visible': 'is_visible',               # BOOLEAN
    'is_deleted': 'is_deleted',               # BOOLEAN
    'deleted_at': 'deleted_at',               # TIMESTAMPTZ
    'created_at': 'created_at',               # TIMESTAMPTZ
    'updated_at': 'updated_at',               # TIMESTAMPTZ
}

# ============================================================
# marketplace_purchases 表 → Purchase 值对象
# ============================================================
PURCHASES_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'purchase_id',                      # UUID
    'listing_id': 'listing_id',               # UUID (FK to marketplace_listings.id)
    'user_id': 'buyer_id',                    # TEXT (FK to profiles.id) - 注意: 代码中使用 buyer_id
    'project_id': 'project_id',               # UUID (FK to projects.id)
    'price_usd': 'price_usd',                 # NUMERIC(10,2)
    'price_credits': 'price_credits',         # INTEGER
    'payment_method': 'payment_method',       # TEXT (usd/credits)
    'stripe_payment_intent_id': 'stripe_payment_intent_id',  # TEXT
    'created_at': 'created_at',               # TIMESTAMPTZ
}

# ============================================================
# system_configs 表 → SystemConfig 实体
# ============================================================
CONFIGS_DB_TO_DOMAIN: Dict[str, str] = {
    'key': 'config_key',                      # TEXT (PRIMARY KEY)
    'value': 'value',                         # TEXT
    'description': 'description',             # TEXT
    'is_public': 'is_public',                 # BOOLEAN
    'created_at': 'created_at',               # TIMESTAMPTZ
    'updated_at': 'updated_at',               # TIMESTAMPTZ
}

# ============================================================
# Mapping Utility Functions
# ============================================================

def map_db_to_domain(
    db_record: Dict[str, Any],
    mapping: Dict[str, str],
    include_nested: bool = True
) -> Dict[str, Any]:
    """
    将数据库记录映射为领域对象属性字典

    Args:
        db_record: 数据库查询结果行 (dict)
        mapping: 字段映射表 (PROFILES_DB_TO_DOMAIN, etc.)
        include_nested: 是否处理嵌套路径 (如 "balance.monthly")

    Returns:
        领域对象属性字典

    Example:
        >>> db_record = {"id": "user_123", "credits_monthly": 100}
        >>> mapping = PROFILES_DB_TO_DOMAIN
        >>> result = map_db_to_domain(db_record, mapping)
        >>> print(result)
        {"user_id": "user_123", "credits_monthly": 100}
    """
    result = {}

    for db_field, domain_path in mapping.items():
        if db_field not in db_record:
            continue

        db_value = db_record[db_field]

        # 处理嵌套路径 (如 "balance.monthly")
        if include_nested and "." in domain_path:
            parts = domain_path.split(".")
            current = result
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = db_value
        else:
            result[domain_path] = db_value

    return result


def map_domain_to_db(
    domain_obj: Any,
    mapping: Dict[str, str],
    reverse: bool = True
) -> Dict[str, Any]:
    """
    将领域对象映射为数据库记录字典

    Args:
        domain_obj: 领域对象 (dataclass 或 dict)
        mapping: 字段映射表
        reverse: 是否反向映射 (domain → db)

    Returns:
        数据库记录字典

    Example:
        >>> user = UserProfile(user_id="user_123", credits_monthly=100, ...)
        >>> mapping = PROFILES_DB_TO_DOMAIN
        >>> result = map_domain_to_db(user, mapping)
        >>> print(result)
        {"id": "user_123", "credits_monthly": 100, ...}
    """
    # 将领域对象转为字典
    if is_dataclass(domain_obj):
        domain_dict = asdict(domain_obj)
    elif isinstance(domain_obj, dict):
        domain_dict = domain_obj
    else:
        domain_dict = vars(domain_obj)

    result = {}

    if reverse:
        # 反向映射: domain_path → db_field
        reverse_mapping = {v: k for k, v in mapping.items()}

        for domain_path, db_field in reverse_mapping.items():
            # 处理嵌套路径
            if "." in domain_path:
                parts = domain_path.split(".")
                current = domain_dict
                for part in parts:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        current = None
                        break
                if current is not None:
                    result[db_field] = current
            else:
                if domain_path in domain_dict:
                    result[db_field] = domain_dict[domain_path]
    else:
        # 正向映射 (与 map_db_to_domain 一致)
        for db_field, domain_path in mapping.items():
            if domain_path in domain_dict:
                result[db_field] = domain_dict[domain_path]

    return result


def get_db_fields(mapping: Dict[str, str]) -> List[str]:
    """
    获取映射表中的所有数据库字段名

    Args:
        mapping: 字段映射表

    Returns:
        数据库字段名列表

    Example:
        >>> fields = get_db_fields(PROFILES_DB_TO_DOMAIN)
        >>> print(fields)
        ['id', 'email', 'tier', 'credits_monthly', ...]
    """
    return list(mapping.keys())


def get_domain_fields(mapping: Dict[str, str]) -> List[str]:
    """
    获取映射表中的所有领域对象字段名

    Args:
        mapping: 字段映射表

    Returns:
        领域对象字段名列表

    Example:
        >>> fields = get_domain_fields(PROFILES_DB_TO_DOMAIN)
        >>> print(fields)
        ['user_id', 'email', 'tier', 'credits_monthly', ...]
    """
    return list(mapping.values())


def validate_db_record(
    db_record: Dict[str, Any],
    mapping: Dict[str, str],
    required_fields: List[str] = None
) -> bool:
    """
    验证数据库记录是否包含所有必需字段

    Args:
        db_record: 数据库查询结果
        mapping: 字段映射表
        required_fields: 必需字段列表 (数据库字段名)

    Returns:
        是否验证通过

    Raises:
        ValueError: 缺少必需字段时

    Example:
        >>> db_record = {"id": "user_123", "email": "test@example.com"}
        >>> validate_db_record(db_record, PROFILES_DB_TO_DOMAIN, ["id", "email"])
        True
    """
    if required_fields is None:
        required_fields = []

    missing_fields = []
    for field in required_fields:
        if field not in db_record or db_record[field] is None:
            missing_fields.append(field)

    if missing_fields:
        raise ValueError(
            f"数据库记录缺少必需字段: {missing_fields}\n"
            f"实际字段: {list(db_record.keys())}"
        )

    return True


# ============================================================
# Mapping Validation (Development/Testing)
# ============================================================

def validate_mapping_consistency(
    mapping_name: str,
    mapping: Dict[str, str],
    schema_fields: List[str]
) -> Dict[str, List[str]]:
    """
    验证映射表与数据库 Schema 的一致性

    Args:
        mapping_name: 映射表名称 (用于错误消息)
        mapping: 字段映射字典
        schema_fields: Schema 中的实际字段列表

    Returns:
        验证结果字典:
        {
            'missing_in_mapping': [...],  # Schema 中有但映射表缺失
            'extra_in_mapping': [...],    # 映射表中有但 Schema 缺失
            'valid': True/False
        }

    Example:
        >>> schema_fields = ["id", "email", "tier", "credits_monthly"]
        >>> result = validate_mapping_consistency(
        ...     "PROFILES_DB_TO_DOMAIN",
        ...     PROFILES_DB_TO_DOMAIN,
        ...     schema_fields
        ... )
        >>> print(result['valid'])
        True
    """
    mapping_fields = set(mapping.keys())
    schema_fields_set = set(schema_fields)

    missing_in_mapping = schema_fields_set - mapping_fields
    extra_in_mapping = mapping_fields - schema_fields_set

    result = {
        'missing_in_mapping': sorted(missing_in_mapping),
        'extra_in_mapping': sorted(extra_in_mapping),
        'valid': len(missing_in_mapping) == 0 and len(extra_in_mapping) == 0
    }

    if not result['valid']:
        print(f"⚠️  映射表 {mapping_name} 与 Schema 不一致:")
        if missing_in_mapping:
            print(f"   缺失字段 (Schema 有但映射表无): {sorted(missing_in_mapping)}")
        if extra_in_mapping:
            print(f"   多余字段 (映射表有但 Schema 无): {sorted(extra_in_mapping)}")

    return result


# ============================================================
# Example Usage (for documentation)
# ============================================================

if __name__ == "__main__":
    # Example: Map database record to domain object
    db_user = {
        "id": "user_2abc3def",
        "email": "test@example.com",
        "tier": "t2",
        "credits_monthly": 200,
        "credits_permanent": 50,
        "created_at": "2026-01-10T12:00:00Z"
    }

    domain_data = map_db_to_domain(db_user, PROFILES_DB_TO_DOMAIN)
    print("Database → Domain:")
    print(domain_data)
    # Output: {'user_id': 'user_2abc3def', 'email': 'test@example.com', ...}

    # Example: Map domain object to database record
    domain_user = {
        "user_id": "user_2abc3def",
        "email": "test@example.com",
        "tier": "t2",
        "credits_monthly": 200,
        "credits_permanent": 50
    }

    db_data = map_domain_to_db(domain_user, PROFILES_DB_TO_DOMAIN)
    print("\nDomain → Database:")
    print(db_data)
    # Output: {'id': 'user_2abc3def', 'email': 'test@example.com', ...}

    # Example: Get all database fields
    db_fields = get_db_fields(PROFILES_DB_TO_DOMAIN)
    print(f"\nProfiles table fields: {db_fields[:5]}...")
