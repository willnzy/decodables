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
    'id': 'user_id',                          # TEXT (Clerk ID)
    'email': 'email',                         # TEXT
    'username': 'username',                   # TEXT
    'display_name': 'display_name',           # TEXT
    'avatar_url': 'avatar_url',               # TEXT
    'user_code': 'user_code',                 # TEXT (26位唯一码)
    'tier': 'tier',                           # TEXT (t1/t2/t3)
    'tier_changed_at': 'tier_changed_at',     # TIMESTAMPTZ
    'credits_monthly': 'credits_monthly',     # INTEGER
    'credits_permanent': 'credits_permanent', # INTEGER
    'trial_start_date': 'trial_start_date',   # TIMESTAMPTZ
    'trial_end_date': 'trial_end_date',       # TIMESTAMPTZ
    'is_trial_active': 'is_trial_active',     # BOOLEAN
    'stripe_customer_id': 'stripe_customer_id',    # TEXT
    'stripe_subscription_id': 'stripe_subscription_id',  # TEXT
    'subscription_status': 'subscription_status',  # TEXT
    'subscription_current_period_start': 'subscription_current_period_start',  # TIMESTAMPTZ
    'subscription_current_period_end': 'subscription_current_period_end',  # TIMESTAMPTZ
    'language': 'language',                   # TEXT
    'timezone': 'timezone',                   # TEXT
    'notification_email_enabled': 'notification_email_enabled',  # BOOLEAN
    'notification_product_enabled': 'notification_product_enabled',  # BOOLEAN
    'created_at_local': 'created_at_local',   # TIMESTAMP
    'cohort_month': 'cohort_month',           # TEXT
    'project_count': 'project_count',         # INTEGER
    'asset_count': 'asset_count',             # INTEGER
    'ext_json': 'ext_json',                   # JSONB
    'created_at': 'created_at',               # TIMESTAMPTZ
    'updated_at': 'updated_at',               # TIMESTAMPTZ
    'is_deleted': 'is_deleted',               # BOOLEAN
    'deleted_at': 'deleted_at',               # TIMESTAMPTZ
    'recovery_expires_at': 'recovery_expires_at',  # TIMESTAMPTZ
}

# ============================================================
# credit_transactions 表 → CreditTransaction 值对象
# ============================================================
CREDIT_TX_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'transaction_id',                   # UUID
    'user_id': 'user_id',                     # TEXT
    'transaction_type': 'tx_type',            # TEXT
    'bucket': 'bucket',                       # TEXT
    'amount': 'amount',                       # INTEGER
    'balance_monthly_after': 'balance_monthly_after',      # INTEGER
    'balance_permanent_after': 'balance_permanent_after',  # INTEGER
    'idempotency_key': 'idempotency_key',     # TEXT (UNIQUE)
    'related_entity_type': 'related_entity_type',  # TEXT
    'related_entity_id': 'related_entity_id',      # TEXT
    'description': 'description',             # TEXT
    'timezone': 'timezone',                   # TEXT
    'created_at_local': 'created_at_local',   # TIMESTAMP
    'metadata': 'metadata',                   # JSONB
    'created_at': 'created_at',               # TIMESTAMPTZ
    'recovery_expires_at': 'recovery_expires_at',  # TIMESTAMPTZ
}

# ============================================================
# projects 表 → Project 聚合根
# ============================================================
PROJECTS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'project_id',                       # UUID
    'user_id': 'user_id',                     # TEXT (FK to profiles.id)
    'title': 'title',                         # TEXT
    'canvas_data': 'canvas_data',             # JSONB
    'thumbnail_url': 'thumbnail_url',         # TEXT
    'last_downloaded_hash': 'last_downloaded_hash',  # TEXT
    'marketplace_listing_id': 'listing_id',   # UUID (nullable)
    'source_listing_id': 'source_listing_id', # UUID (nullable) - 购买来源
    'is_purchased': 'is_purchased',           # BOOLEAN
    'origin_owner_id': 'origin_owner_id',     # TEXT (nullable) - 原作者
    'contains_locked_elements': 'contains_locked_elements',  # BOOLEAN
    'is_hidden_from_trash': 'is_hidden_from_trash',  # BOOLEAN
    'timezone': 'timezone',                   # TEXT
    'created_at_local': 'created_at_local',   # TIMESTAMP
    'updated_at_local': 'updated_at_local',   # TIMESTAMP
    'metadata': 'metadata',                   # JSONB
    'created_at': 'created_at',               # TIMESTAMPTZ
    'updated_at': 'updated_at',               # TIMESTAMPTZ
    'is_deleted': 'is_deleted',               # BOOLEAN
    'deleted_at': 'deleted_at',               # TIMESTAMPTZ
    'recovery_expires_at': 'recovery_expires_at',  # TIMESTAMPTZ
}

