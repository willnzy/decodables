-- ============================================================================
-- HOTFIX: 用户创建方案 P0 风险修复
-- ============================================================================
-- 日期: 2026-01-13
-- 优先级: P0 (紧急)
-- 影响: 修复重复奖励、TOCTOU race、user_code 冲突
-- ============================================================================

-- ============================================================================
-- Fix 1: 修复 user_code 并发冲突
-- ============================================================================

-- 创建序列（原子递增，无冲突）
CREATE SEQUENCE IF NOT EXISTS user_code_seq START 1;

-- 更新 generate_user_code() 函数
CREATE OR REPLACE FUNCTION generate_user_code()
RETURNS TEXT AS $$
DECLARE
    new_user_code TEXT;
    current_timestamp_str TEXT;
    sequence_number BIGINT;
BEGIN
    -- 时间戳 (YYMMDDHHMMSS) - 12 位
    current_timestamp_str := TO_CHAR(NOW(), 'YYMMDDHH24MISS');
    
    -- 使用序列（原子递增，无冲突）- 10 位
    sequence_number := nextval('user_code_seq');
    
    -- 组合成 26 位用户码
    -- 格式: [时间12位][序列10位][随机4位]
    new_user_code := 
        current_timestamp_str ||                           -- 12 位: 时间戳
        LPAD(sequence_number::TEXT, 10, '0') ||           -- 10 位: 序列号
        LPAD(FLOOR(RANDOM() * 10000)::TEXT, 4, '0');      --  4 位: 随机数
    
    RETURN new_user_code;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION generate_user_code() IS 
'生成 26 位唯一用户码（使用序列避免并发冲突）';


-- ============================================================================
-- Fix 2: 修复 TOCTOU Race Condition（使用 UPSERT）
-- ============================================================================

CREATE OR REPLACE FUNCTION create_user_idempotent(
    p_user_id TEXT,
    p_email TEXT,
    p_source TEXT,  -- 'webhook' or 'jit'
    
    -- Optional fields
    p_username TEXT DEFAULT NULL,
    p_first_name TEXT DEFAULT NULL,
    p_last_name TEXT DEFAULT NULL,
    p_avatar_url TEXT DEFAULT NULL,
    p_display_name TEXT DEFAULT NULL
)
RETURNS TABLE(
    user_profile JSONB,
    was_created BOOLEAN,
    created_by TEXT
) 
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_existing_profile profiles%ROWTYPE;
    v_new_user_code TEXT;
    v_was_created BOOLEAN;
    v_display_name_final TEXT;
BEGIN
    -- ✅ 使用 UPSERT 模式（原子操作，无 race condition）
    
    -- Step 1: 尝试插入（如果不存在）
    v_new_user_code := generate_user_code();
    
    v_display_name_final := COALESCE(
        p_display_name,
        p_username,
        p_first_name,
        split_part(p_email, '@', 1)
    );
    
    -- 原子插入（如果已存在则忽略）
    INSERT INTO profiles (
        id,
        email,
        user_code,
        username,
        first_name,
        last_name,
        avatar_url,
        display_name,
        tier,
        credits_permanent,
        created_by,
        created_at,
        updated_at
    ) VALUES (
        p_user_id,
        p_email,
        v_new_user_code,
        p_username,
        p_first_name,
        p_last_name,
        p_avatar_url,
        v_display_name_final,
        't1',
        50,  -- 注册奖励（仅在创建时发放）
        p_source,
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    )
    ON CONFLICT (id) DO NOTHING  -- ✅ 如果已存在，不做任何操作
    RETURNING * INTO v_existing_profile;
    
    -- Step 2: 判断是新创建还是已存在
    IF v_existing_profile.id IS NOT NULL THEN
        -- ✅ 新创建成功
        v_was_created := TRUE;
        
        -- 记录创建事件
        INSERT INTO user_creation_logs (
            user_id,
            source,
            action,
            metadata,
            created_at
        ) VALUES (
            p_user_id,
            p_source,
            'created',
            jsonb_build_object(
                'email', p_email,
                'username', p_username,
                'has_avatar', (p_avatar_url IS NOT NULL)
            ),
            CURRENT_TIMESTAMP
        );
        
        -- 返回新创建的用户
        RETURN QUERY
        SELECT 
            row_to_json(v_existing_profile)::jsonb,
            v_was_created,
            p_source;
        RETURN;
    ELSE
        -- ✅ 用户已存在（被其他进程创建）
        v_was_created := FALSE;
        
        -- 读取现有用户
        SELECT * INTO v_existing_profile
        FROM profiles
        WHERE id = p_user_id;
        
        -- 记录重复创建尝试
        INSERT INTO user_creation_logs (
            user_id,
            source,
            action,
            metadata,
            created_at
        ) VALUES (
            p_user_id,
            p_source,
            'duplicate_attempt',
            jsonb_build_object(
                'existing_created_by', v_existing_profile.created_by,
                'existing_created_at', v_existing_profile.created_at,
                'attempted_with_email', p_email
            ),
            CURRENT_TIMESTAMP
        );
        
        -- 返回现有用户
        RETURN QUERY
        SELECT 
            row_to_json(v_existing_profile)::jsonb,
            v_was_created,
            v_existing_profile.created_by;
        RETURN;
    END IF;
    
EXCEPTION
    WHEN OTHERS THEN
        -- 记录错误（但不影响事务回滚）
        BEGIN
            INSERT INTO error_logs (
                operation,
                error_message,
                details,
                created_at
            ) VALUES (
                'create_user_idempotent',
                SQLERRM,
                jsonb_build_object(
                    'user_id', p_user_id,
                    'source', p_source,
                    'email', p_email
                ),
                CURRENT_TIMESTAMP
            );
        EXCEPTION
            WHEN OTHERS THEN
                -- 即使记录错误失败也不影响主流程
                NULL;
        END;
        
        -- 重新抛出原始异常
        RAISE;
