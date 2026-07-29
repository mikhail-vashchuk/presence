from django.test import TestCase

from accounts.models import User

from .models import Human
from .services import register_human


class RegistrationTests(TestCase):
    def test_register_human_creates_user_and_human(self):
        human = register_human(
            first_name="Mikhail",
            last_name="Vashchuk",
            email="mikhailvashchuk505@gmail.com",
        )

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Human.objects.count(), 1)

        self.assertEqual(
            human.user.email,
            "mikhailvashchuk505@gmail.com",
        )
        self.assertEqual(
            human.user.first_name,
            "Mikhail",
        )
        self.assertEqual(
            human.user.last_name,
            "Vashchuk",
        )
        self.assertFalse(
            human.user.has_usable_password(),
        )