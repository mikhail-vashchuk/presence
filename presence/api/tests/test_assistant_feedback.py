from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from humans.tests.factories import create_test_human

from presence.models import (
    AssistantFeedback,
    AssistantHint,
    Invitation,
    Moment,
    Presence,
    Response,
)


class AssistantFeedbackAPITests(APITestCase):
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
        AssistantHint.objects.create(
            moment=self.moment,
            kind=AssistantHint.Kind.SILENCE,
        )

    def post(self, moment_id=None, rating="helpful"):
        return self.client.post(
            reverse(
                "presence_api:moment-assistant-feedback",
                kwargs={
                    "moment_id": moment_id or self.moment.pk,
                },
            ),
            {"rating": rating},
            format="json",
        )

    def test_send_assistant_feedback(self):
        self.client.force_login(self.inviter.user)

        response = self.post()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data,
            {
                "moment_id": self.moment.pk,
                "rating": "helpful",
            },
        )
        self.assertTrue(
            AssistantFeedback.objects.filter(
                moment=self.moment,
                human=self.inviter,
            ).exists()
        )

    def test_send_assistant_feedback_requires_authentication(self):
        response = self.post()

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_send_assistant_feedback_rejects_unknown_rating(self):
        self.client.force_login(self.inviter.user)

        response = self.post(rating="amazing")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_send_assistant_feedback_returns_not_found_when_user_has_no_human(self):
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

    def test_send_assistant_feedback_returns_not_found_when_moment_does_not_exist(self):
        self.client.force_login(self.inviter.user)

        response = self.post(moment_id=999999)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            response.data["detail"],
            "Moment does not exist",
        )

    def test_send_assistant_feedback_returns_bad_request_when_human_is_not_participant(self):
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
            "Only a moment participant can send feedback",
        )

    def test_send_assistant_feedback_returns_bad_request_when_assistant_was_silent(self):
        AssistantHint.objects.all().delete()
        self.client.force_login(self.inviter.user)

        response = self.post()

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Assistant did not take part in this moment",
        )

    def test_send_assistant_feedback_returns_bad_request_when_already_sent(self):
        self.client.force_login(self.inviter.user)
        self.post()

        response = self.post(rating="unhelpful")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Feedback is already sent",
        )
