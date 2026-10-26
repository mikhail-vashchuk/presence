from django.test import override_settings
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from humans.tests.factories import create_test_human

from presence.models import (
    AssistantHint,
    Invitation,
    Moment,
    Presence,
    Response,
)


TOKEN = "test-assistant-token"


@override_settings(ASSISTANT_SERVICE_TOKEN=TOKEN)
class InternalAssistantAPITests(APITestCase):
    def setUp(self):
        self.inviter = create_test_human(
            email="inviter@example.com",
        )
        self.responder = create_test_human(
            email="responder@example.com",
        )
        self.invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Invitation gesture",
            status=Invitation.Status.MATCHED,
        )
        self.response = Response.objects.create(
            human=self.responder,
            invitation=self.invitation,
            words="Response words",
            status=Response.Status.ACCEPTED,
        )
        self.moment = Moment.objects.create(
            accepted_response=self.response,
            media_room_id="test-media-room-id",
        )
        self.inviter_presence = Presence.objects.create(
            moment=self.moment,
            human=self.inviter,
        )
        self.responder_presence = Presence.objects.create(
            moment=self.moment,
            human=self.responder,
        )

    def session_url(self, moment_id=None):
        return reverse(
            "presence_api:internal-assistant-session",
            kwargs={"moment_id": moment_id or self.moment.pk},
        )

    def hint_url(self, moment_id=None):
        return reverse(
            "presence_api:internal-assistant-hint",
            kwargs={"moment_id": moment_id or self.moment.pk},
        )

    def auth(self):
        return {"HTTP_AUTHORIZATION": f"Bearer {TOKEN}"}

    def give_consent(self):
        Presence.objects.filter(
            moment=self.moment,
        ).update(agent_consent=True)

    def test_get_session(self):
        self.give_consent()

        response = self.client.get(
            self.session_url(),
            **self.auth(),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "active": True,
                "gesture": "Invitation gesture",
                "words": "Response words",
                "dismissed_hint_ids": [],
            },
        )

    def test_get_session_rejects_missing_token(self):
        response = self.client.get(self.session_url())

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_get_session_rejects_wrong_token(self):
        response = self.client.get(
            self.session_url(),
            HTTP_AUTHORIZATION="Bearer wrong",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_user_session_does_not_grant_access(self):
        self.client.force_login(self.inviter.user)

        response = self.client.get(self.session_url())

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    @override_settings(ASSISTANT_SERVICE_TOKEN="")
    def test_empty_token_setting_denies_everything(self):
        response = self.client.get(
            self.session_url(),
            HTTP_AUTHORIZATION="Bearer ",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_get_session_returns_not_found_when_moment_does_not_exist(self):
        response = self.client.get(
            self.session_url(moment_id=999999),
            **self.auth(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_record_hint(self):
        self.give_consent()

        response = self.client.post(
            self.hint_url(),
            {"kind": "silence"},
            format="json",
            **self.auth(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        hint = AssistantHint.objects.get()

        self.assertEqual(response.data["hint_id"], hint.pk)
        self.assertEqual(hint.kind, "silence")

    def test_record_hint_rejects_missing_token(self):
        self.give_consent()

        response = self.client.post(
            self.hint_url(),
            {"kind": "silence"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertFalse(AssistantHint.objects.exists())

    def test_record_hint_rejects_unknown_kind(self):
        self.give_consent()

        response = self.client.post(
            self.hint_url(),
            {"kind": "joke"},
            format="json",
            **self.auth(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_record_hint_returns_bad_request_when_assistant_is_not_active(self):
        response = self.client.post(
            self.hint_url(),
            {"kind": "silence"},
            format="json",
            **self.auth(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Assistant is not active",
        )
