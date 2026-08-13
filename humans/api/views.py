from django.contrib.auth import login
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status
from rest_framework.exceptions import ValidationError as APIValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from humans.api.serializers import (
    CompleteRegistrationSerializer,
    EmailSerializer,
    VerificationCodeSerializer,
)
from humans.services import (
    complete_registration,
    start_registration,
    verify_registration_code,
)


class StartRegistrationView(APIView):
    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            verification = start_registration(
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
        except DjangoValidationError as error:
            raise APIValidationError(
                {"detail": error.messages}
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
        except DjangoValidationError as error:
            raise APIValidationError(
                {"detail": error.messages}
            ) from error

        login(request, human.user)

        return Response(
            {
                "human_id": human.pk,
            },
            status=status.HTTP_201_CREATED,
        )