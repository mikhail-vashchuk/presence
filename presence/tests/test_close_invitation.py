from django.test import TestCase

from humans.exceptions import HumanNotFound
from humans.tests.factories import create_test_human

from presence.exceptions import (
    InvitationNotFound,
    InvitationNotOpen,
    NotInvitationOwner,
)
from presence.models import Invitation, Response
from presence.services import close_invitation


class CloseInvitationTests(TestCase):
    def setUp(self):
        self.inviter = create_test_human(
            email="inviter@example.com",
        )
        self.invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Invitation",
        )

    def test_close_invitation(self):
        responder = create_test_human(
            email="responder@example.com",
        )
        response = Response.objects.create(
            human=responder,
            invitation=self.invitation,
            words="Response",
        )

        close_invitation(
            human_id=self.inviter.pk,
            invitation_id=self.invitation.pk,
        )

        self.invitation.refresh_from_db()
        response.refresh_from_db()

        self.assertEqual(
            self.invitation.status,
            Invitation.Status.CLOSED,
        )
        self.assertEqual(
            response.status,
            Response.Status.CLOSED,
        )

    def test_close_invitation_closes_all_pending_responses(self):
        responder = create_test_human(
            email="responder@example.com",
        )
        another_responder = create_test_human(
            email="another_responder@example.com",
        )
        third_responder = create_test_human(
            email="third-responder@example.com"
        )

        response = Response.objects.create(
            human=responder,
            invitation=self.invitation,
            words="Response",
        )
        another_response = Response.objects.create(
            human=another_responder,
            invitation=self.invitation,
            words="Another response",
        )
        rejected_response = Response.objects.create(
            human=third_responder,
            invitation=self.invitation,
            words="Rejected response",
            status=Response.Status.REJECTED,
        )

        close_invitation(
            human_id=self.inviter.pk,
            invitation_id=self.invitation.pk,
        )

        response.refresh_from_db()
        another_response.refresh_from_db()
        rejected_response.refresh_from_db()

        self.assertEqual(
            response.status,
            Response.Status.CLOSED,
        )
        self.assertEqual(
            another_response.status,
            Response.Status.CLOSED,
        )
        self.assertEqual(
            rejected_response.status,
            Response.Status.REJECTED,
        )

    def test_close_invitation_raises_when_human_not_found(self):
        responder = create_test_human(
            email="responder@example.com",
        )
        response = Response.objects.create(
            human=responder,
            invitation=self.invitation,
            words="Response",
        )

        with self.assertRaises(HumanNotFound):
            close_invitation(
                human_id=999999,
                invitation_id=self.invitation.pk,
            )

        self.invitation.refresh_from_db()
        response.refresh_from_db()

        self.assertEqual(
            self.invitation.status,
            Invitation.Status.OPEN
        )
        self.assertEqual(
            response.status,
            Response.Status.PENDING
        )

    def test_close_invitation_raises_when_invitation_not_found(self):
        with self.assertRaises(InvitationNotFound):
            close_invitation(
                human_id=self.inviter.pk,
                invitation_id=999999,
            )

    def test_close_invitation_raises_when_human_not_invitation_owner(self):
        responder = create_test_human(
            email="responder@example.com",
        )
        response = Response.objects.create(
            human=responder,
            invitation=self.invitation,
            words="Response",
        )

        with self.assertRaises(NotInvitationOwner):
            close_invitation(
                human_id=responder.pk,
                invitation_id=self.invitation.pk,
            )

        self.invitation.refresh_from_db()
        response.refresh_from_db()

        self.assertEqual(
            self.invitation.status,
            Invitation.Status.OPEN,
        )
        self.assertEqual(
            response.status,
            Response.Status.PENDING,
        )

    def test_close_invitation_raises_when_invitation_is_not_open(self):
        responder = create_test_human(
            email="responder@example.com",
        )
        response = Response.objects.create(
            human=responder,
            invitation=self.invitation,
            words="Response",
        )

        self.invitation.status = Invitation.Status.MATCHED
        self.invitation.save(update_fields=["status"])

        response.status = Response.Status.ACCEPTED
        response.save(update_fields=["status"])

        with self.assertRaises(InvitationNotOpen):
            close_invitation(
                human_id=self.inviter.pk,
                invitation_id=self.invitation.pk,
            )

        self.invitation.refresh_from_db()
        response.refresh_from_db()

        self.assertEqual(
            self.invitation.status,
            Invitation.Status.MATCHED,
        )
        self.assertEqual(
            response.status,
            Response.Status.ACCEPTED,
        )