# ============================================================
# marketplace_listings 表 → Listing 聚合根
# ============================================================
LISTINGS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'listing_id',                       # UUID
    'seller_id': 'seller_id',                 # TEXT (FK to profiles.id)
    'title': 'title',                         # TEXT
    'description': 'description',             # TEXT
    'thumbnail_url': 'thumbnail_url',         # TEXT
    'resource_url': 'resource_url',           # TEXT
    'resource_type': 'resource_type',         # TEXT (project/asset/template)
    'resource_id': 'resource_id',             # UUID
    'category': 'category',                   # TEXT
    'source': 'source',                       # TEXT (system/user/ai/community)
    'price_credits': 'price_credits',         # INTEGER
    'allowed_tiers': 'allowed_tiers',         # TEXT[]
    'usage_count': 'usage_count',             # BIGINT
    'sales_count': 'sales_count',             # INTEGER
    'unique_buyers_count': 'unique_buyers_count',  # INTEGER
    'total_revenue': 'total_revenue',         # INTEGER
    'is_public': 'is_public',                 # BOOLEAN
    'moderation_status': 'moderation_status', # TEXT (draft/pending/approved/rejected)
    'moderation_note': 'moderation_note',     # TEXT
    'moderated_by': 'moderated_by',           # TEXT (FK to profiles.id)
    'moderated_at': 'moderated_at',           # TIMESTAMPTZ
    'version': 'version',                     # VARCHAR(20)
    'changelog': 'changelog',                 # TEXT
    'version_history': 'version_history',     # JSONB
    'timezone': 'timezone',                   # TEXT
    'created_at_local': 'created_at_local',   # TIMESTAMP
    'metadata': 'metadata',                   # JSONB
    'created_at': 'created_at',               # TIMESTAMPTZ
    'updated_at': 'updated_at',               # TIMESTAMPTZ
    'is_deleted': 'is_deleted',               # BOOLEAN
    'deleted_at': 'deleted_at',               # TIMESTAMPTZ
    'recovery_expires_at': 'recovery_expires_at',  # TIMESTAMPTZ
}

# ============================================================
# marketplace_purchases 表 → Purchase 值对象
# ============================================================
PURCHASES_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'purchase_id',                      # UUID
    'user_id': 'buyer_id',                    # TEXT (FK to profiles.id) - 注意: 代码中使用 buyer_id
    'listing_id': 'listing_id',               # UUID (FK to marketplace_listings.id)
    'price_paid': 'price_paid',               # INTEGER (积分)
    'idempotency_key': 'idempotency_key',     # TEXT
    'snapshot_title': 'snapshot_title',       # TEXT
    'snapshot_thumbnail_url': 'snapshot_thumbnail_url',  # TEXT
    'snapshot_description': 'snapshot_description',      # TEXT
    'snapshot_version': 'snapshot_version',   # TEXT
    'snapshot_resource_type': 'snapshot_resource_type',  # TEXT
    'snapshot_resource_id': 'snapshot_resource_id',      # UUID
    'utm_source': 'utm_source',               # TEXT
    'utm_medium': 'utm_medium',               # TEXT
    'utm_campaign': 'utm_campaign',           # TEXT
    'referral_context': 'referral_context',   # TEXT
    'timezone': 'timezone',                   # TEXT
    'purchased_at_local': 'purchased_at_local',  # TIMESTAMP
    'metadata': 'metadata',                   # JSONB
    'purchased_at': 'purchased_at',           # TIMESTAMPTZ
}

# ============================================================
# system_configs 表 → SystemConfig 实体
# ============================================================
CONFIGS_DB_TO_DOMAIN: Dict[str, str] = {
    'key': 'config_key',                      # TEXT (PRIMARY KEY)
    'value': 'value',                         # TEXT
    'value_type': 'value_type',               # TEXT (text/number/integer/boolean/json)
    'config_group': 'config_group',           # TEXT
    'description': 'description',             # TEXT
    'is_active': 'is_active',                 # BOOLEAN
    'is_editable': 'is_editable',             # BOOLEAN
    'updated_by': 'updated_by',               # TEXT
    'ext_json': 'ext_json',                   # JSONB
    'created_at': 'created_at',               # TIMESTAMPTZ
    'updated_at': 'updated_at',               # TIMESTAMPTZ
}

