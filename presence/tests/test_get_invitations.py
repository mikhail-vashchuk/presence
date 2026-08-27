from django.test import TestCase

from humans.tests.factories import create_test_human

from presence.models import Invitation
from presence.selectors import get_open_invitations_for_human


class GetOpenInvitationsForHumanTests(TestCase):
    def test_get_open_invitations_for_human(self):
        human = create_test_human()

        second_human = create_test_human(
            email="second-human@test.com",
        )
        third_human = create_test_human(
            email="third-human@test.com",
        )

        Invitation.objects.create(
            human=human,
            gesture="Own invitation",
        )

        older_open_invitation = Invitation.objects.create(
            human=second_human,
            gesture="Older open invitation",
        )

        Invitation.objects.create(
            human=second_human,
            gesture="Closed invitation",
            status=Invitation.Status.CLOSED,
        )

        newer_open_invitation = Invitation.objects.create(
            human=third_human,
            gesture="Newer open invitation",
        )

        invitations = get_open_invitations_for_human(
            human_id=human.pk,
        )

        self.assertQuerySetEqual(
            invitations,
            [
                newer_open_invitation,
                older_open_invitation,
            ],
        )
        