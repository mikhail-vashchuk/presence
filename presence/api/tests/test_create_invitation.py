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


class CreateInvitationAPITests(APITestCase):
    def setUp(self):
        self.human = create_test_human()

    def test_create_invitation(self):
        self.client.force_login(self.human.user)

        response = self.client.post(
            reverse("presence_api:invitations"),
            {
                "gesture": "Invitation",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        invitation = Invitation.objects.get(
            pk=response.data["invitation_id"],
        )

        self.assertEqual(
            invitation.human,
            self.human,
        )
        self.assertEqual(
            invitation.gesture,
            "Invitation",
        )

    def test_create_invitation_requires_authentication(self):
        response = self.client.post(
            reverse("presence_api:invitations"),
            {
                "gesture": "Invitation",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_create_invitation_returns_not_found_when_user_has_no_human(self):
        user = User.objects.create_user(
            email="user@test.com",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("presence_api:invitations"),
            {
                "gesture": "Invitation",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            response.data["detail"],
            "Human does not exist",
        )

    def test_create_invitation_returns_bad_request_when_gesture_is_invalid(self):
        self.client.force_login(self.human.user)

        response = self.client.post(
            reverse("presence_api:invitations"),
            {
                "gesture": "",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_create_invitation_returns_bad_request_when_human_has_open_invitation(self):
        Invitation.objects.create(
            human=self.human,
            gesture="Open invitation",
        )
        self.client.force_login(self.human.user)

        response = self.client.post(
            reverse("presence_api:invitations"),
            {
                "gesture": "Another invitation",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Human already has an open invitation",
        )

    def test_create_invitation_returns_bad_request_when_human_has_active_presence(self):
        inviter = create_test_human(
            email="inviter@test.com",
        )
        invitation = Invitation.objects.create(
            human=inviter,
            gesture="Matched invitation",
            status=Invitation.Status.MATCHED,
        )
        accepted_response = Response.objects.create(
            human=self.human,
            invitation=invitation,
            words="Accepted response",
            status=Response.Status.ACCEPTED,
        )
        moment = Moment.objects.create(
            accepted_response=accepted_response,
            media_room_id="test-media-room-id",
        )
        Presence.objects.create(
            moment=moment,
            human=inviter,
        )
        Presence.objects.create(
            moment=moment,
            human=self.human,
        )

        self.client.force_login(self.human.user)

        response = self.client.post(
            reverse("presence_api:invitations"),
            {
                "gesture": "Invitation",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Human has an active presence",
        )

    def test_create_invitation_returns_bad_request_when_human_has_pending_response(self):
        inviter = create_test_human(
            email="inviter@test.com",
        )
        invitation = Invitation.objects.create(
            human=inviter,
            gesture="Invitation",
        )
        Response.objects.create(
            human=self.human,
            invitation=invitation,
            words="Pending response",
        )

        self.client.force_login(self.human.user)

        response = self.client.post(
            reverse("presence_api:invitations"),
            {
                "gesture": "Own invitation",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Human has a pending response",
        )
