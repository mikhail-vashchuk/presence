from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from humans.tests.factories import create_test_human

from presence.models import Invitation


class GetInvitationsAPITests(APITestCase):
    def setUp(self):
        self.human = create_test_human()

    def test_get_invitations(self):
        second_human = create_test_human(
            email="second-human@test.com",
        )
        third_human = create_test_human(
            email="third-human@test.com",
        )

        Invitation.objects.create(
            human=self.human,
            gesture="Own invitation",
        )

        older_open_invitation = Invitation.objects.create(
            human=second_human,
            gesture="Older open invitation",
        )

        Invitation.objects.create(
            human=second_human,
            gesture="Closed invitation",
            status=Invitation.Status.CLOSED,
        )

        newer_open_invitation = Invitation.objects.create(
            human=third_human,
            gesture="Newer open invitation",
        )

        self.client.force_login(self.human.user)

        response = self.client.get(
            reverse("presence_api:invitations"),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            [
                item["id"]
                for item in response.data
            ],
            [
                newer_open_invitation.pk,
                older_open_invitation.pk,
            ],
        )

        self.assertEqual(
            [
                item["gesture"]
                for item in response.data
            ],
            [
                "Newer open invitation",
                "Older open invitation",
            ],
        )

        for item in response.data:
            self.assertEqual(
                set(item.keys()),
                {
                    "id",
                    "gesture",
                },
            )

    def test_get_invitations_requires_authentication(self):
        response = self.client.get(
            reverse("presence_api:invitations"),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_get_invitations_returns_not_found_when_user_has_no_human(self):
        user = User.objects.create_user(
            email="user@test.com",
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse("presence_api:invitations"),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            response.data["detail"],
            "Human does not exist",
        )
