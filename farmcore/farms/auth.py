from uuid import UUID

from django.contrib.auth.models import User
from rest_framework.exceptions import NotAuthenticated, PermissionDenied

from farms.models import Farm, FarmMembership, FarmRole


class Principal:
    """Authenticated caller with active farm context from the session."""

    def __init__(
        self,
        *,
        user: User,
        farm: Farm,
        role: str,
        allowed_document_ids: frozenset[UUID] | None = None,
    ) -> None:
        self.user = user
        self.farm = farm
        self.role = role
        self.allowed_document_ids = allowed_document_ids


def resolve_principal(request) -> Principal:
    if not request.user or not request.user.is_authenticated:
        raise NotAuthenticated(
            detail={"code": "authentication_failed", "message": "Authentication required."}
        )

    farm_id = request.session.get("active_farm_id")
    if not farm_id:
        raise PermissionDenied(
            detail={"code": "no_active_farm", "message": "Select an active farm in your session."}
        )

    try:
        membership = FarmMembership.objects.select_related("farm").get(
            user=request.user,
            farm_id=farm_id,
        )
    except FarmMembership.DoesNotExist:
        raise PermissionDenied(
            detail={"code": "permission_denied", "message": "You are not a member of the active farm."}
        )

    allowed_document_ids: frozenset[UUID] | None = None
    if membership.role == FarmRole.WORKER:
        # Phase 0: empty set is valid; Phase 9 populates task-linked docs.
        allowed_document_ids = frozenset()

    return Principal(
        user=request.user,
        farm=membership.farm,
        role=membership.role,
        allowed_document_ids=allowed_document_ids,
    )
