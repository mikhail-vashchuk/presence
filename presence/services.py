from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from humans.exceptions import HumanNotFound
from humans.models import Human

from presence.exceptions import (
    CannotRespondToOwnInvitation,
    InvitationNotFound,
    InvitationNotOpen,
    HumanHasActivePresence,
    HumanHasOpenInvitation,
    HumanHasPendingResponse,
    MomentAlreadyCompleted,
    MomentNotFound,
    NotInvitationOwner,
    NotMomentParticipant,
    NotResponseAuthor,
    ResponseNotFound,
    ResponseNotPending,
)
from presence.media import issue_media_access
from presence.models import (
    Invitation,
    Presence,
    Response,
    Moment,
)


@transaction.atomic
def create_invitation(
        *,
        human_id,
        gesture
):
    try:
        human = (
            Human.objects
            .select_for_update()
            .get(pk=human_id)
        )
    except Human.DoesNotExist as error:
        raise HumanNotFound from error

    if human.invitations.filter(
        status=Invitation.Status.OPEN,
    ).exists():
        raise HumanHasOpenInvitation

    if human.presences.filter(
        moment__ended_at__isnull=True,
    ).exists():
        raise HumanHasActivePresence

    if human.responses.filter(
        status=Response.Status.PENDING,
    ).exists():
        raise HumanHasPendingResponse

    return Invitation.objects.create(
        human=human,
        gesture=gesture,
    )


@transaction.atomic
def send_response(
        *,
        human_id,
        invitation_id,
        words
):
    try:
        human = (
            Human.objects
            .select_for_update()
            .get(pk=human_id)
        )
    except Human.DoesNotExist as error:
        raise HumanNotFound from error

    try:
        invitation = (
            Invitation.objects
            .select_for_update()
            .get(pk=invitation_id)
        )
    except Invitation.DoesNotExist as error:
        raise InvitationNotFound from error

    if invitation.status != Invitation.Status.OPEN:
        raise InvitationNotOpen

    if invitation.human_id == human.pk:
        raise CannotRespondToOwnInvitation

    if human.invitations.filter(
        status=Invitation.Status.OPEN,
    ).exists():
        raise HumanHasOpenInvitation

    if human.presences.filter(
        moment__ended_at__isnull=True,
    ).exists():
        raise HumanHasActivePresence

    if human.responses.filter(
        status=Response.Status.PENDING,
    ).exists():
        raise HumanHasPendingResponse

    return Response.objects.create(
        human=human,
        invitation=invitation,
        words=words,
    )


@transaction.atomic
def reject_response(
        *,
        human_id,
        response_id,
):
    try:
        human = (
            Human.objects
            .get(pk=human_id)
        )
    except Human.DoesNotExist as error:
        raise HumanNotFound from error

    try:
        response = (
            Response.objects
            .select_for_update()
            .get(pk=response_id)
        )
    except Response.DoesNotExist as error:
        raise ResponseNotFound from error

    if response.invitation.human_id != human.pk:
        raise NotInvitationOwner

    if response.status != Response.Status.PENDING:
        raise ResponseNotPending

    response.status = Response.Status.REJECTED
    response.save(update_fields=["status"])

    return response


@transaction.atomic
def accept_response(
        *,
        human_id,
        response_id
):
    try:
        human = (
            Human.objects
            .get(pk=human_id)
        )
    except Human.DoesNotExist as error:
        raise HumanNotFound from error

    try:
        invitation_id = (
            Response.objects
            .values_list("invitation_id", flat=True)
            .get(pk=response_id)
        )
    except Response.DoesNotExist as error:
        raise ResponseNotFound from error

    invitation = (
        Invitation.objects
        .select_for_update()
        .get(pk=invitation_id)
    )

    try:
        response = (
            Response.objects
            .select_for_update()
            .get(pk=response_id)
        )
    except Response.DoesNotExist as error:
        raise ResponseNotFound from error

    if human.pk != invitation.human_id:
        raise NotInvitationOwner

    if invitation.status != Invitation.Status.OPEN:
        raise InvitationNotOpen

    if response.status != Response.Status.PENDING:
        raise ResponseNotPending

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
        human=human,
    )

    Presence.objects.create(
        moment=moment,
        human=response.human,
    )

    return moment


@transaction.atomic
def complete_moment(
        *,
        human_id,
        moment_id,
):
    try:
        human = (
            Human.objects
            .get(pk=human_id)
        )
    except Human.DoesNotExist as error:
        raise HumanNotFound from error

    try:
        moment = (
            Moment.objects
            .select_for_update()
            .get(pk=moment_id)
        )
    except Moment.DoesNotExist as error:
        raise MomentNotFound from error

    if not moment.presences.filter(
            human_id=human.pk,
    ).exists():
        raise NotMomentParticipant

    if moment.ended_at is not None:
        raise MomentAlreadyCompleted

    moment.ended_at = timezone.now()
    moment.save(update_fields=["ended_at"])

    return moment


@transaction.atomic
def close_invitation(
        *,
        human_id,
        invitation_id,
):
    try:
        human = Human.objects.get(pk=human_id)
    except Human.DoesNotExist as error:
        raise HumanNotFound from error

    try:
        invitation = (
            Invitation.objects
            .select_for_update()
            .get(pk=invitation_id)
        )
    except Invitation.DoesNotExist as error:
        raise InvitationNotFound from error

    if invitation.human_id != human.pk:
        raise NotInvitationOwner

    if invitation.status != Invitation.Status.OPEN:
        raise InvitationNotOpen

    invitation.status = Invitation.Status.CLOSED
    invitation.save(update_fields=["status"])

    Response.objects.filter(
        invitation=invitation,
        status=Response.Status.PENDING,
    ).update(
        status=Response.Status.CLOSED,
    )

    return invitation


@transaction.atomic
def cancel_response(
        *,
        human_id,
        response_id
):
    try:
        human = (
            Human.objects
            .get(pk=human_id)
        )
    except Human.DoesNotExist as error:
        raise HumanNotFound from error

    try:
        response = (
            Response.objects
            .select_for_update()
            .get(pk=response_id)
        )
    except Response.DoesNotExist as error:
        raise ResponseNotFound from error

    if response.human_id != human.pk:
        raise NotResponseAuthor

    if response.status != Response.Status.PENDING:
        raise ResponseNotPending

    response.status = Response.Status.CANCELLED
    response.save(update_fields=["status"])

    return response


def create_moment_media_access(
        *,
        human_id,
        moment_id,
):
    try:
        human = Human.objects.get(
            pk=human_id,
        )
    except Human.DoesNotExist as error:
        raise HumanNotFound from error

    try:
        moment = Moment.objects.get(
            pk=moment_id,
        )
    except Moment.DoesNotExist as error:
        raise MomentNotFound from error

    try:
        presence = moment.presences.get(
            human_id=human.pk,
        )
    except Presence.DoesNotExist as error:
        raise NotMomentParticipant from error

    if moment.ended_at is not None:
        raise MomentAlreadyCompleted

    return issue_media_access(
        room_id=moment.media_room_id,
        participant_identity=f"presence-{presence.pk}",
    )
