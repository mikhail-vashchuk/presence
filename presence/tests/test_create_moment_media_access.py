from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from humans.exceptions import HumanNotFound
from humans.tests.factories import create_test_human

from presence.exceptions import (
    MomentAlreadyCompleted,
    MomentNotFound,
    NotMomentParticipant,
)
from presence.models import (
    Invitation,
    Moment,
    Presence,
    Response,
)
from presence.services import create_moment_media_access


class CreateMomentMediaAccessTests(TestCase):
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
            status=Invitation.Status.MATCHED,
        )
        self.response = Response.objects.create(
            human=self.responder,
            invitation=self.invitation,
            words="Response",
            status=Response.Status.ACCEPTED,
        )
        self.moment = Moment.objects.create(
            accepted_response=self.response,
            media_room_id="test_media_room_id",
        )
        Presence.objects.create(
            moment=self.moment,
            human=self.inviter,
        )
        Presence.objects.create(
            moment=self.moment,
            human=self.responder,
        )

    @patch("presence.services.issue_media_access")
    def test_create_moment_media_access(self, issue_media_access_mock):
        issue_media_access_mock.return_value = {
            "server_url": "wss://example.livekit.cloud",
            "participant_token": "test-token",
        }

        media_access = create_moment_media_access(
            human_id=self.inviter.pk,
            moment_id=self.moment.pk,
        )

        inviter_presence = Presence.objects.get(
            moment=self.moment,
            human=self.inviter,
        )

        issue_media_access_mock.assert_called_once_with(
            room_id=self.moment.media_room_id,
            participant_identity=f"presence-{inviter_presence.pk}",
        )

        self.assertEqual(
            media_access,
            {
                "server_url": "wss://example.livekit.cloud",
                "participant_token": "test-token",
            },
        )

    def test_create_moment_media_access_raises_when_human_not_found(self):
        with self.assertRaises(HumanNotFound):
            create_moment_media_access(
                human_id=999999,
                moment_id=self.moment.pk,
            )

    def test_create_moment_media_access_raises_when_moment_not_found(self):
        with self.assertRaises(MomentNotFound):
            create_moment_media_access(
                human_id=self.inviter.pk,
                moment_id=999999,
            )

    def test_create_moment_media_access_raises_when_human_is_not_participant(self):
        another_human = create_test_human(
            email="another-human@test.com",
        )

        with self.assertRaises(NotMomentParticipant):
            create_moment_media_access(
                human_id=another_human.pk,
                moment_id=self.moment.pk,
            )

    def test_create_moment_media_access_raises_when_moment_already_completed(self):
        self.moment.ended_at = timezone.now()
        self.moment.save(update_fields=["ended_at"])

        with self.assertRaises(MomentAlreadyCompleted):
            create_moment_media_access(
                human_id=self.inviter.pk,
                moment_id=self.moment.pk,
            )