from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from humans.tests.factories import create_test_human

from presence.models import (
    Invitation,
    Response,
)


class CancelResponseAPITests(APITestCase):
    def setUp(self):
        self.inviter = create_test_human(
            email="inviter@example.com",
        )
        self.responder = create_test_human(
            email="responder@example.com",
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
        self.client.force_login(self.responder.user)

        api_response = self.client.post(
            reverse(
                "presence_api:response-cancel",
                kwargs={
                    "response_id": self.response.pk,
                },
            ),
            format="json",
        )

        self.assertEqual(
            api_response.status_code,
            status.HTTP_200_OK,
        )

        self.response.refresh_from_db()

        self.assertEqual(
            api_response.data,
            {
                "response_id": self.response.pk,
                "status": Response.Status.CANCELLED,
            },
        )
        self.assertEqual(
            self.response.status,
            Response.Status.CANCELLED,
        )

    def test_cancel_response_requires_authentication(self):
        api_response = self.client.post(
            reverse(
                "presence_api:response-cancel",
                kwargs={
                    "response_id": self.response.pk,
                },
            ),
            format="json",
        )

        self.assertEqual(
            api_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_cancel_response_returns_not_found_when_user_has_no_human(self):
        user = User.objects.create_user(
            email="user@example.com",
        )
        self.client.force_login(user)

        api_response = self.client.post(
            reverse(
                "presence_api:response-cancel",
                kwargs={
                    "response_id": self.response.pk,
                },
            ),
            format="json",
        )

        self.assertEqual(
            api_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            api_response.data["detail"],
            "Human does not exist",
        )

    def test_cancel_response_returns_not_found_when_response_does_not_exist(self):
        self.client.force_login(self.responder.user)

        api_response = self.client.post(
            reverse(
                "presence_api:response-cancel",
                kwargs={
                    "response_id": 999999,
                },
            ),
            format="json",
        )

        self.assertEqual(
            api_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            api_response.data["detail"],
            "Response does not exist",
        )

    def test_cancel_response_returns_bad_request_when_human_is_not_response_author(self):
        self.client.force_login(self.inviter.user)

        api_response = self.client.post(
            reverse(
                "presence_api:response-cancel",
                kwargs={
                    "response_id": self.response.pk,
                },
            ),
            format="json",
        )

        self.assertEqual(
            api_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            api_response.data["detail"],
            "Only the response author can cancel this response",
        )

    def test_cancel_response_returns_bad_request_when_response_is_not_pending(self):
        self.response.status = Response.Status.CANCELLED
        self.response.save(
            update_fields=["status"],
        )
        self.client.force_login(self.responder.user)

        api_response = self.client.post(
            reverse(
                "presence_api:response-cancel",
                kwargs={
                    "response_id": self.response.pk,
                },
            ),
            format="json",
        )

        self.assertEqual(
            api_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            api_response.data["detail"],
            "Response is not pending",
        )
