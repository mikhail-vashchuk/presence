from rest_framework import serializers

from presence.models import (
    Invitation,
    Moment,
    Response,
)


class CreateInvitationSerializer(serializers.Serializer):
    gesture = serializers.CharField()


class SendResponseSerializer(serializers.Serializer):
    words = serializers.CharField()


class InvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = [
            "id",
            "gesture",
        ]


class ReadResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Response
        fields = [
            "id",
            "words",
        ]


class MomentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Moment
        fields = [
            "id",
            "media_room_id",
        ]


class CurrentPresenceSerializer(serializers.Serializer):
    state = serializers.ChoiceField(
        choices=[
            "idle",
            "invitation",
            "response",
            "moment",
        ],
    )

    invitation = InvitationSerializer(
        required=False,
    )

    responses = ReadResponseSerializer(
        many=True,
        required=False,
    )

    response = ReadResponseSerializer(
        required=False,
    )

    moment = MomentSerializer(
        required=False,
    )
