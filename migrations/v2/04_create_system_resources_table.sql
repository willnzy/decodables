-- ============================================================================
-- Migration: Create system_resources table
-- Version: v3.04
-- Date: 2026-01-11
-- Description: 创建 system_resources 表用于管理系统资源(stickers, templates等)
-- Issue: P0-1 - system_resources 表完全缺失
-- ============================================================================

CREATE TABLE system_resources (
    -- ========== 主键 ==========
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- ========== 资源标识 ==========
    resource_type TEXT NOT NULL CHECK (resource_type IN (
        'text', 'image', 'shape', 'table', 'sticker',
        'icon', 'frame', 'background', 'font', 'pattern'
    )),

    -- ========== 分类关联 ==========
    category_id UUID REFERENCES asset_categories(id) ON DELETE SET NULL,
    category TEXT,  -- 冗余字段 (ResourceCategory 枚举值)

    -- ========== 资源内容 ==========
    url TEXT NOT NULL,
    thumbnail_url TEXT,

    -- ========== 元数据 ==========
    name TEXT,
    description TEXT,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    metadata JSONB DEFAULT '{}',

    -- ========== 文件信息 ==========
    file_size INTEGER,  -- bytes
    width INTEGER,
    height INTEGER,
    format TEXT,  -- png, svg, jpg

    -- ========== 访问控制 ==========
    allowed_tiers TEXT[] DEFAULT ARRAY['t1']::TEXT[],
    min_tier TEXT DEFAULT 't1' CHECK (min_tier IN ('t1', 't2', 't3')),

    -- ========== 显示控制 ==========
    is_active BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0,

    -- ========== 时间戳 ==========
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    updated_by TEXT,

    -- ========== Soft Delete ==========
    deleted_at TIMESTAMPTZ,
    recovery_expires_at TIMESTAMPTZ,

    CONSTRAINT chk_system_resources_recovery_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

-- ========== 索引优化 ==========
CREATE INDEX idx_sr_type ON system_resources(resource_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_sr_category ON system_resources(category_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_sr_active_type ON system_resources(is_active, resource_type) WHERE deleted_at IS NULL AND is_active = true;
CREATE INDEX idx_sr_tier ON system_resources(min_tier) WHERE deleted_at IS NULL;
CREATE INDEX idx_sr_tags ON system_resources USING GIN(tags) WHERE deleted_at IS NULL;
CREATE INDEX idx_sr_created ON system_resources(created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_sr_featured ON system_resources(is_featured, display_order) WHERE deleted_at IS NULL AND is_featured = true;

-- ========== 触发器 ==========
CREATE TRIGGER update_system_resources_updated_at
    BEFORE UPDATE ON system_resources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ========== 初始数据 (10个示例资源) ==========
INSERT INTO system_resources (
    resource_type, category, url, name, tags, min_tier, allowed_tiers, is_active, is_featured, display_order, created_by
) VALUES
    ('sticker', 'animals', 'https://storage.example.com/stickers/cat-01.png', 'Cute Cat', ARRAY['cat', 'animal', 'cute'], 't1', ARRAY['t1', 't2', 't3'], true, true, 1, 'system'),
    ('sticker', 'animals', 'https://storage.example.com/stickers/dog-01.png', 'Happy Dog', ARRAY['dog', 'animal', 'happy'], 't1', ARRAY['t1', 't2', 't3'], true, true, 2, 'system'),
    ('sticker', 'nature', 'https://storage.example.com/stickers/tree-01.png', 'Green Tree', ARRAY['tree', 'nature', 'green'], 't1', ARRAY['t1', 't2', 't3'], true, false, 3, 'system'),
    ('sticker', 'people', 'https://storage.example.com/stickers/person-01.png', 'Smiling Person', ARRAY['people', 'happy', 'smile'], 't3', ARRAY['t3'], true, true, 4, 'system'),
    ('sticker', 'emotions', 'https://storage.example.com/stickers/heart-01.png', 'Red Heart', ARRAY['heart', 'love', 'emotion'], 't1', ARRAY['t1', 't2', 't3'], true, true, 5, 'system'),
    ('icon', 'basic', 'https://storage.example.com/icons/star-01.png', 'Star Icon', ARRAY['star', 'favorite', 'rating'], 't1', ARRAY['t1', 't2', 't3'], true, false, 6, 'system'),
    ('background', 'gradient', 'https://storage.example.com/backgrounds/gradient-01.png', 'Blue Gradient', ARRAY['gradient', 'blue', 'background'], 't2', ARRAY['t2', 't3'], true, false, 7, 'system'),
    ('frame', 'decorative', 'https://storage.example.com/frames/floral-01.png', 'Floral Frame', ARRAY['frame', 'floral', 'decorative'], 't2', ARRAY['t2', 't3'], true, true, 8, 'system'),
    ('pattern', 'geometric', 'https://storage.example.com/patterns/dots-01.png', 'Polka Dots', ARRAY['pattern', 'dots', 'geometric'], 't1', ARRAY['t1', 't2', 't3'], true, false, 9, 'system'),
    ('shape', 'basic', 'https://storage.example.com/shapes/circle-01.svg', 'Perfect Circle', ARRAY['shape', 'circle', 'basic'], 't1', ARRAY['t1', 't2', 't3'], true, false, 10, 'system');

-- ============================================================================
-- Verification Queries (for testing)
-- ============================================================================

-- 1. 验证表创建
-- SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'system_resources');

-- 2. 验证索引
-- SELECT indexname FROM pg_indexes WHERE tablename = 'system_resources';

-- 3. 验证初始数据
-- SELECT count(*) FROM system_resources;

-- 4. 验证资源类型分布
-- SELECT resource_type, count(*) FROM system_resources GROUP BY resource_type;

-- 5. 验证 Tier 访问控制
-- SELECT min_tier, count(*) FROM system_resources GROUP BY min_tier;
