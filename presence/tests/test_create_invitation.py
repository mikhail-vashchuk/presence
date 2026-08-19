from uuid import uuid4

from django.test import TestCase

from humans.tests.factories import create_test_human

from presence.models import Invitation, Moment, Presence, Response
from presence.services import create_invitation


class CreateInvitationTests(TestCase):
    def setUp(self):
        self.human = create_test_human(
            first_name="Primary",
            last_name="Human",
            email="primary-human@example.com",
        )

    def test_create_invitation(self):
        invitation = create_invitation(
            human=self.human,
            gesture="Invitation",
        )

        self.assertEqual(invitation.human, self.human)
        self.assertEqual(invitation.gesture, "Invitation")
        self.assertEqual(
            invitation.status,
            Invitation.Status.OPEN,
        )

    def test_create_invitation_raises_when_human_has_open_invitation(self):
        Invitation.objects.create(
            human=self.human,
            gesture="First invitation",
            status=Invitation.Status.OPEN,
        )

        with self.assertRaises(ValueError):
            create_invitation(
                human=self.human,
                gesture="Another invitation",
            )

        self.assertEqual(
            self.human.invitations.count(),
            1,
        )

    def test_create_invitation_raises_when_human_has_active_moment(self):
        responder = create_test_human(
            first_name="Responder",
            last_name="Human",
            email="responder@example.com",
        )

        invitation = Invitation.objects.create(
            human=self.human,
            gesture="Invitation",
            status=Invitation.Status.MATCHED,
        )

        response = Response.objects.create(
            human=responder,
            invitation=invitation,
            words="Response",
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
            self.human.invitations.count(),
            1,
        )

    def test_create_invitation_raises_when_human_has_pending_response(self):
        another_inviter = create_test_human(
            first_name="Another",
            last_name="Inviter",
            email="another-inviter@example.com",
        )

        invitation = Invitation.objects.create(
            human=another_inviter,
            gesture="Invitation",
        )

        Response.objects.create(
            human=self.human,
            invitation=invitation,
            words="Response",
        )

        with self.assertRaises(ValueError):
            create_invitation(
                human=self.human,
                gesture="Another invitation",
            )

        self.assertEqual(
            self.human.invitations.count(),
            0,
        )
