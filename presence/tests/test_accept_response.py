from django.test import TestCase

from humans.services import create_human

from presence.models import Invitation, Moment, Presence, Response
from presence.services import create_invitation, send_response, accept_response


class AcceptResponseTests(TestCase):
    def setUp(self):
        self.inviter = create_human(
            first_name="Inviter",
            last_name="Human",
            email="inviter@example.com",
        )

        self.responder = create_human(
            first_name="Responder",
            last_name="Human",
            email="responder@example.com",
        )

    def test_accept_response(self):
        invitation = create_invitation(
            human=self.inviter,
            gesture="Invitation",
        )

        response = send_response(
            human=self.responder,
            invitation=invitation,
            words="Response",
        )

        another_responder = create_human(
            first_name="Another",
            last_name="Responder",
            email="another-responder@example.com",
        )

        another_response = send_response(
            human=another_responder,
            invitation=invitation,
            words="Another response",
        )

        moment = accept_response(
            human=self.inviter,
            response=response,
        )

        invitation.refresh_from_db()
        response.refresh_from_db()
        another_response.refresh_from_db()

        self.assertEqual(
            invitation.status,
            Invitation.Status.MATCHED
        )
        self.assertEqual(
            response.status,
            Response.Status.ACCEPTED
        )
        self.assertEqual(
            another_response.status,
            Response.Status.CLOSED
        )
        self.assertEqual(
            moment.accepted_response,
            response
        )
        self.assertIsNone(
            moment.ended_at
        )
        self.assertSetEqual(
            set(moment.presences.values_list("human_id", flat=True)),
            {
                self.inviter.id,
                self.responder.id,
            },
        )

    def test_accept_response_raises_when_response_is_not_pending(self):
        invitation = create_invitation(
            human=self.inviter,
            gesture="Invitation",
        )

        response = Response.objects.create(
            human=self.responder,
            invitation=invitation,
            words="Response",
            status=Response.Status.CANCELLED,
        )

        with self.assertRaises(ValueError):
            accept_response(
                human=self.inviter,
                response=response,
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

    def test_accept_response_uses_database_state_when_response_instance_is_stale(self):
        invitation = create_invitation(
            human=self.inviter,
            gesture="Invitation",
        )

        response = send_response(
            human=self.responder,
            invitation=invitation,
            words="Response",
        )

        Response.objects.filter(pk=response.pk).update(
            status=Response.Status.CLOSED,
        )

        self.assertEqual(
            response.status,
            Response.Status.PENDING,
        )

        with self.assertRaises(ValueError):
            accept_response(
                human=self.inviter,
                response=response,
            )

        invitation.refresh_from_db()
        response.refresh_from_db()

        self.assertEqual(
            invitation.status,
            Invitation.Status.OPEN,
        )
        self.assertEqual(
            response.status,
            Response.Status.CLOSED,
        )
        self.assertEqual(Moment.objects.count(), 0)
        self.assertEqual(Presence.objects.count(), 0)

    def test_accept_response_raises_when_invitation_is_not_open(self):
        invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Invitation",
            status=Invitation.Status.OPEN,
        )
        response = send_response(
            human=self.responder,
            invitation=invitation,
            words="Response",
        )

        invitation.status = Invitation.Status.CLOSED
        invitation.save(update_fields=["status"])

        with self.assertRaises(ValueError):
            accept_response(
                human=self.inviter,
                response=response,
            )

        response.refresh_from_db()

        self.assertEqual(
            response.status,
            Response.Status.PENDING,
        )
        self.assertEqual(Moment.objects.count(), 0)
        self.assertEqual(Presence.objects.count(), 0)

    def test_accept_response_raises_when_human_is_not_invitation_owner(self):
        invitation = create_invitation(
            human=self.inviter,
            gesture="Invitation",
        )

        response = send_response(
            human=self.responder,
            invitation=invitation,
            words="Response",
        )

        another_human = create_human(
            first_name="Another",
            last_name="Human",
            email="another-human@example.com",
        )

        with self.assertRaises(ValueError):
            accept_response(
                human=another_human,
                response=response,
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
