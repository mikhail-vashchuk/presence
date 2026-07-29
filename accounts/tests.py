from django.test import TestCase

from .models import User


class UserManagerTests(TestCase):
    def test_create_user_without_password_sets_unusable_password(self):
        user = User.objects.create_user(
            first_name="Mikhail",
            last_name="Vashchuk",
            email="mikhail@example.com",
        )

        self.assertFalse(user.has_usable_password())

    def test_create_superuser_requires_password(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                first_name="Admin",
                last_name="Human",
                email="admin@example.com",
                password=None,
            )