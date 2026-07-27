from django.utils import timezone
from uuid import uuid4

from django.db import transaction

from .models import Invitation, Presence, Response, Moment


def create_invitation(*, human, gesture):
    if human.invitations.filter(
        status=Invitation.Status.OPEN,
    ).exists():
        raise ValueError("Human already has an open invitation.")

    if human.presences.filter(
        moment__ended_at__isnull=True,
    ).exists():
        raise ValueError("Human is participating in an active moment.")

    if human.responses.filter(
        status=Response.Status.PENDING,
    ).exists():
        raise ValueError("Human has a pending response.")

    return Invitation.objects.create(
        human=human,
        gesture=gesture,
    )

def send_response(*, human, invitation, words):
    if invitation.status != Invitation.Status.OPEN:
        raise ValueError("Invitation is not open.")

    if invitation.human_id == human.pk:
        raise ValueError(
            "Human cannot respond to their own invitation."
        )

    if human.invitations.filter(
        status=Invitation.Status.OPEN,
    ).exists():
        raise ValueError("Human already has an open invitation.")

    if human.presences.filter(
        moment__ended_at__isnull=True,
    ).exists():
        raise ValueError("Human already has an active presence.")

    if human.responses.filter(
        status=Response.Status.PENDING,
    ).exists():
        raise ValueError("Human already has a pending response.")

    return Response.objects.create(
        human=human,
        invitation=invitation,
        words=words,
    )

def reject_response(*, human, response):
    if response.status != Response.Status.PENDING:
        raise ValueError("Response is not pending.")

    if response.invitation.human_id != human.pk:
        raise ValueError(
            "Only the invitation owner can reject this response."
        )

    response.status = Response.Status.REJECTED
    response.save(update_fields=["status"])

    return response

@transaction.atomic
def accept_response(*, human, response):
    if response.status != Response.Status.PENDING:
        raise ValueError("Response is not pending.")

    invitation = response.invitation

    if invitation.human_id != human.pk:
        raise ValueError(
            "Only the invitation owner can accept this response."
        )

    response.status = Response.Status.ACCEPTED
    response.save(update_fields=["status"])

    Response.objects.filter(
        invitation=invitation,
        status=Response.Status.PENDING,
    ).exclude(
        pk=response.pk,
    ).update(
        status=Response.Status.CLOSED,
    )

    invitation.status = Invitation.Status.MATCHED
    invitation.save(update_fields=["status"])

    moment = Moment.objects.create(
        accepted_response=response,
        media_room_id=str(uuid4()),
    )

    Presence.objects.create(
        moment=moment,
        human=invitation.human,
    )

    Presence.objects.create(
        moment=moment,
        human=response.human,
    )

    return moment

def complete_moment(*, human, moment):
    if moment.ended_at is not None:
        raise ValueError("Moment is already completed.")

    if not moment.presences.filter(human_id=human.pk).exists():
        raise ValueError("Only a moment participant can complete this moment.")

    moment.ended_at = timezone.now()
    moment.save(update_fields=["ended_at"])

    return moment

@transaction.atomic
def close_invitation(*, human, invitation):
    if invitation.status != Invitation.Status.OPEN:
        raise ValueError("Invitation is not open.")

    if invitation.human_id != human.pk:
        raise ValueError("Invitation can be closed only by its author.")

    invitation.status = Invitation.Status.CLOSED
    invitation.save(update_fields=["status"])

    Response.objects.filter(
        invitation=invitation,
        status=Response.Status.PENDING,
    ).update(
        status=Response.Status.CLOSED,
    )

    return invitation

def cancel_response(*, human, response):
    if response.status != Response.Status.PENDING:
        raise ValueError("Only pending responses can be cancelled.")

    if response.human_id != human.pk:
        raise ValueError("Response can be cancelled only by its author.")

    response.status = Response.Status.CANCELLED
    response.save(update_fields=["status"])

    return response