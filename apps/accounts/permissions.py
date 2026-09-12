from rest_framework import permissions

from .models import AuthorityType

LAW_ENFORCEMENT_TYPES = {
    AuthorityType.POLICE,
    AuthorityType.RAB,
    AuthorityType.ARMY,
    AuthorityType.GOVT_EMPLOYEE,
}


class IsLawEnforcement(permissions.BasePermission):
    """
    Restricts a view to verified authority users whose authority_type is one
    of the law-enforcement types (police/RAB/army/govt employee). Morgue
    authorities are found-person reporters, not case reviewers, so they're
    intentionally excluded here.
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_verified
            and user.authority_type in LAW_ENFORCEMENT_TYPES
        )
