-- ============================================
-- Content Reports Table
-- ============================================
-- Users can report marketplace items for copyright violations, 
-- inappropriate content, or other issues

CREATE TABLE IF NOT EXISTS content_reports (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    reporter_id TEXT NOT NULL REFERENCES profiles(id),
    listing_id UUID NOT NULL REFERENCES marketplace_listings(id),
    reason TEXT NOT NULL,           -- User-provided reason for report
    status TEXT DEFAULT 'pending',  -- 'pending' | 'reviewed' | 'resolved' | 'dismissed'
    admin_response TEXT,            -- Admin's response to the reporter
    reviewed_by TEXT REFERENCES profiles(id),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_reports_status ON content_reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_listing_id ON content_reports(listing_id);
CREATE INDEX IF NOT EXISTS idx_reports_reporter_id ON content_reports(reporter_id);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON content_reports(created_at DESC);

-- Prevent duplicate reports from same user for same listing
CREATE UNIQUE INDEX IF NOT EXISTS idx_reports_unique_user_listing 
    ON content_reports(reporter_id, listing_id) 
    WHERE status IN ('pending', 'reviewed');

-- RLS Policies
ALTER TABLE content_reports ENABLE ROW LEVEL SECURITY;

-- Users can view their own reports
CREATE POLICY "Users can view own reports" ON content_reports
    FOR SELECT
    USING (reporter_id = auth.uid()::text);

-- Users can create reports
CREATE POLICY "Users can create reports" ON content_reports
    FOR INSERT
    WITH CHECK (reporter_id = auth.uid()::text);

-- Admin can view all reports
CREATE POLICY "Admin can view all reports" ON content_reports
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE profiles.id = auth.uid()::text 
            AND profiles.role = 'admin'
        )
    );

-- Admin can update reports
CREATE POLICY "Admin can update reports" ON content_reports
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE profiles.id = auth.uid()::text 
            AND profiles.role = 'admin'
        )
    );

-- Update updated_at trigger
CREATE OR REPLACE FUNCTION update_reports_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_reports_updated_at
    BEFORE UPDATE ON content_reports
    FOR EACH ROW
    EXECUTE FUNCTION update_reports_updated_at();
