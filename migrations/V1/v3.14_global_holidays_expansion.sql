-- ============================================================
-- Migration: v3.14 - Global Holidays & Commemorative Days Expansion
-- Description: Add more global holidays and positive historical figure commemorations
-- ============================================================

-- Insert additional global holidays
INSERT INTO holiday_themes (id, name, date_rule, theme_config, priority) VALUES

-- ============================================================
-- GLOBAL CELEBRATIONS
-- ============================================================

-- New Year's Day (已存在，跳过)
-- ('newyear', 'New Year', ...)

-- Chinese New Year / Lunar New Year (Dynamic - varies each year)
-- Note: Date calculation is complex, typically late Jan - mid Feb
('lunar_newyear', 'Lunar New Year',
 '{"type": "fixed", "start": "01-20", "end": "02-15", "note": "Approximate range for Lunar New Year"}',
 '{
    "colors": {
        "primary": "#de2910",
        "secondary": "#ffde00",
        "accent": "#c41e3a",
        "banner_bg": "linear-gradient(135deg, #de2910, #c41e3a)",
        "banner_text": "#ffde00"
    },
    "badge": {"text": "🧧 Happy Lunar New Year!", "style": "festive"},
    "decorations": {"type": "confetti", "density": "medium"},
    "banner_style": "gradient"
 }',
 75),

-- International Women's Day (March 8)
('womens_day', 'International Women''s Day',
 '{"type": "fixed", "start": "03-07", "end": "03-09"}',
 '{
    "colors": {
        "primary": "#9b59b6",
        "secondary": "#8e44ad",
        "accent": "#f39c12",
        "banner_bg": "linear-gradient(135deg, #9b59b6, #e91e63)",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "💜 International Women''s Day", "style": "default"},
    "decorations": {"type": "hearts", "density": "light"},
    "banner_style": "gradient"
 }',
 45),

-- Earth Day (April 22)
('earth_day', 'Earth Day',
 '{"type": "fixed", "start": "04-21", "end": "04-23"}',
 '{
    "colors": {
        "primary": "#2ecc71",
        "secondary": "#27ae60",
        "accent": "#3498db",
        "banner_bg": "linear-gradient(135deg, #2ecc71, #3498db)",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "🌍 Earth Day - Protect Our Planet!", "style": "default"},
    "decorations": {"type": "none"},
    "banner_style": "gradient"
 }',
 50),

-- International Workers' Day / Labor Day (May 1)
('labor_day_intl', 'International Workers'' Day',
 '{"type": "fixed", "start": "04-30", "end": "05-02"}',
 '{
    "colors": {
        "primary": "#e74c3c",
        "secondary": "#c0392b",
        "accent": "#f39c12",
        "banner_bg": "#e74c3c",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "✊ International Workers'' Day", "style": "default"},
    "decorations": {"type": "none"},
    "banner_style": "solid"
 }',
 40),

-- Mother's Day (Dynamic: 2nd Sunday of May)
('mothers_day', 'Mother''s Day',
 '{"type": "dynamic", "rule": "mothers_day", "offset_start": -1, "offset_end": 0}',
 '{
    "colors": {
        "primary": "#ff69b4",
        "secondary": "#db7093",
        "accent": "#ff1493",
        "banner_bg": "linear-gradient(135deg, #ff69b4, #ff1493)",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "💐 Happy Mother''s Day!", "style": "pulse"},
    "decorations": {"type": "hearts", "density": "light"},
    "banner_style": "gradient"
 }',
 70),

-- World Environment Day (June 5)
('environment_day', 'World Environment Day',
 '{"type": "fixed", "start": "06-04", "end": "06-06"}',
 '{
    "colors": {
        "primary": "#16a085",
        "secondary": "#1abc9c",
        "accent": "#2ecc71",
        "banner_bg": "linear-gradient(135deg, #16a085, #2ecc71)",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "🌱 World Environment Day", "style": "default"},
    "decorations": {"type": "none"},
    "banner_style": "gradient"
 }',
 35),

-- Father's Day (Dynamic: 3rd Sunday of June)
('fathers_day', 'Father''s Day',
 '{"type": "dynamic", "rule": "fathers_day", "offset_start": -1, "offset_end": 0}',
 '{
    "colors": {
        "primary": "#2980b9",
        "secondary": "#3498db",
        "accent": "#f39c12",
        "banner_bg": "linear-gradient(135deg, #2980b9, #3498db)",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "👔 Happy Father''s Day!", "style": "default"},
    "decorations": {"type": "none"},
    "banner_style": "gradient"
 }',
 70),

-- International Friendship Day (July 30)
('friendship_day', 'International Friendship Day',
 '{"type": "fixed", "start": "07-29", "end": "07-31"}',
 '{
    "colors": {
        "primary": "#f1c40f",
        "secondary": "#f39c12",
        "accent": "#e67e22",
        "banner_bg": "linear-gradient(135deg, #f1c40f, #e67e22)",
        "banner_text": "#2c3e50"
    },
    "badge": {"text": "🤝 International Friendship Day", "style": "default"},
    "decorations": {"type": "confetti", "density": "light"},
    "banner_style": "gradient"
 }',
 35),

-- International Youth Day (August 12)
('youth_day', 'International Youth Day',
 '{"type": "fixed", "start": "08-11", "end": "08-13"}',
 '{
    "colors": {
        "primary": "#9b59b6",
        "secondary": "#8e44ad",
        "accent": "#3498db",
        "banner_bg": "linear-gradient(135deg, #9b59b6, #3498db)",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "🌟 International Youth Day", "style": "default"},
    "decorations": {"type": "none"},
    "banner_style": "gradient"
 }',
 30),

-- World Humanitarian Day (August 19)
('humanitarian_day', 'World Humanitarian Day',
 '{"type": "fixed", "start": "08-18", "end": "08-20"}',
 '{
    "colors": {
        "primary": "#e74c3c",
        "secondary": "#ffffff",
        "accent": "#3498db",
        "banner_bg": "linear-gradient(135deg, #e74c3c, #c0392b)",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "❤️ World Humanitarian Day", "style": "default"},
    "decorations": {"type": "none"},
    "banner_style": "gradient"
 }',
 40),

-- International Peace Day (September 21)
('peace_day', 'International Day of Peace',
 '{"type": "fixed", "start": "09-20", "end": "09-22"}',
 '{
    "colors": {
        "primary": "#3498db",
        "secondary": "#ffffff",
        "accent": "#2ecc71",
        "banner_bg": "linear-gradient(135deg, #3498db, #2ecc71)",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "☮️ International Day of Peace", "style": "default"},
    "decorations": {"type": "none"},
    "banner_style": "gradient"
 }',
 45),

-- World Teachers' Day (October 5)
('teachers_day', 'World Teachers'' Day',
 '{"type": "fixed", "start": "10-04", "end": "10-06"}',
 '{
    "colors": {
        "primary": "#27ae60",
        "secondary": "#2ecc71",
        "accent": "#f1c40f",
        "banner_bg": "linear-gradient(135deg, #27ae60, #2ecc71)",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "📚 World Teachers'' Day", "style": "default"},
    "decorations": {"type": "none"},
    "banner_style": "gradient"
 }',
 40),

-- Diwali / Festival of Lights (Dynamic - varies, typically Oct/Nov)
('diwali', 'Diwali - Festival of Lights',
 '{"type": "fixed", "start": "10-15", "end": "11-15", "note": "Approximate Diwali period"}',
 '{
    "colors": {
        "primary": "#ff9933",
        "secondary": "#ffd700",
        "accent": "#c41e3a",
        "banner_bg": "linear-gradient(135deg, #ff9933, #ffd700)",
        "banner_text": "#2c3e50"
    },
    "badge": {"text": "🪔 Happy Diwali!", "style": "festive"},
    "decorations": {"type": "fireworks", "density": "light"},
    "banner_style": "gradient"
 }',
 55),

-- ============================================================
-- COMMEMORATIVE DAYS - GREAT MINDS & HUMANITARIANS
-- ============================================================

-- Pi Day / Einstein's Birthday (March 14)
('pi_day', 'Pi Day & Einstein''s Birthday',
 '{"type": "fixed", "start": "03-13", "end": "03-15"}',
 '{
    "colors": {
        "primary": "#3498db",
        "secondary": "#2980b9",
        "accent": "#9b59b6",
        "banner_bg": "linear-gradient(135deg, #3498db, #9b59b6)",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "🔬 Pi Day & Einstein''s Birthday", "style": "default"},
    "decorations": {"type": "none"},
    "banner_style": "gradient"
 }',
 35),

