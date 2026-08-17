from django.contrib.auth import login, logout

from rest_framework import status
from rest_framework.exceptions import (
    NotFound,
    ValidationError as APIValidationError,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.api.serializers import (
    EmailSerializer,
    VerificationCodeSerializer,
)
from accounts.exceptions import (
    EmailNotRegistered,
    InvalidVerificationCode,
    VerificationAlreadyUsed,
    VerificationAttemptsExceeded,
    VerificationExpired,
    VerificationNotFound,
    VerificationPurposeMismatch,
    VerificationUserNotFound,
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
        except EmailNotRegistered as error:
            raise APIValidationError(
                {
                    "detail": "Email is not registered",
                }
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

        except VerificationNotFound as error:
            raise NotFound(
                {
                    "detail": "Verification does not exist",
                }
            ) from error

        except VerificationPurposeMismatch as error:
            raise APIValidationError(
                {
                    "detail": "Verification cannot be used for login",
                }
            ) from error

        except VerificationExpired as error:
            raise APIValidationError(
                {
                    "detail": "Verification code has expired",
                }
            ) from error

        except VerificationAlreadyUsed as error:
            raise APIValidationError(
                {
                    "detail": "Verification has already been used",
                }
            ) from error

        except VerificationAttemptsExceeded as error:
            raise APIValidationError(
                {
                    "detail": "Too many failed verification attempts",
                }
            ) from error

        except InvalidVerificationCode as error:
            raise APIValidationError(
                {
                    "detail": "Invalid verification code",
                }
            ) from error

        except VerificationUserNotFound as error:
            raise NotFound(
                {
                    "detail": "User does not exist",
                }
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