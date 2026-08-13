from rest_framework import serializers


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerificationCodeSerializer(serializers.Serializer):
    code = serializers.RegexField(
        regex=r"^\d{6}$",
    )


class CompleteRegistrationSerializer(serializers.Serializer):
    first_name = serializers.CharField(
        max_length=150,
    )
    last_name = serializers.CharField(
        max_length=150,
    )