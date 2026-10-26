from django.test import TestCase
from django.utils import timezone

from humans.tests.factories import create_test_human

from presence.exceptions import MomentNotFound
from presence.models import (
    AssistantHint,
    Invitation,
    Moment,
    Presence,
    Response,
)
from presence.services import get_assistant_session


class AssistantSessionTests(TestCase):
    def setUp(self):
        self.inviter = create_test_human(
            email="inviter@example.com",
        )
        self.responder = create_test_human(
            email="responder@example.com",
        )
        self.invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Invitation gesture",
            status=Invitation.Status.MATCHED,
        )
        self.response = Response.objects.create(
            human=self.responder,
            invitation=self.invitation,
            words="Response words",
            status=Response.Status.ACCEPTED,
        )
        self.moment = Moment.objects.create(
            accepted_response=self.response,
            media_room_id="test-media-room-id",
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

    def test_session_carries_the_reason_for_the_meeting(self):
        session = get_assistant_session(
            moment_id=self.moment.pk,
        )

        self.assertEqual(session["gesture"], "Invitation gesture")
        self.assertEqual(session["words"], "Response words")

    def test_session_is_not_active_without_consent(self):
        session = get_assistant_session(
            moment_id=self.moment.pk,
        )

        self.assertFalse(session["active"])

    def test_session_is_active_when_both_consent(self):
        self.give_consent()

        session = get_assistant_session(
            moment_id=self.moment.pk,
        )

        self.assertTrue(session["active"])

    def test_session_is_not_active_when_one_withdrew(self):
        self.give_consent()
        self.responder_presence.agent_consent = False
        self.responder_presence.save(update_fields=["agent_consent"])

        session = get_assistant_session(
            moment_id=self.moment.pk,
        )

        self.assertFalse(session["active"])

    def test_session_is_not_active_when_moment_is_completed(self):
        self.give_consent()
        self.moment.ended_at = timezone.now()
        self.moment.save(update_fields=["ended_at"])

        session = get_assistant_session(
            moment_id=self.moment.pk,
        )

        self.assertFalse(session["active"])

    def test_session_lists_only_dismissed_hints(self):
        kept = AssistantHint.objects.create(
            moment=self.moment,
            kind=AssistantHint.Kind.SILENCE,
        )
        dismissed = AssistantHint.objects.create(
            moment=self.moment,
            kind=AssistantHint.Kind.BALANCE,
            dismissed_at=timezone.now(),
        )

        session = get_assistant_session(
            moment_id=self.moment.pk,
        )

        self.assertEqual(
            session["dismissed_hint_ids"],
            [dismissed.pk],
        )
        self.assertNotIn(kept.pk, session["dismissed_hint_ids"])

    def test_session_raises_when_moment_not_found(self):
        with self.assertRaises(MomentNotFound):
            get_assistant_session(moment_id=999999)