-- Leonardo da Vinci's Birthday (April 15)
('davinci_day', 'Leonardo da Vinci Day',
 '{"type": "fixed", "start": "04-14", "end": "04-16"}',
 '{
    "colors": {
        "primary": "#8b4513",
        "secondary": "#d2691e",
        "accent": "#daa520",
        "banner_bg": "linear-gradient(135deg, #8b4513, #d2691e)",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "🎨 Leonardo da Vinci Day - Art & Science", "style": "default"},
    "decorations": {"type": "none"},
    "banner_style": "gradient"
 }',
 30),

-- World Book & Shakespeare Day (April 23)
('book_day', 'World Book Day',
 '{"type": "fixed", "start": "04-22", "end": "04-24"}',
 '{
    "colors": {
        "primary": "#8e44ad",
        "secondary": "#9b59b6",
        "accent": "#f39c12",
        "banner_bg": "linear-gradient(135deg, #8e44ad, #3498db)",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "📖 World Book Day", "style": "default"},
    "decorations": {"type": "none"},
    "banner_style": "gradient"
 }',
 35),

-- Florence Nightingale Day / International Nurses Day (May 12)
('nurses_day', 'International Nurses Day',
 '{"type": "fixed", "start": "05-11", "end": "05-13"}',
 '{
    "colors": {
        "primary": "#e91e63",
        "secondary": "#ffffff",
        "accent": "#3f51b5",
        "banner_bg": "linear-gradient(135deg, #e91e63, #9c27b0)",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "💉 International Nurses Day", "style": "default"},
    "decorations": {"type": "none"},
    "banner_style": "gradient"
 }',
 40),

-- Nelson Mandela International Day (July 18)
('mandela_day', 'Nelson Mandela International Day',
 '{"type": "fixed", "start": "07-17", "end": "07-19"}',
 '{
    "colors": {
        "primary": "#2ecc71",
        "secondary": "#f1c40f",
        "accent": "#e74c3c",
        "banner_bg": "linear-gradient(135deg, #2ecc71, #27ae60)",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "✊ Mandela Day - 67 Minutes of Service", "style": "default"},
    "decorations": {"type": "none"},
    "banner_style": "gradient"
 }',
 45),

-- International Charity Day / Mother Teresa Day (September 5)
('charity_day', 'International Day of Charity',
 '{"type": "fixed", "start": "09-04", "end": "09-06"}',
 '{
    "colors": {
        "primary": "#3498db",
        "secondary": "#ffffff",
        "accent": "#e74c3c",
        "banner_bg": "linear-gradient(135deg, #3498db, #2980b9)",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "💙 International Day of Charity", "style": "default"},
    "decorations": {"type": "none"},
    "banner_style": "gradient"
 }',
 40),

-- International Day of Non-Violence / Gandhi's Birthday (October 2)
('gandhi_day', 'International Day of Non-Violence',
 '{"type": "fixed", "start": "10-01", "end": "10-03"}',
 '{
    "colors": {
        "primary": "#ff9933",
        "secondary": "#ffffff",
        "accent": "#138808",
        "banner_bg": "linear-gradient(135deg, #ff9933, #ffffff, #138808)",
        "banner_text": "#2c3e50"
    },
    "badge": {"text": "☮️ International Day of Non-Violence", "style": "default"},
    "decorations": {"type": "none"},
    "banner_style": "gradient"
 }',
 45),

-- Marie Curie's Birthday (November 7)
('curie_day', 'Marie Curie Day - Science & Discovery',
 '{"type": "fixed", "start": "11-06", "end": "11-08"}',
 '{
    "colors": {
        "primary": "#9b59b6",
        "secondary": "#8e44ad",
        "accent": "#f1c40f",
        "banner_bg": "linear-gradient(135deg, #9b59b6, #8e44ad)",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "⚗️ Marie Curie Day - Science & Discovery", "style": "default"},
    "decorations": {"type": "none"},
    "banner_style": "gradient"
 }',
 35),

