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
from presence.services import complete_moment


class CompleteMomentTests(TestCase):
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
            status = Invitation.Status.MATCHED,
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

    def test_complete_moment(self):
        complete_moment(
            human_id=self.inviter.pk,
            moment_id=self.moment.pk,
        )

        self.moment.refresh_from_db()

        self.assertIsNotNone(self.moment.ended_at)

    def test_complete_moment_raises_when_human_not_found(self):
        with self.assertRaises(HumanNotFound):
            complete_moment(
                human_id=999999,
                moment_id=self.moment.pk,
            )

        self.moment.refresh_from_db()

        self.assertIsNone(self.moment.ended_at)

    def test_complete_moment_raises_when_moment_not_found(self):
        with self.assertRaises(MomentNotFound):
            complete_moment(
                human_id=self.responder.pk,
                moment_id=999999,
            )

    def test_complete_moment_raises_when_human_is_not_participant(self):
        another_human = create_test_human(
            email="another-human@test.com",
        )

        with self.assertRaises(NotMomentParticipant):
            complete_moment(
                human_id=another_human.pk,
                moment_id=self.moment.pk,
            )

        self.moment.refresh_from_db()

        self.assertIsNone(self.moment.ended_at)

    def test_complete_moment_raises_when_moment_already_completed(self):
        original_ended_at_time = timezone.now()

        self.moment.ended_at = original_ended_at_time
        self.moment.save(update_fields=["ended_at"])

        with self.assertRaises(MomentAlreadyCompleted):
            complete_moment(
                human_id=self.inviter.pk,
                moment_id=self.moment.pk,
            )

        self.moment.refresh_from_db()

        self.assertEqual(self.moment.ended_at, original_ended_at_time)
