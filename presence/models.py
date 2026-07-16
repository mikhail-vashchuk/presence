from django.conf import settings
from django.db import models


class Human(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="human",
    )
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Invitation(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        MATCHED = "matched", "Matched"
        CLOSED = "closed", "Closed"

    human = models.ForeignKey(
        Human,
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
        EXPIRED = "expired", "Expired"

    human = models.ForeignKey(
        Human,
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
        ]

    def __str__(self):
        return f"Response #{self.pk} by {self.human}: {self.words[:40]}"


class Moment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"

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
    ended_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(status="active", ended_at__isnull=True)
                    | models.Q(status="completed", ended_at__isnull=False)
                ),
                name="moment_status_matches_ended_at"
            )
        ]

    def __str__(self):
        responder = self.accepted_response.human
        inviter = self.accepted_response.invitation.human

        return (
            f"Moment #{self.pk} grown from "
            f"{responder} response to {inviter} invitation"
        )


class Presence(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"

    moment = models.ForeignKey(
        Moment,
        on_delete=models.PROTECT,
        related_name="presences",
    )
    human = models.ForeignKey(
        Human,
        on_delete=models.PROTECT,
        related_name="presences",
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["moment", "human"],
                name="unique_presence_per_moment_and_human",
            ),
            models.UniqueConstraint(
                fields=["human"],
                condition=models.Q(status="active"),
                name="unique_active_presence_per_human",
            ),
            models.CheckConstraint(
                condition=(
                        models.Q(status="active", left_at__isnull=True)
                        | models.Q(status="completed", left_at__isnull=False)
                ),
                name="presence_status_matches_left_at"
            )
        ]

    def __str__(self):
        return f"{self.human} in Moment #{self.moment.pk}"
