-- =============================================================================
-- Migration v3.22: Atomic Transactions for Credits and Marketplace
-- 原子化事务 - Credits 扣款和 Marketplace 购买
-- =============================================================================
-- 
-- Purpose:
-- - Ensure credit operations are atomic (deduct/add with transaction logging)
-- - Ensure marketplace purchases are atomic (buyer deduct, seller add, record purchase)
-- - Add idempotency support to prevent duplicate processing
-- - Add webhook event deduplication table
--
-- Related Issues:
-- - P0-1: Credits 扣款事务化
-- - P0-2: Marketplace 购买事务化
-- - P1-3: Webhook 幂等性
--
-- =============================================================================

-- =============================================================================
-- 1. Webhook Events Table (for idempotency)
-- =============================================================================

CREATE TABLE IF NOT EXISTS webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    payload JSONB,
    result JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_webhook_events_event_id ON webhook_events(event_id);
CREATE INDEX IF NOT EXISTS idx_webhook_events_type ON webhook_events(event_type);
CREATE INDEX IF NOT EXISTS idx_webhook_events_created_at ON webhook_events(created_at);

COMMENT ON TABLE webhook_events IS 'Webhook event deduplication for idempotency';

-- =============================================================================
-- 2. Add idempotency_key to credit_transactions (if not exists)
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'credit_transactions' 
        AND column_name = 'idempotency_key'
    ) THEN
        ALTER TABLE credit_transactions ADD COLUMN idempotency_key TEXT;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_credit_transactions_idempotency 
            ON credit_transactions(idempotency_key) WHERE idempotency_key IS NOT NULL;
    END IF;
END $$;

-- =============================================================================
-- 3. Add idempotency_key to user_purchases (if not exists)
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_purchases' 
        AND column_name = 'idempotency_key'
    ) THEN
        ALTER TABLE user_purchases ADD COLUMN idempotency_key TEXT;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_user_purchases_idempotency 
            ON user_purchases(idempotency_key) WHERE idempotency_key IS NOT NULL;
    END IF;
END $$;

-- =============================================================================
-- 4. Atomic Credit Deduction Function
-- =============================================================================

CREATE OR REPLACE FUNCTION deduct_credits_atomic(
    p_user_id UUID,
    p_amount INT,
    p_tx_type TEXT,
    p_description TEXT DEFAULT NULL,
    p_timezone TEXT DEFAULT 'UTC',
    p_idempotency_key TEXT DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    v_monthly INT;
    v_permanent INT;
    v_deduct_monthly INT;
    v_deduct_permanent INT;
    v_new_monthly INT;
    v_new_permanent INT;
    v_bucket TEXT;
    v_existing_tx RECORD;
BEGIN
    -- 1. Idempotency check (if key provided)
    IF p_idempotency_key IS NOT NULL THEN
        SELECT * INTO v_existing_tx 
        FROM credit_transactions 
        WHERE idempotency_key = p_idempotency_key
        LIMIT 1;
        
        IF FOUND THEN
            RETURN jsonb_build_object(
                'success', true,
                'idempotent', true,
                'message', 'Already processed',
                'balance_monthly', v_existing_tx.balance_monthly_after,
                'balance_permanent', v_existing_tx.balance_permanent_after
            );
        END IF;
    END IF;
    
    -- 2. Lock user row (SELECT FOR UPDATE) to prevent race conditions
    SELECT credits_monthly, credits_permanent 
    INTO v_monthly, v_permanent
    FROM profiles 
    WHERE id = p_user_id 
    FOR UPDATE;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', false, 
            'error', 'User not found',
            'error_code', 'USER_NOT_FOUND'
        );
    END IF;
    
    -- 3. Check sufficient balance
    IF (v_monthly + v_permanent) < p_amount THEN
        RETURN jsonb_build_object(
            'success', false, 
            'error', 'Insufficient credits',
            'error_code', 'CREDITS_INSUFFICIENT',
            'available', v_monthly + v_permanent,
            'required', p_amount
        );
    END IF;
    
    -- 4. Calculate deduction (monthly first, then permanent per PRD)
    v_deduct_monthly := LEAST(v_monthly, p_amount);
    v_deduct_permanent := p_amount - v_deduct_monthly;
    v_new_monthly := v_monthly - v_deduct_monthly;
    v_new_permanent := v_permanent - v_deduct_permanent;
    v_bucket := CASE WHEN v_deduct_monthly > 0 THEN 'monthly' ELSE 'permanent' END;
    
    -- 5. Update balance (within same transaction)
    UPDATE profiles 
    SET credits_monthly = v_new_monthly,
        credits_permanent = v_new_permanent,
        updated_at = NOW()
    WHERE id = p_user_id;
    
    -- 6. Log transaction for monthly deduction (if any)
    IF v_deduct_monthly > 0 THEN
        INSERT INTO credit_transactions (
            user_id, amount, bucket, 
            balance_monthly_after, balance_permanent_after,
            type, description, timezone, idempotency_key
        ) VALUES (
            p_user_id, -v_deduct_monthly, 'monthly',
            v_new_monthly, v_new_permanent,
            p_tx_type, p_description, p_timezone, 
            CASE WHEN v_deduct_permanent = 0 THEN p_idempotency_key ELSE NULL END
        );
    END IF;
    
    -- 7. Log transaction for permanent deduction (if any)
    IF v_deduct_permanent > 0 THEN
        INSERT INTO credit_transactions (
            user_id, amount, bucket, 
            balance_monthly_after, balance_permanent_after,
            type, description, timezone, idempotency_key
        ) VALUES (
            p_user_id, -v_deduct_permanent, 'permanent',
            v_new_monthly, v_new_permanent,
            p_tx_type, p_description, p_timezone, p_idempotency_key
        );
    END IF;
    
    -- 8. Return success
    RETURN jsonb_build_object(
        'success', true,
        'deducted', p_amount,
        'balance_monthly', v_new_monthly,
        'balance_permanent', v_new_permanent,
        'bucket', v_bucket
    );
    
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'error_code', 'DB_ERROR'
    );
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION deduct_credits_atomic IS 'Atomic credit deduction with row locking and idempotency';

