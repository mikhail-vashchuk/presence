from rest_framework import serializers

from humans.models import Human


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


class CurrentHumanSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    class Meta:
        model = Human
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
        )