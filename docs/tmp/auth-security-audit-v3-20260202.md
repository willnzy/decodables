# Auth Security Audit v3 — Final Corrected Report

**Date**: 2026-02-02
**Auditor**: Claude Opus 4.5
**Scope**: Self-hosted auth system (replaced Clerk) — all backend + frontend auth code
**Method**: Line-by-line code review + cross-reference verification of every finding

## Audit Methodology

This is the **third and final pass**. Every finding from v1/v2 was cross-referenced against the actual code execution paths. False positives and severity overestimates from earlier passes have been corrected.

**Changes from v2:**
- **Removed 3 false positives**: C4 (register binding), H2 (dual-key expired), M13 (redirect bypass)
- **Downgraded 6 issues**: C2→HIGH, C3→MEDIUM, C5→MEDIUM, C6→HIGH, H4→LOW, M6→LOW
- **Added 1 new issue**: dependencies.py error message leakage
- **Merged**: C6 + H9 into one issue (same root cause)

---

## Summary

| Severity | Count | Change from v2 |
|----------|-------|----------------|
| CRITICAL | 2 | ↓ from 6 (4 downgraded/removed) |
| HIGH | 8 | ↓ from 13 (adjusted) |
| MEDIUM | 14 | adjusted |
| LOW | 10 | adjusted |
| **Total** | **34** | ↓ from 50 (16 removed/merged) |

---

## CRITICAL Issues (2)

### C1: OTP Hash Comparison Vulnerable to Timing Attack

**Status**: CONFIRMED
**Files**: `domains/auth/service.py` lines 259, 675, 793
**Risk**: Theoretical — mitigated by 5-attempt limit and 10-min OTP expiry

Three locations use Python `!=` for OTP hash comparison:

```python
# Line 259 - verify_registration_otp
if input_hash != auth_user.otp_code_hash:

# Line 675 - verify_authenticated_otp
if input_hash != auth_user.otp_code_hash:

# Line 793 - verify_password_reset_otp
if input_hash != auth_user.otp_code_hash:
```

**Why CRITICAL**: Timing attacks on string comparison are a well-documented vulnerability class. Even with mitigations (5-attempt limit, 10-min expiry), the fix is trivial (`hmac.compare_digest`) and there's no reason not to apply it.

**Fix**: Replace all 3 with `hmac.compare_digest(input_hash, auth_user.otp_code_hash or "")`.

---

### C2: Cookie Path Breaks Middleware Auth Detection (H10 in v2, promoted)

**Status**: CONFIRMED — most impactful real-world bug
**File**: `decodables-fe/app/api/auth/[...action]/route.ts` line 104
**Impact**: Middleware route protection is completely non-functional

```typescript
res.cookies.set(REFRESH_COOKIE_NAME, newRefreshToken, {
  httpOnly: true,
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'lax',
  path: '/api/auth',    // ← BUG: cookie only sent on /api/auth/* routes
  maxAge: REFRESH_COOKIE_MAX_AGE,
})
```

**Root cause**: `path: '/api/auth'` means `middleware.ts:77` (`req.cookies.has('refresh_token')`) **always returns false** on page routes like `/dashboard`, `/editor`, etc. This means:
- Logged-in users visiting `/login` are NOT redirected to `/dashboard`
- Unauthenticated users accessing `/dashboard` are NOT redirected to `/login`
- The middleware is entirely decorative

**Why promoted to CRITICAL**: This affects every user session. Middleware protection is the primary frontend auth gate.

**Fix**: Change `path: '/api/auth'` to `path: '/'`.

---

## HIGH Issues (8)

### H1: X-Forwarded-For Header Trusted Without Proxy Validation

**Status**: CONFIRMED
**Files**: `api/auth/router.py` lines 100-107, `route.ts` lines 65-66
**Impact**: Rate limiting can be bypassed by spoofing X-Forwarded-For

Backend blindly trusts X-Forwarded-For:
```python
def _get_client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()  # Attacker controls this
```

BFF also forwards it:
```typescript
...(req.headers.get('x-forwarded-for')
  ? { 'X-Forwarded-For': req.headers.get('x-forwarded-for')! }
  : {}),
```

**Fix**: Configure trusted proxy hops or use Railway/Vercel's real client IP header.

---

### H2: JWT Role/Tier Hardcoded in Access Token

