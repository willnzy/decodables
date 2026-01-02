-- ==============================================================================
-- Migration v3.9: Timezone Dual-Storage Strategy (时区双重存储策略)
-- 
-- 核心原则：
-- 1. UTC-0 (基准)：系统逻辑、跨区计算永远使用标准 UTC 时间 (created_at)
-- 2. Local Time (快照)：业务数据产生时"快照"存入当时的时区和当地时间
--    - 即使用户后续修改个人资料时区，历史数据的当地时间也不变
-- 
-- 变更内容：
-- - 业务表新增 timezone (快照时区) 和 created_at_local (当地时间) 字段
-- - 创建通用 Trigger 函数 handle_timezone_conversion
-- - 所有涉及时间的核心业务表应用该 Trigger
-- ==============================================================================

-- ==========================================
-- Part 1: 通用时区转换函数
-- ==========================================

-- 核心转换函数：将 UTC 时间转换为指定时区的本地时间
-- 参数：
--   p_utc_time: UTC 时间 (timestamptz)
--   p_timezone: IANA 时区标识符 (text)，如 'Asia/Shanghai'
-- 返回：本地时间 (timestamp without time zone)
CREATE OR REPLACE FUNCTION convert_utc_to_local(
    p_utc_time TIMESTAMPTZ,
    p_timezone TEXT
)
RETURNS TIMESTAMP WITHOUT TIME ZONE
LANGUAGE plpgsql
IMMUTABLE
STRICT
AS $$
BEGIN
    -- 验证时区有效性，无效则回退到 UTC
    BEGIN
        RETURN (p_utc_time AT TIME ZONE COALESCE(NULLIF(p_timezone, ''), 'UTC'));
    EXCEPTION WHEN OTHERS THEN
        -- 如果时区无效（如拼写错误），返回 UTC 时间
        RAISE NOTICE 'Invalid timezone "%", falling back to UTC', p_timezone;
        RETURN (p_utc_time AT TIME ZONE 'UTC');
    END;
END;
$$;

COMMENT ON FUNCTION convert_utc_to_local(TIMESTAMPTZ, TEXT) IS 
'Convert UTC timestamp to local time based on IANA timezone identifier. 
Safe fallback to UTC if timezone is invalid.';


-- ==========================================
-- Part 2: 通用 Trigger 函数 (核心)
-- ==========================================

-- 通用 Trigger 函数：自动计算并填充 created_at_local
-- 逻辑：
--   1. 读取该行的 timezone 字段
--   2. 读取该行的 UTC 时间字段（created_at 或 purchased_at）
--   3. 使用 AT TIME ZONE 计算本地时间
--   4. 填充到 _local 字段
-- 
-- 优势：无论通过 API 还是 SQL 直接写入，created_at_local 永远与 UTC 保持数学一致
CREATE OR REPLACE FUNCTION handle_timezone_conversion()
RETURNS TRIGGER AS $$
DECLARE
    v_timezone TEXT;
    v_utc_time TIMESTAMPTZ;
    v_local_field TEXT;
    v_utc_field TEXT;
BEGIN
    -- 获取时区（从当前行的 timezone 字段读取，而非查询用户表）
    v_timezone := COALESCE(NEW.timezone, 'UTC');
    
    -- 确定 UTC 时间字段名称（支持不同命名约定）
    -- 优先检查常见的时间字段名
    IF TG_TABLE_NAME = 'user_purchases' THEN
        v_utc_field := 'purchased_at';
        v_local_field := 'purchased_at_local';
        v_utc_time := NEW.purchased_at;
    ELSE
        v_utc_field := 'created_at';
        v_local_field := 'created_at_local';
        v_utc_time := NEW.created_at;
    END IF;
    
    -- 确保 UTC 时间存在
    IF v_utc_time IS NULL THEN
        v_utc_time := NOW();
    END IF;
    
    -- 计算本地时间并写入
    IF TG_TABLE_NAME = 'user_purchases' THEN
        NEW.purchased_at_local := convert_utc_to_local(v_utc_time, v_timezone);
    ELSE
        NEW.created_at_local := convert_utc_to_local(v_utc_time, v_timezone);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION handle_timezone_conversion() IS 
'Universal trigger function for dual-storage timezone strategy.
Reads timezone from the same row (snapshot) and auto-computes local time.
Ensures data consistency regardless of write method (API or direct SQL).';


-- ==========================================
-- Part 3: profiles 表（用户表）
-- ==========================================

-- 用户表的 timezone 是"当前设置"，可变
-- created_at_local 是注册时的本地时间
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'UTC';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS created_at_local TIMESTAMP WITHOUT TIME ZONE;

