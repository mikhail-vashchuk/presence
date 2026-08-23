from uuid import uuid4

from django.test import TestCase

from humans.exceptions import HumanNotFound
from humans.tests.factories import create_test_human

from presence.exceptions import (
    HumanHasActivePresence,
    HumanHasOpenInvitation,
    HumanHasPendingResponse,
)
from presence.models import (
    Invitation,
    Moment,
    Presence,
    Response,
)
from presence.services import create_invitation


class CreateInvitationTests(TestCase):
    def test_create_invitation_raises_when_human_does_not_exist(self):
        with self.assertRaises(HumanNotFound):
            create_invitation(
                human_id=999999,
                gesture="Invitation",
            )

    def test_create_invitation(self):
        human = create_test_human()

        invitation = create_invitation(
            human_id=human.pk,
            gesture="Invitation",
        )

        self.assertEqual(invitation.human, human)
        self.assertEqual(invitation.gesture, "Invitation")
        self.assertEqual(
            invitation.status,
            Invitation.Status.OPEN,
        )

    def test_create_invitation_raises_when_human_has_open_invitation(self):
        human = create_test_human()

        Invitation.objects.create(
            human=human,
            gesture="Invitation",
            status=Invitation.Status.OPEN,
        )

        with self.assertRaises(HumanHasOpenInvitation):
            create_invitation(
                human_id=human.pk,
                gesture="Another invitation",
            )

        self.assertEqual(
            human.invitations.count(),
            1,
        )

    def test_create_invitation_raises_when_human_has_active_presence(self):
        human = create_test_human()

        invitation = Invitation.objects.create(
            human=human,
            gesture="Invitation",
            status=Invitation.Status.MATCHED,
        )

        responder = create_test_human(
            email="responder@test.com",
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
            human=human,
            moment=moment,
        )

        with self.assertRaises(HumanHasActivePresence):
            create_invitation(
                human_id=human.pk,
                gesture="Invitation",
            )

        self.assertEqual(
            human.invitations.count(),
            1,
        )

    def test_create_invitation_raises_when_human_has_pending_response(self):
        human = create_test_human()

        another_human = create_test_human(
            email="another-human@test.com",
        )

        invitation = Invitation.objects.create(
            human=another_human,
            gesture="Invitation",
        )

        Response.objects.create(
            human=human,
            invitation=invitation,
            words="Response",
        )

        with self.assertRaises(HumanHasPendingResponse):
            create_invitation(
                human_id=human.pk,
                gesture="Another invitation",
            )

        self.assertEqual(
            human.invitations.count(),
            0,
        )
