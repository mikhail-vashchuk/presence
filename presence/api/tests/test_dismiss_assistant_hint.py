from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from humans.tests.factories import create_test_human

from presence.models import (
    AssistantHint,
    Invitation,
    Moment,
    Presence,
    Response,
)


class DismissAssistantHintAPITests(APITestCase):
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
        self.hint = AssistantHint.objects.create(
            moment=self.moment,
            kind=AssistantHint.Kind.SILENCE,
        )

    def post(self, hint_id=None):
        return self.client.post(
            reverse(
                "presence_api:assistant-hint-dismiss",
                kwargs={
                    "hint_id": hint_id or self.hint.pk,
                },
            ),
            format="json",
        )

    def test_dismiss_assistant_hint(self):
        self.client.force_login(self.responder.user)

        response = self.post()

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.hint.refresh_from_db()

        self.assertEqual(response.data["hint_id"], self.hint.pk)
        self.assertIsNotNone(self.hint.dismissed_at)

    def test_dismiss_assistant_hint_requires_authentication(self):
        response = self.post()

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_dismiss_assistant_hint_returns_not_found_when_user_has_no_human(self):
        user = User.objects.create_user(
            email="user@example.com",
        )
        self.client.force_login(user)

        response = self.post()

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            response.data["detail"],
            "Human does not exist",
        )

    def test_dismiss_assistant_hint_returns_not_found_when_hint_does_not_exist(self):
        self.client.force_login(self.inviter.user)

        response = self.post(hint_id=999999)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            response.data["detail"],
            "Assistant hint does not exist",
        )

    def test_dismiss_assistant_hint_returns_bad_request_when_human_is_not_participant(self):
        human = create_test_human(
            email="other-human@example.com",
        )
        self.client.force_login(human.user)

        response = self.post()

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Only a moment participant can dismiss this hint",
        )

    def test_dismiss_assistant_hint_returns_bad_request_when_moment_is_completed(self):
        self.moment.ended_at = timezone.now()
        self.moment.save(update_fields=["ended_at"])
        self.client.force_login(self.inviter.user)

        response = self.post()

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Moment is already completed",
        )
