from .models import Human, Invitation, Response, Moment, Presence


def create_invitation(human, gesture):
    if not isinstance(gesture, str):
        raise TypeError("Gesture must be a string.")

    gesture = gesture.strip()

    if not gesture:
        raise ValueError("Gesture cannot be empty.")

    if human.invitations.filter(
        status=Invitation.Status.OPEN,
    ).exists():
        raise ValueError("Human already has an open invitation.")

    if human.presences.filter(
        status=Presence.Status.ACTIVE,
    ).exists():
        raise ValueError("Human is already in an active presence.")

    if human.responses.filter(
        status=Response.Status.PENDING,
    ).exists():
        raise ValueError("Human has a pending response.")

    return Invitation.objects.create(
        human=human,
        gesture=gesture
    )
