from datetime import timedelta

from django.conf import settings

from livekit import api


def issue_media_access(
        *,
        room_id,
        participant_identity,
):
    token = (
        api.AccessToken(
            settings.LIVEKIT_API_KEY,
            settings.LIVEKIT_API_SECRET,
        )
        .with_identity(participant_identity)
        .with_ttl(
            timedelta(minutes=15),
        )
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_id,
                can_publish=True,
                can_subscribe=True,
            )
        )
        .to_jwt()
    )

    return {
        "server_url": settings.LIVEKIT_URL,
        "participant_token": token,
    }