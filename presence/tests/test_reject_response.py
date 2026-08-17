from django.test import TestCase

from humans.services import create_human

from presence.models import Response
from presence.services import create_invitation, reject_response, send_response


class RejectResponseTests(TestCase):
    def setUp(self):
        self.inviter = create_human(
            first_name="Inviter",
            last_name="Human",
            email="inviter@example.com",
        )

        self.responder = create_human(
            first_name="Responder",
            last_name="Human",
            email="responder@example.com",
        )

    def test_reject_response(self):
        invitation = create_invitation(
            human=self.inviter,
            gesture="Invitation",
        )

        response = send_response(
            human=self.responder,
            invitation=invitation,
            words="Response",
        )

        reject_response(
            human=self.inviter,
            response=response,
        )

        response.refresh_from_db()

        self.assertEqual(
            response.status,
            Response.Status.REJECTED,
        )

    def test_reject_response_raises_when_response_is_not_pending(self):
        invitation = create_invitation(
            human=self.inviter,
            gesture="Invitation",
        )

        response = Response.objects.create(
            human=self.responder,
            invitation=invitation,
            words="Response",
            status=Response.Status.CANCELLED,
        )

        with self.assertRaises(ValueError):
            reject_response(
                human=self.inviter,
                response=response,
            )

        response.refresh_from_db()

        self.assertEqual(
            response.status,
            Response.Status.CANCELLED,
        )

    def test_reject_response_uses_database_state_when_response_instance_is_stale(self):
        invitation = create_invitation(
            human=self.inviter,
            gesture="Invitation",
        )

        response = send_response(
            human=self.responder,
            invitation=invitation,
            words="Response",
        )

        Response.objects.filter(
            pk=response.pk,
        ).update(
            status=Response.Status.ACCEPTED,
        )

        self.assertEqual(
            response.status,
            Response.Status.PENDING,
        )

        with self.assertRaises(ValueError):
            reject_response(
                human=self.inviter,
                response=response,
            )

        response.refresh_from_db()

        self.assertEqual(
            response.status,
            Response.Status.ACCEPTED,
        )

    def test_reject_response_raises_when_human_is_not_invitation_owner(self):
        invitation = create_invitation(
            human=self.inviter,
            gesture="Invitation",
        )

        response = send_response(
            human=self.responder,
            invitation=invitation,
            words="Response",
        )

        another_human = create_human(
            first_name="Another",
            last_name="Human",
            email="another-human@example.com",
        )

        with self.assertRaises(ValueError):
            reject_response(
                human=another_human,
                response=response,
            )

        response.refresh_from_db()

        self.assertEqual(
            response.status,
            Response.Status.PENDING,
        )