COMMENT ON COLUMN profiles.timezone IS 'User current timezone preference (IANA format). Mutable.';
COMMENT ON COLUMN profiles.created_at_local IS 'Registration time in local timezone (snapshot at registration).';

-- profiles 表使用自身的 timezone 字段
DROP TRIGGER IF EXISTS trigger_profiles_timezone ON profiles;
CREATE TRIGGER trigger_profiles_timezone
    BEFORE INSERT OR UPDATE OF created_at, timezone ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION handle_timezone_conversion();


-- ==========================================
-- Part 4: credit_transactions 表（交易记录）
-- ==========================================

-- 交易记录的 timezone 是"快照"，记录交易发生时的时区
ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'UTC';
ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS created_at_local TIMESTAMP WITHOUT TIME ZONE;

COMMENT ON COLUMN credit_transactions.timezone IS 'Snapshot: timezone when transaction occurred. Immutable after creation.';
COMMENT ON COLUMN credit_transactions.created_at_local IS 'Transaction time in local timezone (snapshot).';

DROP TRIGGER IF EXISTS trigger_credit_tx_timezone ON credit_transactions;
CREATE TRIGGER trigger_credit_tx_timezone
    BEFORE INSERT ON credit_transactions
    FOR EACH ROW
    EXECUTE FUNCTION handle_timezone_conversion();


-- ==========================================
-- Part 5: user_purchases 表（购买记录）
-- ==========================================

ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'UTC';
ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS purchased_at_local TIMESTAMP WITHOUT TIME ZONE;

COMMENT ON COLUMN user_purchases.timezone IS 'Snapshot: timezone when purchase occurred.';
COMMENT ON COLUMN user_purchases.purchased_at_local IS 'Purchase time in local timezone (snapshot).';

DROP TRIGGER IF EXISTS trigger_purchases_timezone ON user_purchases;
CREATE TRIGGER trigger_purchases_timezone
    BEFORE INSERT ON user_purchases
    FOR EACH ROW
    EXECUTE FUNCTION handle_timezone_conversion();


-- ==========================================
-- Part 6: admin_operation_logs 表（管理员操作日志）
-- ==========================================

ALTER TABLE admin_operation_logs ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'UTC';
ALTER TABLE admin_operation_logs ADD COLUMN IF NOT EXISTS created_at_local TIMESTAMP WITHOUT TIME ZONE;

COMMENT ON COLUMN admin_operation_logs.timezone IS 'Snapshot: timezone when admin operation occurred.';
COMMENT ON COLUMN admin_operation_logs.created_at_local IS 'Operation time in local timezone (snapshot).';

DROP TRIGGER IF EXISTS trigger_admin_logs_timezone ON admin_operation_logs;
CREATE TRIGGER trigger_admin_logs_timezone
    BEFORE INSERT ON admin_operation_logs
    FOR EACH ROW
    EXECUTE FUNCTION handle_timezone_conversion();


-- ==========================================
-- Part 7: activity_logs 表（用户活动日志）
-- ==========================================

ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'UTC';
ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS created_at_local TIMESTAMP WITHOUT TIME ZONE;

COMMENT ON COLUMN activity_logs.timezone IS 'Snapshot: timezone when activity occurred.';
COMMENT ON COLUMN activity_logs.created_at_local IS 'Activity time in local timezone (snapshot).';

DROP TRIGGER IF EXISTS trigger_activity_logs_timezone ON activity_logs;
CREATE TRIGGER trigger_activity_logs_timezone
    BEFORE INSERT ON activity_logs
    FOR EACH ROW
    EXECUTE FUNCTION handle_timezone_conversion();


-- ==========================================
-- Part 8: error_logs 表（错误日志）
-- ==========================================

ALTER TABLE error_logs ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'UTC';
ALTER TABLE error_logs ADD COLUMN IF NOT EXISTS created_at_local TIMESTAMP WITHOUT TIME ZONE;

COMMENT ON COLUMN error_logs.timezone IS 'Snapshot: timezone when error occurred.';
COMMENT ON COLUMN error_logs.created_at_local IS 'Error time in local timezone (snapshot).';

DROP TRIGGER IF EXISTS trigger_error_logs_timezone ON error_logs;
CREATE TRIGGER trigger_error_logs_timezone
    BEFORE INSERT ON error_logs
    FOR EACH ROW
    EXECUTE FUNCTION handle_timezone_conversion();


-- ==========================================
-- Part 9: analytics_events 表（分析事件）
-- ==========================================

ALTER TABLE analytics_events ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'UTC';
ALTER TABLE analytics_events ADD COLUMN IF NOT EXISTS created_at_local TIMESTAMP WITHOUT TIME ZONE;

COMMENT ON COLUMN analytics_events.timezone IS 'Snapshot: timezone when event occurred.';
COMMENT ON COLUMN analytics_events.created_at_local IS 'Event time in local timezone (snapshot).';

