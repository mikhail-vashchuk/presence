from django.contrib.auth import login, logout
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status
from rest_framework.exceptions import ValidationError as APIValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.api.serializers import (
    EmailSerializer,
    VerificationCodeSerializer,
)
from accounts.services import (
    start_login,
    verify_login_code,
)


class StartLoginView(APIView):
    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            verification = start_login(
                email=serializer.validated_data["email"],
            )
        except DjangoValidationError as error:
            raise APIValidationError(
                {"detail": error.messages}
            ) from error

        return Response(
            {
                "verification_id": verification.pk,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyLoginCodeView(APIView):
    def post(self, request, verification_id):
        serializer = VerificationCodeSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            user = verify_login_code(
                verification_id=verification_id,
                code=serializer.validated_data["code"],
            )
        except DjangoValidationError as error:
            raise APIValidationError(
                {"detail": error.messages}
            ) from error

        login(request, user)

        return Response(
            {
                "user_id": user.pk,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )