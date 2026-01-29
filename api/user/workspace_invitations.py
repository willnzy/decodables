"""
Workspace Invitations Router - User-scoped invitation endpoints (v3.33 Phase 5)

@module api.user.workspace_invitations
@version 1.0.0

Endpoints:
- GET  /api/v2/user/invitations           - List pending invitations for current user
- POST /api/v2/user/invitations/{id}/accept  - Accept an invitation
- POST /api/v2/user/invitations/{id}/decline - Decline an invitation
"""

import re

from fastapi import APIRouter, Request, Depends, HTTPException

from domains.identity.aggregates.user_profile import UserProfile
from infrastructure.logging.activity_logger import log_activity_async
from infrastructure.rate_limiter import limiter
from dependencies import get_current_user
from container import get_container

router = APIRouter(prefix="/invitations", tags=["workspace-invitations-v1"])

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def validate_uuid(value: str, field_name: str = "ID") -> None:
    if not UUID_PATTERN.match(value):
        raise HTTPException(400, f"Invalid {field_name} format")


@router.get("")
@limiter.limit("30/minute")
async def list_my_invitations(
    request: Request,
    user: UserProfile = Depends(get_current_user),
):
    """
    List all pending invitations for the current user.

    Returns invitations sent to the user's email address.
    """
    container = get_container()
    member_service = await container.get_member_service()

    user_email = getattr(user, "email", None)
    if not user_email:
        return {"items": [], "total": 0}

    invitations = await member_service.get_user_invitations(user_email)

    # Enrich with workspace name
    workspace_service = await container.get_workspace_service()
    enriched = []
    for inv in invitations:
        inv_dict = inv.to_dict()
        workspace = await workspace_service.get_by_id(inv.workspace_id)
        inv_dict["workspace_name"] = workspace.name if workspace else "Unknown"
        enriched.append(inv_dict)

    return {
        "items": enriched,
        "total": len(enriched),
    }


@router.post("/{invitation_id}/accept")
@limiter.limit("10/minute")
async def accept_invitation(
    request: Request,
    invitation_id: str,
    user: UserProfile = Depends(get_current_user),
):
    """
    Accept a workspace invitation.

    The user's email must match the invitation's invited_email.
    """
    validate_uuid(invitation_id, "invitation_id")

    user_email = getattr(user, "email", None)
    if not user_email:
        raise HTTPException(400, "User email not available")

    container = get_container()
    member_service = await container.get_member_service()

    try:
        member = await member_service.accept_invitation(
            invitation_id=invitation_id,
            user_id=user.user_id,
            user_email=user_email,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    await log_activity_async(
        user_id=user.user_id,
        action="workspace_invitation_accepted",
        metadata={
            "invitation_id": invitation_id,
            "workspace_id": member.workspace_id,
        },
    )

    return member.to_dict()


@router.post("/{invitation_id}/decline")
@limiter.limit("10/minute")
async def decline_invitation(
    request: Request,
    invitation_id: str,
    user: UserProfile = Depends(get_current_user),
):
    """
    Decline a workspace invitation.
    """
    validate_uuid(invitation_id, "invitation_id")

    user_email = getattr(user, "email", None)
    if not user_email:
        raise HTTPException(400, "User email not available")

    container = get_container()
    member_service = await container.get_member_service()

    try:
        await member_service.decline_invitation(
            invitation_id=invitation_id,
            user_email=user_email,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    await log_activity_async(
        user_id=user.user_id,
        action="workspace_invitation_declined",
        metadata={"invitation_id": invitation_id},
    )

    return {"success": True, "message": "Invitation declined"}
