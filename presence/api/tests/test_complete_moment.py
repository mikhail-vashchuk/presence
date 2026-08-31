from django.urls import reverse
from django.utils import timezone

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


class CompleteMomentAPITests(APITestCase):
    def setUp(self):
        self.inviter = create_test_human(
            email="inviter@example.com",
        )
        self.responder = create_test_human(
            email="responder@example.com",
        )
        invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Invitation",
            status=Invitation.Status.MATCHED,
        )
        accepted_response = Response.objects.create(
            human=self.responder,
            invitation=invitation,
            words="Response",
            status=Response.Status.ACCEPTED,
        )
        self.moment = Moment.objects.create(
            accepted_response=accepted_response,
            media_room_id="test-media-room-id",
        )
        Presence.objects.create(
            moment=self.moment,
            human=self.inviter,
        )
        Presence.objects.create(
            moment=self.moment,
            human=self.responder,
        )

    def test_complete_moment(self):
        self.client.force_login(self.inviter.user)

        response = self.client.post(
            reverse(
                "presence_api:moment-complete",
                kwargs={
                    "moment_id": self.moment.pk,
                },
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.moment.refresh_from_db()

        self.assertEqual(
            response.data["moment_id"],
            self.moment.pk,
        )
        self.assertIsNotNone(
            self.moment.ended_at,
        )

    def test_complete_moment_requires_authentication(self):
        response = self.client.post(
            reverse(
                "presence_api:moment-complete",
                kwargs={
                    "moment_id": self.moment.pk,
                },
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_complete_moment_returns_not_found_when_user_has_no_human(self):
        user = User.objects.create_user(
            email="user@example.com",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse(
                "presence_api:moment-complete",
                kwargs={
                    "moment_id": self.moment.pk,
                },
            ),
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

    def test_complete_moment_returns_not_found_when_moment_does_not_exist(self):
        self.client.force_login(self.inviter.user)

        response = self.client.post(
            reverse(
                "presence_api:moment-complete",
                kwargs={
                    "moment_id": 999999,
                },
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            response.data["detail"],
            "Moment does not exist",
        )

    def test_complete_moment_returns_bad_request_when_human_is_not_participant(self):
        human = create_test_human(
            email="other-human@example.com",
        )
        self.client.force_login(human.user)

        response = self.client.post(
            reverse(
                "presence_api:moment-complete",
                kwargs={
                    "moment_id": self.moment.pk,
                },
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Only a moment participant can complete this moment",
        )

    def test_complete_moment_returns_bad_request_when_moment_is_already_completed(self):
        self.moment.ended_at = timezone.now()
        self.moment.save(
            update_fields=["ended_at"],
        )
        self.client.force_login(self.inviter.user)

        response = self.client.post(
            reverse(
                "presence_api:moment-complete",
                kwargs={
                    "moment_id": self.moment.pk,
                },
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Moment is already completed",
        )
