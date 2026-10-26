from unittest.mock import patch

from django.test import TestCase

from humans.tests.factories import create_test_human

from presence.models import (
    Invitation,
    Moment,
    Presence,
    Response,
)
from presence.services import set_agent_consent


class AssistantDispatchTests(TestCase):
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

    @patch("presence.services.dispatch_assistant")
    def test_assistant_is_dispatched_when_both_consent(self, dispatch):
        with self.captureOnCommitCallbacks(execute=True):
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

        dispatch.assert_called_once_with(
            room_id="test-media-room-id",
            moment_id=self.moment.pk,
        )

    @patch("presence.services.dispatch_assistant")
    def test_assistant_is_not_dispatched_when_only_one_consents(self, dispatch):
        with self.captureOnCommitCallbacks(execute=True):
            set_agent_consent(
                human_id=self.inviter.pk,
                moment_id=self.moment.pk,
                consent=True,
            )

        dispatch.assert_not_called()

    @patch("presence.services.dispatch_assistant")
    def test_assistant_is_not_dispatched_when_consent_is_withdrawn(self, dispatch):
        self.inviter_presence.agent_consent = True
        self.inviter_presence.save(update_fields=["agent_consent"])

        with self.captureOnCommitCallbacks(execute=True):
            set_agent_consent(
                human_id=self.responder.pk,
                moment_id=self.moment.pk,
                consent=False,
            )

        dispatch.assert_not_called()
