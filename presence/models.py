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


class Moment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"

    human = models.ForeignKey(
        Human,
        on_delete=models.PROTECT,
        related_name="moments",
    )
    gesture = models.TextField()
    media_stream = models.CharField(
        max_length=255,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    def __str__(self):
        return f"Moment #{self.pk} by {self.human}: {self.gesture[:40]}"


class Response(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        CANCELED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    human = models.ForeignKey(
        Human,
        on_delete=models.PROTECT,
        related_name="responses",
    )
    moment = models.ForeignKey(
        Moment,
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

    def __str__(self):
        return f"Response #{self.pk} by {self.human}: {self.words[:40]}"


class Presence(models.Model):
    class Role(models.TextChoices):
        AUTHOR = "author", "Author"
        PARTICIPANT = "participant", "Participant"

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
    role = models.CharField(
        max_length=12,
        choices=Role.choices,
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    def __str__(self):
        return f"{self.human} as {self.role} in Moment #{self.moment_id}"


class Memory(models.Model):
    class SourceType(models.TextChoices):
        GESTURE = "gesture", "Gesture"
        RESPONSE = "response", "Response"

    human = models.ForeignKey(
        Human,
        on_delete=models.PROTECT,
        related_name="memories",
    )
    moment = models.ForeignKey(
        Moment,
        on_delete=models.PROTECT,
        related_name="memories",
    )
    source_type = models.CharField(
        max_length=10,
        choices=SourceType.choices,
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Memory #{self.pk} from {self.human}: {self.content[:40]}"