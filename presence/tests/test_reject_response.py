from django.test import TestCase

from humans.exceptions import HumanNotFound
from humans.tests.factories import create_test_human

from presence.exceptions import (
    NotInvitationOwner,
    ResponseNotFound,
    ResponseNotPending,
)
from presence.models import Response, Invitation
from presence.services import reject_response


class RejectResponseTests(TestCase):
    def setUp(self):
        self.inviter = create_test_human(
            email="inviter@test.com",
        )

        self.responder = create_test_human(
            email="responder@test.com",
        )

    def test_reject_response(self):
        invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Invitation",
        )

        response = Response.objects.create(
            human=self.responder,
            invitation=invitation,
            words="Response",
        )

        reject_response(
            human_id=self.inviter.pk,
            response_id=response.pk,
        )

        response.refresh_from_db()

        self.assertEqual(
            response.status,
            Response.Status.REJECTED,
        )

    def test_reject_response_raises_when_human_not_found(self):
        invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Invitation",
        )

        response = Response.objects.create(
            human=self.responder,
            invitation=invitation,
            words="Response",
        )

        with self.assertRaises(HumanNotFound):
            reject_response(
                human_id=999999,
                response_id=response.pk,
            )

        response.refresh_from_db()

        self.assertEqual(
            response.status,
            Response.Status.PENDING,
        )

    def test_reject_response_raises_when_response_not_found(self):
        with self.assertRaises(ResponseNotFound):
            reject_response(
                human_id=self.inviter.pk,
                response_id=999999,
            )

    def test_reject_response_raises_when_response_is_not_pending(self):
        invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Invitation",
        )

        response = Response.objects.create(
            human=self.responder,
            invitation=invitation,
            words="Response",
            status=Response.Status.CANCELLED,
        )

        with self.assertRaises(ResponseNotPending):
            reject_response(
                human_id=self.inviter.pk,
                response_id=response.pk,
            )

        response.refresh_from_db()

        self.assertEqual(
            response.status,
            Response.Status.CANCELLED,
        )

    def test_reject_response_raises_when_human_is_not_invitation_owner(self):
        invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Invitation",
        )

        response = Response.objects.create(
            human=self.responder,
            invitation=invitation,
            words="Response",
        )

        another_human = create_test_human(
            email="another-human@test.com",
        )

        with self.assertRaises(NotInvitationOwner):
            reject_response(
                human_id=another_human.pk,
                response_id=response.pk,
            )

        response.refresh_from_db()

        self.assertEqual(
            response.status,
            Response.Status.PENDING,
        )
