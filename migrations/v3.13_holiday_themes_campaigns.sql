-- ==============================================================================
-- v3.13: Holiday Themes & Marketing Campaigns System
-- 
-- This migration adds:
-- 1. holiday_themes - Auto-scheduled visual decorations for US holidays
-- 2. campaigns - Marketing promotions (credits gift/discount/bonus)
-- 3. campaign_claims - Track user claims
-- 4. campaign_dismissals - Track notification dismissals
-- ==============================================================================

-- ============================================================
-- Part 1: Holiday Themes System
-- ============================================================

CREATE TABLE IF NOT EXISTS holiday_themes (
    id TEXT PRIMARY KEY,                    -- Theme ID, e.g., 'christmas', 'halloween'
    name TEXT NOT NULL,                     -- Display name
    
    -- Date rule (supports fixed and dynamic dates)
    -- Fixed: { "type": "fixed", "start": "12-20", "end": "12-26" }
    -- Dynamic: { "type": "dynamic", "rule": "us_thanksgiving", "offset_start": -1, "offset_end": 3 }
    date_rule JSONB NOT NULL,
    
    -- Theme visual configuration
    theme_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    /*
    {
        "colors": {
            "primary": "#c41e3a",
            "secondary": "#228b22",
            "accent": "#ffd700",
            "banner_bg": "#c41e3a",
            "banner_text": "#ffffff"
        },
        "badge": {
            "text": "🎄 Merry Christmas!",
            "style": "festive"
        },
        "decorations": {
            "type": "snowflakes",     -- snowflakes | hearts | confetti | fireworks | none
            "density": "medium"       -- light | medium | heavy
        },
        "banner_style": "striped"     -- solid | striped | gradient
    }
    */
    
    priority INTEGER DEFAULT 0,              -- Higher priority wins when multiple themes overlap
    is_active BOOLEAN DEFAULT true,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_holiday_themes_active ON holiday_themes(is_active, priority DESC);

-- ============================================================
-- Part 1.1: Preset Holiday Data for US Holidays
-- ============================================================

INSERT INTO holiday_themes (id, name, date_rule, theme_config, priority) VALUES

-- New Year
('newyear', 'New Year', 
 '{"type": "fixed", "start": "12-31", "end": "01-02"}',
 '{
    "colors": {
        "primary": "#ffd700",
        "secondary": "#1a1a2e",
        "accent": "#ff6b35",
        "banner_bg": "linear-gradient(135deg, #1a1a2e, #16213e)",
        "banner_text": "#ffd700"
    },
    "badge": {"text": "🎆 Happy New Year!", "style": "glow"},
    "decorations": {"type": "fireworks", "density": "medium"},
    "banner_style": "gradient"
 }',
 100),

-- Valentine's Day
('valentine', 'Valentine''s Day',
 '{"type": "fixed", "start": "02-12", "end": "02-15"}',
 '{
    "colors": {
        "primary": "#ff69b4",
        "secondary": "#ff1493",
        "accent": "#dc143c",
        "banner_bg": "linear-gradient(135deg, #ff69b4, #ff1493)",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "💝 Valentine''s Day", "style": "pulse"},
    "decorations": {"type": "hearts", "density": "light"},
    "banner_style": "gradient"
 }',
 50),

-- St. Patrick's Day
('stpatrick', 'St. Patrick''s Day',
 '{"type": "fixed", "start": "03-15", "end": "03-18"}',
 '{
    "colors": {
        "primary": "#228b22",
        "secondary": "#32cd32",
        "accent": "#ffd700",
        "banner_bg": "#228b22",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "☘️ St. Patrick''s Day", "style": "default"},
    "decorations": {"type": "none"},
    "banner_style": "solid"
 }',
 40),