# ============================================================
# PART 2: Additional Table Mappings (54 tables)
# Auto-generated and manually reviewed on 2026-01-10
# ============================================================

# activity_logs 表
ACTIVITY_LOGS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'user_id': 'user_id',
    'action': 'action',
    'resource_type': 'resource_type',
    'resource_id': 'resource_id',
    'description': 'description',
    'metadata': 'metadata',
    'ip_address': 'ip_address',
    'timezone': 'timezone',
    'created_at_local': 'created_at_local',
    'created_at': 'created_at',
}

# admin_operations 表
ADMIN_OPERATIONS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'admin_id': 'admin_id',
    'operation_type': 'operation_type',
    'target_type': 'target_type',
    'target_id': 'target_id',
    'action_details': 'action_details',
    'ip_address': 'ip_address',
    'user_agent': 'user_agent',
    'status': 'status',
    'error_message': 'error_message',
    'created_at': 'created_at',
}

# aggregated_stats 表
AGGREGATED_STATS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'stat_type': 'stat_type',
    'stat_key': 'stat_key',
    'stat_value': 'stat_value',
    'metadata': 'metadata',
    'period_start': 'period_start',
    'period_end': 'period_end',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
}

# ai_call_logs 表
AI_CALL_LOGS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'user_id': 'user_id',
    'provider': 'provider',
    'model': 'model',
    'call_type': 'call_type',
    'status': 'status',
    'input_data': 'input_data',
    'output_data': 'output_data',
    'input_tokens': 'input_tokens',
    'output_tokens': 'output_tokens',
    'total_tokens': 'total_tokens',
    'latency_ms': 'latency_ms',
    'cost_usd': 'cost_usd',
    'error_code': 'error_code',
    'error_message': 'error_message',
    'metadata': 'metadata',
    'created_at': 'created_at',
}

# ai_usage_daily 表
AI_USAGE_DAILY_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'date': 'date',
    'provider': 'provider',
    'model': 'model',
    'call_type': 'call_type',
    'total_calls': 'total_calls',
    'successful_calls': 'successful_calls',
    'failed_calls': 'failed_calls',
    'total_input_tokens': 'total_input_tokens',
    'total_output_tokens': 'total_output_tokens',
    'total_images': 'total_images',
    'avg_latency_ms': 'avg_latency_ms',
    'min_latency_ms': 'min_latency_ms',
    'max_latency_ms': 'max_latency_ms',
    'estimated_cost_usd': 'estimated_cost_usd',
    'error_counts': 'error_counts',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
}

# analytics_aggregation 表
ANALYTICS_AGGREGATION_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'date': 'date',
    'granularity': 'granularity',
    'dimension_type': 'dimension_type',
    'dimension_value': 'dimension_value',
    'metrics': 'metrics',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
}

# analytics_events 表
ANALYTICS_EVENTS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'user_id': 'user_id',
    'session_id': 'session_id',
    'event_id': 'event_id',
    'event_name': 'event_name',
    'event_type': 'event_type',
    'context': 'context',
    'properties': 'properties',
    'timestamp': 'timestamp',
    'created_at': 'created_at',
}

# api_logs 表
API_LOGS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'user_id': 'user_id',
    'endpoint': 'endpoint',
    'method': 'method',
    'status_code': 'status_code',
    'latency_ms': 'latency_ms',
    'ip_address': 'ip_address',
    'user_agent': 'user_agent',
    'request_body': 'request_body',
    'response_body': 'response_body',
    'error_message': 'error_message',
    'created_at': 'created_at',
}

# asset_categories 表
ASSET_CATEGORIES_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'category_id',
    'parent_id': 'parent_id',
    'path': 'path',
    'level': 'level',
    'slug': 'slug',
    'name': 'name',
    'name_i18n': 'name_i18n',
    'description': 'description',
    'icon': 'icon',
    'asset_type': 'asset_type',
    'is_visible': 'is_visible',
    'is_featured': 'is_featured',
    'display_order': 'display_order',
    'min_tier': 'min_tier',
    'visible_from': 'visible_from',
    'visible_until': 'visible_until',
    'asset_count': 'asset_count',
    'usage_count': 'usage_count',
    'metadata': 'metadata',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
}

