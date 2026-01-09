-- =====================================================
-- Migration: v3.17_system_resources_enhancement.sql
-- Description: Enhance system_resources table for admin management
-- Date: 2026-01-03
-- =====================================================

-- =====================================================
-- Step 1: 添加新字段
-- =====================================================

ALTER TABLE system_resources 
  ADD COLUMN IF NOT EXISTS name TEXT,
  ADD COLUMN IF NOT EXISTS description TEXT,
  ADD COLUMN IF NOT EXISTS thumbnail_url TEXT,
  ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true,
  ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS file_size INTEGER,
  ADD COLUMN IF NOT EXISTS file_type TEXT,
  ADD COLUMN IF NOT EXISTS dimensions JSONB,  -- {"width": 800, "height": 600}
  ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS created_by TEXT,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS updated_by TEXT;

-- =====================================================
-- Step 2: 创建索引（提升查询性能）
-- =====================================================

-- 类型索引
CREATE INDEX IF NOT EXISTS idx_system_resources_type 
  ON system_resources(type);

-- 分类索引
CREATE INDEX IF NOT EXISTS idx_system_resources_category 
  ON system_resources(category);

-- 标签索引（GIN 支持数组包含查询）
CREATE INDEX IF NOT EXISTS idx_system_resources_tags 
  ON system_resources USING GIN(tags);

-- 活跃素材索引（常用查询优化）
CREATE INDEX IF NOT EXISTS idx_system_resources_active_type 
  ON system_resources(type, is_active) 
  WHERE is_active = true;

-- 排序索引
CREATE INDEX IF NOT EXISTS idx_system_resources_sort 
  ON system_resources(type, sort_order, created_at DESC);

-- =====================================================
-- Step 3: 更新时间触发器
-- =====================================================

CREATE OR REPLACE FUNCTION update_system_resources_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_system_resources_updated_at ON system_resources;
CREATE TRIGGER trigger_system_resources_updated_at
  BEFORE UPDATE ON system_resources
  FOR EACH ROW
  EXECUTE FUNCTION update_system_resources_timestamp();

-- =====================================================
-- Step 4: RLS 策略（安全控制）
-- =====================================================

-- 删除旧策略
DROP POLICY IF EXISTS "Public can view system resources" ON system_resources;
DROP POLICY IF EXISTS "Admin can manage system resources" ON system_resources;

-- 公开读取（只读取启用的素材）
CREATE POLICY "Public can view active system resources" 
  ON system_resources FOR SELECT
  USING (is_active = true);

-- Admin 完全控制（包括查看未启用的）
CREATE POLICY "Admin full access to system resources" 
  ON system_resources FOR ALL
  USING (is_admin())
  WITH CHECK (is_admin());

-- =====================================================
-- Step 5: 添加审计日志支持
-- =====================================================

-- 素材变更审计表
CREATE TABLE IF NOT EXISTS system_resource_audit_logs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  resource_id UUID REFERENCES system_resources(id) ON DELETE SET NULL,
  action TEXT NOT NULL,  -- 'create', 'update', 'delete', 'activate', 'deactivate'
  old_data JSONB,
  new_data JSONB,
  changed_by TEXT NOT NULL,
  changed_at TIMESTAMPTZ DEFAULT NOW(),
  ip_address TEXT,
  user_agent TEXT
);

-- 审计日志索引
CREATE INDEX IF NOT EXISTS idx_resource_audit_resource_id 
  ON system_resource_audit_logs(resource_id);
CREATE INDEX IF NOT EXISTS idx_resource_audit_changed_at 
  ON system_resource_audit_logs(changed_at DESC);

-- 审计日志 RLS
ALTER TABLE system_resource_audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Admin can view resource audit logs" 
  ON system_resource_audit_logs FOR SELECT
  USING (is_admin());

CREATE POLICY "Service can insert audit logs" 
  ON system_resource_audit_logs FOR INSERT
  WITH CHECK (true);  -- 由后端服务控制

-- =====================================================
-- Step 6: 验证
-- =====================================================

DO $$
BEGIN
  RAISE NOTICE '✅ system_resources table enhanced successfully';
  RAISE NOTICE '  - Added: name, description, thumbnail_url, tags, is_active, sort_order';
  RAISE NOTICE '  - Added: file_size, file_type, dimensions, metadata';
  RAISE NOTICE '  - Added: created_by, updated_at, updated_by';
  RAISE NOTICE '  - Created indexes for performance';
  RAISE NOTICE '  - Updated RLS policies for security';
  RAISE NOTICE '  - Created audit log table';
END $$;
