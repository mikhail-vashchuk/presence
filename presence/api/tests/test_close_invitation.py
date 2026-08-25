from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from humans.tests.factories import create_test_human

from presence.models import (
    Invitation,
    Response,
)


class CloseInvitationAPITests(APITestCase):
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

    def test_close_invitation(self):
        self.client.force_login(self.inviter.user)

        api_response = self.client.post(
            reverse(
                "presence_api:invitation-close",
                kwargs={
                    "invitation_id": self.invitation.pk,
                },
            ),
            format="json",
        )

        self.assertEqual(
            api_response.status_code,
            status.HTTP_200_OK,
        )

        self.invitation.refresh_from_db()

        self.assertEqual(
            api_response.data,
            {
                "invitation_id": self.invitation.pk,
                "status": Invitation.Status.CLOSED,
            },
        )
        self.assertEqual(
            self.invitation.status,
            Invitation.Status.CLOSED,
        )

    def test_close_invitation_requires_authentication(self):
        api_response = self.client.post(
            reverse(
                "presence_api:invitation-close",
                kwargs={
                    "invitation_id": self.invitation.pk,
                },
            ),
            format="json",
        )

        self.assertEqual(
            api_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_close_invitation_returns_not_found_when_user_has_no_human(self):
        user = User.objects.create_user(
            email="user@test.com",
        )
        self.client.force_login(user)

        api_response = self.client.post(
            reverse(
                "presence_api:invitation-close",
                kwargs={
                    "invitation_id": self.invitation.pk,
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

    def test_close_invitation_returns_not_found_when_invitation_does_not_exist(self):
        self.client.force_login(self.inviter.user)

        api_response = self.client.post(
            reverse(
                "presence_api:invitation-close",
                kwargs={
                    "invitation_id": 999999,
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
            "Invitation does not exist",
        )

    def test_close_invitation_returns_bad_request_when_human_is_not_invitation_owner(self):
        self.client.force_login(self.responder.user)

        api_response = self.client.post(
            reverse(
                "presence_api:invitation-close",
                kwargs={
                    "invitation_id": self.invitation.pk,
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
            "Only the invitation owner can close this invitation",
        )

    def test_close_invitation_returns_bad_request_when_invitation_is_not_open(self):
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
                "presence_api:invitation-close",
                kwargs={
                    "invitation_id": self.invitation.pk,
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
