from django.test import TestCase

from humans.services import create_human

from presence.models import Invitation, Response
from presence.services import create_invitation, send_response, close_invitation


class CloseInvitationTests(TestCase):
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

    def test_close_invitation(self):
        response = send_response(
            human=self.responder,
            invitation=self.invitation,
            words="Response",
        )

        another_human = create_human(
            first_name="Another",
            last_name="Human",
            email="another@example.com",
        )

        another_response = send_response(
            human=another_human,
            invitation=self.invitation,
            words="Another response",
        )

        close_invitation(
            human=self.inviter,
            invitation=self.invitation,
        )

        self.invitation.refresh_from_db()
        response.refresh_from_db()
        another_response.refresh_from_db()

        self.assertEqual(
            self.invitation.status,
            Invitation.Status.CLOSED
        )
        self.assertEqual(
            response.status,
            Response.Status.CLOSED
        )
        self.assertEqual(
            another_response.status,
            Response.Status.CLOSED
        )

    def test_close_invitation_raises_when_invitation_is_not_open(self):
        self.invitation.status = Invitation.Status.MATCHED
        self.invitation.save(update_fields=["status"])

        with self.assertRaises(ValueError):
            close_invitation(
                human=self.inviter,
                invitation=self.invitation,
            )

        self.invitation.refresh_from_db()

        self.assertEqual(
            self.invitation.status,
            Invitation.Status.MATCHED
        )

    def test_close_invitation_uses_database_state_when_invitation_instance_is_stale(self):
        Invitation.objects.filter(pk=self.invitation.pk).update(
            status=Invitation.Status.CLOSED
        )

        self.assertEqual(
            self.invitation.status,
            Invitation.Status.OPEN
        )

        with self.assertRaises(ValueError):
            close_invitation(
                human=self.inviter,
                invitation=self.invitation,
            )

        self.invitation.refresh_from_db()

        self.assertEqual(
            self.invitation.status,
            Invitation.Status.CLOSED
        )

    def test_close_invitation_raises_when_human_is_not_invitation_owner(self):
        with self.assertRaises(ValueError):
            close_invitation(
                human=self.responder,
                invitation=self.invitation,
            )

        self.invitation.refresh_from_db()

        self.assertEqual(
            self.invitation.status,
            Invitation.Status.OPEN,
        )
