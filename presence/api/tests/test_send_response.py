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


class SendResponseAPITests(APITestCase):
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

    def test_send_response(self):
        self.client.force_login(self.responder.user)

        response = self.client.post(
            reverse(
                "presence_api:response-send",
                kwargs={
                    "invitation_id": self.invitation.pk,
                },
            ),
            {
                "words": "Response",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        created_response = Response.objects.get(
            pk=response.data["response_id"],
        )

        self.assertEqual(
            created_response.human,
            self.responder,
        )
        self.assertEqual(
            created_response.invitation,
            self.invitation,
        )
        self.assertEqual(
            created_response.words,
            "Response",
        )

    def test_send_response_requires_authentication(self):
        response = self.client.post(
            reverse(
                "presence_api:response-send",
                kwargs={
                    "invitation_id": self.invitation.pk,
                },
            ),
            {
                "words": "Response",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_send_response_returns_not_found_when_user_has_no_human(self):
        user = User.objects.create_user(
            email="user@test.com",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse(
                "presence_api:response-send",
                kwargs={
                    "invitation_id": self.invitation.pk,
                },
            ),
            {
                "words": "Response",
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

    def test_send_response_returns_not_found_when_invitation_does_not_exist(self):
        self.client.force_login(self.responder.user)

        response = self.client.post(
            reverse(
                "presence_api:response-send",
                kwargs={
                    "invitation_id": 999999,
                },
            ),
            {
                "words": "Response",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            response.data["detail"],
            "Invitation does not exist",
        )

    def test_send_response_returns_bad_request_when_words_are_invalid(self):
        self.client.force_login(self.responder.user)

        response = self.client.post(
            reverse(
                "presence_api:response-send",
                kwargs={
                    "invitation_id": self.invitation.pk,
                },
            ),
            {
                "words": "",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_send_response_returns_bad_request_when_invitation_is_not_open(self):
        self.invitation.status = Invitation.Status.CLOSED
        self.invitation.save(
            update_fields=["status"],
        )
        self.client.force_login(self.responder.user)

        response = self.client.post(
            reverse(
                "presence_api:response-send",
                kwargs={
                    "invitation_id": self.invitation.pk,
                },
            ),
            {
                "words": "Response",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Invitation is not open",
        )

    def test_send_response_returns_bad_request_for_own_invitation(self):
        self.client.force_login(self.inviter.user)

        response = self.client.post(
            reverse(
                "presence_api:response-send",
                kwargs={
                    "invitation_id": self.invitation.pk,
                },
            ),
            {
                "words": "Response",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Cannot respond to own invitation",
        )

    def test_send_response_returns_bad_request_when_human_has_open_invitation(self):
        Invitation.objects.create(
            human=self.responder,
            gesture="Responder invitation",
        )
        self.client.force_login(self.responder.user)

        response = self.client.post(
            reverse(
                "presence_api:response-send",
                kwargs={
                    "invitation_id": self.invitation.pk,
                },
            ),
            {
                "words": "Response",
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

    def test_send_response_returns_bad_request_when_human_has_active_presence(self):
        another_inviter = create_test_human(
            email="another-inviter@test.com",
        )
        matched_invitation = Invitation.objects.create(
            human=another_inviter,
            gesture="Matched invitation",
            status=Invitation.Status.MATCHED,
        )
        accepted_response = Response.objects.create(
            human=self.responder,
            invitation=matched_invitation,
            words="Accepted response",
            status=Response.Status.ACCEPTED,
        )
        moment = Moment.objects.create(
            accepted_response=accepted_response,
            media_room_id="test-media-room-id",
        )
        Presence.objects.create(
            moment=moment,
            human=another_inviter,
        )
        Presence.objects.create(
            moment=moment,
            human=self.responder,
        )

        self.client.force_login(self.responder.user)

        response = self.client.post(
            reverse(
                "presence_api:response-send",
                kwargs={
                    "invitation_id": self.invitation.pk,
                },
            ),
            {
                "words": "Response",
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

    def test_send_response_returns_bad_request_when_human_has_pending_response(self):
        another_inviter = create_test_human(
            email="another-inviter@test.com",
        )
        another_invitation = Invitation.objects.create(
            human=another_inviter,
            gesture="Another invitation",
        )
        Response.objects.create(
            human=self.responder,
            invitation=another_invitation,
            words="Pending response",
        )

        self.client.force_login(self.responder.user)

        response = self.client.post(
            reverse(
                "presence_api:response-send",
                kwargs={
                    "invitation_id": self.invitation.pk,
                },
            ),
            {
                "words": "Another response",
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