-- Independence Day (July 4th)
('july4th', 'Independence Day',
 '{"type": "fixed", "start": "07-02", "end": "07-05"}',
 '{
    "colors": {
        "primary": "#b22234",
        "secondary": "#3c3b6e",
        "accent": "#ffffff",
        "banner_bg": "#b22234",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "🇺🇸 Happy 4th of July!", "style": "default"},
    "decorations": {"type": "fireworks", "density": "heavy"},
    "banner_style": "striped"
 }',
 60),

-- Halloween
('halloween', 'Halloween',
 '{"type": "fixed", "start": "10-28", "end": "11-01"}',
 '{
    "colors": {
        "primary": "#ff6600",
        "secondary": "#1a1a1a",
        "accent": "#9933ff",
        "banner_bg": "#1a1a1a",
        "banner_text": "#ff6600"
    },
    "badge": {"text": "🎃 Happy Halloween!", "style": "spooky"},
    "decorations": {"type": "confetti", "density": "light"},
    "banner_style": "solid"
 }',
 70),

-- Thanksgiving (Dynamic: 4th Thursday of November)
('thanksgiving', 'Thanksgiving',
 '{"type": "dynamic", "rule": "us_thanksgiving", "offset_start": -1, "offset_end": 1}',
 '{
    "colors": {
        "primary": "#cd853f",
        "secondary": "#8b4513",
        "accent": "#daa520",
        "banner_bg": "linear-gradient(135deg, #cd853f, #8b4513)",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "🦃 Happy Thanksgiving!", "style": "warm"},
    "decorations": {"type": "none"},
    "banner_style": "gradient"
 }',
 80),

-- Black Friday (Dynamic: Day after Thanksgiving)
('blackfriday', 'Black Friday',
 '{"type": "dynamic", "rule": "black_friday", "offset_start": 0, "offset_end": 3}',
 '{
    "colors": {
        "primary": "#000000",
        "secondary": "#1a1a1a",
        "accent": "#ff0000",
        "banner_bg": "#000000",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "🖤 BLACK FRIDAY DEALS!", "style": "flash"},
    "decorations": {"type": "none"},
    "banner_style": "solid"
 }',
 90),

-- Christmas
('christmas', 'Christmas',
 '{"type": "fixed", "start": "12-20", "end": "12-26"}',
 '{
    "colors": {
        "primary": "#c41e3a",
        "secondary": "#228b22",
        "accent": "#ffd700",
        "banner_bg": "#c41e3a",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "🎄 Merry Christmas!", "style": "festive"},
    "decorations": {"type": "snowflakes", "density": "medium"},
    "banner_style": "striped"
 }',
 95)

ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    date_rule = EXCLUDED.date_rule,
    theme_config = EXCLUDED.theme_config,
    priority = EXCLUDED.priority,
    updated_at = NOW();


-- ============================================================
-- Part 2: Marketing Campaigns System
-- ============================================================

CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Basic info
    name TEXT NOT NULL,
    description TEXT,
    
    -- Campaign type: credits_gift | credits_discount | credits_bonus
    type TEXT NOT NULL,
    
    -- Type-specific configuration
    -- credits_gift: { "amount": 100 }
    -- credits_discount: { "discount_percent": 20 }
    -- credits_bonus: { "buy_amount": 500, "bonus_amount": 100 }
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Target audience
    -- all | subscription | users | new_users | inactive_users
    target_type TEXT NOT NULL DEFAULT 'all',
    target_config JSONB DEFAULT '{}'::jsonb,
    /*
    subscription: { "tiers": ["starter", "pro"] }
    users: { "user_ids": ["user_1", "user_2"] }
    new_users: { "days_since_signup": 7 }
    inactive_users: { "days_inactive": 30 }
    */
    
    -- Notification channels (can be multiple)
    -- personal_message | modal | toast | banner
    notification_channels TEXT[] DEFAULT ARRAY['banner'],
    
    -- Notification content configuration
    notification_config JSONB DEFAULT '{}'::jsonb,
    /*
    {
        "title": "🎁 Special Offer!",
        "message": "Get 100 free credits today!",
        "cta_text": "Claim Now",
        "cta_url": "/pricing",
        "banner_style": "marquee",
        "modal_size": "md",
        "show_once": true,
        "dismiss_cooldown": 24
    }
    */
    
    -- Time settings
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ NOT NULL,
    timezone TEXT DEFAULT 'America/New_York',
    
    -- Usage limits
    usage_limit INTEGER,              -- Total claims limit (NULL = unlimited)
    usage_per_user INTEGER DEFAULT 1, -- Per-user limit
    usage_count INTEGER DEFAULT 0,    -- Current claim count
    
    -- Status management
    -- draft | scheduled | active | paused | ended
    status TEXT DEFAULT 'draft',
    is_active BOOLEAN DEFAULT true,
    
    -- Audit
    created_by TEXT REFERENCES profiles(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status, is_active);
