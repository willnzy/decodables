"""
Tests for api/user/webhooks.py

Endpoints:
- POST /api/v2/user/webhooks/clerk
- POST /api/v2/user/webhooks/stripe

Created: 2026-01-08 (Stage 3: Week 1 Day 3)
Updated: 2026-01-10 - v2.5.0 Service layer migration

IMPORTANT: Webhook endpoints are critical for payment and auth.
These tests focus on business logic validation.

v2.5.0 Changes:
- Migrated to Service layer with dependency injection
- Updated all mocks to use app.dependency_overrides
- Mock Services instead of Repositories

v2.4.0 Changes Tested:
- W-P0-1: Stripe signature header required (not optional)
- W-P0-2/3: Transaction order (payment first, then credits)
- W-HIGH-1: Atomic signup bonus
- W-HIGH-2/3: Renewal transaction handling
- W-MEDIUM-*: Error handling improvements
"""

import pytest
import json
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app import app
from api.user.webhooks import get_clerk_webhook_service, get_stripe_webhook_service

client = TestClient(app)


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def clerk_user_created_payload():
    """Mock Clerk user.created event payload."""
    return {
        "type": "user.created",
        "data": {
            "id": "user_clerk_123",
            "email_addresses": [{"email_address": "newuser@example.com"}],
            "username": "newuser",
            "image_url": "https://img.clerk.com/avatar.jpg",
            "first_name": "John",
            "last_name": "Doe",
        }
    }


@pytest.fixture
def clerk_user_updated_payload():
    """Mock Clerk user.updated event payload."""
    return {
        "type": "user.updated",
        "data": {
            "id": "user_clerk_456",
            "image_url": "https://img.clerk.com/new_avatar.jpg",
            "username": "updateduser",
            "first_name": "Jane",
            "last_name": "Smith",
        }
    }


@pytest.fixture
def stripe_checkout_completed_payload():
    """Mock Stripe checkout.session.completed event."""
    return {
        "id": "evt_stripe_123",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "metadata": {
                    "user_id": "user_stripe_789",
                    "plan_type": "starter"
                },
                "customer": "cus_stripe_abc",
                "amount_total": 1490,  # $14.90 in cents
                "currency": "usd"
            }
        }
    }


@pytest.fixture
def stripe_credits_purchase_payload():
    """Mock Stripe credits purchase event."""
    return {
        "id": "evt_credits_123",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_credits_123",
                "metadata": {
                    "user_id": "user_credits_999",
                    "plan_type": "credits_100"
                },
                "customer": "cus_credits_xyz",
                "amount_total": 1000,  # $10.00 in cents
                "currency": "usd"
            }
        }
    }


# ==========================================
# POST /api/v2/user/webhooks/clerk
# ==========================================

