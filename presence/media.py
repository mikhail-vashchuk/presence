import json
import logging
from datetime import timedelta

from asgiref.sync import async_to_sync

from django.conf import settings

from livekit import api


logger = logging.getLogger(__name__)


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


async def _create_assistant_dispatch(*, room_id, moment_id):
    async with api.LiveKitAPI(
            settings.LIVEKIT_URL,
            settings.LIVEKIT_API_KEY,
            settings.LIVEKIT_API_SECRET,
    ) as livekit:
        await livekit.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=settings.ASSISTANT_AGENT_NAME,
                room=room_id,
                metadata=json.dumps({"moment_id": moment_id}),
            )
        )


def dispatch_assistant(
        *,
        room_id,
        moment_id,
):
    try:
        async_to_sync(_create_assistant_dispatch)(
            room_id=room_id,
            moment_id=moment_id,
        )
    except Exception:
        logger.exception(
            "Could not dispatch the assistant to Moment %s",
            moment_id,
        )
