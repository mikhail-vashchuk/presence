from django.test import TestCase
from django.utils import timezone

from humans.exceptions import HumanNotFound
from humans.tests.factories import create_test_human

from presence.exceptions import (
    MomentAlreadyCompleted,
    MomentNotFound,
    NotMomentParticipant,
)
from presence.models import (
    Invitation,
    Moment,
    Presence,
    Response,
)
from presence.services import (
    get_assistant_state,
    set_agent_consent,
)


class SetAgentConsentTests(TestCase):
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

    def test_set_agent_consent(self):
        state = set_agent_consent(
            human_id=self.inviter.pk,
            moment_id=self.moment.pk,
            consent=True,
        )

        self.inviter_presence.refresh_from_db()

        self.assertTrue(self.inviter_presence.agent_consent)
        self.assertEqual(
            state,
            {
                "consent": True,
                "invited": False,
                "active": False,
            },
        )

    def test_other_participant_is_invited_without_knowing_who(self):
        set_agent_consent(
            human_id=self.inviter.pk,
            moment_id=self.moment.pk,
            consent=True,
        )
        self.moment.refresh_from_db()

        state = get_assistant_state(
            moment=self.moment,
            human_id=self.responder.pk,
        )

        self.assertEqual(
            state,
            {
                "consent": False,
                "invited": True,
                "active": False,
            },
        )

    def test_agent_is_active_when_both_consent(self):
        set_agent_consent(
            human_id=self.inviter.pk,
            moment_id=self.moment.pk,
            consent=True,
        )

        state = set_agent_consent(
            human_id=self.responder.pk,
            moment_id=self.moment.pk,
            consent=True,
        )

        self.assertEqual(
            state,
            {
                "consent": True,
                "invited": False,
                "active": True,
            },
        )

    def test_withdrawing_consent_deactivates_agent(self):
        set_agent_consent(
            human_id=self.inviter.pk,
            moment_id=self.moment.pk,
            consent=True,
        )
        set_agent_consent(
            human_id=self.responder.pk,
            moment_id=self.moment.pk,
            consent=True,
        )

        state = set_agent_consent(
            human_id=self.inviter.pk,
            moment_id=self.moment.pk,
            consent=False,
        )

        self.assertFalse(state["active"])
        self.assertFalse(state["consent"])

    def test_set_agent_consent_raises_when_human_not_found(self):
        with self.assertRaises(HumanNotFound):
            set_agent_consent(
                human_id=999999,
                moment_id=self.moment.pk,
                consent=True,
            )

    def test_set_agent_consent_raises_when_moment_not_found(self):
        with self.assertRaises(MomentNotFound):
            set_agent_consent(
                human_id=self.inviter.pk,
                moment_id=999999,
                consent=True,
            )

    def test_set_agent_consent_raises_when_human_is_not_participant(self):
        human = create_test_human(
            email="other-human@example.com",
        )

        with self.assertRaises(NotMomentParticipant):
            set_agent_consent(
                human_id=human.pk,
                moment_id=self.moment.pk,
                consent=True,
            )

    def test_set_agent_consent_raises_when_moment_is_completed(self):
        self.moment.ended_at = timezone.now()
        self.moment.save(update_fields=["ended_at"])

        with self.assertRaises(MomentAlreadyCompleted):
            set_agent_consent(
                human_id=self.inviter.pk,
                moment_id=self.moment.pk,
                consent=True,
            )

        self.inviter_presence.refresh_from_db()

        self.assertFalse(self.inviter_presence.agent_consent)
