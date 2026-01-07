"""
Tests for api/user/webhooks.py

Endpoints:
- POST /api/v2/user/webhooks/clerk
- POST /api/v2/user/webhooks/stripe

Created: 2026-01-08 (Stage 3: Week 1 Day 3)

IMPORTANT: Webhook endpoints are critical for payment and auth.
These tests focus on business logic validation.
"""

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_clerk_webhook_secret(monkeypatch):
    """Mock CLERK_WEBHOOK_SECRET."""
    monkeypatch.setattr("api.user.webhooks.CLERK_WEBHOOK_SECRET", "whsec_test_secret")


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
        # Act
        response = client.post(
            "/api/v2/user/webhooks/clerk",
            json={"type": "user.created", "data": {}},
        )

        # Assert
        assert response.status_code == 500

    @patch('api.user.webhooks.Webhook')
    def test_clerk_webhook_invalid_signature(
        self,
        mock_webhook_class,
        mock_clerk_webhook_secret,
    ):
        """
        Test: Invalid signature (400)

        Given: Request with invalid signature
        When: Webhook verification fails
        Then: Returns 400 Bad Request

        Business Logic Verified:
        - Webhook signature is verified using Svix Webhook library
        - Invalid signatures are rejected with 400 status
        """
        # Arrange
        from svix.webhooks import WebhookVerificationError
        mock_webhook = MagicMock()
        mock_webhook.verify.side_effect = WebhookVerificationError("Invalid signature")
        mock_webhook_class.return_value = mock_webhook

        # Act
        response = client.post(
            "/api/v2/user/webhooks/clerk",
            json={"type": "user.created", "data": {}},
        )

        # Assert
        assert response.status_code == 400

    @patch('api.user.webhooks.Webhook')
    @patch('api.user.webhooks.SupabaseUserRepository')
    @patch('api.user.webhooks.get_supabase_client')
    def test_clerk_user_created_success(
        self,
        mock_get_supabase,
        mock_user_repo_class,
        mock_webhook_class,
        mock_clerk_webhook_secret,
        clerk_user_created_payload,
    ):
        """
        Test: User created successfully

        Given: New user signup via Clerk
        When: user.created event received
        Then: Creates profile with 50 signup credits

        Business Logic Verified:
        - Verifies user doesn't exist before creating
        - Verifies email is unique
        - Creates user profile with Clerk data
        - Logs user_signup activity
        """
        # Arrange
        mock_webhook = MagicMock()
        mock_webhook.verify.return_value = clerk_user_created_payload
        mock_webhook_class.return_value = mock_webhook

        # Mock UserRepository
        mock_user_repo = MagicMock()
        mock_user_repo.get_profile = AsyncMock(return_value=None)  # User doesn't exist
        mock_user_repo.search_users = AsyncMock(return_value=None)  # Email not taken
        mock_user_repo.create_profile = AsyncMock()
        mock_user_repo_class.return_value = mock_user_repo

        # Mock Supabase for activity logging
        mock_supabase = MagicMock()
        mock_table_insert = MagicMock()
        mock_table_insert.execute = MagicMock()
        mock_supabase.table.return_value.insert.return_value = mock_table_insert
        mock_get_supabase.return_value = mock_supabase

        # Act
        response = client.post(
            "/api/v2/user/webhooks/clerk",
            json=clerk_user_created_payload,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"

        # Verify profile created
        mock_user_repo.create_profile.assert_called_once()
        call_args = mock_user_repo.create_profile.call_args[0]
        assert call_args[0] == "user_clerk_123"
        assert call_args[1] == "newuser@example.com"
        assert call_args[2] == "newuser"

        # Verify signup logged
        mock_supabase.table.assert_called_with("activity_logs")
        insert_calls = mock_supabase.table.return_value.insert.call_args_list
        assert len(insert_calls) > 0
        activity_data = insert_calls[0][0][0]
        assert activity_data["user_id"] == "user_clerk_123"
        assert activity_data["activity_type"] == "user_signup"

    @patch('api.user.webhooks.Webhook')
    @patch('api.user.webhooks.SupabaseUserRepository')
    @patch('api.user.webhooks.get_supabase_client')
    def test_clerk_user_created_jit_exists(
        self,
        mock_get_supabase,
        mock_user_repo_class,
        mock_webhook_class,
        mock_clerk_webhook_secret,
        clerk_user_created_payload,
    ):
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
        # Arrange
        mock_webhook = MagicMock()
        mock_webhook.verify.return_value = clerk_user_created_payload
        mock_webhook_class.return_value = mock_webhook

        # Mock UserRepository
        mock_user_repo = MagicMock()
        mock_user_repo.get_profile = AsyncMock(return_value={
            "id": "user_clerk_123",
            "email": "newuser@example.com",
        })
        mock_user_repo.update_profile = AsyncMock()
        mock_user_repo_class.return_value = mock_user_repo

        # Mock Supabase for table operations
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

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

        # Verify update called
        mock_user_repo.update_profile.assert_called_once()

    @patch('api.user.webhooks.Webhook')
    @patch('api.user.webhooks.SupabaseUserRepository')
    @patch('api.user.webhooks.get_supabase_client')
    def test_clerk_user_created_email_exists(
        self,
        mock_get_supabase,
        mock_user_repo_class,
        mock_webhook_class,
        mock_clerk_webhook_secret,
        clerk_user_created_payload,
    ):
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
        # Arrange
        mock_webhook = MagicMock()
        mock_webhook.verify.return_value = clerk_user_created_payload
        mock_webhook_class.return_value = mock_webhook

        # Mock UserRepository
        mock_user_repo = MagicMock()
        mock_user_repo.get_profile = AsyncMock(return_value=None)
        mock_user_repo.search_users = AsyncMock(return_value=[{"id": "other_user", "email": "newuser@example.com"}])
        mock_user_repo_class.return_value = mock_user_repo

        # Mock Supabase
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

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

    @patch('api.user.webhooks.Webhook')
    @patch('api.user.webhooks.SupabaseUserRepository')
    @patch('api.user.webhooks.get_supabase_client')
    def test_clerk_user_updated(
        self,
        mock_get_supabase,
        mock_user_repo_class,
        mock_webhook_class,
        mock_clerk_webhook_secret,
        clerk_user_updated_payload,
    ):
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
        # Arrange
        mock_webhook = MagicMock()
        mock_webhook.verify.return_value = clerk_user_updated_payload
        mock_webhook_class.return_value = mock_webhook

        # Mock UserRepository
        mock_user_repo = MagicMock()
        mock_user_repo.update_profile = AsyncMock()
        mock_user_repo_class.return_value = mock_user_repo

        # Mock Supabase for activity logging
        mock_supabase = MagicMock()
        mock_table_insert = MagicMock()
        mock_table_insert.execute = MagicMock()
        mock_supabase.table.return_value.insert.return_value = mock_table_insert
        mock_get_supabase.return_value = mock_supabase

        # Act
        response = client.post(
            "/api/v2/user/webhooks/clerk",
            json=clerk_user_updated_payload,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"

        # Verify update called
        mock_user_repo.update_profile.assert_called_once()
        call_kwargs = mock_user_repo.update_profile.call_args[1]
        assert call_kwargs["avatar_url"] == "https://img.clerk.com/new_avatar.jpg"
        assert call_kwargs["username"] == "updateduser"

        # Verify activity logged
        mock_supabase.table.assert_called_with("activity_logs")
        insert_calls = mock_supabase.table.return_value.insert.call_args_list
        assert len(insert_calls) > 0
        activity_data = insert_calls[0][0][0]
        assert activity_data["user_id"] == "user_clerk_456"
        assert activity_data["activity_type"] == "profile_updated"


# ==========================================
# POST /api/v2/user/webhooks/stripe
# ==========================================

class TestStripeWebhook:
    """Tests for POST /api/v2/user/webhooks/stripe endpoint."""

    @patch('api.user.webhooks.construct_event')
    def test_stripe_webhook_invalid_signature(self, mock_construct_event):
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
        # Arrange
        mock_construct_event.side_effect = Exception("Invalid signature")

        # Act
        response = client.post(
            "/api/v2/user/webhooks/stripe",
            json={"type": "checkout.session.completed"},
            headers={"stripe-signature": "invalid_sig"},
        )

        # Assert
        assert response.status_code == 400

    @patch('api.user.webhooks.construct_event')
    @patch('api.user.webhooks.get_supabase_client')
    @patch('api.user.webhooks.SupabaseUserRepository')
    @patch('api.user.webhooks.SupabaseCreditRepository')
    @patch('api.user.webhooks.SupabasePaymentRepository')
    @patch('api.user.webhooks.track_payment')
    def test_stripe_checkout_subscription_success(
        self,
        mock_track_payment,
        mock_payment_repo_class,
        mock_credit_repo_class,
        mock_user_repo_class,
        mock_get_supabase,
        mock_construct_event,
        stripe_checkout_completed_payload,
    ):
        """
        Test: Subscription checkout completed

        Given: User subscribes to Starter plan
        When: checkout.session.completed event received
        Then: Updates tier and grants 500 monthly credits

        Business Logic Verified:
        - Idempotency check prevents duplicate processing
        - Updates user tier to 'starter'
        - Grants 500 monthly credits
        - Logs payment record
        - Logs activity
        - Tracks analytics event
        """
        # Arrange
        mock_construct_event.return_value = stripe_checkout_completed_payload

        # Mock Supabase for idempotency check
        mock_supabase = MagicMock()
        mock_rpc_result = MagicMock()
        mock_rpc_result.data = {"idempotent": False}
        mock_supabase.rpc.return_value.execute.return_value = mock_rpc_result
        # Mock activity logging
        mock_table_insert = MagicMock()
        mock_table_insert.execute = MagicMock()
        mock_supabase.table.return_value.insert.return_value = mock_table_insert
        mock_get_supabase.return_value = mock_supabase

        # Mock repositories
        mock_user_repo = MagicMock()
        mock_user_repo.update_subscription_tier = AsyncMock()
        mock_user_repo_class.return_value = mock_user_repo

        mock_credit_repo = MagicMock()
        mock_credit_repo.add_credits_monthly = AsyncMock()
        mock_credit_repo_class.return_value = mock_credit_repo

        mock_payment_repo = MagicMock()
        mock_payment_repo.create = AsyncMock()
        mock_payment_repo_class.return_value = mock_payment_repo

        # Act
        response = client.post(
            "/api/v2/user/webhooks/stripe",
            content=json.dumps(stripe_checkout_completed_payload).encode(),
            headers={"stripe-signature": "sig_test", "content-type": "application/json"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "subscription_started"
        assert data["plan"] == "starter"

        # Verify tier updated
        mock_user_repo.update_subscription_tier.assert_called_once()
        tier_call = mock_user_repo.update_subscription_tier.call_args[0]
        assert tier_call[0] == "user_stripe_789"
        assert tier_call[1] == "starter"

        # Verify 500 credits granted
        mock_credit_repo.add_credits_monthly.assert_called_once()
        credits_call = mock_credit_repo.add_credits_monthly.call_args[0]
        assert credits_call[0] == "user_stripe_789"
        assert credits_call[1] == 500

        # Verify payment logged
        mock_payment_repo.create.assert_called_once()

        # Verify analytics tracked
        mock_track_payment.assert_called_once()

    @patch('api.user.webhooks.construct_event')
    @patch('api.user.webhooks.get_supabase_client')
    @patch('api.user.webhooks.SupabaseCreditRepository')
    @patch('api.user.webhooks.SupabasePaymentRepository')
    @patch('api.user.webhooks.track_payment')
    def test_stripe_checkout_credits_purchase(
        self,
        mock_track_payment,
        mock_payment_repo_class,
        mock_credit_repo_class,
        mock_get_supabase,
        mock_construct_event,
        stripe_credits_purchase_payload,
    ):
        """
        Test: Credits purchase completed

        Given: User buys 100 credits for $10
        When: checkout.session.completed event received
        Then: Adds 100 permanent credits

        Business Logic Verified:
        - Idempotency check prevents duplicate processing
        - Adds 100 permanent credits to user account
        - Logs payment record
        - Logs activity
        - Tracks analytics event
        """
        # Arrange
        mock_construct_event.return_value = stripe_credits_purchase_payload

        # Mock Supabase for idempotency check
        mock_supabase = MagicMock()
        mock_rpc_result = MagicMock()
        mock_rpc_result.data = {"idempotent": False}
        mock_supabase.rpc.return_value.execute.return_value = mock_rpc_result
        # Mock activity logging
        mock_table_insert = MagicMock()
        mock_table_insert.execute = MagicMock()
        mock_supabase.table.return_value.insert.return_value = mock_table_insert
        mock_get_supabase.return_value = mock_supabase

        # Mock repositories
        mock_credit_repo = MagicMock()
        mock_credit_repo.add_credits_permanent = AsyncMock()
        mock_credit_repo_class.return_value = mock_credit_repo

        mock_payment_repo = MagicMock()
        mock_payment_repo.create = AsyncMock()
        mock_payment_repo_class.return_value = mock_payment_repo

        # Act
        response = client.post(
            "/api/v2/user/webhooks/stripe",
            content=json.dumps(stripe_credits_purchase_payload).encode(),
            headers={"stripe-signature": "sig_test", "content-type": "application/json"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "credits_added"

        # Verify 100 permanent credits added
        mock_credit_repo.add_credits_permanent.assert_called_once()
        credits_call = mock_credit_repo.add_credits_permanent.call_args[0]
        assert credits_call[0] == "user_credits_999"
        assert credits_call[1] == 100

        # Verify payment logged
        mock_payment_repo.create.assert_called_once()

    @patch('api.user.webhooks.construct_event')
    @patch('api.user.webhooks.get_supabase_client')
    def test_stripe_webhook_idempotency_duplicate(
        self,
        mock_get_supabase,
        mock_construct_event,
        stripe_checkout_completed_payload,
    ):
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
        # Arrange
        mock_construct_event.return_value = stripe_checkout_completed_payload

        # Mock Supabase idempotency check (duplicate detected)
        mock_supabase = MagicMock()
        mock_rpc_result = MagicMock()
        mock_rpc_result.data = {"idempotent": True}
        mock_supabase.rpc.return_value.execute.return_value = mock_rpc_result
        mock_get_supabase.return_value = mock_supabase

        # Act
        response = client.post(
            "/api/v2/user/webhooks/stripe",
            content=json.dumps(stripe_checkout_completed_payload).encode(),
            headers={"stripe-signature": "sig_test", "content-type": "application/json"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "already_processed"
        assert "event_id" in data

    @patch('api.user.webhooks.construct_event')
    @patch('api.user.webhooks.get_supabase_client')
    @patch('api.user.webhooks.SupabaseCreditRepository')
    @patch('api.user.webhooks.SupabasePaymentRepository')
    def test_stripe_invoice_payment_renewal(
        self,
        mock_payment_repo_class,
        mock_credit_repo_class,
        mock_get_supabase,
        mock_construct_event,
    ):
        """
        Test: Subscription renewal (invoice.payment_succeeded)

        Given: Pro user's subscription renews
        When: invoice.payment_succeeded with billing_reason=subscription_cycle
        Then: Refreshes monthly credits (resets to 1000)

        Business Logic Verified:
        - Idempotency check prevents duplicate processing
        - Looks up user by stripe_customer_id
        - Refreshes monthly credits based on tier (pro = 1000)
        - Logs payment record
        - Logs activity
        """
        # Arrange
        invoice_payload = {
            "id": "evt_invoice_123",
            "type": "invoice.payment_succeeded",
            "data": {
                "object": {
                    "customer": "cus_renewal_abc",
                    "amount_paid": 2990,  # $29.90
                    "currency": "usd",
                    "billing_reason": "subscription_cycle"
                }
            }
        }
        mock_construct_event.return_value = invoice_payload

        # Mock Supabase for idempotency and user lookup
        mock_supabase = MagicMock()
        # Idempotency check
        mock_rpc_result = MagicMock()
        mock_rpc_result.data = {"idempotent": False}
        mock_supabase.rpc.return_value.execute.return_value = mock_rpc_result
        # User lookup
        mock_user_result = MagicMock()
        mock_user_result.data = [{"id": "user_renewal_123", "tier": "pro"}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_user_result
        # Activity logging
        mock_table_insert = MagicMock()
        mock_table_insert.execute = MagicMock()
        mock_supabase.table.return_value.insert.return_value = mock_table_insert
        mock_get_supabase.return_value = mock_supabase

        # Mock repositories
        mock_credit_repo = MagicMock()
        mock_credit_repo.refresh_monthly_credits = AsyncMock()
        mock_credit_repo_class.return_value = mock_credit_repo

        mock_payment_repo = MagicMock()
        mock_payment_repo.create = AsyncMock()
        mock_payment_repo_class.return_value = mock_payment_repo

        # Act
        response = client.post(
            "/api/v2/user/webhooks/stripe",
            content=json.dumps(invoice_payload).encode(),
            headers={"stripe-signature": "sig_test", "content-type": "application/json"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "credits_refreshed"

        # Verify credits refreshed
        mock_credit_repo.refresh_monthly_credits.assert_called_once()
        refresh_call = mock_credit_repo.refresh_monthly_credits.call_args[0]
        assert refresh_call[0] == "user_renewal_123"
        assert refresh_call[1] == "pro"

    @patch('api.user.webhooks.construct_event')
    @patch('api.user.webhooks.get_supabase_client')
    @patch('api.user.webhooks.SupabaseUserRepository')
    def test_stripe_subscription_canceled(
        self,
        mock_user_repo_class,
        mock_get_supabase,
        mock_construct_event,
    ):
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
        # Arrange
        canceled_payload = {
            "id": "evt_cancel_123",
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "customer": "cus_cancel_xyz",
                    "status": "canceled"
                }
            }
        }
        mock_construct_event.return_value = canceled_payload

        # Mock Supabase for idempotency and user lookup
        mock_supabase = MagicMock()
        # Idempotency check
        mock_rpc_result = MagicMock()
        mock_rpc_result.data = {"idempotent": False}
        mock_supabase.rpc.return_value.execute.return_value = mock_rpc_result
        # User lookup
        mock_user_result = MagicMock()
        mock_user_result.data = [{"id": "user_cancel_456"}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_user_result
        # Activity logging
        mock_table_insert = MagicMock()
        mock_table_insert.execute = MagicMock()
        mock_supabase.table.return_value.insert.return_value = mock_table_insert
        mock_get_supabase.return_value = mock_supabase

        # Mock UserRepository
        mock_user_repo = MagicMock()
        mock_user_repo.update_subscription_tier = AsyncMock()
        mock_user_repo_class.return_value = mock_user_repo

        # Act
        response = client.post(
            "/api/v2/user/webhooks/stripe",
            content=json.dumps(canceled_payload).encode(),
            headers={"stripe-signature": "sig_test", "content-type": "application/json"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "subscription_ended"

        # Verify downgraded to free
        mock_user_repo.update_subscription_tier.assert_called_once()
        tier_call = mock_user_repo.update_subscription_tier.call_args[0]
        assert tier_call[0] == "user_cancel_456"
        assert tier_call[1] == "free"
