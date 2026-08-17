from django.contrib.auth import login

from rest_framework import status
from rest_framework.exceptions import (
    NotFound,
    ValidationError as APIValidationError,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.exceptions import (
    InvalidVerificationCode,
    VerificationAlreadyUsed,
    VerificationAttemptsExceeded,
    VerificationExpired,
    VerificationNotFound,
    VerificationPurposeMismatch,
)

from humans.exceptions import (
    EmailAlreadyRegistered,
    HumanNotFound,
    RegistrationNotVerified,
)
from humans.api.serializers import (
    CompleteRegistrationSerializer,
    EmailSerializer,
    VerificationCodeSerializer,
    CurrentHumanSerializer,
)
from humans.services import (
    complete_registration,
    start_registration,
    verify_registration_code,
    get_current_human,
)


class StartRegistrationView(APIView):
    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            verification = start_registration(
                email=serializer.validated_data["email"],
            )
        except EmailAlreadyRegistered as error:
            raise APIValidationError(
                {
                    "detail": "Email is already registered",
                }
            ) from error

        return Response(
            {
                "verification_id": verification.pk,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyRegistrationCodeView(APIView):
    def post(self, request, verification_id):
        serializer = VerificationCodeSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            verify_registration_code(
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
                    "detail": "Verification cannot be used for registration",
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

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )


class CompleteRegistrationView(APIView):
    def post(self, request, verification_id):
        serializer = CompleteRegistrationSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            human = complete_registration(
                verification_id=verification_id,
                first_name=serializer.validated_data["first_name"],
                last_name=serializer.validated_data["last_name"],
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
                    "detail": "Verification cannot be used for registration",
                }
            ) from error

        except RegistrationNotVerified as error:
            raise APIValidationError(
                {
                    "detail": "Email verification is incomplete",
                }
            ) from error

        except EmailAlreadyRegistered as error:
            raise APIValidationError(
                {
                    "detail": "Email is already registered",
                }
            ) from error

        login(request, human.user)

        return Response(
            {
                "human_id": human.pk,
            },
            status=status.HTTP_201_CREATED,
        )


class CurrentHumanView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            human = get_current_human(
                user_id=request.user.pk,
            )
        except HumanNotFound as error:
            raise NotFound(
                {
                    "detail": "Human does not exist",
                }
            ) from error

        serializer = CurrentHumanSerializer(human)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )