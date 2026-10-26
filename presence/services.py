from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from humans.exceptions import HumanNotFound
from humans.models import Human

from presence.exceptions import (
    AssistantFeedbackAlreadySent,
    AssistantHintNotFound,
    AssistantNotActive,
    CannotRespondToOwnInvitation,
    InvitationNotFound,
    InvitationNotOpen,
    HumanHasActivePresence,
    HumanHasOpenInvitation,
    HumanHasPendingResponse,
    MomentAlreadyCompleted,
    MomentNotFound,
    NotInvitationOwner,
    NoAssistantHints,
    NotMomentParticipant,
    NotResponseAuthor,
    ResponseNotFound,
    ResponseNotPending,
)
from presence.media import (
    dispatch_assistant,
    issue_media_access,
)
from presence.models import (
    AssistantFeedback,
    AssistantHint,
    Invitation,
    Presence,
    Response,
    Moment,
)
from presence.selectors import get_assistant_state


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



@transaction.atomic
def set_agent_consent(
        *,
        human_id,
        moment_id,
        consent,
):
    try:
        human = Human.objects.get(pk=human_id)
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

    try:
        presence = moment.presences.get(
            human_id=human.pk,
        )
    except Presence.DoesNotExist as error:
        raise NotMomentParticipant from error

    if moment.ended_at is not None:
        raise MomentAlreadyCompleted

    presence.agent_consent = consent
    presence.save(update_fields=["agent_consent"])

    assistant_state = get_assistant_state(
        moment=moment,
        human_id=human.pk,
    )

    if consent and assistant_state["active"]:
        transaction.on_commit(
            lambda: dispatch_assistant(
                room_id=moment.media_room_id,
                moment_id=moment.pk,
            )
        )

    return assistant_state


@transaction.atomic
def record_assistant_hint(
        *,
        moment_id,
        kind,
):
    try:
        moment = (
            Moment.objects
            .select_for_update()
            .get(pk=moment_id)
        )
    except Moment.DoesNotExist as error:
        raise MomentNotFound from error

    if moment.ended_at is not None:
        raise MomentAlreadyCompleted

    consents = list(
        moment.presences.values_list(
            "agent_consent",
            flat=True,
        )
    )

    if not consents or not all(consents):
        raise AssistantNotActive

    return AssistantHint.objects.create(
        moment=moment,
        kind=kind,
    )


@transaction.atomic
def dismiss_assistant_hint(
        *,
        human_id,
        hint_id,
):
    try:
        human = Human.objects.get(pk=human_id)
    except Human.DoesNotExist as error:
        raise HumanNotFound from error

    try:
        hint = (
            AssistantHint.objects
            .select_for_update()
            .select_related("moment")
            .get(pk=hint_id)
        )
    except AssistantHint.DoesNotExist as error:
        raise AssistantHintNotFound from error

    if not hint.moment.presences.filter(
            human_id=human.pk,
    ).exists():
        raise NotMomentParticipant

    if hint.moment.ended_at is not None:
        raise MomentAlreadyCompleted

    if hint.dismissed_at is None:
        hint.dismissed_at = timezone.now()
        hint.save(update_fields=["dismissed_at"])

    return hint


@transaction.atomic
def send_assistant_feedback(
        *,
        human_id,
        moment_id,
        rating,
):
    try:
        human = Human.objects.get(pk=human_id)
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

    if not moment.assistant_hints.exists():
        raise NoAssistantHints

    if moment.assistant_feedback.filter(
            human_id=human.pk,
    ).exists():
        raise AssistantFeedbackAlreadySent

    return AssistantFeedback.objects.create(
        moment=moment,
        human=human,
        rating=rating,
    )


def get_assistant_session(*, moment_id):
    try:
        moment = (
            Moment.objects
            .select_related(
                "accepted_response__invitation",
            )
            .get(pk=moment_id)
        )
    except Moment.DoesNotExist as error:
        raise MomentNotFound from error

    consents = list(
        moment.presences.values_list(
            "agent_consent",
            flat=True,
        )
    )

    return {
        "active": (
            moment.ended_at is None
            and bool(consents)
            and all(consents)
        ),
        "gesture": moment.accepted_response.invitation.gesture,
        "words": moment.accepted_response.words,
        "dismissed_hint_ids": list(
            moment.assistant_hints
            .filter(dismissed_at__isnull=False)
            .values_list("pk", flat=True)
        ),
    }