CREATE INDEX IF NOT EXISTS idx_campaigns_dates ON campaigns(start_at, end_at);
CREATE INDEX IF NOT EXISTS idx_campaigns_type ON campaigns(type);


-- ============================================================
-- Part 2.1: Campaign Claims (User Claim Records)
-- ============================================================

CREATE TABLE IF NOT EXISTS campaign_claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    user_id TEXT REFERENCES profiles(id),
    
    -- Claim details
    credits_received INTEGER,         -- Actual credits received
    original_amount INTEGER,          -- Original price (for discounts)
    discount_amount INTEGER,          -- Discount amount
    
    claimed_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Prevent duplicate claims
    UNIQUE(campaign_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_claims_user ON campaign_claims(user_id);
CREATE INDEX IF NOT EXISTS idx_claims_campaign ON campaign_claims(campaign_id);


-- ============================================================
-- Part 2.2: Campaign Dismissals (Notification Close Records)
-- ============================================================

CREATE TABLE IF NOT EXISTS campaign_dismissals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    user_id TEXT REFERENCES profiles(id),
    channel TEXT NOT NULL,            -- modal | toast | banner
    dismissed_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- One dismissal per channel per user per campaign
    UNIQUE(campaign_id, user_id, channel)
);

CREATE INDEX IF NOT EXISTS idx_dismissals_user ON campaign_dismissals(user_id, campaign_id);


-- ============================================================
-- Part 3: RLS Policies
-- ============================================================

-- Holiday themes: Public read access
ALTER TABLE holiday_themes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Holiday themes are publicly readable"
    ON holiday_themes FOR SELECT
    USING (true);

CREATE POLICY "Only admins can modify holiday themes"
    ON holiday_themes FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE id = auth.uid()::text 
            AND role = 'admin'
        )
    );

-- Campaigns: Public read for active campaigns
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Active campaigns are publicly readable"
    ON campaigns FOR SELECT
    USING (status = 'active' AND is_active = true);

CREATE POLICY "Only admins can modify campaigns"
    ON campaigns FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE id = auth.uid()::text 
            AND role = 'admin'
        )
    );

-- Campaign claims: Users can read their own claims
ALTER TABLE campaign_claims ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read their own claims"
    ON campaign_claims FOR SELECT
    USING (user_id = auth.uid()::text);

CREATE POLICY "Users can create their own claims"
    ON campaign_claims FOR INSERT
    WITH CHECK (user_id = auth.uid()::text);

-- Campaign dismissals: Users can manage their own dismissals
ALTER TABLE campaign_dismissals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own dismissals"
    ON campaign_dismissals FOR ALL
    USING (user_id = auth.uid()::text);


-- ============================================================
-- Part 4: Helper Functions
-- ============================================================

-- Function to get current active holiday theme
CREATE OR REPLACE FUNCTION get_current_holiday_theme()
RETURNS SETOF holiday_themes
LANGUAGE plpgsql
AS $$
DECLARE
    today DATE := CURRENT_DATE;
    theme_record holiday_themes%ROWTYPE;