DROP TRIGGER IF EXISTS trigger_analytics_timezone ON analytics_events;
CREATE TRIGGER trigger_analytics_timezone
    BEFORE INSERT ON analytics_events
    FOR EACH ROW
    EXECUTE FUNCTION handle_timezone_conversion();


-- ==========================================
-- Part 10: user_events 表（用户事件）
-- ==========================================

ALTER TABLE user_events ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'UTC';
ALTER TABLE user_events ADD COLUMN IF NOT EXISTS created_at_local TIMESTAMP WITHOUT TIME ZONE;

COMMENT ON COLUMN user_events.timezone IS 'Snapshot: timezone when user event occurred.';
COMMENT ON COLUMN user_events.created_at_local IS 'Event time in local timezone (snapshot).';

DROP TRIGGER IF EXISTS trigger_user_events_timezone ON user_events;
CREATE TRIGGER trigger_user_events_timezone
    BEFORE INSERT ON user_events
    FOR EACH ROW
    EXECUTE FUNCTION handle_timezone_conversion();


-- ==========================================
-- Part 11: projects 表（项目）
-- ==========================================

ALTER TABLE projects ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'UTC';
ALTER TABLE projects ADD COLUMN IF NOT EXISTS created_at_local TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS updated_at_local TIMESTAMP WITHOUT TIME ZONE;

COMMENT ON COLUMN projects.timezone IS 'Snapshot: timezone when project was created.';
COMMENT ON COLUMN projects.created_at_local IS 'Creation time in local timezone (snapshot).';
COMMENT ON COLUMN projects.updated_at_local IS 'Last update time in local timezone.';

-- projects 表需要处理 created_at 和 updated_at 两个时间字段
CREATE OR REPLACE FUNCTION handle_projects_timezone()
RETURNS TRIGGER AS $$
DECLARE
    v_timezone TEXT;
BEGIN
    v_timezone := COALESCE(NEW.timezone, 'UTC');
    
    -- 新建时设置 created_at_local
    IF TG_OP = 'INSERT' THEN
        NEW.created_at_local := convert_utc_to_local(COALESCE(NEW.created_at, NOW()), v_timezone);
    END IF;
    
    -- 更新时设置 updated_at_local
    NEW.updated_at_local := convert_utc_to_local(COALESCE(NEW.updated_at, NOW()), v_timezone);
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_projects_timezone ON projects;
CREATE TRIGGER trigger_projects_timezone
    BEFORE INSERT OR UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION handle_projects_timezone();


-- ==========================================
-- Part 12: assets 表（用户素材）
-- ==========================================

ALTER TABLE assets ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'UTC';
ALTER TABLE assets ADD COLUMN IF NOT EXISTS created_at_local TIMESTAMP WITHOUT TIME ZONE;

COMMENT ON COLUMN assets.timezone IS 'Snapshot: timezone when asset was created.';
COMMENT ON COLUMN assets.created_at_local IS 'Creation time in local timezone (snapshot).';

DROP TRIGGER IF EXISTS trigger_assets_timezone ON assets;
CREATE TRIGGER trigger_assets_timezone
    BEFORE INSERT ON assets
    FOR EACH ROW
    EXECUTE FUNCTION handle_timezone_conversion();


-- ==========================================
-- Part 13: marketplace_listings 表（市场商品）
-- ==========================================

ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'UTC';
ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS created_at_local TIMESTAMP WITHOUT TIME ZONE;

COMMENT ON COLUMN marketplace_listings.timezone IS 'Snapshot: timezone when listing was created.';
COMMENT ON COLUMN marketplace_listings.created_at_local IS 'Creation time in local timezone (snapshot).';

DROP TRIGGER IF EXISTS trigger_listings_timezone ON marketplace_listings;
CREATE TRIGGER trigger_listings_timezone
    BEFORE INSERT ON marketplace_listings
    FOR EACH ROW
    EXECUTE FUNCTION handle_timezone_conversion();


-- ==========================================
-- Part 14: notifications 表（通知）
-- ==========================================

ALTER TABLE notifications ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'UTC';
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS created_at_local TIMESTAMP WITHOUT TIME ZONE;

COMMENT ON COLUMN notifications.timezone IS 'Snapshot: timezone when notification was created.';
COMMENT ON COLUMN notifications.created_at_local IS 'Creation time in local timezone (snapshot).';

DROP TRIGGER IF EXISTS trigger_notifications_timezone ON notifications;
CREATE TRIGGER trigger_notifications_timezone
    BEFORE INSERT ON notifications
    FOR EACH ROW
    EXECUTE FUNCTION handle_timezone_conversion();


-- ==========================================
-- Part 15: content_reports 表（内容举报）
-- ==========================================

