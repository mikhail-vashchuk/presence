from django.test import TestCase

from humans.tests.factories import create_test_human

from presence.models import (
    Invitation,
    Moment,
    Presence,
    Response,
)
from presence.selectors import get_open_invitations_for_human


class GetOpenInvitationsForHumanTests(TestCase):
    def setUp(self):
        self.human = create_test_human()

    def test_get_open_invitations_for_human(self):
        second_human = create_test_human(
            email="second-human@test.com",
        )
        third_human = create_test_human(
            email="third-human@test.com",
        )

        Invitation.objects.create(
            human=self.human,
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
            human_id=self.human.pk,
        )

        self.assertQuerySetEqual(
            invitations,
            [
                newer_open_invitation,
                older_open_invitation,
            ],
        )

    def test_get_open_invitations_for_human_when_human_has_active_moment(self):
        inviter = create_test_human(
            email="inviter@test.com",
        )
        another_human = create_test_human(
            email="another-human@test.com",
        )

        invitation = Invitation.objects.create(
            human=inviter,
            gesture="Matched invitation",
            status=Invitation.Status.MATCHED,
        )

        response = Response.objects.create(
            human=self.human,
            invitation=invitation,
            words="Accepted response",
            status=Response.Status.ACCEPTED,
        )

        moment = Moment.objects.create(
            accepted_response=response,
            media_room_id="test-media-room-id",
        )

        Presence.objects.create(
            human=self.human,
            moment=moment,
        )

        Invitation.objects.create(
            human=another_human,
            gesture="Invitation",
        )

        invitations = get_open_invitations_for_human(
            human_id=self.human.pk,
        )

        self.assertQuerySetEqual(
            invitations,
            [],
        )