BEGIN
    FOR theme_record IN 
        SELECT * FROM holiday_themes 
        WHERE is_active = true 
        ORDER BY priority DESC
    LOOP
        -- Check if theme is active for today
        IF is_holiday_theme_active(theme_record.date_rule, today) THEN
            RETURN NEXT theme_record;
            RETURN;
        END IF;
    END LOOP;
    RETURN;
END;
$$;

-- Function to check if a holiday theme is active for a given date
CREATE OR REPLACE FUNCTION is_holiday_theme_active(date_rule JSONB, check_date DATE)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    rule_type TEXT;
    start_md TEXT;
    end_md TEXT;
    start_date DATE;
    end_date DATE;
    base_date DATE;
    offset_start INT;
    offset_end INT;
BEGIN
    rule_type := date_rule->>'type';
    
    IF rule_type = 'fixed' THEN
        -- Parse MM-DD format
        start_md := date_rule->>'start';
        end_md := date_rule->>'end';
        
        -- Create dates for current year
        start_date := make_date(
            EXTRACT(YEAR FROM check_date)::INT,
            SPLIT_PART(start_md, '-', 1)::INT,
            SPLIT_PART(start_md, '-', 2)::INT
        );
        end_date := make_date(
            EXTRACT(YEAR FROM check_date)::INT,
            SPLIT_PART(end_md, '-', 1)::INT,
            SPLIT_PART(end_md, '-', 2)::INT
        );
        
        -- Handle year wrap (e.g., Dec 31 - Jan 2)
        IF start_date > end_date THEN
            -- Either check_date >= start_date (this year) OR check_date <= end_date (next year context)
            RETURN check_date >= start_date OR check_date <= end_date;
        END IF;
        
        RETURN check_date >= start_date AND check_date <= end_date;
        
    ELSIF rule_type = 'dynamic' THEN
        -- Calculate base date for dynamic rules
        base_date := calculate_dynamic_holiday(
            date_rule->>'rule',
            EXTRACT(YEAR FROM check_date)::INT
        );
        
        IF base_date IS NULL THEN
            RETURN FALSE;
        END IF;
        
        offset_start := COALESCE((date_rule->>'offset_start')::INT, 0);
        offset_end := COALESCE((date_rule->>'offset_end')::INT, 0);
        
        start_date := base_date + offset_start;
        end_date := base_date + offset_end;
        
        RETURN check_date >= start_date AND check_date <= end_date;
    END IF;
    
    RETURN FALSE;
END;
$$;

-- Function to calculate dynamic US holidays
CREATE OR REPLACE FUNCTION calculate_dynamic_holiday(rule TEXT, year INT)
RETURNS DATE
LANGUAGE plpgsql
AS $$
DECLARE
    nov_first DATE;
    first_thursday DATE;
    thanksgiving DATE;
BEGIN
    IF rule = 'us_thanksgiving' THEN
        -- 4th Thursday of November
        nov_first := make_date(year, 11, 1);
        -- Find first Thursday (weekday 4)
        first_thursday := nov_first + ((4 - EXTRACT(DOW FROM nov_first)::INT + 7) % 7);
        -- Add 3 weeks to get 4th Thursday
        thanksgiving := first_thursday + INTERVAL '21 days';
        RETURN thanksgiving;
        
    ELSIF rule = 'black_friday' THEN
        -- Day after Thanksgiving
        thanksgiving := calculate_dynamic_holiday('us_thanksgiving', year);
        RETURN thanksgiving + INTERVAL '1 day';
        
    ELSIF rule = 'easter' THEN
        -- Easter calculation (Computus algorithm) - simplified
        -- For now, return NULL; can be implemented if needed
        RETURN NULL;
    END IF;
    
    RETURN NULL;
END;
$$;


-- ============================================================
-- Done!
-- ============================================================
