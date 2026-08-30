from rest_framework import status
from rest_framework.exceptions import (
    NotFound,
    ValidationError as APIValidationError,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from humans.exceptions import HumanNotFound
from humans.services import get_current_human

from presence.api.serializers import (
    CreateInvitationSerializer,
    CurrentPresenceSerializer,
    InvitationSerializer,
    SendResponseSerializer,
)
from presence.exceptions import (
    CannotRespondToOwnInvitation,
    HumanHasActivePresence,
    HumanHasOpenInvitation,
    HumanHasPendingResponse,
    InvitationNotFound,
    InvitationNotOpen,
    MomentAlreadyCompleted,
    MomentNotFound,
    NotInvitationOwner,
    NotMomentParticipant,
    NotResponseAuthor,
    ResponseNotFound,
    ResponseNotPending,
)
from presence.selectors import (
    get_current_presence_state,
    get_open_invitations_for_human,
)
from presence.services import (
    accept_response,
    cancel_response,
    close_invitation,
    complete_moment,
    create_invitation,
    create_moment_media_access,
    reject_response,
    send_response,
)


class InvitationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            human = get_current_human(
                user_id=request.user.pk,
            )
        except HumanNotFound as error:
            raise NotFound(
                {
                    "detail": "Human does not exist",
                }
            ) from error

        invitations = get_open_invitations_for_human(
            human_id=human.pk,
        )

        serializer = InvitationSerializer(
            invitations,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        serializer = CreateInvitationSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            human = get_current_human(
                user_id=request.user.pk,
            )

            invitation = create_invitation(
                human_id=human.pk,
                gesture=serializer.validated_data["gesture"],
            )

        except HumanNotFound as error:
            raise NotFound(
                {
                    "detail": "Human does not exist",
                }
            ) from error

        except HumanHasOpenInvitation as error:
            raise APIValidationError(
                {
                    "detail": "Human already has an open invitation",
                }
            ) from error

        except HumanHasActivePresence as error:
            raise APIValidationError(
                {
                    "detail": "Human has an active presence",
                }
            ) from error

        except HumanHasPendingResponse as error:
            raise APIValidationError(
                {
                    "detail": "Human has a pending response",
                }
            ) from error

        return Response(
            {
                "invitation_id": invitation.pk,
            },
            status=status.HTTP_201_CREATED,
        )


class SendResponseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, invitation_id):
        serializer = SendResponseSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            human = get_current_human(
                user_id=request.user.pk,
            )

            response = send_response(
                human_id=human.pk,
                invitation_id=invitation_id,
                words=serializer.validated_data["words"],
            )

        except HumanNotFound as error:
            raise NotFound(
                {
                    "detail": "Human does not exist",
                }
            ) from error

        except InvitationNotFound as error:
            raise NotFound(
                {
                    "detail": "Invitation does not exist",
                }
            ) from error

        except InvitationNotOpen as error:
            raise APIValidationError(
                {
                    "detail": "Invitation is not open",
                }
            ) from error

        except CannotRespondToOwnInvitation as error:
            raise APIValidationError(
                {
                    "detail": "Cannot respond to own invitation",
                }
            ) from error

        except HumanHasOpenInvitation as error:
            raise APIValidationError(
                {
                    "detail": "Human already has an open invitation",
                }
            ) from error

        except HumanHasActivePresence as error:
            raise APIValidationError(
                {
                    "detail": "Human has an active presence",
                }
            ) from error

        except HumanHasPendingResponse as error:
            raise APIValidationError(
                {
                    "detail": "Human has a pending response",
                }
            ) from error

        return Response(
            {
                "response_id": response.pk,
            },
            status=status.HTTP_201_CREATED,
        )


class RejectResponseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, response_id):
        try:
            human = get_current_human(
                user_id=request.user.pk,
            )

            response = reject_response(
                human_id=human.pk,
                response_id=response_id,
            )

        except HumanNotFound as error:
            raise NotFound(
                {
                    "detail": "Human does not exist",
                }
            ) from error

        except ResponseNotFound as error:
            raise NotFound(
                {
                    "detail": "Response does not exist",
                }
            ) from error

        except NotInvitationOwner as error:
            raise APIValidationError(
                {
                    "detail": "Only the invitation owner can reject this response",
                }
            ) from error

        except ResponseNotPending as error:
            raise APIValidationError(
                {
                    "detail": "Response is not pending",
                }
            ) from error

        return Response(
            {
                "response_id": response.pk,
                "status": response.status,
            },
            status=status.HTTP_200_OK,
        )


class AcceptResponseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, response_id):
        try:
            human = get_current_human(
                user_id=request.user.pk,
            )

            moment = accept_response(
                human_id=human.pk,
                response_id=response_id,
            )

        except HumanNotFound as error:
            raise NotFound(
                {
                    "detail": "Human does not exist",
                }
            ) from error

        except ResponseNotFound as error:
            raise NotFound(
                {
                    "detail": "Response does not exist",
                }
            ) from error

        except NotInvitationOwner as error:
            raise APIValidationError(
                {
                    "detail": "Only the invitation owner can accept this response",
                }
            ) from error

        except InvitationNotOpen as error:
            raise APIValidationError(
                {
                    "detail": "Invitation is not open",
                }
            ) from error

        except ResponseNotPending as error:
            raise APIValidationError(
                {
                    "detail": "Response is not pending",
                }
            ) from error

        return Response(
            {
                "moment_id": moment.pk,
            },
            status=status.HTTP_200_OK,
        )


class MomentMediaAccessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, moment_id):
        try:
            human = get_current_human(
                user_id=request.user.pk,
            )

            media_access = create_moment_media_access(
                human_id=human.pk,
                moment_id=moment_id,
            )

        except HumanNotFound as error:
            raise NotFound(
                {
                    "detail": "Human does not exist",
                }
            ) from error

        except MomentNotFound as error:
            raise NotFound(
                {
                    "detail": "Moment does not exist",
                }
            ) from error

        except NotMomentParticipant as error:
            raise APIValidationError(
                {
                    "detail": "Only a moment participant can access this moment",
                }
            ) from error

        except MomentAlreadyCompleted as error:
            raise APIValidationError(
                {
                    "detail": "Moment is already completed",
                }
            ) from error

        return Response(
            media_access,
            status=status.HTTP_200_OK,
        )


class CompleteMomentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, moment_id):
        try:
            human = get_current_human(
                user_id=request.user.pk,
            )

            moment = complete_moment(
                human_id=human.pk,
                moment_id=moment_id,
            )

        except HumanNotFound as error:
            raise NotFound(
                {
                    "detail": "Human does not exist",
                }
            ) from error

        except MomentNotFound as error:
            raise NotFound(
                {
                    "detail": "Moment does not exist",
                }
            ) from error

        except NotMomentParticipant as error:
            raise APIValidationError(
                {
                    "detail": "Only a moment participant can complete this moment",
                }
            ) from error

        except MomentAlreadyCompleted as error:
            raise APIValidationError(
                {
                    "detail": "Moment is already completed",
                }
            ) from error

        return Response(
            {
                "moment_id": moment.pk,
                "ended_at": moment.ended_at,
            },
            status=status.HTTP_200_OK,
        )


class CloseInvitationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, invitation_id):
        try:
            human = get_current_human(
                user_id=request.user.pk,
            )

            invitation = close_invitation(
                human_id=human.pk,
                invitation_id=invitation_id,
            )

        except HumanNotFound as error:
            raise NotFound(
                {
                    "detail": "Human does not exist",
                }
            ) from error

        except InvitationNotFound as error:
            raise NotFound(
                {
                    "detail": "Invitation does not exist",
                }
            ) from error

        except NotInvitationOwner as error:
            raise APIValidationError(
                {
                    "detail": "Only the invitation owner can close this invitation",
                }
            ) from error

        except InvitationNotOpen as error:
            raise APIValidationError(
                {
                    "detail": "Invitation is not open",
                }
            ) from error

        return Response(
            {
                "invitation_id": invitation.pk,
                "status": invitation.status,
            },
            status=status.HTTP_200_OK,
        )


class CancelResponseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, response_id):
        try:
            human = get_current_human(
                user_id=request.user.pk,
            )

            response = cancel_response(
                human_id=human.pk,
                response_id=response_id,
            )

        except HumanNotFound as error:
            raise NotFound(
                {
                    "detail": "Human does not exist",
                }
            ) from error

        except ResponseNotFound as error:
            raise NotFound(
                {
                    "detail": "Response does not exist",
                }
            ) from error

        except NotResponseAuthor as error:
            raise APIValidationError(
                {
                    "detail": "Only the response author can cancel this response",
                }
            ) from error

        except ResponseNotPending as error:
            raise APIValidationError(
                {
                    "detail": "Response is not pending",
                }
            ) from error

        return Response(
            {
                "response_id": response.pk,
                "status": response.status,
            },
            status=status.HTTP_200_OK,
        )


class CurrentPresenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            human = get_current_human(
                user_id=request.user.pk,
            )
        except HumanNotFound as error:
            raise NotFound(
                {
                    "detail": "Human does not exist",
                }
            ) from error

        current_state = get_current_presence_state(
            human_id=human.pk,
        )

        serializer = CurrentPresenceSerializer(
            current_state,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
