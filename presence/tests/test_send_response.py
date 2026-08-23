from uuid import uuid4

from django.test import TestCase

from humans.exceptions import HumanNotFound
from humans.tests.factories import create_test_human

from presence.exceptions import (
    CannotRespondToOwnInvitation,
    HumanHasActivePresence,
    HumanHasOpenInvitation,
    HumanHasPendingResponse,
    InvitationNotFound,
    InvitationNotOpen,
)
from presence.models import (
    Invitation,
    Moment,
    Presence,
    Response
)
from presence.services import send_response


class SendResponseTests(TestCase):
    def setUp(self):
        self.inviter = create_test_human(
            email="inviter@test.com",
        )

    def test_send_response(self):
        invitation = Invitation.objects.create(
            human_id=self.inviter.pk,
            gesture="Invitation",
        )

        responder = create_test_human()

        response = send_response(
            human_id=responder.pk,
            invitation_id=invitation.pk,
            words="Response",
        )

        self.assertEqual(Response.objects.count(), 1)
        self.assertEqual(response.human, responder)
        self.assertEqual(response.invitation, invitation)
        self.assertEqual(response.words, "Response")
        self.assertEqual(
            response.status,
            Response.Status.PENDING,
        )

    def test_send_response_raises_when_human_not_found(self):
        invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Invitation",
        )

        with self.assertRaises(HumanNotFound):
            send_response(
                human_id=999999,
                invitation_id=invitation.pk,
                words="Response",
            )

        self.assertEqual(
            Response.objects.count(),
            0,
        )

    def test_send_response_raises_when_invitation_not_found(self):
        responder = create_test_human()

        with self.assertRaises(InvitationNotFound):
            send_response(
                human_id=responder.pk,
                invitation_id=999999,
                words="Response",
            )

        self.assertEqual(
            responder.responses.count(),
            0,
        )

    def test_send_response_raises_when_invitation_is_closed(self):
        invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Invitation",
            status=Invitation.Status.CLOSED,
        )

        responder = create_test_human()

        with self.assertRaises(InvitationNotOpen):
            send_response(
                human_id=responder.pk,
                invitation_id=invitation.pk,
                words="Response",
            )

        self.assertEqual(
            responder.responses.count(),
            0,
        )

    def test_send_response_raises_when_invitation_belongs_to_responder(self):
        responder = create_test_human()

        own_invitation = Invitation.objects.create(
            human_id=responder.pk,
            gesture="Own invitation",
        )

        with self.assertRaises(CannotRespondToOwnInvitation):
            send_response(
                human_id=responder.pk,
                invitation_id=own_invitation.pk,
                words="Response",
            )

        self.assertEqual(
            responder.responses.count(),
            0,
        )

    def test_send_response_raises_when_responder_has_open_invitation(self):
        invitation = Invitation.objects.create(
            human_id=self.inviter.pk,
            gesture="Invitation",
        )

        responder = create_test_human()

        Invitation.objects.create(
            human=responder,
            gesture="Responders own invitation",
        )

        with self.assertRaises(HumanHasOpenInvitation):
            send_response(
                human_id=responder.pk,
                invitation_id=invitation.pk,
                words="Response",
            )

        self.assertEqual(
            responder.responses.count(),
            0,
        )

    def test_send_response_raises_when_responder_has_an_active_presence(self):
        matched_invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Matched invitation",
            status=Invitation.Status.MATCHED,
        )

        responder = create_test_human()

        accepted_response = Response.objects.create(
            human=responder,
            invitation=matched_invitation,
            words="Accepted response",
            status=Response.Status.ACCEPTED,
        )

        moment = Moment.objects.create(
            accepted_response=accepted_response,
            media_room_id=str(uuid4()),
        )

        Presence.objects.create(
            human=responder,
            moment=moment,
        )

        another_inviter = create_test_human(
            email="another-inviter@test.com",
        )

        another_invitation = Invitation.objects.create(
            human_id=another_inviter.pk,
            gesture="Another invitation",
        )

        with self.assertRaises(HumanHasActivePresence):
            send_response(
                human_id=responder.pk,
                invitation_id=another_invitation.pk,
                words="Response",
            )

        self.assertEqual(
            responder.responses.count(),
            1,
        )

    def test_send_response_raises_when_responder_has_a_pending_response(self):
        invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Invitation",
        )

        responder = create_test_human()

        Response.objects.create(
            human=responder,
            invitation=invitation,
            words="Pending response",
        )

        another_inviter = create_test_human(
            email="another-inviter@test.com",
        )

        another_invitation = Invitation.objects.create(
            human=another_inviter,
            gesture="Another invitation",
        )

        with self.assertRaises(HumanHasPendingResponse):
            send_response(
                human_id=responder.pk,
                invitation_id=another_invitation.pk,
                words="Another response",
            )

        self.assertEqual(
            responder.responses.count(),
            1,
        )
