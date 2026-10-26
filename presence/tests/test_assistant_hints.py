from django.test import TestCase
from django.utils import timezone

from humans.exceptions import HumanNotFound
from humans.tests.factories import create_test_human

from presence.exceptions import (
    AssistantHintNotFound,
    AssistantNotActive,
    MomentAlreadyCompleted,
    MomentNotFound,
    NotMomentParticipant,
)
from presence.models import (
    AssistantHint,
    Invitation,
    Moment,
    Presence,
    Response,
)
from presence.services import (
    dismiss_assistant_hint,
    record_assistant_hint,
)


class AssistantHintTests(TestCase):
    def setUp(self):
        self.inviter = create_test_human(
            email="inviter@example.com",
        )
        self.responder = create_test_human(
            email="responder@example.com",
        )
        self.invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Invitation",
            status=Invitation.Status.MATCHED,
        )
        self.response = Response.objects.create(
            human=self.responder,
            invitation=self.invitation,
            words="Response",
            status=Response.Status.ACCEPTED,
        )
        self.moment = Moment.objects.create(
            accepted_response=self.response,
            media_room_id="test_media_room_id",
        )
        self.inviter_presence = Presence.objects.create(
            moment=self.moment,
            human=self.inviter,
        )
        self.responder_presence = Presence.objects.create(
            moment=self.moment,
            human=self.responder,
        )

    def give_consent(self):
        Presence.objects.filter(
            moment=self.moment,
        ).update(agent_consent=True)

    def test_record_assistant_hint(self):
        self.give_consent()

        hint = record_assistant_hint(
            moment_id=self.moment.pk,
            kind=AssistantHint.Kind.SILENCE,
        )

        self.assertEqual(hint.moment, self.moment)
        self.assertEqual(hint.kind, AssistantHint.Kind.SILENCE)
        self.assertIsNone(hint.dismissed_at)

    def test_record_assistant_hint_raises_when_only_one_consented(self):
        self.inviter_presence.agent_consent = True
        self.inviter_presence.save(update_fields=["agent_consent"])

        with self.assertRaises(AssistantNotActive):
            record_assistant_hint(
                moment_id=self.moment.pk,
                kind=AssistantHint.Kind.SILENCE,
            )

        self.assertFalse(AssistantHint.objects.exists())

    def test_record_assistant_hint_raises_when_moment_not_found(self):
        with self.assertRaises(MomentNotFound):
            record_assistant_hint(
                moment_id=999999,
                kind=AssistantHint.Kind.SILENCE,
            )

    def test_record_assistant_hint_raises_when_moment_is_completed(self):
        self.give_consent()
        self.moment.ended_at = timezone.now()
        self.moment.save(update_fields=["ended_at"])

        with self.assertRaises(MomentAlreadyCompleted):
            record_assistant_hint(
                moment_id=self.moment.pk,
                kind=AssistantHint.Kind.SILENCE,
            )

    def test_dismiss_assistant_hint(self):
        hint = AssistantHint.objects.create(
            moment=self.moment,
            kind=AssistantHint.Kind.BALANCE,
        )

        dismiss_assistant_hint(
            human_id=self.responder.pk,
            hint_id=hint.pk,
        )

        hint.refresh_from_db()

        self.assertIsNotNone(hint.dismissed_at)

    def test_dismiss_assistant_hint_keeps_first_dismissal_time(self):
        hint = AssistantHint.objects.create(
            moment=self.moment,
            kind=AssistantHint.Kind.BALANCE,
        )

        dismiss_assistant_hint(
            human_id=self.responder.pk,
            hint_id=hint.pk,
        )
        hint.refresh_from_db()
        first_dismissed_at = hint.dismissed_at

        dismiss_assistant_hint(
            human_id=self.inviter.pk,
            hint_id=hint.pk,
        )
        hint.refresh_from_db()

        self.assertEqual(hint.dismissed_at, first_dismissed_at)

    def test_dismiss_assistant_hint_raises_when_human_not_found(self):
        hint = AssistantHint.objects.create(
            moment=self.moment,
            kind=AssistantHint.Kind.SILENCE,
        )

        with self.assertRaises(HumanNotFound):
            dismiss_assistant_hint(
                human_id=999999,
                hint_id=hint.pk,
            )

    def test_dismiss_assistant_hint_raises_when_hint_not_found(self):
        with self.assertRaises(AssistantHintNotFound):
            dismiss_assistant_hint(
                human_id=self.inviter.pk,
                hint_id=999999,
            )

    def test_dismiss_assistant_hint_raises_when_human_is_not_participant(self):
        human = create_test_human(
            email="other-human@example.com",
        )
        hint = AssistantHint.objects.create(
            moment=self.moment,
            kind=AssistantHint.Kind.SILENCE,
        )

        with self.assertRaises(NotMomentParticipant):
            dismiss_assistant_hint(
                human_id=human.pk,
                hint_id=hint.pk,
            )

        hint.refresh_from_db()

        self.assertIsNone(hint.dismissed_at)

    def test_dismiss_assistant_hint_raises_when_moment_is_completed(self):
        hint = AssistantHint.objects.create(
            moment=self.moment,
            kind=AssistantHint.Kind.SILENCE,
        )
        self.moment.ended_at = timezone.now()
        self.moment.save(update_fields=["ended_at"])

        with self.assertRaises(MomentAlreadyCompleted):
            dismiss_assistant_hint(
                human_id=self.inviter.pk,
                hint_id=hint.pk,
            )