# asset_prompt_templates 表
ASSET_PROMPT_TEMPLATES_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'template_id',
    'user_id': 'user_id',
    'name': 'name',
    'description': 'description',
    'who_type': 'who_type',
    'who_custom': 'who_custom',
    'what_type': 'what_type',
    'what_custom': 'what_custom',
    'where_type': 'where_type',
    'where_custom': 'where_custom',
    'style': 'style',
    'moods': 'moods',
    'aspect_ratio': 'aspect_ratio',
    'creativity_level': 'creativity_level',
    'negative_prompt': 'negative_prompt',
    'use_count': 'use_count',
    'last_used_at': 'last_used_at',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
    'is_deleted': 'is_deleted',
    'deleted_at': 'deleted_at',
    'recovery_expires_at': 'recovery_expires_at',
}

# assets 表
ASSETS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'asset_id',
    'user_id': 'user_id',
    'project_id': 'project_id',
    'url': 'url',
    'type': 'type',
    'prompt': 'prompt',
    'description': 'description',
    'metadata': 'metadata',
    'source_listing_id': 'source_listing_id',
    'is_purchased': 'is_purchased',
    'origin_owner_id': 'origin_owner_id',
    'is_hidden_from_trash': 'is_hidden_from_trash',
    'timezone': 'timezone',
    'created_at_local': 'created_at_local',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
    'is_deleted': 'is_deleted',
    'deleted_at': 'deleted_at',
    'recovery_expires_at': 'recovery_expires_at',
}

# campaign_dismissals 表
CAMPAIGN_DISMISSALS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'campaign_id': 'campaign_id',
    'user_id': 'user_id',
    'channel': 'channel',
    'dismissed_at': 'dismissed_at',
}

# campaign_participations 表
CAMPAIGN_PARTICIPATIONS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'campaign_id': 'campaign_id',
    'user_id': 'user_id',
    'credits_received': 'credits_received',
    'claimed_at': 'claimed_at',
}

# campaigns 表
CAMPAIGNS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'campaign_id',
    'name': 'name',
    'description': 'description',
    'type': 'type',
    'config': 'config',
    'target_type': 'target_type',
    'target_config': 'target_config',
    'notification_channels': 'notification_channels',
    'notification_config': 'notification_config',
    'start_at': 'start_at',
    'end_at': 'end_at',
    'timezone': 'timezone',
    'usage_limit': 'usage_limit',
    'usage_per_user': 'usage_per_user',
    'usage_count': 'usage_count',
    'status': 'status',
    'is_active': 'is_active',
    'created_by': 'created_by',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
    'is_deleted': 'is_deleted',
    'deleted_at': 'deleted_at',
    'recovery_expires_at': 'recovery_expires_at',
    'is_permanently_deleted': 'is_permanently_deleted',
}

# clerk_webhook_events 表
CLERK_WEBHOOK_EVENTS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'event_id': 'event_id',
    'event_type': 'event_type',
    'payload': 'payload',
    'processed': 'processed',
    'processed_at': 'processed_at',
    'error_message': 'error_message',
    'retry_count': 'retry_count',
    'created_at': 'created_at',
    'processing_status': 'processing_status',
    'last_error': 'last_error',
}

# config_audit_logs 表
CONFIG_AUDIT_LOGS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'config_key': 'config_key',
    'old_value': 'old_value',
    'new_value': 'new_value',
    'action': 'action',
    'changed_by': 'changed_by',
    'changed_at': 'changed_at',
}

# content_reports 表
CONTENT_REPORTS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'report_id',
    'reporter_id': 'reporter_id',
    'listing_id': 'listing_id',
    'reason': 'reason',
    'description': 'description',
    'status': 'status',
    'admin_response': 'admin_response',
    'reviewed_by': 'reviewed_by',
    'reviewed_at': 'reviewed_at',
    'timezone': 'timezone',
    'created_at_local': 'created_at_local',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
    'is_deleted': 'is_deleted',
    'deleted_at': 'deleted_at',
    'recovery_expires_at': 'recovery_expires_at',
}

