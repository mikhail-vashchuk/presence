from django.test import TestCase
from django.contrib.auth import get_user_model
from uuid import uuid4

from .models import Human, Invitation, Response, Moment, Presence
from .services import create_invitation


class CreateInvitationTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="mikhail",
            password="test-password",
        )
        self.human = Human.objects.create(
            user=user,
            name="Mikhail",
        )

    def test_create_invitation(self):
        invitation = create_invitation(
            human=self.human,
            gesture="I just want to feel a person near me.",
        )

        self.assertEqual(invitation.human, self.human)
        self.assertEqual(
            invitation.gesture,
            "I just want to feel a person near me.",
        )
        self.assertEqual(
            invitation.status,
            Invitation.Status.OPEN,
        )

    def test_empty_gesture_is_rejected(self):
        with self.assertRaises(ValueError):
            create_invitation(
                human=self.human,
                gesture="   ",
            )

        self.assertFalse(
            Invitation.objects.filter(
                human=self.human,
            ).exists()
        )

    def test_non_string_gesture_is_rejected(self):
        with self.assertRaises(TypeError):
            create_invitation(
                human=self.human,
                gesture=1,
            )

        self.assertFalse(
            Invitation.objects.filter(
                human=self.human,
            ).exists()
        )

    def test_human_with_open_invitation_is_rejected(self):
        create_invitation(
            human=self.human,
            gesture="I'm smiling to myself in mirror, I would like to smile with you too!",
        )
        with self.assertRaises(ValueError):
            create_invitation(
                human=self.human,
                gesture="I'm smiling to myself in mirror, I would like to smile with you too!",
            )

        self.assertEqual(
            Invitation.objects.filter(
                human=self.human,
            ).count(),
            1,
        )

    def test_human_with_active_presence_is_rejected(self):
        responder_user = get_user_model().objects.create_user(
            username="responder",
            password="test-password",
        )
        responder = Human.objects.create(
            user=responder_user,
            name="Responder",
        )

        invitation = Invitation.objects.create(
            human=self.human,
            gesture="A quiet invitation",
            status=Invitation.Status.MATCHED,
        )
        response = Response.objects.create(
            human=responder,
            invitation=invitation,
            words="I would like to join you.",
            status=Response.Status.ACCEPTED,
        )
        moment = Moment.objects.create(
            accepted_response=response,
            media_room_id=str(uuid4()),
        )
        Presence.objects.create(
            human=self.human,
            moment=moment,
        )

        with self.assertRaises(ValueError):
            create_invitation(
                human=self.human,
                gesture="Another invitation",
            )

        self.assertEqual(
            Invitation.objects.filter(
                human=self.human,
                status=Invitation.Status.OPEN,
            ).count(),
            0,
        )

    def test_human_with_pending_response_is_rejected(self):
        inviter_user = get_user_model().objects.create_user(
            username="inviter",
            password="test-password",
        )
        inviter = Human.objects.create(
            user=inviter_user,
            name="Inviter",
        )
        invitation = Invitation.objects.create(
            human=inviter,
            gesture="A quiet invitation",
        )
        Response.objects.create(
            human=self.human,
            invitation=invitation,
            words="I would like to join you.",
        )

        with self.assertRaises(ValueError):
            create_invitation(
                human=self.human,
                gesture="My own invitation",
            )

        self.assertEqual(
            Invitation.objects.filter(
                human=self.human,
            ).count(),
            0,
        )