ALTER TABLE content_reports ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'UTC';
ALTER TABLE content_reports ADD COLUMN IF NOT EXISTS created_at_local TIMESTAMP WITHOUT TIME ZONE;

COMMENT ON COLUMN content_reports.timezone IS 'Snapshot: timezone when report was submitted.';
COMMENT ON COLUMN content_reports.created_at_local IS 'Report time in local timezone (snapshot).';

DROP TRIGGER IF EXISTS trigger_reports_timezone ON content_reports;
CREATE TRIGGER trigger_reports_timezone
    BEFORE INSERT ON content_reports
    FOR EACH ROW
    EXECUTE FUNCTION handle_timezone_conversion();


-- ==========================================
-- Part 16: 索引优化
-- ==========================================

-- 用户时区索引（用于统计分布）
CREATE INDEX IF NOT EXISTS idx_profiles_timezone ON profiles(timezone);

-- 本地时间索引（用于 Admin 面板按当地日期查询）
CREATE INDEX IF NOT EXISTS idx_credit_tx_local_date ON credit_transactions(DATE(created_at_local));
CREATE INDEX IF NOT EXISTS idx_purchases_local_date ON user_purchases(DATE(purchased_at_local));
CREATE INDEX IF NOT EXISTS idx_projects_local_date ON projects(DATE(created_at_local));


-- ==========================================
-- Part 17: 辅助视图与函数
-- ==========================================

-- 用户时区分布视图
CREATE OR REPLACE VIEW user_timezone_distribution AS
SELECT 
    COALESCE(NULLIF(timezone, ''), 'UTC') as timezone,
    COUNT(*) as user_count,
    ROUND(COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER(), 0), 2) as percentage
FROM profiles
GROUP BY timezone
ORDER BY user_count DESC;

COMMENT ON VIEW user_timezone_distribution IS 'User distribution by timezone for Admin analytics.';


-- 格式化本地时间函数（Admin 面板使用）
CREATE OR REPLACE FUNCTION format_local_datetime(
    p_local_time TIMESTAMP WITHOUT TIME ZONE,
    p_timezone TEXT,
    p_format TEXT DEFAULT 'YYYY-MM-DD HH24:MI:SS'
)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    v_offset TEXT;
BEGIN
    IF p_local_time IS NULL THEN
        RETURN NULL;
    END IF;
    
    -- 计算时区偏移量用于显示
    BEGIN
        v_offset := TO_CHAR(NOW() AT TIME ZONE p_timezone - NOW() AT TIME ZONE 'UTC', 'FMHH24:MI');
        IF v_offset !~ '^-' THEN
            v_offset := '+' || v_offset;
        END IF;
    EXCEPTION WHEN OTHERS THEN
        v_offset := '+00:00';
    END;
    
    RETURN TO_CHAR(p_local_time, p_format) || ' (UTC' || v_offset || ')';
END;
$$;

COMMENT ON FUNCTION format_local_datetime IS 
'Format local timestamp for Admin panel display with timezone offset.
Example output: "2026-01-03 18:00:00 (UTC+08:00)"';


-- ==========================================
-- 完成说明
-- ==========================================
-- 
-- ## Trigger 工作原理
-- 
-- 1. 当执行 INSERT 时：
--    - Trigger 读取该行的 `timezone` 字段（快照值，由应用层写入）
--    - 使用 `convert_utc_to_local()` 计算本地时间
--    - 自动填充 `created_at_local` 字段
-- 
-- 2. 关键点：
--    - `timezone` 是快照值，必须由应用层在写入时提供
--    - 即使用户后续修改个人资料时区，历史数据不受影响
--    - Trigger 只负责计算，不负责获取时区（解耦）
-- 
-- ## 应用层责任
-- 
-- 后端写入数据时必须：
-- 1. 从 Context（用户会话/请求头）获取时区
-- 2. 将时区作为 `timezone` 字段写入数据库
-- 
-- 示例代码（Python）：
-- ```python
-- def create_transaction(user_id, amount, timezone='UTC'):
--     data = {
--         'user_id': user_id,
--         'amount': amount,
--         'timezone': timezone,  # 必须提供！
--         # created_at_local 由 Trigger 自动计算
--     }
--     supabase.table('credit_transactions').insert(data).execute()
-- ```
-- 
-- ## Admin 面板查询示例
-- 
-- ```sql
-- SELECT 
--     id,
--     amount,
--     created_at,                 -- UTC 时间（用于排序/计算）
--     format_local_datetime(created_at_local, timezone) as display_time,  -- 显示用
--     timezone
-- FROM credit_transactions
-- WHERE user_id = 'xxx'
-- ORDER BY created_at DESC;
-- ```
-- ==============================================================================
