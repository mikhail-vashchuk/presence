from rest_framework import serializers


class CreateInvitationSerializer(serializers.Serializer):
    gesture = serializers.CharField()


class SendResponseSerializer(serializers.Serializer):
    words = serializers.CharField()
