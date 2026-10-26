from django.urls import path

from presence.api.views import (
    AcceptResponseView,
    AgentConsentView,
    AssistantFeedbackView,
    AssistantSessionView,
    CancelResponseView,
    CloseInvitationView,
    CompleteMomentView,
    CurrentPresenceView,
    DismissAssistantHintView,
    InvitationsView,
    MomentMediaAccessView,
    RecordAssistantHintView,
    RejectResponseView,
    SendResponseView,
)


app_name = "presence_api"


urlpatterns = [
    path(
        "invitations/",
        InvitationsView.as_view(),
        name="invitations",
    ),
    path(
        "invitations/<int:invitation_id>/responses/",
        SendResponseView.as_view(),
        name="response-send",
    ),
    path(
        "responses/<int:response_id>/reject/",
        RejectResponseView.as_view(),
        name="response-reject",
    ),
    path(
        "responses/<int:response_id>/accept/",
        AcceptResponseView.as_view(),
        name="response-accept",
    ),
    path(
        "moments/<int:moment_id>/media-access/",
        MomentMediaAccessView.as_view(),
        name="moment-media-access",
    ),
    path(
        "moments/<int:moment_id>/complete/",
        CompleteMomentView.as_view(),
        name="moment-complete",
    ),
    path(
        "moments/<int:moment_id>/agent-consent/",
        AgentConsentView.as_view(),
        name="moment-agent-consent",
    ),
    path(
        "moments/<int:moment_id>/assistant-feedback/",
        AssistantFeedbackView.as_view(),
        name="moment-assistant-feedback",
    ),
    path(
        "assistant-hints/<int:hint_id>/dismiss/",
        DismissAssistantHintView.as_view(),
        name="assistant-hint-dismiss",
    ),
    path(
        "internal/moments/<int:moment_id>/assistant/",
        AssistantSessionView.as_view(),
        name="internal-assistant-session",
    ),
    path(
        "internal/moments/<int:moment_id>/assistant-hints/",
        RecordAssistantHintView.as_view(),
        name="internal-assistant-hint",
    ),
    path(
        "invitations/<int:invitation_id>/close/",
        CloseInvitationView.as_view(),
        name="invitation-close",
    ),
    path(
        "responses/<int:response_id>/cancel/",
        CancelResponseView.as_view(),
        name="response-cancel",
    ),
    path(
        "current/",
        CurrentPresenceView.as_view(),
        name="current",
    ),
]