# credit_purchases 表
CREDIT_PURCHASES_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'purchase_id',
    'user_id': 'user_id',
    'plan_type': 'plan_type',
    'credits_amount': 'credits_amount',
    'price_usd': 'price_usd',
    'stripe_payment_intent_id': 'stripe_payment_intent_id',
    'stripe_invoice_id': 'stripe_invoice_id',
    'status': 'status',
    'idempotency_key': 'idempotency_key',
    'metadata': 'metadata',
    'completed_at': 'completed_at',
    'created_at': 'created_at',
}

# daily_metrics 表
DAILY_METRICS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'metric_date': 'metric_date',
    'total_users': 'total_users',
    'active_users': 'active_users',
    'new_users': 'new_users',
    'total_projects': 'total_projects',
    'new_projects': 'new_projects',
    'total_listings': 'total_listings',
    'new_listings': 'new_listings',
    'total_purchases': 'total_purchases',
    'revenue_usd': 'revenue_usd',
    'revenue_credits': 'revenue_credits',
    'ai_generations': 'ai_generations',
    'smart_scans': 'smart_scans',
    'credits_consumed': 'credits_consumed',
    'credits_granted': 'credits_granted',
    'error_count': 'error_count',
    'avg_response_time_ms': 'avg_response_time_ms',
    'p95_response_time_ms': 'p95_response_time_ms',
    'metadata': 'metadata',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
}

# daily_themes 表
DAILY_THEMES_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'theme_id',
    'title': 'title',
    'description': 'description',
    'date': 'date',
    'thumbnail_url': 'thumbnail_url',
    'preview_urls': 'preview_urls',
    'featured_asset_ids': 'featured_asset_ids',
    'recommended_categories': 'recommended_categories',
    'tags': 'tags',
    'status': 'status',
    'metadata': 'metadata',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
    'is_deleted': 'is_deleted',
    'deleted_at': 'deleted_at',
    'recovery_expires_at': 'recovery_expires_at',
}

# error_logs 表
ERROR_LOGS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'user_id': 'user_id',
    'error_type': 'error_type',
    'error_message': 'error_message',
    'error_stack': 'error_stack',
    'request_path': 'request_path',
    'request_method': 'request_method',
    'request_body': 'request_body',
    'response_status': 'response_status',
    'environment': 'environment',
    'severity': 'severity',
    'metadata': 'metadata',
    'resolved': 'resolved',
    'resolved_at': 'resolved_at',
    'resolved_by': 'resolved_by',
    'created_at': 'created_at',
}

# experiment_assignments 表
EXPERIMENT_ASSIGNMENTS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'experiment_id': 'experiment_id',
    'user_id': 'user_id',
    'variant_key': 'variant_key',
    'assigned_at': 'assigned_at',
    'is_deleted': 'is_deleted',
    'deleted_at': 'deleted_at',
    'recovery_expires_at': 'recovery_expires_at',
}

# experiment_conversions 表
EXPERIMENT_CONVERSIONS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'experiment_id': 'experiment_id',
    'user_id': 'user_id',
    'variant_key': 'variant_key',
    'metric_key': 'metric_key',
    'value': 'value',
    'metadata': 'metadata',
    'created_at': 'created_at',
}

# experiment_exposures 表
EXPERIMENT_EXPOSURES_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'experiment_id': 'experiment_id',
    'user_id': 'user_id',
    'variant_key': 'variant_key',
    'context': 'context',
    'created_at': 'created_at',
}

# experiment_results 表
EXPERIMENT_RESULTS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'experiment_id': 'experiment_id',
    'date': 'date',
    'variant_key': 'variant_key',
    'metrics': 'metrics',
    'sample_size': 'sample_size',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
}

# experiments 表
EXPERIMENTS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'experiment_id',
    'experiment_key': 'experiment_key',
    'experiment_name': 'experiment_name',
    'description': 'description',
    'hypothesis': 'hypothesis',
    'variants': 'variants',
    'status': 'status',
    'traffic_percentage': 'traffic_percentage',
    'target_tiers': 'target_tiers',
    'start_date': 'start_date',
    'end_date': 'end_date',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
    'is_deleted': 'is_deleted',
    'deleted_at': 'deleted_at',
    'recovery_expires_at': 'recovery_expires_at',
}

# feature_flags 表
FEATURE_FLAGS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'flag_id',
    'flag_key': 'flag_key',
    'flag_name': 'flag_name',
    'description': 'description',
    'is_enabled': 'is_enabled',
    'rollout_percentage': 'rollout_percentage',
    'target_tiers': 'target_tiers',
    'target_user_ids': 'target_user_ids',
    'config': 'config',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
}