END;
$$;

COMMENT ON FUNCTION create_user_idempotent(TEXT, TEXT, TEXT, TEXT, TEXT, TEXT, TEXT, TEXT) IS 
'幂等用户创建函数（HOTFIX: 使用 UPSERT 避免 race condition）';


-- ============================================================================
-- Fix 3: 创建错误日志表（如果不存在）
-- ============================================================================

CREATE TABLE IF NOT EXISTS error_logs (
    id BIGSERIAL PRIMARY KEY,
    operation TEXT NOT NULL,
    error_message TEXT NOT NULL,
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_error_logs_created_at 
ON error_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_error_logs_operation 
ON error_logs(operation);

COMMENT ON TABLE error_logs IS '系统错误日志（用于追踪 RPC 函数异常）';


-- ============================================================================
-- Fix 4: 优化监控统计函数（避免重复计数）
-- ============================================================================

CREATE OR REPLACE FUNCTION get_user_creation_stats(p_days INTEGER)
RETURNS TABLE(
    total_users BIGINT,
    webhook_created BIGINT,
    jit_created BIGINT,
    webhook_success_rate NUMERIC,
    jit_fallback_rate NUMERIC,
    avg_webhook_delay NUMERIC,
    duplicate_attempts BIGINT
) AS $$
BEGIN
    RETURN QUERY
    WITH recent_users AS (
        SELECT 
            id,
            created_by,
            created_at
        FROM profiles
        WHERE created_at >= NOW() - INTERVAL '1 day' * p_days
    ),
    creation_events AS (
        -- ✅ 使用 DISTINCT ON 避免重复计数
        SELECT DISTINCT ON (user_id)
            user_id,
            source,
            action,
            created_at
        FROM user_creation_logs
        WHERE created_at >= NOW() - INTERVAL '1 day' * p_days
          AND action = 'created'
        ORDER BY user_id, created_at ASC
    )
    SELECT
        COUNT(DISTINCT ru.id) AS total_users,
        COUNT(DISTINCT CASE WHEN ru.created_by = 'webhook' THEN ru.id END) AS webhook_created,
        COUNT(DISTINCT CASE WHEN ru.created_by = 'jit' THEN ru.id END) AS jit_created,
        
        -- ✅ 避免除以 0
        ROUND(
            COALESCE(
                COUNT(DISTINCT CASE WHEN ru.created_by = 'webhook' THEN ru.id END)::NUMERIC 
                / NULLIF(COUNT(DISTINCT ru.id), 0) * 100,
                0
            ), 
            2
        ) AS webhook_success_rate,
        
        ROUND(
            COALESCE(
                COUNT(DISTINCT CASE WHEN ru.created_by = 'jit' THEN ru.id END)::NUMERIC 
                / NULLIF(COUNT(DISTINCT ru.id), 0) * 100,
                0
            ), 
            2
        ) AS jit_fallback_rate,
        
        -- 计算平均延迟（webhook 创建时间 - 用户注册时间）
        ROUND(
            COALESCE(
                AVG(EXTRACT(EPOCH FROM (ru.created_at - ce.created_at))),
                0
            ), 
            2
        ) AS avg_webhook_delay,
        
        -- 重复尝试次数
        (
            SELECT COUNT(*) 
            FROM user_creation_logs 
            WHERE action = 'duplicate_attempt'
              AND created_at >= NOW() - INTERVAL '1 day' * p_days
        ) AS duplicate_attempts
        
    FROM recent_users ru
    LEFT JOIN creation_events ce ON ru.id = ce.user_id;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- Validation: 验证修复是否成功
-- ============================================================================

DO $$
BEGIN
    -- 验证序列
    IF EXISTS (SELECT 1 FROM pg_sequences WHERE sequencename = 'user_code_seq') THEN
        RAISE NOTICE '✅ user_code_seq 序列创建成功';
    ELSE
        RAISE EXCEPTION '❌ user_code_seq 序列创建失败';
    END IF;
    
    -- 验证函数
    IF EXISTS (
        SELECT 1 FROM pg_proc 
        WHERE proname = 'create_user_idempotent'
    ) THEN
        RAISE NOTICE '✅ create_user_idempotent 函数已更新';
    ELSE
        RAISE EXCEPTION '❌ create_user_idempotent 函数未找到';
    END IF;
    
    -- 验证错误日志表
    IF EXISTS (
        SELECT 1 FROM pg_tables 
        WHERE tablename = 'error_logs'
    ) THEN
        RAISE NOTICE '✅ error_logs 表已创建';
    ELSE
        RAISE EXCEPTION '❌ error_logs 表创建失败';
    END IF;
    
    RAISE NOTICE '🎉 所有 P0 修复已成功应用！';
END
$$;


-- ============================================================================
-- 使用说明
-- ============================================================================

COMMENT ON FUNCTION create_user_idempotent(TEXT, TEXT, TEXT, TEXT, TEXT, TEXT, TEXT, TEXT) IS 
'
🔧 HOTFIX 修复内容：
1. ✅ 使用 UPSERT 避免 TOCTOU race condition
2. ✅ 使用序列生成 user_code 避免并发冲突
3. ✅ 完善错误处理和日志记录
4. ✅ 优化监控统计避免重复计数

📊 性能提升：
- 减少 1 次 SELECT FOR UPDATE（更快）
- 原子操作（更安全）
- 无锁等待（更高并发）

🎯 下一步：
- 在应用层删除重复的 _grant_signup_bonus() 调用
- 配置日志表定期清理
- 添加 Grafana 监控
';