**Status**: CONFIRMED but impact limited
**File**: `domains/auth/service.py` lines 522-523, 1104-1105, 1132-1133
**Impact**: Frontend displays wrong tier/role until `/user/me` data loads

```python
access_token = self._token_svc.create_access_token(
    user_id=user.id, email=user.email,
    role="user",   # TODO: get from profile
    tier="t1",     # TODO: get from profile
)
```

**Why HIGH not CRITICAL**: No backend authorization decisions use JWT role/tier. Only `payload.sub` (user_id) is used in `dependencies.py` and `get_current_auth_user_id()`. Frontend `useUser.ts` falls back to `useUserStore` data (from `/user/me`). The JWT values are only used as temporary fallback before store loads.

**Fix**: Fetch actual tier/role from user profile when creating the token.

---

### H3: No CSRF Protection on BFF Proxy

**Status**: CONFIRMED
**File**: `decodables-fe/app/api/auth/[...action]/route.ts`
**Impact**: State-changing POST requests lack CSRF tokens

The BFF proxy accepts POST requests with no CSRF validation. While `sameSite: 'lax'` on the cookie provides partial protection (blocks cross-origin POST from `<form>`), it doesn't protect against:
- Same-site subdomain attacks
- GET→POST conversion attacks

**Fix**: Add custom header check (`X-Requested-With: XMLHttpRequest`) or CSRF token.

---

### H4: Logout Endpoint Has No Rate Limit

**Status**: CONFIRMED
**File**: `api/auth/router.py` lines 332-339
**Impact**: Potential for mass session revocation abuse

```python
@router.post("/logout", response_model=SuccessResponse)
async def logout(
    body: LogoutRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
```

No `@limiter.limit()` and no auth dependency. Similarly, `logout-all` (line 519) and `sessions` endpoints (lines 529, 542) also lack rate limits.

**Fix**: Add rate limits. For `logout`, add `@limiter.limit("10/minute")`.

---

### H5: LoginRequest.password Has No max_length

**Status**: CONFIRMED
**File**: `api/auth/schemas.py` line 54
**Impact**: Argon2id DoS — sending a 1MB+ password causes CPU-intensive hashing

```python
class LoginRequest(BaseModel):
    email: EmailStr
    password: str  # No max_length!
```

Compare with `CompleteRegistrationRequest` (line 42) which correctly has `max_length=128`.

**Fix**: Add `password: str = Field(..., min_length=1, max_length=128)`.

---

### H6: Purpose Token No Dual-Key Fallback

**Status**: CONFIRMED
**File**: `domains/auth/token_service.py` lines 324-334
**Impact**: During JWT secret rotation, all in-flight purpose tokens fail

```python
def verify_purpose_token(self, token, expected_purpose):
    payload = jwt.decode(
        token, self._jwt_secret,  # Only current key, no fallback to old key
        algorithms=[ACCESS_TOKEN_ALGORITHM],
    )
```

While `verify_access_token` and `_decode_jwt` support dual-key fallback, `verify_purpose_token` does not. During key rotation, users in the middle of registration/password-reset would fail.

**Fix**: Add `_jwt_secret_old` fallback similar to `_decode_jwt`.

---

### H7: localStorage Token Persistence (Cross-Tab Sync Fallback)

**Status**: CONFIRMED
**File**: `decodables-fe/lib/auth/tokenManager.ts` line 329
**Impact**: Access token persisted in localStorage, never cleaned up

```typescript
// Fallback: localStorage (triggers 'storage' event in other tabs)
localStorage.setItem(AUTH_SYNC_STORAGE_KEY, JSON.stringify(message))
// message = { type, token, timestamp } — token in plaintext
```

