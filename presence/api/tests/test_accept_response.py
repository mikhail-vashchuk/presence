from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from humans.tests.factories import create_test_human

from presence.models import (
    Invitation,
    Moment,
    Response,
)


class AcceptResponseAPITests(APITestCase):
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

    def test_accept_response(self):
        self.client.force_login(self.inviter.user)

        api_response = self.client.post(
            reverse(
                "presence_api:response-accept",
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

        moment = Moment.objects.get(
            pk=api_response.data["moment_id"],
        )

        self.assertEqual(
            moment.accepted_response,
            self.response,
        )

    def test_accept_response_requires_authentication(self):
        api_response = self.client.post(
            reverse(
                "presence_api:response-accept",
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

    def test_accept_response_returns_not_found_when_user_has_no_human(self):
        user = User.objects.create_user(
            email="user@test.com",
        )
        self.client.force_login(user)

        api_response = self.client.post(
            reverse(
                "presence_api:response-accept",
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

    def test_accept_response_returns_not_found_when_response_does_not_exist(self):
        self.client.force_login(self.inviter.user)

        api_response = self.client.post(
            reverse(
                "presence_api:response-accept",
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

    def test_accept_response_returns_bad_request_when_human_is_not_invitation_owner(self):
        self.client.force_login(self.responder.user)

        api_response = self.client.post(
            reverse(
                "presence_api:response-accept",
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
            "Only the invitation owner can accept this response",
        )

    def test_accept_response_returns_bad_request_when_invitation_is_closed(self):
        self.invitation.status = Invitation.Status.CLOSED
        self.invitation.save(
            update_fields=["status"],
        )
        self.response.status = Response.Status.CLOSED
        self.response.save(
            update_fields=["status"],
        )
        self.client.force_login(self.inviter.user)

        api_response = self.client.post(
            reverse(
                "presence_api:response-accept",
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
            "Invitation is not open",
        )

    def test_accept_response_returns_bad_request_when_response_is_not_pending(self):
        self.response.status = Response.Status.CANCELLED
        self.response.save(
            update_fields=["status"],
        )
        self.client.force_login(self.inviter.user)

        api_response = self.client.post(
            reverse(
                "presence_api:response-accept",
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
