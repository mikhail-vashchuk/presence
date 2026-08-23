from django.test import TestCase

from humans.exceptions import HumanNotFound
from humans.tests.factories import create_test_human

from presence.exceptions import (
    ResponseNotFound,
    NotResponseAuthor,
    ResponseNotPending,
)
from presence.models import Invitation, Response
from presence.services import cancel_response


class CancelResponseTests(TestCase):
    def setUp(self):
        self.inviter = create_test_human(
            email="inviter@test.com",
        )

        self.responder = create_test_human(
            email="responder@test.com",
        )

        self.invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Invitation",
        )
        self.response = Response.objects.create(
            human=self.responder,
            invitation=self.invitation,
            words="Response",
        )

    def test_cancel_response(self):
        cancel_response(
            human_id=self.responder.pk,
            response_id=self.response.pk,
        )

        self.response.refresh_from_db()

        self.assertEqual(
            self.response.status,
            Response.Status.CANCELLED
        )

    def test_cancel_response_raises_when_human_not_found(self):
        with self.assertRaises(HumanNotFound):
            cancel_response(
                human_id=999999,
                response_id=self.response.pk,
            )

        self.response.refresh_from_db()

        self.assertEqual(
            self.response.status,
            Response.Status.PENDING,
        )

    def test_cancel_response_raises_when_response_not_found(self):
        with self.assertRaises(ResponseNotFound):
            cancel_response(
                human_id=self.responder.pk,
                response_id=999999,
            )

    def test_cancel_response_raises_when_human_is_not_response_author(self):
        with self.assertRaises(NotResponseAuthor):
            cancel_response(
                human_id=self.inviter.pk,
                response_id=self.response.pk,
            )

        self.response.refresh_from_db()

        self.assertEqual(
            self.response.status,
            Response.Status.PENDING
        )

    def test_cancel_response_raises_when_response_is_not_pending(self):
        self.response.status = Response.Status.CANCELLED
        self.response.save(update_fields=["status"])

        with self.assertRaises(ResponseNotPending):
            cancel_response(
                human_id=self.responder.pk,
                response_id=self.response.pk,
            )

        self.response.refresh_from_db()

        self.assertEqual(
            self.response.status,
            Response.Status.CANCELLED
        )