# generation_tasks 表
GENERATION_TASKS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'task_id',
    'user_id': 'user_id',
    'project_id': 'project_id',
    'task_type': 'task_type',
    'prompt': 'prompt',
    'parameters': 'parameters',
    'status': 'status',
    'result_url': 'result_url',
    'result_metadata': 'result_metadata',
    'error_message': 'error_message',
    'credits_cost': 'credits_cost',
    'processing_time_ms': 'processing_time_ms',
    'retry_count': 'retry_count',
    'created_at': 'created_at',
    'started_at': 'started_at',
    'completed_at': 'completed_at',
    'updated_at': 'updated_at',
}

# holidays 表
HOLIDAYS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'holiday_id',
    'name': 'name',
    'name_i18n': 'name_i18n',
    'slug': 'slug',
    'month': 'month',
    'day': 'day',
    'regions': 'regions',
    'category': 'category',
    'is_major': 'is_major',
    'theme_colors': 'theme_colors',
    'asset_category_ids': 'asset_category_ids',
    'description': 'description',
    'tags': 'tags',
    'metadata': 'metadata',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
    'is_deleted': 'is_deleted',
    'deleted_at': 'deleted_at',
    'recovery_expires_at': 'recovery_expires_at',
}

# listing_usages 表
LISTING_USAGES_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'listing_id': 'listing_id',
    'user_id': 'user_id',
    'project_id': 'project_id',
    'usage_type': 'usage_type',
    'usage_count': 'usage_count',
    'metadata': 'metadata',
    'created_at': 'created_at',
}

# marketplace_favorites 表
MARKETPLACE_FAVORITES_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'user_id': 'user_id',
    'listing_id': 'listing_id',
    'created_at': 'created_at',
    'is_deleted': 'is_deleted',
    'deleted_at': 'deleted_at',
    'recovery_expires_at': 'recovery_expires_at',
}

# marketplace_reports 表
MARKETPLACE_REPORTS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'report_id',
    'listing_id': 'listing_id',
    'reporter_id': 'reporter_id',
    'report_reason': 'report_reason',
    'description': 'description',
    'status': 'status',
    'reviewed_by': 'reviewed_by',
    'reviewed_at': 'reviewed_at',
    'resolution': 'resolution',
    'action_taken': 'action_taken',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
}

# marketplace_reviews 表
MARKETPLACE_REVIEWS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'review_id',
    'listing_id': 'listing_id',
    'reviewer_id': 'reviewer_id',
    'rating': 'rating',
    'review_text': 'review_text',
    'is_verified_purchase': 'is_verified_purchase',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
    'is_deleted': 'is_deleted',
    'deleted_at': 'deleted_at',
    'recovery_expires_at': 'recovery_expires_at',
}

# monthly_metrics 表
MONTHLY_METRICS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'metric_year': 'metric_year',
    'metric_month': 'metric_month',
    'total_users': 'total_users',
    'active_users': 'active_users',
    'new_users': 'new_users',
    'churned_users': 'churned_users',
    'total_projects': 'total_projects',
    'new_projects': 'new_projects',
    'total_listings': 'total_listings',
    'new_listings': 'new_listings',
    'total_purchases': 'total_purchases',
    'revenue_usd': 'revenue_usd',
    'revenue_credits': 'revenue_credits',
    'ai_generations': 'ai_generations',
    'smart_scans': 'smart_scans',
    'credits_consumed': 'credits_consumed',
    'credits_granted': 'credits_granted',
    'mrr': 'mrr',
    'arr': 'arr',
    'ltv': 'ltv',
    'cac': 'cac',
    'retention_rate': 'retention_rate',
    'metadata': 'metadata',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
}

# notifications 表
NOTIFICATIONS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'notification_id',
    'user_id': 'user_id',
    'notification_type': 'notification_type',
    'title': 'title',
    'message': 'message',
    'action_url': 'action_url',
    'is_read': 'is_read',
    'read_at': 'read_at',
    'metadata': 'metadata',
    'created_at': 'created_at',
}

# onboarding_steps 表
ONBOARDING_STEPS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'step_id',
    'step_key': 'step_key',
    'step_name': 'step_name',
    'description': 'description',
    'step_order': 'step_order',
    'is_required': 'is_required',
    'target_tiers': 'target_tiers',
    'config': 'config',
    'is_active': 'is_active',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
}

