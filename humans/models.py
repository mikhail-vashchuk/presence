from django.conf import settings
from django.db import models


class Human(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="human",
    )

    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.get_full_name()