BroadcastChannel itself is same-origin (not a cross-origin leak — corrected from v2's C6). But the localStorage fallback persists the access token as plaintext, surviving browser restarts and available to any XSS.

**Fix**: Clear localStorage entry after use, or use `sessionStorage`. Or remove plaintext token from the localStorage fallback message.

---

### H8: Server-Side Auth Uses NEXT_PUBLIC URL

**Status**: CONFIRMED
**File**: `decodables-fe/lib/auth/server.ts` line ~8
**Impact**: Backend internal URL exposed in client-side JavaScript bundle

`NEXT_PUBLIC_API_BASE_URL` is used for server-side calls but is also included in client bundles (Next.js exposes all `NEXT_PUBLIC_*` vars to client). This reveals the internal backend service URL.

**Fix**: Use a non-prefixed env var (e.g., `API_BASE_URL`) for server-side code.

---

## MEDIUM Issues (14)

### M1: BFF Proxy No Action Whitelist

**Status**: CONFIRMED but lower risk than initially assessed
**File**: `route.ts` line 33, 56
**Impact**: Arbitrary backend paths can be probed via the BFF

```typescript
const action = actionParts.join('/')
const backendUrl = `${BACKEND_URL}/api/v2/auth/${action}`
```

**Why MEDIUM not CRITICAL**: Next.js normalizes paths (prevents `../` traversal), and FastAPI only responds to defined routes. But it still allows probing any `/api/v2/auth/*` path.

**Fix**: Add `const ALLOWED_ACTIONS = new Set([...])` whitelist.

---

### M2: Password Reset OTP Not Cleared on Verify

**Status**: CONFIRMED but window is narrow
**File**: `domains/auth/service.py` lines 807-811
**Impact**: OTP remains valid between verify and password reset calls

`verify_password_reset_otp` does NOT call `clear_otp()` (unlike `verify_authenticated_otp` at line 690 which does). However, `reset_password` → `update_password` at `auth_user_repository.py:296-315` DOES clear OTP fields.

**Window**: Only between `verify_password_reset_otp` and `reset_password` calls. During this window, the same OTP could theoretically be re-verified to get another `otp_verified_token`. But each token is 10-min expiry and tied to purpose.

**Fix**: Add `await self._auth_user_repo.clear_otp(auth_user.id)` after successful verify in `verify_password_reset_otp`.

---

### M3: Account Lockout Has No Auto-Unlock

**Status**: CONFIRMED
**File**: `domains/auth/service.py` (login logic, `domains/auth/auth_user.py`)
**Impact**: Locked accounts stay locked forever unless manually unlocked

After `LOGIN_MAX_FAILED_ATTEMPTS` (10) failures, the account is locked. There is no TTL-based auto-unlock mechanism.

**Fix**: Add `locked_until` timestamp with configurable unlock duration (e.g., 30 min).

---

### M4: Refresh Token Stored as SHA-256 Hash

**Status**: CONFIRMED — design note, not urgent
**File**: `domains/auth/token_service.py` `hash_token` method
**Impact**: SHA-256 is fast; if DB is leaked, tokens can be brute-forced

Refresh tokens are 256-bit random (URL-safe), stored as SHA-256 hash. Given the high entropy of the token (256 bits), brute-forcing is infeasible even with SHA-256. This is a theoretical concern only.

**Fix**: Consider bcrypt/Argon2 for token hashing if defense-in-depth is desired. Low priority given token entropy.

---

### M5: OTP Code Only 6 Digits (Numeric)

**Status**: CONFIRMED
**File**: `domains/auth/token_service.py` OTP generation
**Impact**: 1M possibilities, but mitigated by 5-attempt limit and 10-min expiry

6-digit numeric OTPs are industry standard (Google, Stripe, etc.). The 5-attempt limit makes brute-forcing infeasible (0.0005% chance). This is informational.

**Fix**: No change needed. Current mitigations are sufficient.

---

### M6: Rate Limit String Exposed in 429 Response

**Status**: CONFIRMED
**File**: `infrastructure/rate_limiter.py` line 135
**Impact**: Information disclosure — reveals exact rate limit configuration

```python
detail=f"Rate limit exceeded. Please try again later. (Limit: {limit_string})",
```

**Fix**: Remove the `(Limit: {limit_string})` suffix from the error message.

---

### M7: No Session Binding to IP/Device

**Status**: CONFIRMED — design limitation
**File**: `domains/auth/service.py` refresh flow
**Impact**: Stolen refresh token usable from any device

Session stores `device_name` and `ip_address` but doesn't validate them on refresh. A stolen refresh token cookie works from any network/device.

**Fix**: Optional IP/device fingerprint validation on refresh with configurable strictness.

---

### M8: Registration Email Enumeration via Timing

**Status**: CONFIRMED
**File**: `domains/auth/service.py` `send_registration_otp`
**Impact**: Slight timing difference between existing vs new email

Unlike `send_password_reset_otp` which always returns success, `send_registration_otp` raises `EmailAlreadyRegisteredException` for existing accounts. This is a conscious design choice (the user needs to know the email is taken), but it does enable enumeration.

**Fix**: Accept as designed — registration inherently reveals if email exists. The forgot-password flow correctly prevents enumeration.

---

### M9: BFF Error Logging Leaks Backend Info

**Status**: CONFIRMED
**File**: `route.ts` line 76
**Impact**: Backend error details in server logs

```typescript
console.error(`[BFF Auth] Failed to reach backend: ${error}`)
```

In production, this could log full error objects including stack traces. Not a direct vulnerability but poor log hygiene.

**Fix**: Log only `error.message` or a sanitized version.

---

### M10: Email Regex in Value Objects No TLD Check

**Status**: CONFIRMED but mitigated at API layer
**File**: `domains/auth/value_objects.py` Email class
**Impact**: None in practice — Pydantic `EmailStr` in schemas validates TLD

The domain layer's Email value object uses a regex that doesn't enforce TLD. But all API endpoints use `EmailStr` (which does check TLD) before data reaches the domain layer.

**Fix**: Low priority. Could add TLD check to Email value object for defense in depth.

---

### M11: Logout Does Not Require Authentication

**Status**: CONFIRMED — by design
**File**: `api/auth/router.py` lines 332-339
**Impact**: Anyone with a refresh token can revoke it

The logout endpoint accepts a refresh token in body (injected by BFF from httpOnly cookie). It has no JWT auth requirement. This is intentional — logout should work even if access token is expired.

**Fix**: Add rate limiting (see H4). The design is acceptable.

---

### M12: No Content-Security-Policy Headers

**Status**: CONFIRMED
**File**: Next.js configuration
**Impact**: XSS protection relies solely on React's built-in escaping

No CSP headers are set to restrict script sources, preventing XSS exploitation.

**Fix**: Add CSP headers via `next.config.js` or middleware.

---

### M13: Session `revoke_reason` Missing from Constants

**Status**: CONFIRMED
**File**: `domains/auth/constants.py` `VALID_REVOKE_REASONS`
**Impact**: Minor — hardcoded string in `session.py:176`

`session_limit_exceeded` is used as a revoke reason but not defined in `VALID_REVOKE_REASONS`.

**Fix**: Add to constants.

---

### M14: ChangePasswordRequest.current_password No max_length

**Status**: CONFIRMED
**File**: `api/auth/schemas.py` line 117
**Impact**: Same Argon2 DoS risk as H5 but requires authentication

```python
class ChangePasswordRequest(BaseModel):
    otp_verified_token: str
    current_password: str  # No max_length
    new_password: str = Field(..., min_length=8, max_length=128)
```

**Fix**: Add `current_password: str = Field(..., min_length=1, max_length=128)`.

---

## LOW Issues (10)

### L1: Access Token 15-min Lifetime May Be Long

**Status**: Info
**File**: `domains/auth/constants.py`
**Note**: 15 minutes is standard. Some high-security apps use 5 min. Current value is acceptable.

### L2: `emailVerified: true` Hardcoded in useUser.ts

**Status**: CONFIRMED
**File**: `decodables-fe/lib/auth/useUser.ts` line 43
**Note**: Comment says "if they have a valid token, email status comes from /user/me". Acceptable for now but should eventually reflect actual verification state.

### L3: Token Refresh Grace Period 30s

**Status**: Info
**File**: `domains/auth/constants.py` `REFRESH_TOKEN_GRACE_PERIOD_SECONDS = 30`
**Note**: 30-second grace period for token rotation is standard. Allows for network latency.

### L4: No Audit Logging for Security Events

**Status**: CONFIRMED
**File**: Various — no structured security event logging
**Note**: Login failures, password changes, account deletions should be logged to a security audit table.

### L5: Registration Bonus Credits Not Idempotent

**Status**: CONFIRMED
**File**: `api/auth/router.py` line 250 → `service.py` `complete_registration`
**Note**: If registration completes twice (race condition), bonus credits could be doubled. Low risk due to purpose token single-use.

### L6: Session TOCTOU in Limit Check

**Status**: CONFIRMED — benign
**File**: `domains/auth/service.py` session creation
**Note**: Check-then-act for session limit could allow 1-2 extra sessions. Not a security issue.

### L7: dependencies.py Error Message Leakage

**Status**: CONFIRMED — NEW finding
**File**: `dependencies.py` line 64
**Impact**: Internal error details leaked to client

```python
except TokenInvalidException as e:
    raise UnauthorizedException(message=f"Invalid token: {e.message}")
```

The `e.message` from `TokenInvalidException` may contain internal details (e.g., "Invalid token purpose", "Malformed token payload"). These should not be exposed to the client.

**Fix**: Use a generic message: `raise UnauthorizedException(message="Invalid token")`.

### L8: container.py JWT Secret Empty String Fallback

**Status**: CONFIRMED — mitigated by startup validation
**File**: `container.py` line 306

```python
jwt_secret = getattr(config, 'AUTH_JWT_SECRET', None) or ''
```

Falls back to empty string if config attribute is missing. However, `config.py:validate_secrets_at_startup()` validates JWT secret length ≥ 43 chars, so this can't happen in production.

**Fix**: Low priority. Could raise an error instead of defaulting to empty string.

### L9: config.py Logs JWT Secret Length in Error

**Status**: CONFIRMED
**File**: `config.py` lines 96-98

```python
raise ValueError(
    f"AUTH_JWT_SECRET too short: {len(AUTH_JWT_SECRET)} chars, "
    f"minimum 43 required (256-bit key as base64)"
)
```

Logging the actual length of the secret could aid an attacker in narrowing the keyspace. Minor concern.

**Fix**: Change to "AUTH_JWT_SECRET too short, minimum 43 chars required".

### L10: BFF proxy console.error in production

**Status**: CONFIRMED
**File**: `route.ts` line 76 (overlaps with M9)
**Note**: Should use structured logging in production, not console.error.

---

## False Positives Removed (from v1/v2)

| ID | Original Claim | Why False Positive |
|----|---------------|-------------------|
| C4 (v1) | Registration step 2→3 no crypto binding | `router.py:190-194` creates purpose JWT with `create_purpose_token`, `router.py:225-228` verifies it |
| H2 (v2) | Dual-key expired token handling broken | `jwt.ExpiredSignatureError` is correct — expired tokens SHOULD be rejected. `jwt.InvalidSignatureError` (different exception) allows fallback to old key |
| M13 (v2) | Login redirect bypass via `javascript:` | `router.push()` is client-side Next.js navigation, not browser redirect. Cannot execute `javascript:` URLs |
| M14 (v2) | Client-side JWT decode without verification | Standard practice — client decodes for display only, all authorization happens server-side |

---

## Priority Fix Order

### Phase 1 — Immediate (Critical + Quick Wins)

1. **C2**: Change cookie `path: '/api/auth'` → `path: '/'` (1 line fix, biggest user impact)
2. **C1**: Replace `!=` with `hmac.compare_digest` in 3 locations
3. **H5**: Add `max_length=128` to `LoginRequest.password`
4. **M14**: Add `max_length=128` to `ChangePasswordRequest.current_password`

### Phase 2 — Important (HIGH)

5. **H1**: Fix X-Forwarded-For trust (use platform-specific client IP header)
6. **H2**: Fetch real role/tier when creating access tokens
7. **H3**: Add CSRF protection (custom header check)
8. **H4**: Add rate limits to logout/sessions endpoints
9. **H6**: Add dual-key fallback to `verify_purpose_token`
10. **H7**: Fix localStorage token persistence (clear after use)
11. **H8**: Use non-NEXT_PUBLIC env var for server-side auth

### Phase 3 — Hardening (MEDIUM + LOW)

12. **M1**: Add BFF action whitelist
13. **M2**: Clear OTP in `verify_password_reset_otp`
14. **M3**: Add auto-unlock for locked accounts
15. **M6**: Remove rate limit string from 429 response
16. **M12**: Add CSP headers
17. **L7**: Sanitize error messages in dependencies.py
18. Remaining LOW issues

---

## Architecture Assessment

**Strengths:**
- DDD architecture with clean separation of concerns
- Purpose tokens (JWT) for multi-step flow binding — well designed
- Argon2id for password hashing (OWASP 2024 recommended)
- Refresh token rotation with family-based reuse detection
- Anti-enumeration in forgot-password flow
- Rate limiting on all sensitive endpoints (except logout/sessions)
- BFF proxy correctly strips refresh token from client response

**Weaknesses:**
- Cookie path misconfiguration renders middleware useless (C2)
- No CSRF protection
- X-Forwarded-For trust model inappropriate for public-facing service
- localStorage fallback leaks token
- Some schema validation gaps (password max_length)

**Overall**: The auth system is architecturally sound. The critical issues are implementation bugs (cookie path, timing comparison) rather than design flaws. The priority fixes are mostly 1-line changes with outsized impact.
