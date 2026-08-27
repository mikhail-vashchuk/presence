from django.test import TestCase

from humans.tests.factories import create_test_human

from presence.models import (
    Invitation,
    Moment,
    Presence,
    Response,
)
from presence.selectors import get_current_presence_state


class GetCurrentPresenceStateTests(TestCase):
    def setUp(self):
        self.human = create_test_human()

    def test_get_current_presence_state_when_idle(self):
        current_state = get_current_presence_state(
            human_id=self.human.pk,
        )

        self.assertEqual(
            current_state,
            {
                "state": "idle",
            },
        )

    def test_get_current_presence_state_when_human_has_open_invitation(self):
        invitation = Invitation.objects.create(
            human=self.human,
            gesture="Invitation",
        )

        first_responder = create_test_human(
            email="first-responder@test.com",
        )
        second_responder = create_test_human(
            email="second-responder@test.com",
        )

        older_response = Response.objects.create(
            human=first_responder,
            invitation=invitation,
            words="Older response",
        )
        newer_response = Response.objects.create(
            human=second_responder,
            invitation=invitation,
            words="Newer response",
        )

        current_state = get_current_presence_state(
            human_id=self.human.pk,
        )

        self.assertEqual(
            current_state["state"],
            "invitation",
        )
        self.assertEqual(
            current_state["invitation"],
            invitation,
        )
        self.assertQuerySetEqual(
            current_state["responses"],
            [
                newer_response,
                older_response,
            ],
        )

    def test_get_current_presence_state_when_human_has_pending_response(self):
        inviter = create_test_human(
            email="inviter@test.com",
        )

        invitation = Invitation.objects.create(
            human=inviter,
            gesture="Invitation",
        )

        response = Response.objects.create(
            human=self.human,
            invitation=invitation,
            words="Response",
        )

        current_state = get_current_presence_state(
            human_id=self.human.pk,
        )

        self.assertEqual(
            current_state,
            {
                "state": "response",
                "invitation": invitation,
                "response": response,
            },
        )

    def test_get_current_presence_state_when_human_has_active_moment(self):
        inviter = create_test_human(
            email="inviter@test.com",
        )

        invitation = Invitation.objects.create(
            human=inviter,
            gesture="Invitation",
            status=Invitation.Status.MATCHED,
        )

        response = Response.objects.create(
            human=self.human,
            invitation=invitation,
            words="Response",
            status=Response.Status.ACCEPTED,
        )

        moment = Moment.objects.create(
            accepted_response=response,
            media_room_id="test-media-room-id",
        )

        Presence.objects.create(
            human=self.human,
            moment=moment,
        )

        current_state = get_current_presence_state(
            human_id=self.human.pk,
        )

        self.assertEqual(
            current_state,
            {
                "state": "moment",
                "moment": moment,
            },
        )
