from django.test import TestCase
from django.utils import timezone

from humans.exceptions import HumanNotFound
from humans.tests.factories import create_test_human

from presence.exceptions import (
    AssistantFeedbackAlreadySent,
    MomentNotFound,
    NoAssistantHints,
    NotMomentParticipant,
)
from presence.models import (
    AssistantFeedback,
    AssistantHint,
    Invitation,
    Moment,
    Presence,
    Response,
)
from presence.services import send_assistant_feedback


class SendAssistantFeedbackTests(TestCase):
    def setUp(self):
        self.inviter = create_test_human(
            email="inviter@example.com",
        )
        self.responder = create_test_human(
            email="responder@example.com",
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
        self.inviter_presence = Presence.objects.create(
            moment=self.moment,
            human=self.inviter,
        )
        self.responder_presence = Presence.objects.create(
            moment=self.moment,
            human=self.responder,
        )
        AssistantHint.objects.create(
            moment=self.moment,
            kind=AssistantHint.Kind.SILENCE,
        )

    def test_send_assistant_feedback(self):
        feedback = send_assistant_feedback(
            human_id=self.inviter.pk,
            moment_id=self.moment.pk,
            rating=AssistantFeedback.Rating.HELPFUL,
        )

        self.assertEqual(feedback.human, self.inviter)
        self.assertEqual(feedback.moment, self.moment)
        self.assertEqual(
            feedback.rating,
            AssistantFeedback.Rating.HELPFUL,
        )

    def test_send_assistant_feedback_after_moment_is_completed(self):
        self.moment.ended_at = timezone.now()
        self.moment.save(update_fields=["ended_at"])

        feedback = send_assistant_feedback(
            human_id=self.responder.pk,
            moment_id=self.moment.pk,
            rating=AssistantFeedback.Rating.NEUTRAL,
        )

        self.assertEqual(feedback.human, self.responder)

    def test_both_participants_can_send_feedback(self):
        send_assistant_feedback(
            human_id=self.inviter.pk,
            moment_id=self.moment.pk,
            rating=AssistantFeedback.Rating.HELPFUL,
        )
        send_assistant_feedback(
            human_id=self.responder.pk,
            moment_id=self.moment.pk,
            rating=AssistantFeedback.Rating.UNHELPFUL,
        )

        self.assertEqual(
            AssistantFeedback.objects.count(),
            2,
        )

    def test_send_assistant_feedback_raises_when_human_not_found(self):
        with self.assertRaises(HumanNotFound):
            send_assistant_feedback(
                human_id=999999,
                moment_id=self.moment.pk,
                rating=AssistantFeedback.Rating.HELPFUL,
            )

    def test_send_assistant_feedback_raises_when_moment_not_found(self):
        with self.assertRaises(MomentNotFound):
            send_assistant_feedback(
                human_id=self.inviter.pk,
                moment_id=999999,
                rating=AssistantFeedback.Rating.HELPFUL,
            )

    def test_send_assistant_feedback_raises_when_human_is_not_participant(self):
        human = create_test_human(
            email="other-human@example.com",
        )

        with self.assertRaises(NotMomentParticipant):
            send_assistant_feedback(
                human_id=human.pk,
                moment_id=self.moment.pk,
                rating=AssistantFeedback.Rating.HELPFUL,
            )

    def test_send_assistant_feedback_raises_when_assistant_was_silent(self):
        AssistantHint.objects.all().delete()

        with self.assertRaises(NoAssistantHints):
            send_assistant_feedback(
                human_id=self.inviter.pk,
                moment_id=self.moment.pk,
                rating=AssistantFeedback.Rating.HELPFUL,
            )

    def test_send_assistant_feedback_raises_when_already_sent(self):
        send_assistant_feedback(
            human_id=self.inviter.pk,
            moment_id=self.moment.pk,
            rating=AssistantFeedback.Rating.HELPFUL,
        )

        with self.assertRaises(AssistantFeedbackAlreadySent):
            send_assistant_feedback(
                human_id=self.inviter.pk,
                moment_id=self.moment.pk,
                rating=AssistantFeedback.Rating.UNHELPFUL,
            )

        self.assertEqual(
            AssistantFeedback.objects.count(),
            1,
        )
