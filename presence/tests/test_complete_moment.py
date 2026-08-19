from django.test import TestCase
from django.utils import timezone

from humans.tests.factories import create_test_human

from presence.models import Moment
from presence.services import create_invitation, send_response, accept_response, complete_moment


class CompleteMomentTests(TestCase):
    def setUp(self):
        self.inviter = create_test_human(
            first_name="Inviter",
            last_name="Human",
            email="inviter@example.com",
        )
        self.responder = create_test_human(
            first_name="Responder",
            last_name="Human",
            email="responder@example.com",
        )
        self.invitation = create_invitation(
            human=self.inviter,
            gesture="Invitation",
        )
        self.response = send_response(
            human=self.responder,
            invitation=self.invitation,
            words="Response",
        )
        self.moment = accept_response(
            human=self.inviter,
            response=self.response,
        )

    def test_complete_moment(self):
        complete_moment(
            human=self.inviter,
            moment=self.moment,
        )

        self.moment.refresh_from_db()

        self.assertIsNotNone(self.moment.ended_at)

    def test_complete_moment_raises_when_moment_is_already_completed(self):
        original_ended_at_time = timezone.now()

        self.moment.ended_at = original_ended_at_time
        self.moment.save(update_fields=["ended_at"])

        with self.assertRaises(ValueError):
            complete_moment(
                human=self.inviter,
                moment=self.moment,
            )

        self.moment.refresh_from_db()

        self.assertEqual(self.moment.ended_at, original_ended_at_time)

    def test_complete_moment_uses_database_state_when_moment_instance_is_stale(self):
        original_ended_at_time = timezone.now()

        Moment.objects.filter(pk=self.moment.pk).update(
            ended_at=original_ended_at_time,
        )

        self.assertIsNone(self.moment.ended_at)

        with self.assertRaises(ValueError):
            complete_moment(
                human=self.inviter,
                moment=self.moment,
            )

        self.moment.refresh_from_db()

        self.assertEqual(self.moment.ended_at, original_ended_at_time)

    def test_complete_moment_raises_when_human_is_not_participant(self):
        another_human = create_test_human(
            first_name="Another",
            last_name="Human",
            email="another-human@example.com",
        )

        with self.assertRaises(ValueError):
            complete_moment(
                human=another_human,
                moment=self.moment,
            )

        self.moment.refresh_from_db()

        self.assertIsNone(self.moment.ended_at)