-- =============================================================================
-- 5. Atomic Credit Addition Function
-- =============================================================================

CREATE OR REPLACE FUNCTION add_credits_atomic(
    p_user_id UUID,
    p_amount INT,
    p_bucket TEXT,  -- 'monthly' or 'permanent'
    p_tx_type TEXT,
    p_description TEXT DEFAULT NULL,
    p_timezone TEXT DEFAULT 'UTC',
    p_idempotency_key TEXT DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    v_monthly INT;
    v_permanent INT;
    v_new_monthly INT;
    v_new_permanent INT;
    v_existing_tx RECORD;
BEGIN
    -- Validate amount
    IF p_amount <= 0 THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Amount must be positive',
            'error_code', 'INVALID_AMOUNT'
        );
    END IF;
    
    -- Validate bucket
    IF p_bucket NOT IN ('monthly', 'permanent') THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Invalid bucket, must be monthly or permanent',
            'error_code', 'INVALID_BUCKET'
        );
    END IF;
    
    -- 1. Idempotency check
    IF p_idempotency_key IS NOT NULL THEN
        SELECT * INTO v_existing_tx 
        FROM credit_transactions 
        WHERE idempotency_key = p_idempotency_key
        LIMIT 1;
        
        IF FOUND THEN
            RETURN jsonb_build_object(
                'success', true,
                'idempotent', true,
                'message', 'Already processed'
            );
        END IF;
    END IF;
    
    -- 2. Lock user row
    SELECT credits_monthly, credits_permanent 
    INTO v_monthly, v_permanent
    FROM profiles 
    WHERE id = p_user_id 
    FOR UPDATE;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', false, 
            'error', 'User not found',
            'error_code', 'USER_NOT_FOUND'
        );
    END IF;
    
    -- 3. Calculate new balances
    IF p_bucket = 'monthly' THEN
        v_new_monthly := v_monthly + p_amount;
        v_new_permanent := v_permanent;
    ELSE
        v_new_monthly := v_monthly;
        v_new_permanent := v_permanent + p_amount;
    END IF;
    
    -- 4. Update balance
    UPDATE profiles 
    SET credits_monthly = v_new_monthly,
        credits_permanent = v_new_permanent,
        updated_at = NOW()
    WHERE id = p_user_id;
    
    -- 5. Log transaction
    INSERT INTO credit_transactions (
        user_id, amount, bucket, 
        balance_monthly_after, balance_permanent_after,
        type, description, timezone, idempotency_key
    ) VALUES (
        p_user_id, p_amount, p_bucket,
        v_new_monthly, v_new_permanent,
        p_tx_type, p_description, p_timezone, p_idempotency_key
    );
    
    -- 6. Return success
    RETURN jsonb_build_object(
        'success', true,
        'added', p_amount,
        'bucket', p_bucket,
        'balance_monthly', v_new_monthly,
        'balance_permanent', v_new_permanent
    );
    
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'error_code', 'DB_ERROR'
    );
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION add_credits_atomic IS 'Atomic credit addition with row locking and idempotency';

-- =============================================================================
-- 6. Atomic Marketplace Purchase Function
-- =============================================================================

