from django.test import TestCase

from humans.services import create_human

from presence.models import Response
from presence.services import create_invitation, send_response, cancel_response


class CancelResponseTests(TestCase):
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

        self.invitation = create_invitation(
            human=self.inviter,
            gesture="Invitation",
        )

        self.response = send_response(
            human=self.responder,
            invitation=self.invitation,
            words="Response",
        )

    def test_cancel_response(self):
        cancel_response(
            human=self.responder,
            response=self.response,
        )

        self.response.refresh_from_db()

        self.assertEqual(
            self.response.status,
            Response.Status.CANCELLED
        )

    def test_cancel_response_raises_when_response_is_not_pending(self):
        self.response.status = Response.Status.CLOSED
        self.response.save(update_fields=["status"])

        with self.assertRaises(ValueError):
            cancel_response(
                human=self.responder,
                response=self.response,
            )

        self.response.refresh_from_db()

        self.assertEqual(
            self.response.status,
            Response.Status.CLOSED
        )

    def test_cancel_response_uses_database_state_when_response_instance_is_stale(self):
        Response.objects.filter(pk=self.response.pk).update(
            status=Response.Status.CANCELLED
        )

        self.assertEqual(
            self.response.status,
            Response.Status.PENDING
        )

        with self.assertRaises(ValueError):
            cancel_response(
                human=self.responder,
                response=self.response,
            )

        self.response.refresh_from_db()

        self.assertEqual(
            self.response.status,
            Response.Status.CANCELLED
        )

    def test_cancel_response_raises_when_human_is_not_response_author(self):
        with self.assertRaises(ValueError):
            cancel_response(
                human=self.inviter,
                response=self.response,
            )

        self.response.refresh_from_db()

        self.assertEqual(
            self.response.status,
            Response.Status.PENDING
        )