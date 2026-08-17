from django.test import TestCase

from accounts.models import User


class UserManagerTests(TestCase):
    def test_create_user_without_password_sets_unusable_password(self):
        user = User.objects.create_user(
            email="human@example.com",
        )

        self.assertFalse(user.has_usable_password())

    def test_create_superuser_requires_password(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="admin@example.com",
                password=None,
            )