CREATE OR REPLACE FUNCTION execute_marketplace_purchase(
    p_listing_id UUID,
    p_buyer_id UUID,
    p_timezone TEXT DEFAULT 'UTC',
    p_idempotency_key TEXT DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    v_listing RECORD;
    v_buyer RECORD;
    v_price INT;
    v_seller_id UUID;
    v_seller_revenue INT;
    v_buyer_monthly INT;
    v_buyer_permanent INT;
    v_deduct_monthly INT;
    v_deduct_permanent INT;
    v_new_buyer_monthly INT;
    v_new_buyer_permanent INT;
    v_existing_purchase RECORD;
    v_purchase_id UUID;
BEGIN
    -- 1. Idempotency check
    IF p_idempotency_key IS NOT NULL THEN
        SELECT * INTO v_existing_purchase 
        FROM user_purchases 
        WHERE idempotency_key = p_idempotency_key
        LIMIT 1;
        
        IF FOUND THEN
            RETURN jsonb_build_object(
                'success', true,
                'idempotent', true,
                'purchase_id', v_existing_purchase.id,
                'message', 'Already processed'
            );
        END IF;
    END IF;
    
    -- 2. Check if already purchased (by listing + buyer combo)
    SELECT id INTO v_purchase_id
    FROM user_purchases
    WHERE user_id = p_buyer_id AND listing_id = p_listing_id
    LIMIT 1;
    
    IF FOUND THEN
        RETURN jsonb_build_object(
            'success', true,
            'already_owned', true,
            'purchase_id', v_purchase_id,
            'message', 'Already purchased'
        );
    END IF;
    
    -- 3. Lock and get listing
    SELECT * INTO v_listing
    FROM marketplace_listings
    WHERE id = p_listing_id
    FOR UPDATE;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', false, 
            'error', 'Listing not found', 
            'status', 404
        );
    END IF;
    
    -- 4. Validate listing status
    IF v_listing.moderation_status != 'approved' THEN
        RETURN jsonb_build_object(
            'success', false, 
            'error', 'Listing is not approved', 
            'status', 400
        );
    END IF;
    
    IF NOT COALESCE(v_listing.is_public, false) THEN
        RETURN jsonb_build_object(
            'success', false, 
            'error', 'Listing is not public', 
            'status', 400
        );
    END IF;
    
    IF COALESCE(v_listing.is_deleted, false) THEN
        RETURN jsonb_build_object(
            'success', false, 
            'error', 'Listing has been deleted', 
            'status', 400
        );
    END IF;
    
    v_price := COALESCE(v_listing.price_credits, 0);
    v_seller_id := v_listing.seller_id;
    
    -- 5. Handle free items
    IF v_price = 0 THEN
        INSERT INTO user_purchases (user_id, listing_id, price_paid, timezone, idempotency_key)
        VALUES (p_buyer_id, p_listing_id, 0, p_timezone, p_idempotency_key)
        RETURNING id INTO v_purchase_id;
        
        UPDATE marketplace_listings 
        SET sales_count = COALESCE(sales_count, 0) + 1
        WHERE id = p_listing_id;
        
        RETURN jsonb_build_object(
            'success', true,
            'purchase_id', v_purchase_id,
            'price_paid', 0,
            'message', 'Free item acquired'
        );
    END IF;
    
    -- 6. Lock and get buyer
    SELECT credits_monthly, credits_permanent 
    INTO v_buyer_monthly, v_buyer_permanent
    FROM profiles
    WHERE id = p_buyer_id
    FOR UPDATE;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', false, 
            'error', 'Buyer not found', 
            'status', 404
        );
    END IF;
    
    -- 7. Check buyer has enough credits
    IF (v_buyer_monthly + v_buyer_permanent) < v_price THEN
        RETURN jsonb_build_object(
            'success', false, 
            'error', 'Insufficient credits',
            'status', 402,
            'available', v_buyer_monthly + v_buyer_permanent,
            'required', v_price
        );
    END IF;
    
    -- 8. Calculate deduction (monthly first)
    v_deduct_monthly := LEAST(v_buyer_monthly, v_price);
    v_deduct_permanent := v_price - v_deduct_monthly;
    v_new_buyer_monthly := v_buyer_monthly - v_deduct_monthly;
    v_new_buyer_permanent := v_buyer_permanent - v_deduct_permanent;
    
    -- 9. Deduct from buyer
    UPDATE profiles SET
        credits_monthly = v_new_buyer_monthly,
        credits_permanent = v_new_buyer_permanent,
        updated_at = NOW()
    WHERE id = p_buyer_id;
    
    -- 10. Log buyer transaction(s)
    IF v_deduct_monthly > 0 THEN
        INSERT INTO credit_transactions (
            user_id, amount, bucket, type, description, timezone,
            balance_monthly_after, balance_permanent_after
        ) VALUES (
            p_buyer_id, -v_deduct_monthly, 'monthly',
            'market_purchase', 
            'Purchased: ' || COALESCE(v_listing.title, 'Item'),
            p_timezone,
            v_new_buyer_monthly, v_new_buyer_permanent
        );
    END IF;
    
    IF v_deduct_permanent > 0 THEN
        INSERT INTO credit_transactions (
            user_id, amount, bucket, type, description, timezone,
            balance_monthly_after, balance_permanent_after
        ) VALUES (
            p_buyer_id, -v_deduct_permanent, 'permanent',
            'market_purchase', 
            'Purchased: ' || COALESCE(v_listing.title, 'Item'),
            p_timezone,
            v_new_buyer_monthly, v_new_buyer_permanent
        );
    END IF;
    
    -- 11. Add to seller (90% revenue)
    v_seller_revenue := (v_price * 90) / 100;
    
    IF v_seller_id IS NOT NULL AND v_seller_revenue > 0 THEN
        -- Lock seller row
        PERFORM 1 FROM profiles WHERE id = v_seller_id FOR UPDATE;
        
        UPDATE profiles SET
            credits_permanent = credits_permanent + v_seller_revenue,
            updated_at = NOW()
        WHERE id = v_seller_id;
        
        INSERT INTO credit_transactions (
            user_id, amount, bucket, type, description, timezone,
            balance_monthly_after, balance_permanent_after
        ) 
        SELECT 
            v_seller_id, v_seller_revenue, 'permanent',
            'market_sale', 
            'Sale: ' || COALESCE(v_listing.title, 'Item'),
            p_timezone,
            p.credits_monthly, p.credits_permanent
        FROM profiles p WHERE p.id = v_seller_id;
    END IF;
    
    -- 12. Record purchase
    INSERT INTO user_purchases (user_id, listing_id, price_paid, timezone, idempotency_key)
    VALUES (p_buyer_id, p_listing_id, v_price, p_timezone, p_idempotency_key)
    RETURNING id INTO v_purchase_id;
    
    -- 13. Update sales count
    UPDATE marketplace_listings 
    SET sales_count = COALESCE(sales_count, 0) + 1
    WHERE id = p_listing_id;
    
    -- 14. Return success
    RETURN jsonb_build_object(
        'success', true,
        'purchase_id', v_purchase_id,
        'price_paid', v_price,
        'seller_revenue', v_seller_revenue,
        'buyer_balance_monthly', v_new_buyer_monthly,
        'buyer_balance_permanent', v_new_buyer_permanent,
        'message', 'Purchase successful'
    );
    
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'status', 500
    );
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION execute_marketplace_purchase IS 'Atomic marketplace purchase with all credit operations in single transaction';

