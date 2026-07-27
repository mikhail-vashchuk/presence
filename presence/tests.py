from uuid import uuid4

from django.test import TestCase
from django.utils import timezone

from humans.services import register_human

from .models import Invitation, Moment, Presence, Response
from .services import create_invitation, reject_response, send_response, accept_response, complete_moment, \
    close_invitation, cancel_response


class CreateInvitationTests(TestCase):
    def setUp(self):
        self.human = register_human(
            first_name="Primary",
            last_name="Human",
            email="primary-human@example.com",
            password="test-password",
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

    def test_human_with_open_invitation_is_rejected(self):
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

    def test_human_participating_in_an_active_moment_is_rejected(self):
        responder = register_human(
            first_name="Responder",
            last_name="Human",
            email="responder@example.com",
            password="test-password",
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

    def test_human_with_pending_response_is_rejected(self):
        another_inviter = register_human(
            first_name="Another",
            last_name="Inviter",
            email="another-inviter@example.com",
            password="test-password",
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


class SendResponseTests(TestCase):
    def setUp(self):
        self.inviter = register_human(
            first_name="Inviter",
            last_name="Human",
            email="inviter@example.com",
            password="test-password",
        )

        self.responder = register_human(
            first_name="Responder",
            last_name="Human",
            email="responder@example.com",
            password="test-password",
        )

    def test_send_response(self):
        invitation = create_invitation(
            human=self.inviter,
            gesture="Invitation",
        )

        response = send_response(
            human=self.responder,
            invitation=invitation,
            words="Response",
        )

        self.assertEqual(Response.objects.count(), 1)
        self.assertEqual(response.human, self.responder)
        self.assertEqual(response.invitation, invitation)
        self.assertEqual(response.words, "Response")
        self.assertEqual(
            response.status,
            Response.Status.PENDING,
        )

    def test_closed_invitation_rejects_response(self):
        invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Invitation",
            status=Invitation.Status.CLOSED,
        )

        with self.assertRaises(ValueError):
            send_response(
                human=self.responder,
                invitation=invitation,
                words="Response",
            )

        self.assertEqual(
            self.responder.responses.count(),
            0,
        )

    def test_send_response_to_own_invitation_is_rejected(self):
        own_invitation = create_invitation(
            human=self.responder,
            gesture="Own invitation",
        )

        with self.assertRaises(ValueError):
            send_response(
                human=self.responder,
                invitation=own_invitation,
                words="Response",
            )

        self.assertEqual(
            self.responder.responses.count(),
            0,
        )

    def test_responder_with_open_invitation_is_rejected(self):
        create_invitation(
            human=self.responder,
            gesture="Responders own invitation",
        )

        another_invitation = create_invitation(
            human=self.inviter,
            gesture="Another invitation",
        )

        with self.assertRaises(ValueError):
            send_response(
                human=self.responder,
                invitation=another_invitation,
                words="Response",
            )

        self.assertEqual(
            self.responder.responses.count(),
            0,
        )

    def test_human_participating_in_an_active_moment_is_rejected(self):
        matched_invitation = Invitation.objects.create(
            human=self.inviter,
            gesture="Matched invitation",
            status=Invitation.Status.MATCHED,
        )

        accepted_response = Response.objects.create(
            human=self.responder,
            invitation=matched_invitation,
            words="Accepted response",
            status=Response.Status.ACCEPTED,
        )

        moment = Moment.objects.create(
            accepted_response=accepted_response,
            media_room_id=str(uuid4()),
        )

        Presence.objects.create(
            human=self.responder,
            moment=moment,
        )

        another_inviter = register_human(
            first_name="Another",
            last_name="Inviter",
            email="another-inviter@example.com",
            password="test-password",
        )

        another_invitation = create_invitation(
            human=another_inviter,
            gesture="Another invitation",
        )

        with self.assertRaises(ValueError):
            send_response(
                human=self.responder,
                invitation=another_invitation,
                words="Response",
            )

        self.assertEqual(
            self.responder.responses.count(),
            1,
        )

    def test_responder_with_pending_response_is_rejected(self):
        invitation = create_invitation(
            human=self.inviter,
            gesture="First invitation",
        )

        Response.objects.create(
            human=self.responder,
            invitation=invitation,
            words="Pending response",
        )

        another_inviter = register_human(
            first_name="Another",
            last_name="Inviter",
            email="another-inviter@example.com",
            password="test-password",
        )

        another_invitation = create_invitation(
            human=another_inviter,
            gesture="Another invitation",
        )

        with self.assertRaises(ValueError):
            send_response(
                human=self.responder,
                invitation=another_invitation,
                words="Another response",
            )

        self.assertEqual(
            self.responder.responses.count(),
            1,
        )


class RejectResponseTests(TestCase):
    def setUp(self):
        self.inviter = register_human(
            first_name="Inviter",
            last_name="Human",
            email="inviter@example.com",
            password="test-password",
        )

        self.responder = register_human(
            first_name="Responder",
            last_name="Human",
            email="responder@example.com",
            password="test-password",
        )

    def test_reject_response(self):
        invitation = create_invitation(
            human=self.inviter,
            gesture="Invitation",
        )

        response = send_response(
            human=self.responder,
            invitation=invitation,
            words="Response",
        )

        reject_response(
            human=self.inviter,
            response=response,
        )

        response.refresh_from_db()

        self.assertEqual(
            response.status,
            Response.Status.REJECTED,
        )

    def test_non_pending_response_cannot_be_rejected(self):
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
            reject_response(
                human=self.inviter,
                response=response,
            )

        response.refresh_from_db()

        self.assertEqual(
            response.status,
            Response.Status.CANCELLED,
        )

    def test_non_owner_cannot_reject_response(self):
        invitation = create_invitation(
            human=self.inviter,
            gesture="Invitation",
        )

        response = send_response(
            human=self.responder,
            invitation=invitation,
            words="Response",
        )

        another_human = register_human(
            first_name="Another",
            last_name="Human",
            email="another-human@example.com",
            password="test-password",
        )

        with self.assertRaises(ValueError):
            reject_response(
                human=another_human,
                response=response,
            )

        response.refresh_from_db()

        self.assertEqual(
            response.status,
            Response.Status.PENDING,
        )


class AcceptResponseTests(TestCase):
    def setUp(self):
        self.inviter = register_human(
            first_name="Inviter",
            last_name="Human",
            email="inviter@example.com",
            password="test-password",
        )

        self.responder = register_human(
            first_name="Responder",
            last_name="Human",
            email="responder@example.com",
            password="test-password",
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

        another_responder = register_human(
            first_name="Another",
            last_name="Responder",
            email="another-responder@example.com",
            password="test-password",
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

    def test_non_pending_response_cannot_be_accepted(self):
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

    def test_non_owner_cannot_accept_response(self):
        invitation = create_invitation(
            human=self.inviter,
            gesture="Invitation",
        )

        response = send_response(
            human=self.responder,
            invitation=invitation,
            words="Response",
        )

        another_human = register_human(
            first_name="Another",
            last_name="Human",
            email="another-human@example.com",
            password="test-password",
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


class CompleteMomentTests(TestCase):
    def setUp(self):
        self.inviter = register_human(
            first_name="Inviter",
            last_name="Human",
            email="inviter@example.com",
            password="test-password",
        )
        self.responder = register_human(
            first_name="Responder",
            last_name="Human",
            email="responder@example.com",
            password="test-password",
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

    def test_completed_moment_cannot_be_completed_again(self):
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

    def test_non_participant_cannot_complete_moment(self):
        another_human = register_human(
            first_name="Another",
            last_name="Human",
            email="another-human@example.com",
            password="test-password",
        )

        with self.assertRaises(ValueError):
            complete_moment(
                human=another_human,
                moment=self.moment,
            )

        self.moment.refresh_from_db()

        self.assertIsNone(self.moment.ended_at)


class CloseInvitationTests(TestCase):
    def setUp(self):
        self.inviter = register_human(
            first_name="Inviter",
            last_name="Human",
            email="inviter@example.com",
            password="test-password",
        )
        self.responder = register_human(
            first_name="Responder",
            last_name="Human",
            email="responder@example.com",
            password="test-password",
        )
        self.invitation = create_invitation(
            human=self.inviter,
            gesture="Invitation",
        )

    def test_close_invitation(self):
        response = send_response(
            human=self.responder,
            invitation=self.invitation,
            words="Response",
        )

        another_human = register_human(
            first_name="Another",
            last_name="Human",
            email="another@example.com",
            password="test-password",
        )

        another_response = send_response(
            human=another_human,
            invitation=self.invitation,
            words="Another response",
        )

        close_invitation(
            human=self.inviter,
            invitation=self.invitation,
        )

        self.invitation.refresh_from_db()
        response.refresh_from_db()
        another_response.refresh_from_db()

        self.assertEqual(
            self.invitation.status,
            Invitation.Status.CLOSED
        )
        self.assertEqual(
            response.status,
            Response.Status.CLOSED
        )
        self.assertEqual(
            another_response.status,
            Response.Status.CLOSED
        )

    def test_non_open_invitation_cannot_be_closed(self):
        self.invitation.status = Invitation.Status.MATCHED
        self.invitation.save(update_fields=["status"])

        with self.assertRaises(ValueError):
            close_invitation(
                human=self.inviter,
                invitation=self.invitation,
            )

        self.invitation.refresh_from_db()

        self.assertEqual(
            self.invitation.status,
            Invitation.Status.MATCHED
        )

    def test_non_author_cannot_close_invitation(self):
        with self.assertRaises(ValueError):
            close_invitation(
                human=self.responder,
                invitation=self.invitation,
            )

        self.invitation.refresh_from_db()

        self.assertEqual(
            self.invitation.status,
            Invitation.Status.OPEN,
        )


class CancelResponseTests(TestCase):
    def setUp(self):
        self.inviter = register_human(
            first_name="Inviter",
            last_name="Human",
            email="inviter@example.com",
            password="test-password",
        )

        self.responder = register_human(
            first_name="Responder",
            last_name="Human",
            email="responder@example.com",
            password="test-password",
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

    def test_cancel_response(self):
        cancel_response(
            human=self.responder,
            response=self.response,
        )

        self.response.refresh_from_db()

        self.assertEqual(
            self.response.status,
            Response.Status.CANCELLED
        )

    def test_non_pending_response_cannot_be_cancelled(self):
        self.response.status = Response.Status.CLOSED
        self.response.save(update_fields=["status"])

        with self.assertRaises(ValueError):
            cancel_response(
                human=self.responder,
                response=self.response,
            )

        self.response.refresh_from_db()

        self.assertEqual(
            self.response.status,
            Response.Status.CLOSED
        )

    def test_non_author_cannot_cancel_response(self):
        with self.assertRaises(ValueError):
            cancel_response(
                human=self.inviter,
                response=self.response,
            )

        self.response.refresh_from_db()

        self.assertEqual(
            self.response.status,
            Response.Status.PENDING
        )