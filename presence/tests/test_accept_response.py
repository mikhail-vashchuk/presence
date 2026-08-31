from django.test import TestCase

from humans.exceptions import HumanNotFound
from humans.tests.factories import create_test_human

from presence.exceptions import (
    ResponseNotFound,
    NotInvitationOwner,
    InvitationNotOpen,
    ResponseNotPending
)
from presence.models import (
    Invitation,
    Moment,
    Presence,
    Response
)
from presence.services import accept_response


class AcceptResponseTests(TestCase):
    def setUp(self):
        self.inviter = create_test_human(
            email="inviter@example.com",
        )

        self.responder = create_test_human(
            email="responder@example.com",
        )

    def test_accept_response(self):
        invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Invitation",
        )

        response = Response.objects.create(
            human=self.responder,
            invitation=invitation,
            words="Response",
        )

        another_responder = create_test_human(
            email="another-responder@example.com",
        )

        another_response = Response.objects.create(
            human=another_responder,
            invitation=invitation,
            words="Another response",
        )

        moment = accept_response(
            human_id=self.inviter.pk,
            response_id=response.pk,
        )

        invitation.refresh_from_db()
        response.refresh_from_db()
        another_response.refresh_from_db()

        self.assertEqual(
            response.status,
            Response.Status.ACCEPTED
        )
        self.assertEqual(
            another_response.status,
            Response.Status.CLOSED
        )
        self.assertEqual(
            invitation.status,
            Invitation.Status.MATCHED
        )
        self.assertEqual(
            moment.accepted_response,
            response
        )
        self.assertSetEqual(
            set(moment.presences.values_list("human_id", flat=True)),
            {
                self.inviter.pk,
                self.responder.pk,
            },
        )

    def test_accept_response_raises_when_human_not_found(self):
        invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Invitation",
        )

        response = Response.objects.create(
            human=self.responder,
            invitation=invitation,
            words="Response",
        )

        with self.assertRaises(HumanNotFound):
            accept_response(
                human_id=999999,
                response_id=response.pk,
            )

        invitation.refresh_from_db()
        response.refresh_from_db()

        self.assertEqual(
            invitation.status,
            Invitation.Status.OPEN,
        )
        self.assertEqual(
            response.status,
            Response.Status.PENDING,
        )
        self.assertEqual(Moment.objects.count(), 0)
        self.assertEqual(Presence.objects.count(), 0)

    def test_accept_response_raises_when_response_not_found(self):
        with self.assertRaises(ResponseNotFound):
            accept_response(
                human_id=self.inviter.pk,
                response_id=999999,
            )

    def test_accept_response_raises_when_human_is_not_invitation_owner(self):
        invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Invitation",
        )

        response = Response.objects.create(
            human=self.responder,
            invitation=invitation,
            words="Response",
        )

        another_human = create_test_human(
            email="another-human@example.com",
        )

        with self.assertRaises(NotInvitationOwner):
            accept_response(
                human_id=another_human.pk,
                response_id=response.pk,
            )

        invitation.refresh_from_db()
        response.refresh_from_db()

        self.assertEqual(
            invitation.status,
            Invitation.Status.OPEN,
        )
        self.assertEqual(
            response.status,
            Response.Status.PENDING,
        )
        self.assertEqual(Moment.objects.count(), 0)
        self.assertEqual(Presence.objects.count(), 0)

    def test_accept_response_raises_when_invitation_is_not_open(self):
        invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Invitation",
            status=Invitation.Status.OPEN,
        )
        response = Response.objects.create(
            human=self.responder,
            invitation=invitation,
            words="Response",
        )

        invitation.status = Invitation.Status.CLOSED
        invitation.save(update_fields=["status"])

        with self.assertRaises(InvitationNotOpen):
            accept_response(
                human_id=self.inviter.pk,
                response_id=response.pk,
            )

        response.refresh_from_db()

        self.assertEqual(
            response.status,
            Response.Status.PENDING,
        )
        self.assertEqual(Moment.objects.count(), 0)
        self.assertEqual(Presence.objects.count(), 0)

    def test_accept_response_raises_when_response_is_not_pending(self):
        invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Invitation",
        )

        response = Response.objects.create(
            human=self.responder,
            invitation=invitation,
            words="Response",
            status=Response.Status.CANCELLED,
        )

        with self.assertRaises(ResponseNotPending):
            accept_response(
                human_id=self.inviter.pk,
                response_id=response.pk,
            )

        invitation.refresh_from_db()
        response.refresh_from_db()

        self.assertEqual(
            invitation.status,
            Invitation.Status.OPEN,
        )
        self.assertEqual(
            response.status,
            Response.Status.CANCELLED,
        )
        self.assertEqual(Moment.objects.count(), 0)
        self.assertEqual(Presence.objects.count(), 0)
