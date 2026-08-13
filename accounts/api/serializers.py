from rest_framework import serializers


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerificationCodeSerializer(serializers.Serializer):
    code = serializers.RegexField(
        regex=r"^\d{6}$",
    )