from django.conf import settings
from django.db import models


class Human(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="human",
    )

    def __str__(self):
        return self.user.get_full_name()