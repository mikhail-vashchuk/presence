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
        responder = register_human(
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
        another_inviter = register_human(
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


class SendResponseTests(TestCase):
    def setUp(self):
        self.inviter = register_human(
            first_name="Inviter",
            last_name="Human",
            email="inviter@example.com",
        )

        self.responder = register_human(
            first_name="Responder",
            last_name="Human",
            email="responder@example.com",
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

    def test_send_response_raises_when_invitation_is_closed(self):
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

    def test_send_response_raises_when_invitation_belongs_to_responder(self):
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

    def test_send_response_raises_when_responder_has_open_invitation(self):
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

    def test_send_response_uses_database_state_when_invitation_instance_is_stale(self):
        invitation = create_invitation(
            human=self.inviter,
            gesture="Invitation",
        )

        Invitation.objects.filter(
            pk=invitation.pk,
        ).update(
            status=Invitation.Status.CLOSED,
        )

        self.assertEqual(
            invitation.status,
            Invitation.Status.OPEN,
        )

        with self.assertRaises(ValueError):
            send_response(
                human=self.responder,
                invitation=invitation,
                words="Response",
            )

        invitation.refresh_from_db()

        self.assertEqual(
            invitation.status,
            Invitation.Status.CLOSED,
        )
        self.assertEqual(
            Response.objects.count(),
            0,
        )

    def test_send_response_raises_when_responder_has_active_moment(self):
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

    def test_send_response_raises_when_responder_has_pending_response(self):
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
        )

        self.responder = register_human(
            first_name="Responder",
            last_name="Human",
            email="responder@example.com",
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

    def test_reject_response_raises_when_response_is_not_pending(self):
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

    def test_reject_response_uses_database_state_when_response_instance_is_stale(self):
        invitation = create_invitation(
            human=self.inviter,
            gesture="Invitation",
        )

        response = send_response(
            human=self.responder,
            invitation=invitation,
            words="Response",
        )

        Response.objects.filter(
            pk=response.pk,
        ).update(
            status=Response.Status.ACCEPTED,
        )

        self.assertEqual(
            response.status,
            Response.Status.PENDING,
        )

        with self.assertRaises(ValueError):
            reject_response(
                human=self.inviter,
                response=response,
            )

        response.refresh_from_db()

        self.assertEqual(
            response.status,
            Response.Status.ACCEPTED,
        )

    def test_reject_response_raises_when_human_is_not_invitation_owner(self):
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
        )

        self.responder = register_human(
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

        another_responder = register_human(
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

        another_human = register_human(
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


class CompleteMomentTests(TestCase):
    def setUp(self):
        self.inviter = register_human(
            first_name="Inviter",
            last_name="Human",
            email="inviter@example.com",
        )
        self.responder = register_human(
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
        another_human = register_human(
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


class CloseInvitationTests(TestCase):
    def setUp(self):
        self.inviter = register_human(
            first_name="Inviter",
            last_name="Human",
            email="inviter@example.com",
        )
        self.responder = register_human(
            first_name="Responder",
            last_name="Human",
            email="responder@example.com",
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

    def test_close_invitation_raises_when_invitation_is_not_open(self):
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

    def test_close_invitation_uses_database_state_when_invitation_instance_is_stale(self):
        Invitation.objects.filter(pk=self.invitation.pk).update(
            status=Invitation.Status.CLOSED
        )

        self.assertEqual(
            self.invitation.status,
            Invitation.Status.OPEN
        )

        with self.assertRaises(ValueError):
            close_invitation(
                human=self.inviter,
                invitation=self.invitation,
            )

        self.invitation.refresh_from_db()

        self.assertEqual(
            self.invitation.status,
            Invitation.Status.CLOSED
        )

    def test_close_invitation_raises_when_human_is_not_invitation_owner(self):
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
        )

        self.responder = register_human(
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

    def test_cancel_response_raises_when_response_is_not_pending(self):
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

    def test_cancel_response_uses_database_state_when_response_instance_is_stale(self):
        Response.objects.filter(pk=self.response.pk).update(
            status=Response.Status.CANCELLED
        )

        self.assertEqual(
            self.response.status,
            Response.Status.PENDING
        )

        with self.assertRaises(ValueError):
            cancel_response(
                human=self.responder,
                response=self.response,
            )

        self.response.refresh_from_db()

        self.assertEqual(
            self.response.status,
            Response.Status.CANCELLED
        )

    def test_cancel_response_raises_when_human_is_not_response_author(self):
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