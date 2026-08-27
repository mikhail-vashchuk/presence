from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from humans.tests.factories import create_test_human

from presence.models import (
    Invitation,
    Moment,
    Presence,
    Response,
)


class GetCurrentPresenceAPITests(APITestCase):
    def setUp(self):
        self.human = create_test_human()

    def test_get_current_presence_when_idle(self):
        self.client.force_login(self.human.user)

        response = self.client.get(
            reverse("presence_api:current"),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data,
            {
                "state": "idle",
            },
        )

    def test_get_current_presence_with_open_invitation(self):
        invitation = Invitation.objects.create(
            human=self.human,
            gesture="Invitation",
        )

        responder = create_test_human(
            email="responder@test.com",
        )

        pending_response = Response.objects.create(
            human=responder,
            invitation=invitation,
            words="Response",
        )

        self.client.force_login(self.human.user)

        response = self.client.get(
            reverse("presence_api:current"),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data,
            {
                "state": "invitation",
                "invitation": {
                    "id": invitation.pk,
                    "gesture": "Invitation",
                },
                "responses": [
                    {
                        "id": pending_response.pk,
                        "words": "Response",
                    },
                ],
            },
        )

    def test_get_current_presence_with_pending_response(self):
        inviter = create_test_human(
            email="inviter@test.com",
        )

        invitation = Invitation.objects.create(
            human=inviter,
            gesture="Invitation",
        )

        pending_response = Response.objects.create(
            human=self.human,
            invitation=invitation,
            words="Response",
        )

        self.client.force_login(self.human.user)

        response = self.client.get(
            reverse("presence_api:current"),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data,
            {
                "state": "response",
                "invitation": {
                    "id": invitation.pk,
                    "gesture": "Invitation",
                },
                "response": {
                    "id": pending_response.pk,
                    "words": "Response",
                },
            },
        )

    def test_get_current_presence_with_active_moment(self):
        inviter = create_test_human(
            email="inviter@test.com",
        )

        invitation = Invitation.objects.create(
            human=inviter,
            gesture="Invitation",
            status=Invitation.Status.MATCHED,
        )

        accepted_response = Response.objects.create(
            human=self.human,
            invitation=invitation,
            words="Response",
            status=Response.Status.ACCEPTED,
        )

        moment = Moment.objects.create(
            accepted_response=accepted_response,
            media_room_id="test-media-room-id",
        )

        Presence.objects.create(
            human=self.human,
            moment=moment,
        )

        self.client.force_login(self.human.user)

        response = self.client.get(
            reverse("presence_api:current"),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data,
            {
                "state": "moment",
                "moment": {
                    "id": moment.pk,
                    "media_room_id": "test-media-room-id",
                },
            },
        )

    def test_get_current_presence_requires_authentication(self):
        response = self.client.get(
            reverse("presence_api:current"),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_get_current_presence_returns_not_found_when_user_has_no_human(self):
        user = User.objects.create_user(
            email="user@test.com",
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse("presence_api:current"),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            response.data["detail"],
            "Human does not exist",
        )
