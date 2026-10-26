from rest_framework import serializers

from presence.models import (
    AssistantFeedback,
    AssistantHint,
    Invitation,
    Moment,
    Response,
)


class CreateInvitationSerializer(serializers.Serializer):
    gesture = serializers.CharField()


class SendResponseSerializer(serializers.Serializer):
    words = serializers.CharField()


class AgentConsentSerializer(serializers.Serializer):
    consent = serializers.BooleanField()


class AssistantFeedbackSerializer(serializers.Serializer):
    rating = serializers.ChoiceField(
        choices=AssistantFeedback.Rating.choices,
    )


class RecordAssistantHintSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(
        choices=AssistantHint.Kind.choices,
    )


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


class AssistantStateSerializer(serializers.Serializer):
    consent = serializers.BooleanField()
    invited = serializers.BooleanField()
    active = serializers.BooleanField()


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

    assistant = AssistantStateSerializer(
        required=False,
    )
