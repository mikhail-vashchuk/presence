from uuid import uuid4

from django.test import TestCase

from humans.tests.factories import create_test_human

from presence.models import Invitation, Moment, Presence, Response
from presence.services import create_invitation, send_response


class SendResponseTests(TestCase):
    def setUp(self):
        self.inviter = create_test_human(
            first_name="Inviter",
            last_name="Human",
            email="inviter@example.com",
        )

        self.responder = create_test_human(
            first_name="Responder",
            last_name="Human",
            email="responder@example.com",
        )

    def test_send_response(self):
        invitation = create_invitation(
            human=self.inviter,
            gesture="Invitation",
        )

        response = send_response(
            human=self.responder,
            invitation=invitation,
            words="Response",
        )

        self.assertEqual(Response.objects.count(), 1)
        self.assertEqual(response.human, self.responder)
        self.assertEqual(response.invitation, invitation)
        self.assertEqual(response.words, "Response")
        self.assertEqual(
            response.status,
            Response.Status.PENDING,
        )

    def test_send_response_raises_when_invitation_is_closed(self):
        invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Invitation",
            status=Invitation.Status.CLOSED,
        )

        with self.assertRaises(ValueError):
            send_response(
                human=self.responder,
                invitation=invitation,
                words="Response",
            )

        self.assertEqual(
            self.responder.responses.count(),
            0,
        )

    def test_send_response_raises_when_invitation_belongs_to_responder(self):
        own_invitation = create_invitation(
            human=self.responder,
            gesture="Own invitation",
        )

        with self.assertRaises(ValueError):
            send_response(
                human=self.responder,
                invitation=own_invitation,
                words="Response",
            )

        self.assertEqual(
            self.responder.responses.count(),
            0,
        )

    def test_send_response_raises_when_responder_has_open_invitation(self):
        create_invitation(
            human=self.responder,
            gesture="Responders own invitation",
        )

        another_invitation = create_invitation(
            human=self.inviter,
            gesture="Another invitation",
        )

        with self.assertRaises(ValueError):
            send_response(
                human=self.responder,
                invitation=another_invitation,
                words="Response",
            )

        self.assertEqual(
            self.responder.responses.count(),
            0,
        )

    def test_send_response_uses_database_state_when_invitation_instance_is_stale(self):
        invitation = create_invitation(
            human=self.inviter,
            gesture="Invitation",
        )

        Invitation.objects.filter(
            pk=invitation.pk,
        ).update(
            status=Invitation.Status.CLOSED,
        )

        self.assertEqual(
            invitation.status,
            Invitation.Status.OPEN,
        )

        with self.assertRaises(ValueError):
            send_response(
                human=self.responder,
                invitation=invitation,
                words="Response",
            )

        invitation.refresh_from_db()

        self.assertEqual(
            invitation.status,
            Invitation.Status.CLOSED,
        )
        self.assertEqual(
            Response.objects.count(),
            0,
        )

    def test_send_response_raises_when_responder_has_active_moment(self):
        matched_invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Matched invitation",
            status=Invitation.Status.MATCHED,
        )

        accepted_response = Response.objects.create(
            human=self.responder,
            invitation=matched_invitation,
            words="Accepted response",
            status=Response.Status.ACCEPTED,
        )

        moment = Moment.objects.create(
            accepted_response=accepted_response,
            media_room_id=str(uuid4()),
        )

        Presence.objects.create(
            human=self.responder,
            moment=moment,
        )

        another_inviter = create_test_human(
            first_name="Another",
            last_name="Inviter",
            email="another-inviter@example.com",
        )

        another_invitation = create_invitation(
            human=another_inviter,
            gesture="Another invitation",
        )

        with self.assertRaises(ValueError):
            send_response(
                human=self.responder,
                invitation=another_invitation,
                words="Response",
            )

        self.assertEqual(
            self.responder.responses.count(),
            1,
        )

    def test_send_response_raises_when_responder_has_pending_response(self):
        invitation = create_invitation(
            human=self.inviter,
            gesture="First invitation",
        )

        Response.objects.create(
            human=self.responder,
            invitation=invitation,
            words="Pending response",
        )

        another_inviter = create_test_human(
            first_name="Another",
            last_name="Inviter",
            email="another-inviter@example.com",
        )

        another_invitation = create_invitation(
            human=another_inviter,
            gesture="Another invitation",
        )

        with self.assertRaises(ValueError):
            send_response(
                human=self.responder,
                invitation=another_invitation,
                words="Another response",
            )

        self.assertEqual(
            self.responder.responses.count(),
            1,
        )