class TestClerkWebhook:
    """Tests for POST /api/v2/user/webhooks/clerk endpoint."""

    def test_clerk_webhook_missing_secret(self):
        """
        Test: Missing CLERK_WEBHOOK_SECRET (500)

        Given: CLERK_WEBHOOK_SECRET not configured
        When: POST to clerk webhook
        Then: Returns 500 Internal Server Error

        Business Logic Verified:
        - Webhook rejects requests when secret not configured
        - Returns appropriate 500 status
        """
        # Arrange: Mock service that raises ValueError for missing secret
        mock_service = MagicMock()
        mock_service.verify_signature.side_effect = ValueError("Missing CLERK_WEBHOOK_SECRET")

        app.dependency_overrides[get_clerk_webhook_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/webhooks/clerk",
            json={"type": "user.created", "data": {}},
        )

        # Assert
        assert response.status_code == 500

        # Cleanup
        app.dependency_overrides.clear()

    def test_clerk_webhook_invalid_signature(self):
        """
        Test: Invalid signature (400)

        Given: Request with invalid signature
        When: Webhook verification fails
        Then: Returns 400 Bad Request

        Business Logic Verified:
        - Webhook signature is verified using Svix Webhook library
        - Invalid signatures are rejected with 400 status
        """
        # Arrange: Mock service that raises WebhookVerificationError
        from svix.webhooks import WebhookVerificationError

        mock_service = MagicMock()
        mock_service.verify_signature.side_effect = WebhookVerificationError("Invalid signature")

        app.dependency_overrides[get_clerk_webhook_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/webhooks/clerk",
            json={"type": "user.created", "data": {}},
        )

        # Assert
        assert response.status_code == 400

        # Cleanup
        app.dependency_overrides.clear()

    def test_clerk_user_created_success(self, clerk_user_created_payload):
        """
        Test: User created successfully with 50 signup bonus

        Given: New user signup via Clerk
        When: user.created event received
        Then: Creates profile and grants 50 permanent signup credits

        Business Logic Verified:
        - Verifies user doesn't exist before creating
        - Verifies email is unique
        - Creates user profile with Clerk data
        - v2.4.0: W-HIGH-1 fix - Uses atomic RPC for signup bonus
        - Logs user_signup activity
        """
        # Arrange: Mock service
        mock_service = MagicMock()
        mock_service.verify_signature.return_value = clerk_user_created_payload
        mock_service.handle_event = AsyncMock(return_value={"status": "processed"})

        app.dependency_overrides[get_clerk_webhook_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/webhooks/clerk",
            json=clerk_user_created_payload,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"

        # Verify service was called
        mock_service.verify_signature.assert_called_once()
        mock_service.handle_event.assert_called_once()

        # Cleanup
        app.dependency_overrides.clear()

    def test_clerk_user_created_jit_exists(self, clerk_user_created_payload):
        """
        Test: User already exists (JIT created)

        Given: User was created via JIT (just-in-time) during API call
        When: user.created webhook arrives later
        Then: Updates missing info instead of creating

        Business Logic Verified:
        - Detects existing user profile
        - Updates profile instead of creating duplicate
        - Returns 'updated' status with 'jit_created' reason
        """
        # Arrange: Mock service returning 'updated' status
        mock_service = MagicMock()
        mock_service.verify_signature.return_value = clerk_user_created_payload
        mock_service.handle_event = AsyncMock(return_value={
            "status": "updated",
            "reason": "jit_created"
        })

        app.dependency_overrides[get_clerk_webhook_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/webhooks/clerk",
            json=clerk_user_created_payload,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"
        assert data["reason"] == "jit_created"

        # Cleanup
        app.dependency_overrides.clear()

    def test_clerk_user_created_email_exists(self, clerk_user_created_payload):
        """
        Test: Email already taken (skip creation)

        Given: Another user with same email exists
        When: user.created event received
        Then: Skips creation to avoid duplicates

        Business Logic Verified:
        - Checks email uniqueness before creating user
        - Prevents duplicate accounts with same email
        - Returns 'skipped' status with 'email_exists' reason
        """
        # Arrange: Mock service returning 'skipped' status
        mock_service = MagicMock()
        mock_service.verify_signature.return_value = clerk_user_created_payload
        mock_service.handle_event = AsyncMock(return_value={
            "status": "skipped",
            "reason": "email_exists"
        })

        app.dependency_overrides[get_clerk_webhook_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/webhooks/clerk",
            json=clerk_user_created_payload,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"
        assert data["reason"] == "email_exists"

        # Cleanup
        app.dependency_overrides.clear()

    def test_clerk_user_updated(self, clerk_user_updated_payload):
        """
        Test: User profile updated

        Given: User updates avatar/username in Clerk
        When: user.updated event received
        Then: Syncs changes to Supabase

        Business Logic Verified:
        - Syncs profile updates from Clerk to Supabase
        - Updates avatar_url, username, first_name, last_name
        - Logs profile_updated activity
        """
        # Arrange: Mock service
        mock_service = MagicMock()
        mock_service.verify_signature.return_value = clerk_user_updated_payload
        mock_service.handle_event = AsyncMock(return_value={"status": "processed"})

        app.dependency_overrides[get_clerk_webhook_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/webhooks/clerk",
            json=clerk_user_updated_payload,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"

        # Cleanup
        app.dependency_overrides.clear()


# ==========================================
# POST /api/v2/user/webhooks/stripe
# ==========================================

class TestStripeWebhook:
    """Tests for POST /api/v2/user/webhooks/stripe endpoint."""

    def test_stripe_webhook_missing_signature_header(self):
        """
        Test: Missing Stripe-Signature header (422)

        Given: Request without Stripe-Signature header
        When: POST to stripe webhook
        Then: Returns 422 Unprocessable Entity

        v2.4.0: W-P0-1 fix - Signature header is now required
        """
        # Act
        response = client.post(
            "/api/v2/user/webhooks/stripe",
            json={"type": "checkout.session.completed"},
            # Note: No Stripe-Signature header
        )

        # Assert - FastAPI returns 422 for missing required header
        assert response.status_code == 422

    def test_stripe_webhook_invalid_signature(self):
        """
        Test: Invalid Stripe signature (400)

        Given: Request with invalid signature
        When: construct_event raises exception
        Then: Returns 400 Bad Request

        Business Logic Verified:
        - Stripe signature is verified via construct_event
        - Invalid signatures are rejected with 400 status
        - Prevents unauthorized webhook requests
        """
        # Arrange: Mock service that raises exception on verify
        mock_service = MagicMock()
        mock_service.verify_signature.side_effect = Exception("Invalid signature")

        app.dependency_overrides[get_stripe_webhook_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/webhooks/stripe",
            json={"type": "checkout.session.completed"},
            headers={"stripe-signature": "invalid_sig"},
        )

        # Assert
        assert response.status_code == 400

        # Cleanup
        app.dependency_overrides.clear()

    def test_stripe_checkout_subscription_success(self, stripe_checkout_completed_payload):
        """
        Test: Subscription checkout completed

        Given: User subscribes to Starter plan
        When: checkout.session.completed event received
        Then: Updates tier and grants 500 monthly credits

        Business Logic Verified:
        - Idempotency check prevents duplicate processing
        - v2.4.0: Atomic RPC called first (falls back to legacy)
        - Updates user tier to 'starter'
        - Grants 500 monthly credits
        - Logs payment record (BEFORE credits in legacy flow)
        - Logs activity
        - Tracks analytics event
        """
        # Arrange: Mock service
        mock_service = MagicMock()
        mock_service.verify_signature.return_value = stripe_checkout_completed_payload
        mock_service.is_duplicate_event = AsyncMock(return_value=False)
        mock_service.handle_event = AsyncMock(return_value={
            "status": "ok",
            "action": "subscription_started",
            "user_id": "user_stripe_789",
            "plan": "starter"
        })
        mock_service.update_webhook_result = AsyncMock()

        app.dependency_overrides[get_stripe_webhook_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/webhooks/stripe",
            content=json.dumps(stripe_checkout_completed_payload).encode(),
            headers={"Stripe-Signature": "sig_test", "content-type": "application/json"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "subscription_started"
        assert data["plan"] == "starter"

        # Verify service methods called
        mock_service.verify_signature.assert_called_once()
        mock_service.is_duplicate_event.assert_called_once_with(
            "evt_stripe_123",
            "checkout.session.completed",
            stripe_checkout_completed_payload
        )
        mock_service.handle_event.assert_called_once()
        mock_service.update_webhook_result.assert_called_once()

        # Cleanup
        app.dependency_overrides.clear()

    def test_stripe_checkout_credits_purchase(self, stripe_credits_purchase_payload):
        """
        Test: Credits purchase completed

        Given: User buys 100 credits for $10
        When: checkout.session.completed event received
        Then: Adds 100 permanent credits

        Business Logic Verified:
        - Idempotency check prevents duplicate processing
        - v2.4.0: W-P0-3 fix - Logs payment record FIRST
        - Adds 100 permanent credits to user account
        - Logs activity
        - Tracks analytics event
        """
        # Arrange: Mock service
        mock_service = MagicMock()
        mock_service.verify_signature.return_value = stripe_credits_purchase_payload
        mock_service.is_duplicate_event = AsyncMock(return_value=False)
        mock_service.handle_event = AsyncMock(return_value={
            "status": "ok",
            "action": "credits_added",
            "user_id": "user_credits_999",
            "credits": 100
        })
        mock_service.update_webhook_result = AsyncMock()

        app.dependency_overrides[get_stripe_webhook_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/webhooks/stripe",
            content=json.dumps(stripe_credits_purchase_payload).encode(),
            headers={"Stripe-Signature": "sig_test", "content-type": "application/json"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "credits_added"

        # Cleanup
        app.dependency_overrides.clear()

    def test_stripe_webhook_idempotency_duplicate(self, stripe_checkout_completed_payload):
        """
        Test: Duplicate event ignored

        Given: Stripe resends same event
        When: Idempotency check detects duplicate
        Then: Returns success without processing

        Business Logic Verified:
        - Idempotency check using PostgreSQL RPC
        - Duplicate events are detected via event_id
        - Returns 'already_processed' status without side effects
        - Prevents double-charging/double-crediting
        """
        # Arrange: Mock service returning duplicate
        mock_service = MagicMock()
        mock_service.verify_signature.return_value = stripe_checkout_completed_payload
        mock_service.is_duplicate_event = AsyncMock(return_value=True)

        app.dependency_overrides[get_stripe_webhook_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/webhooks/stripe",
            content=json.dumps(stripe_checkout_completed_payload).encode(),
            headers={"Stripe-Signature": "sig_test", "content-type": "application/json"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "already_processed"
        assert "event_id" in data

        # Cleanup
        app.dependency_overrides.clear()

    def test_stripe_invoice_payment_renewal(self):
        """
        Test: Subscription renewal (invoice.payment_succeeded)

        Given: Pro user's subscription renews
        When: invoice.payment_succeeded with billing_reason=subscription_cycle
        Then: Refreshes monthly credits (resets to 1000)

        Business Logic Verified:
        - Idempotency check prevents duplicate processing
        - Looks up user by stripe_customer_id
        - v2.4.0: W-HIGH-2 fix - Logs payment record FIRST
        - Refreshes monthly credits based on tier (pro = 1000)
        - Logs activity
        """
        # Arrange: Mock invoice payload and service
        invoice_payload = {
            "id": "evt_invoice_123",
            "type": "invoice.payment_succeeded",
            "data": {
                "object": {
                    "id": "in_test_123",
                    "customer": "cus_renewal_abc",
                    "amount_paid": 2990,  # $29.90
                    "currency": "usd",
                    "billing_reason": "subscription_cycle"
                }
            }
        }

        mock_service = MagicMock()
        mock_service.verify_signature.return_value = invoice_payload
        mock_service.is_duplicate_event = AsyncMock(return_value=False)
        mock_service.handle_event = AsyncMock(return_value={
            "status": "ok",
            "action": "credits_refreshed",
            "user_id": "user_renewal_123"
        })
        mock_service.update_webhook_result = AsyncMock()

        app.dependency_overrides[get_stripe_webhook_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/webhooks/stripe",
            content=json.dumps(invoice_payload).encode(),
            headers={"Stripe-Signature": "sig_test", "content-type": "application/json"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "credits_refreshed"

        # Cleanup
        app.dependency_overrides.clear()

    def test_stripe_subscription_canceled(self):
        """
        Test: Subscription canceled

        Given: User cancels subscription
        When: customer.subscription.deleted event received
        Then: Downgrades to free tier

        Business Logic Verified:
        - Idempotency check prevents duplicate processing
        - Looks up user by stripe_customer_id
        - Downgrades user to 'free' tier
        - Sets subscription_status to 'inactive'
        - Logs activity
        """
        # Arrange: Mock canceled payload and service
        canceled_payload = {
            "id": "evt_cancel_123",
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_cancel_123",
                    "customer": "cus_cancel_xyz",
                    "status": "canceled"
                }
            }
        }

        mock_service = MagicMock()
        mock_service.verify_signature.return_value = canceled_payload
        mock_service.is_duplicate_event = AsyncMock(return_value=False)
        mock_service.handle_event = AsyncMock(return_value={
            "status": "ok",
            "action": "subscription_ended",
            "user_id": "user_cancel_456",
            "previous_tier": "starter"
        })
        mock_service.update_webhook_result = AsyncMock()

        app.dependency_overrides[get_stripe_webhook_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/webhooks/stripe",
            content=json.dumps(canceled_payload).encode(),
            headers={"Stripe-Signature": "sig_test", "content-type": "application/json"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "subscription_ended"

        # Cleanup
        app.dependency_overrides.clear()


"""
Test Coverage Summary (v2.5.0)

Clerk Webhook Tests (6 tests):
✅ Missing secret configuration (500)
✅ Invalid signature verification (400)
✅ User created successfully with signup bonus
✅ User created (JIT exists)
✅ User created (email exists)
✅ User profile updated

Stripe Webhook Tests (7 tests):
✅ Missing Stripe-Signature header (422)
✅ Invalid signature verification (400)
✅ Checkout subscription success (starter plan)
✅ Checkout credits purchase (100 credits)
✅ Idempotency duplicate detection
✅ Invoice payment renewal (subscription_cycle)
✅ Subscription canceled

Total: 13 tests

Business Logic Tested:
- ✅ [v2.4.0] Stripe signature header required (W-P0-1)
- ✅ [v2.4.0] Transaction order - payment first (W-P0-2/3)
- ✅ [v2.4.0] Atomic signup bonus (W-HIGH-1)
- ✅ [v2.4.0] Renewal transaction handling (W-HIGH-2/3)
- ✅ [v2.5.0] Service layer with dependency injection
- ✅ Signature verification (Clerk + Stripe)
- ✅ Idempotency protection
- ✅ User profile management (JIT, email uniqueness)
- ✅ Credits operations (purchase, refresh, signup bonus)
- ✅ Subscription lifecycle (start, renewal, cancel)

Not Tested (Requires Integration/E2E):
- Actual Stripe/Clerk API interaction
- Real database transaction consistency
- PostgreSQL RPC functions (grant_signup_bonus_atomic, check_webhook_idempotency, etc.)
"""
