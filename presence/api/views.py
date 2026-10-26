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

from presence.api.permissions import HasAssistantServiceToken
from presence.api.serializers import (
    AgentConsentSerializer,
    AssistantFeedbackSerializer,
    CreateInvitationSerializer,
    CurrentPresenceSerializer,
    InvitationSerializer,
    RecordAssistantHintSerializer,
    SendResponseSerializer,
)
from presence.exceptions import (
    AssistantFeedbackAlreadySent,
    AssistantHintNotFound,
    AssistantNotActive,
    CannotRespondToOwnInvitation,
    HumanHasActivePresence,
    HumanHasOpenInvitation,
    HumanHasPendingResponse,
    InvitationNotFound,
    InvitationNotOpen,
    MomentAlreadyCompleted,
    MomentNotFound,
    NoAssistantHints,
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
    dismiss_assistant_hint,
    get_assistant_session,
    record_assistant_hint,
    reject_response,
    send_assistant_feedback,
    send_response,
    set_agent_consent,
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



class AgentConsentView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, moment_id):
        serializer = AgentConsentSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            human = get_current_human(
                user_id=request.user.pk,
            )

            assistant_state = set_agent_consent(
                human_id=human.pk,
                moment_id=moment_id,
                consent=serializer.validated_data["consent"],
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
                    "detail": "Only a moment participant can set agent consent",
                }
            ) from error

        except MomentAlreadyCompleted as error:
            raise APIValidationError(
                {
                    "detail": "Moment is already completed",
                }
            ) from error

        return Response(
            assistant_state,
            status=status.HTTP_200_OK,
        )


class DismissAssistantHintView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, hint_id):
        try:
            human = get_current_human(
                user_id=request.user.pk,
            )

            hint = dismiss_assistant_hint(
                human_id=human.pk,
                hint_id=hint_id,
            )

        except HumanNotFound as error:
            raise NotFound(
                {
                    "detail": "Human does not exist",
                }
            ) from error

        except AssistantHintNotFound as error:
            raise NotFound(
                {
                    "detail": "Assistant hint does not exist",
                }
            ) from error

        except NotMomentParticipant as error:
            raise APIValidationError(
                {
                    "detail": "Only a moment participant can dismiss this hint",
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
                "hint_id": hint.pk,
                "dismissed_at": hint.dismissed_at,
            },
            status=status.HTTP_200_OK,
        )


class AssistantFeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, moment_id):
        serializer = AssistantFeedbackSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            human = get_current_human(
                user_id=request.user.pk,
            )

            feedback = send_assistant_feedback(
                human_id=human.pk,
                moment_id=moment_id,
                rating=serializer.validated_data["rating"],
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
                    "detail": "Only a moment participant can send feedback",
                }
            ) from error

        except NoAssistantHints as error:
            raise APIValidationError(
                {
                    "detail": "Assistant did not take part in this moment",
                }
            ) from error

        except AssistantFeedbackAlreadySent as error:
            raise APIValidationError(
                {
                    "detail": "Feedback is already sent",
                }
            ) from error

        return Response(
            {
                "moment_id": feedback.moment_id,
                "rating": feedback.rating,
            },
            status=status.HTTP_201_CREATED,
        )


class AssistantSessionView(APIView):
    authentication_classes = []
    permission_classes = [HasAssistantServiceToken]

    def get(self, request, moment_id):
        try:
            session = get_assistant_session(
                moment_id=moment_id,
            )

        except MomentNotFound as error:
            raise NotFound(
                {
                    "detail": "Moment does not exist",
                }
            ) from error

        return Response(
            session,
            status=status.HTTP_200_OK,
        )


class RecordAssistantHintView(APIView):
    authentication_classes = []
    permission_classes = [HasAssistantServiceToken]

    def post(self, request, moment_id):
        serializer = RecordAssistantHintSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            hint = record_assistant_hint(
                moment_id=moment_id,
                kind=serializer.validated_data["kind"],
            )

        except MomentNotFound as error:
            raise NotFound(
                {
                    "detail": "Moment does not exist",
                }
            ) from error

        except MomentAlreadyCompleted as error:
            raise APIValidationError(
                {
                    "detail": "Moment is already completed",
                }
            ) from error

        except AssistantNotActive as error:
            raise APIValidationError(
                {
                    "detail": "Assistant is not active",
                }
            ) from error

        return Response(
            {
                "hint_id": hint.pk,
            },
            status=status.HTTP_201_CREATED,
        )