-- Human Rights Day (December 10)
('human_rights_day', 'Human Rights Day',
 '{"type": "fixed", "start": "12-09", "end": "12-11"}',
 '{
    "colors": {
        "primary": "#3498db",
        "secondary": "#2980b9",
        "accent": "#f1c40f",
        "banner_bg": "linear-gradient(135deg, #3498db, #2980b9)",
        "banner_text": "#ffffff"
    },
    "badge": {"text": "🌐 Human Rights Day", "style": "default"},
    "decorations": {"type": "none"},
    "banner_style": "gradient"
 }',
 50)

ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    date_rule = EXCLUDED.date_rule,
    theme_config = EXCLUDED.theme_config,
    priority = EXCLUDED.priority,
    updated_at = NOW();


-- ============================================================
-- Add helper function for Mother's Day (2nd Sunday of May)
-- ============================================================
CREATE OR REPLACE FUNCTION calculate_mothers_day(year_val INTEGER)
RETURNS DATE AS $$
DECLARE
    first_day DATE;
    first_sunday DATE;
BEGIN
    first_day := make_date(year_val, 5, 1);
    -- Find first Sunday (day of week 0)
    first_sunday := first_day + ((7 - EXTRACT(DOW FROM first_day)::INTEGER) % 7);
    -- If first_day is Sunday, first_sunday is first_day
    IF EXTRACT(DOW FROM first_day) = 0 THEN
        first_sunday := first_day;
    END IF;
    -- 2nd Sunday is 7 days after first Sunday
    RETURN first_sunday + 7;
END;
$$ LANGUAGE plpgsql IMMUTABLE;


-- ============================================================
-- Add helper function for Father's Day (3rd Sunday of June)
-- ============================================================
CREATE OR REPLACE FUNCTION calculate_fathers_day(year_val INTEGER)
RETURNS DATE AS $$
DECLARE
    first_day DATE;
    first_sunday DATE;
BEGIN
    first_day := make_date(year_val, 6, 1);
    -- Find first Sunday
    first_sunday := first_day + ((7 - EXTRACT(DOW FROM first_day)::INTEGER) % 7);
    IF EXTRACT(DOW FROM first_day) = 0 THEN
        first_sunday := first_day;
    END IF;
    -- 3rd Sunday is 14 days after first Sunday
    RETURN first_sunday + 14;
END;
$$ LANGUAGE plpgsql IMMUTABLE;


-- ============================================================
-- Update calculate_dynamic_date function to support new holidays
-- ============================================================
CREATE OR REPLACE FUNCTION calculate_dynamic_date(rule_name TEXT, year_val INTEGER)
RETURNS DATE AS $$
BEGIN
    CASE rule_name
        WHEN 'us_thanksgiving' THEN
            RETURN calculate_us_thanksgiving(year_val);
        WHEN 'black_friday' THEN
            RETURN calculate_us_thanksgiving(year_val) + 1;
        WHEN 'mothers_day' THEN
            RETURN calculate_mothers_day(year_val);
        WHEN 'fathers_day' THEN
            RETURN calculate_fathers_day(year_val);
        ELSE
            RETURN NULL;
    END CASE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;


-- ============================================================
-- Summary Comment
-- ============================================================
COMMENT ON TABLE holiday_themes IS 
'Global holidays and commemorative days including:

GLOBAL CELEBRATIONS:
- New Year, Lunar New Year, Valentine''s Day, St. Patrick''s Day
- International Women''s Day, Earth Day, International Workers'' Day
- Mother''s Day, World Environment Day, Father''s Day
- Friendship Day, Youth Day, Humanitarian Day, Peace Day
- Teachers'' Day, Halloween, Diwali, Thanksgiving, Black Friday, Christmas

GREAT MINDS & HUMANITARIANS:
- Pi Day/Einstein Day (Mar 14), Da Vinci Day (Apr 15)
- World Book Day (Apr 23), Nurses Day/Nightingale Day (May 12)
- Mandela Day (Jul 18), Charity Day/Teresa Day (Sep 5)
- Gandhi Day/Non-Violence Day (Oct 2), Curie Day (Nov 7)
- Human Rights Day (Dec 10), MLK Day (Jan, 3rd Monday)

Priority levels: 30-95 (higher = more important/takes precedence)';
