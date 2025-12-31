-- ============================================
-- Admin Operation Logs Table ()
-- ============================================
-- ，

CREATE TABLE IF NOT EXISTS admin_operation_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    admin_id UUID NOT NULL REFERENCES profiles(id),
    operation_type VARCHAR(50) NOT NULL,  -- credit_adjust, tier_change, refund, subscription_cancel, etc.
    target_user_id UUID REFERENCES profiles(id),
    details TEXT,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 
CREATE INDEX IF NOT EXISTS idx_admin_logs_created_at ON admin_operation_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_logs_operation_type ON admin_operation_logs(operation_type);
CREATE INDEX IF NOT EXISTS idx_admin_logs_admin_id ON admin_operation_logs(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_logs_target_user ON admin_operation_logs(target_user_id);

-- RLS  ( admin )
ALTER TABLE admin_operation_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Admin can view operation logs" ON admin_operation_logs
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE profiles.id = auth.uid() 
            AND profiles.role = 'admin'
        )
    );

CREATE POLICY "Admin can insert operation logs" ON admin_operation_logs
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE profiles.id = auth.uid() 
            AND profiles.role = 'admin'
        )
    );


-- ============================================
-- User Events Table ()
-- ============================================
-- ，

CREATE TABLE IF NOT EXISTS user_events (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES profiles(id),  -- （）
    event_type VARCHAR(100) NOT NULL,
    properties JSONB DEFAULT '{}',
    session_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 
CREATE INDEX IF NOT EXISTS idx_user_events_created_at ON user_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_events_event_type ON user_events(event_type);
CREATE INDEX IF NOT EXISTS idx_user_events_user_id ON user_events(user_id);
CREATE INDEX IF NOT EXISTS idx_user_events_session ON user_events(session_id);
CREATE INDEX IF NOT EXISTS idx_user_events_properties ON user_events USING GIN(properties);

-- RLS 
ALTER TABLE user_events ENABLE ROW LEVEL SECURITY;

-- （）
CREATE POLICY "Anyone can insert events" ON user_events
    FOR INSERT
    WITH CHECK (true);

--  admin 
CREATE POLICY "Admin can view all events" ON user_events
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE profiles.id = auth.uid() 
            AND profiles.role = 'admin'
        )
    );

-- 
CREATE POLICY "Users can view own events" ON user_events
    FOR SELECT
    USING (user_id = auth.uid());


-- ============================================
-- （）
-- ============================================

-- profiles 
CREATE INDEX IF NOT EXISTS idx_profiles_tier ON profiles(tier);
CREATE INDEX IF NOT EXISTS idx_profiles_created_at ON profiles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_profiles_subscription_status ON profiles(subscription_status);

-- credit_transactions 
CREATE INDEX IF NOT EXISTS idx_credit_tx_bucket ON credit_transactions(bucket);
CREATE INDEX IF NOT EXISTS idx_credit_tx_type ON credit_transactions(type);
CREATE INDEX IF NOT EXISTS idx_credit_tx_created_at ON credit_transactions(created_at DESC);

-- projects 
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at DESC);

-- activity_logs 
CREATE INDEX IF NOT EXISTS idx_activity_logs_action ON activity_logs(action);
CREATE INDEX IF NOT EXISTS idx_activity_logs_created_at ON activity_logs(created_at DESC);


-- ============================================
--  user_code  profiles （）
-- ============================================
-- 

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'profiles' AND column_name = 'user_code'
    ) THEN
        ALTER TABLE profiles ADD COLUMN user_code VARCHAR(20);
        
        --  user_code
        UPDATE profiles 
        SET user_code = 'U' || SUBSTRING(id::text, 1, 8)
        WHERE user_code IS NULL;
        
        -- 
        CREATE UNIQUE INDEX idx_profiles_user_code ON profiles(user_code);
    END IF;
END $$;


-- ============================================
-- （，）
-- ============================================

-- 
CREATE OR REPLACE VIEW admin_user_stats AS
SELECT 
    DATE_TRUNC('day', created_at) AS date,
    COUNT(*) AS new_users,
    COUNT(*) FILTER (WHERE tier = 'free') AS free_users,
    COUNT(*) FILTER (WHERE tier = 'starter') AS starter_users,
    COUNT(*) FILTER (WHERE tier = 'pro') AS pro_users
FROM profiles
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY date DESC;

-- 
CREATE OR REPLACE VIEW admin_revenue_stats AS
SELECT 
    DATE_TRUNC('day', created_at) AS date,
    COUNT(*) FILTER (WHERE type LIKE '%sub%') AS subscription_transactions,
    COUNT(*) FILTER (WHERE type LIKE '%topup%' OR type LIKE '%credits%') AS credit_transactions
FROM credit_transactions
WHERE bucket = 'payment'
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY date DESC;