-- =============================================================================
-- 7. Webhook Idempotency Check Function
-- =============================================================================

CREATE OR REPLACE FUNCTION check_webhook_idempotency(
    p_event_id TEXT,
    p_event_type TEXT,
    p_payload JSONB DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    v_existing RECORD;
BEGIN
    -- Check if event already processed
    SELECT * INTO v_existing
    FROM webhook_events
    WHERE event_id = p_event_id;
    
    IF FOUND THEN
        RETURN jsonb_build_object(
            'success', true,
            'idempotent', true,
            'message', 'Event already processed',
            'original_result', v_existing.result
        );
    END IF;
    
    -- Insert record to claim processing
    INSERT INTO webhook_events (event_id, event_type, payload)
    VALUES (p_event_id, p_event_type, p_payload);
    
    RETURN jsonb_build_object(
        'success', true,
        'idempotent', false,
        'should_process', true
    );
    
EXCEPTION WHEN unique_violation THEN
    -- Concurrent insert, event being processed by another request
    RETURN jsonb_build_object(
        'success', true,
        'idempotent', true,
        'message', 'Concurrent processing detected'
    );
WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM
    );
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION check_webhook_idempotency IS 'Check and claim webhook event for idempotent processing';

-- =============================================================================
-- 8. Update Webhook Result Function
-- =============================================================================

CREATE OR REPLACE FUNCTION update_webhook_result(
    p_event_id TEXT,
    p_result JSONB
) RETURNS BOOLEAN AS $$
BEGIN
    UPDATE webhook_events
    SET result = p_result,
        processed_at = NOW()
    WHERE event_id = p_event_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_webhook_result IS 'Update webhook event with processing result';

-- =============================================================================
-- 9. Cleanup old webhook events (optional, for maintenance)
-- =============================================================================

CREATE OR REPLACE FUNCTION cleanup_old_webhook_events(
    p_days_old INT DEFAULT 30
) RETURNS INT AS $$
DECLARE
    v_deleted INT;
BEGIN
    DELETE FROM webhook_events
    WHERE created_at < NOW() - (p_days_old || ' days')::INTERVAL;
    
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN v_deleted;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_webhook_events IS 'Clean up webhook events older than specified days';

-- =============================================================================
-- End of Migration
-- =============================================================================
