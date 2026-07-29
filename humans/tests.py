from django.core.exceptions import ValidationError
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
            password="gd2g78d626i",
        )

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Human.objects.count(), 1)

        self.assertEqual(
            human.user.email,
            "mikhailvashchuk505@gmail.com",
        )
        self.assertEqual(human.user.first_name, "Mikhail")
        self.assertEqual(human.user.last_name, "Vashchuk")
        self.assertTrue(
            human.user.check_password("gd2g78d626i")
        )

    def test_register_human_raises_when_password_is_invalid(self):
        with self.assertRaises(ValidationError):
            register_human(
                first_name="Mikhail",
                last_name="Vashchuk",
                email="mikhailvashchuk505@gmail.com",
                password="12345678",
            )

        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Human.objects.count(), 0)