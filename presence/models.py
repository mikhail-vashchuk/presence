from django.db import models


class Invitation(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        MATCHED = "matched", "Matched"
        CLOSED = "closed", "Closed"

    human = models.ForeignKey(
        "humans.Human",
        on_delete=models.PROTECT,
        related_name="invitations",
    )
    gesture = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["human"],
                condition=models.Q(status="open"),
                name="unique_open_invitation_per_human",
            )
        ]

    def __str__(self):
        return (
            f"Invitation #{self.pk} by {self.human}: "
            f"{self.gesture[:40]}"
        )


class Response(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"
        CLOSED = "closed", "Closed"

    human = models.ForeignKey(
        "humans.Human",
        on_delete=models.PROTECT,
        related_name="responses",
    )
    invitation = models.ForeignKey(
        Invitation,
        on_delete=models.PROTECT,
        related_name="responses",
    )
    words = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["human"],
                condition=models.Q(status="pending"),
                name="unique_pending_response_per_human",
            ),
            models.UniqueConstraint(
                fields=["invitation"],
                condition=models.Q(status="accepted"),
                name="unique_accepted_response_per_invitation",
            )
        ]

    def __str__(self):
        return f"Response #{self.pk} by {self.human}: {self.words[:40]}"


class Moment(models.Model):
    accepted_response = models.OneToOneField(
        Response,
        on_delete=models.PROTECT,
        related_name="moment",
    )
    media_room_id = models.CharField(
        max_length=255,
        unique=True,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        responder = self.accepted_response.human
        inviter = self.accepted_response.invitation.human

        return (
            f"Moment #{self.pk} grown from "
            f"{responder} response to {inviter} invitation"
        )


class Presence(models.Model):
    moment = models.ForeignKey(
        Moment,
        on_delete=models.PROTECT,
        related_name="presences",
    )
    human = models.ForeignKey(
        "humans.Human",
        on_delete=models.PROTECT,
        related_name="presences",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["moment", "human"],
                name="unique_presence_per_moment_and_human",
            )
        ]

    def __str__(self):
        return f"{self.human} in Moment #{self.moment.pk}"