# page_prompt_templates 表
PAGE_PROMPT_TEMPLATES_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'template_id',
    'template_name': 'template_name',
    'template_category': 'template_category',
    'prompt_template': 'prompt_template',
    'description': 'description',
    'example_input': 'example_input',
    'example_output': 'example_output',
    'parameters': 'parameters',
    'is_active': 'is_active',
    'usage_count': 'usage_count',
    'created_by': 'created_by',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
}

# payment_records 表
PAYMENT_RECORDS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'payment_id',
    'user_id': 'user_id',
    'payment_type': 'payment_type',
    'payment_method': 'payment_method',
    'amount_usd': 'amount_usd',
    'amount_credits': 'amount_credits',
    'currency': 'currency',
    'stripe_payment_intent_id': 'stripe_payment_intent_id',
    'stripe_charge_id': 'stripe_charge_id',
    'stripe_customer_id': 'stripe_customer_id',
    'status': 'status',
    'failure_reason': 'failure_reason',
    'receipt_url': 'receipt_url',
    'metadata': 'metadata',
    'refunded_amount': 'refunded_amount',
    'refunded_at': 'refunded_at',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
}

# pricing_history 表
PRICING_HISTORY_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'plan_id': 'plan_id',
    'plan_code': 'plan_code',
    'action': 'action',
    'old_data': 'old_data',
    'new_data': 'new_data',
    'changed_by': 'changed_by',
    'changed_at': 'changed_at',
}

# pricing_plans 表
PRICING_PLANS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'plan_id',
    'plan_code': 'plan_code',
    'plan_type': 'plan_type',
    'plan_name': 'plan_name',
    'description': 'description',
    'price_cents': 'price_cents',
    'original_price_cents': 'original_price_cents',
    'currency': 'currency',
    'billing_interval': 'billing_interval',
    'tier': 'tier',
    'monthly_credits': 'monthly_credits',
    'credits_amount': 'credits_amount',
    'stripe_price_id_prod': 'stripe_price_id_prod',
    'stripe_price_id_dev': 'stripe_price_id_dev',
    'stripe_product_id': 'stripe_product_id',
    'is_active': 'is_active',
    'is_visible': 'is_visible',
    'is_featured': 'is_featured',
    'sort_order': 'sort_order',
    'version': 'version',
    'effective_from': 'effective_from',
    'effective_until': 'effective_until',
    'metadata': 'metadata',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
    'created_by': 'created_by',
    'updated_by': 'updated_by',
}

# project_versions 表
PROJECT_VERSIONS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'version_id',
    'project_id': 'project_id',
    'version_number': 'version_number',
    'canvas_data': 'canvas_data',
    'thumbnail_url': 'thumbnail_url',
    'change_description': 'change_description',
    'created_by': 'created_by',
    'created_at': 'created_at',
}

# referrals 表
REFERRALS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'referral_id',
    'referrer_id': 'referrer_id',
    'referee_id': 'referee_id',
    'referral_code': 'referral_code',
    'status': 'status',
    'reward_given': 'reward_given',
    'reward_amount': 'reward_amount',
    'completed_at': 'completed_at',
    'created_at': 'created_at',
}

# scheduled_task_logs 表
SCHEDULED_TASK_LOGS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'task_name': 'task_name',
    'task_type': 'task_type',
    'started_at': 'started_at',
    'completed_at': 'completed_at',
    'duration_ms': 'duration_ms',
    'status': 'status',
    'result_summary': 'result_summary',
    'error_message': 'error_message',
    'error_stack': 'error_stack',
    'hostname': 'hostname',
    'pid': 'pid',
    'created_at': 'created_at',
}

# stripe_webhook_events 表
STRIPE_WEBHOOK_EVENTS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'event_id': 'event_id',
    'event_type': 'event_type',
    'payload': 'payload',
    'processed': 'processed',
    'processed_at': 'processed_at',
    'error_message': 'error_message',
    'retry_count': 'retry_count',
    'created_at': 'created_at',
    'processing_status': 'processing_status',
    'last_error': 'last_error',
}

# subscription_history 表
SUBSCRIPTION_HISTORY_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'user_id': 'user_id',
    'tier': 'tier',
    'action': 'action',
    'stripe_subscription_id': 'stripe_subscription_id',
    'stripe_event_id': 'stripe_event_id',
    'effective_date': 'effective_date',
    'metadata': 'metadata',
    'created_at': 'created_at',
}

