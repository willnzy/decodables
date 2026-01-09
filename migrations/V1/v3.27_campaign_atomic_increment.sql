-- ==========================================
-- v3.27: Campaign Atomic Usage Increment
-- ==========================================
-- Adds atomic increment function for campaign usage_count
-- to prevent race conditions during concurrent claims
-- ==========================================

-- Create atomic increment function for campaign usage
CREATE OR REPLACE FUNCTION increment_campaign_usage(p_campaign_id UUID)
RETURNS TABLE(
    success BOOLEAN,
    new_usage_count INTEGER,
    usage_limit INTEGER
) AS $$
DECLARE
    v_result RECORD;
BEGIN
    -- Atomic increment with optional limit check
    UPDATE campaigns
    SET usage_count = usage_count + 1,
        updated_at = NOW()
    WHERE id = p_campaign_id
      AND is_active = true
      AND (usage_limit IS NULL OR usage_count < usage_limit)
    RETURNING
        true AS success,
        campaigns.usage_count AS new_usage_count,
        campaigns.usage_limit
    INTO v_result;

    IF v_result IS NULL THEN
        -- Either campaign doesn't exist, is inactive, or limit reached
        RETURN QUERY SELECT false, NULL::INTEGER, NULL::INTEGER;
    ELSE
        RETURN QUERY SELECT v_result.success, v_result.new_usage_count, v_result.usage_limit;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION increment_campaign_usage(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION increment_campaign_usage(UUID) TO service_role;

-- Add comment
COMMENT ON FUNCTION increment_campaign_usage IS 'Atomically increment campaign usage_count with optional limit check. Returns success=false if limit reached or campaign inactive.';
