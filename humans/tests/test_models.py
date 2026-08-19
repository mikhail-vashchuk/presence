from django.db.models.deletion import ProtectedError
from django.test import TestCase

from accounts.models import User
from humans.models import Human


class HumanDeletionPolicyTests(TestCase):
    def test_user_cannot_be_deleted_while_human_exists(self):
        user = User.objects.create_user(
            email="human@example.com",
        )
        Human.objects.create(
            user=user,
            first_name="My",
            last_name="Human",
        )

        with self.assertRaises(ProtectedError):
            user.delete()

        self.assertTrue(
            User.objects.filter(pk=user.pk).exists()
        )