# support_replies 表
SUPPORT_REPLIES_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'reply_id',
    'ticket_id': 'ticket_id',
    'user_id': 'user_id',
    'is_staff_reply': 'is_staff_reply',
    'message': 'message',
    'attachments': 'attachments',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
    'is_deleted': 'is_deleted',
    'deleted_at': 'deleted_at',
    'recovery_expires_at': 'recovery_expires_at',
}

# support_tickets 表
SUPPORT_TICKETS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'ticket_id',
    'user_id': 'user_id',
    'ticket_number': 'ticket_number',
    'subject': 'subject',
    'description': 'description',
    'category': 'category',
    'priority': 'priority',
    'status': 'status',
    'assigned_to': 'assigned_to',
    'attachments': 'attachments',
    'metadata': 'metadata',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
    'resolved_at': 'resolved_at',
    'closed_at': 'closed_at',
    'is_deleted': 'is_deleted',
    'deleted_at': 'deleted_at',
    'recovery_expires_at': 'recovery_expires_at',
}

# system_assets 表
SYSTEM_ASSETS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'asset_id',
    'category_id': 'category_id',
    'name': 'name',
    'slug': 'slug',
    'description': 'description',
    'asset_type': 'asset_type',
    'source': 'source',
    'source_user_id': 'source_user_id',
    'file_url': 'file_url',
    'thumbnail_url': 'thumbnail_url',
    'file_size': 'file_size',
    'file_format': 'file_format',
    'width': 'width',
    'height': 'height',
    'content': 'content',
    'min_tier': 'min_tier',
    'is_pro_only': 'is_pro_only',
    'tags': 'tags',
    'is_visible': 'is_visible',
    'is_featured': 'is_featured',
    'display_order': 'display_order',
    'usage_count': 'usage_count',
    'download_count': 'download_count',
    'favorite_count': 'favorite_count',
    'metadata': 'metadata',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
}

# system_resource_audit_logs 表
SYSTEM_RESOURCE_AUDIT_LOGS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'resource_id': 'resource_id',
    'action': 'action',
    'old_data': 'old_data',
    'new_data': 'new_data',
    'changed_by': 'changed_by',
    'changed_at': 'changed_at',
    'ip_address': 'ip_address',
    'user_agent': 'user_agent',
}

# user_discounts 表
USER_DISCOUNTS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'discount_id',
    'user_id': 'user_id',
    'discount_percent': 'discount_percent',
    'valid_from': 'valid_from',
    'valid_until': 'valid_until',
    'target_plan': 'target_plan',
    'created_at': 'created_at',
}

# user_events 表
USER_EVENTS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'user_id': 'user_id',
    'event_type': 'event_type',
    'event_data': 'event_data',
    'session_id': 'session_id',
    'ip_address': 'ip_address',
    'user_agent': 'user_agent',
    'referer': 'referer',
    'created_at': 'created_at',
    'is_deleted': 'is_deleted',
    'deleted_at': 'deleted_at',
    'recovery_expires_at': 'recovery_expires_at',
}

# user_generations 表
USER_GENERATIONS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'generation_id',
    'user_id': 'user_id',
    'generation_type': 'generation_type',
    'prompt': 'prompt',
    'result_url': 'result_url',
    'result_data': 'result_data',
    'credits_used': 'credits_used',
    'provider': 'provider',
    'model': 'model',
    'status': 'status',
    'error_message': 'error_message',
    'metadata': 'metadata',
    'created_at': 'created_at',
    'completed_at': 'completed_at',
}

# user_onboarding_progress 表
USER_ONBOARDING_PROGRESS_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'id',
    'user_id': 'user_id',
    'step_id': 'step_id',
    'status': 'status',
    'completed_at': 'completed_at',
    'skipped_at': 'skipped_at',
    'created_at': 'created_at',
}

# user_price_overrides 表
USER_PRICE_OVERRIDES_DB_TO_DOMAIN: Dict[str, str] = {
    'id': 'override_id',
    'user_id': 'user_id',
    'pricing_plan_id': 'pricing_plan_id',
    'override_price_cents': 'override_price_cents',
    'reason': 'reason',
    'valid_from': 'valid_from',
    'valid_until': 'valid_until',
    'created_by': 'created_by',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
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
