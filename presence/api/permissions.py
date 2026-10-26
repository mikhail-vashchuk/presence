import hmac

from django.conf import settings

from rest_framework.permissions import BasePermission


class HasAssistantServiceToken(BasePermission):
    def has_permission(self, request, view):
        expected = settings.ASSISTANT_SERVICE_TOKEN

        if not expected:
            return False

        scheme, _, token = (
            request.headers.get("Authorization", "").partition(" ")
        )

        return (
            scheme == "Bearer"
            and hmac.compare_digest(token, expected)
        )
