class PresenceError(Exception):
    pass


class CannotRespondToOwnInvitation(PresenceError):
    pass


class HumanHasActivePresence(PresenceError):
    pass


class HumanHasOpenInvitation(PresenceError):
    pass


class HumanHasPendingResponse(PresenceError):
    pass


class InvitationNotFound(PresenceError):
    pass


class InvitationNotOpen(PresenceError):
    pass


class MomentNotFound(PresenceError):
    pass


class MomentAlreadyCompleted(PresenceError):
    pass


class NotInvitationOwner(PresenceError):
    pass


class NotMomentParticipant(PresenceError):
    pass


class NotResponseAuthor(PresenceError):
    pass


class ResponseNotFound(PresenceError):
    pass


class ResponseNotPending(PresenceError):
    pass