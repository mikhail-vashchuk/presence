from presence.models import (
    Invitation,
    Presence,
    Response,
)


def get_open_invitations_for_human(*, human_id):
    return (
        Invitation.objects
        .filter(status=Invitation.Status.OPEN)
        .exclude(human_id=human_id)
        .order_by("-created_at", "-pk")
    )


def get_current_presence_state(*, human_id):
    presence = (
        Presence.objects
        .select_related("moment")
        .filter(
            human_id=human_id,
            moment__ended_at__isnull=True,
        )
        .first()
    )

    if presence is not None:
        return {
            "state": "moment",
            "moment": presence.moment,
        }

    invitation = (
        Invitation.objects
        .filter(
            human_id=human_id,
            status=Invitation.Status.OPEN,
        )
        .first()
    )

    if invitation is not None:
        responses = (
            invitation.responses
            .filter(status=Response.Status.PENDING)
            .order_by("-created_at", "-pk")
        )

        return {
            "state": "invitation",
            "invitation": invitation,
            "responses": responses,
        }

    response = (
        Response.objects
        .select_related("invitation")
        .filter(
            human_id=human_id,
            status=Response.Status.PENDING,
        )
        .first()
    )

    if response is not None:
        return {
            "state": "response",
            "invitation": response.invitation,
            "response": response,
        }

    return {
        "state": "idle",
    }