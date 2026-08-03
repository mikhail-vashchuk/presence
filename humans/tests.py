from datetime import timedelta

from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.utils import timezone

from accounts.models import User, EmailVerification
from accounts.services import verify_registration_code

from humans.models import Human
from humans.services import create_human, complete_registration


class CreateHumanTests(TestCase):
    def test_create_human_creates_user_and_human(self):
        human = create_human(
            first_name="My",
            last_name="Human",
            email="human@example.com",
        )

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Human.objects.count(), 1)

        self.assertEqual(
            human.user.email,
            "human@example.com",
        )
        self.assertEqual(
            human.user.first_name,
            "My",
        )
        self.assertEqual(
            human.user.last_name,
            "Human",
        )
        self.assertFalse(
            human.user.has_usable_password(),
        )


class CompleteRegistrationTests(TestCase):
    def setUp(self):
       self.verification = EmailVerification.objects.create(
           email="human@example.com",
           code_hash=make_password("123456"),
           expires_at=timezone.now() + timedelta(minutes=5),
       )

    def test_complete_registration_creates_user_and_human(self):
        verify_registration_code(
            verification_id=self.verification.pk,
            users_code="123456"
        )

        human =  complete_registration(
            verification_id=self.verification.pk,
            first_name="My",
            last_name="Human",
        )

        self.assertEqual(Human.objects.count(), 1)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(human.user.email, "human@example.com")
        self.assertEqual(human.user.first_name, "My")
        self.assertEqual(human.user.last_name, "Human")
        self.assertEqual(EmailVerification.objects.count(), 0)

    def test_complete_registration_raises_when_email_is_not_verified(self):
        self.assertIsNone(self.verification.verified_at)

        with self.assertRaises(ValidationError):
            complete_registration(
                verification_id=self.verification.pk,
                first_name="My",
                last_name="Human",
            )

        self.assertEqual(Human.objects.count(), 0)
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(EmailVerification.objects.count(), 1)

    def test_complete_registration_raises_when_email_is_already_registered(self):
        verify_registration_code(
            verification_id=self.verification.pk,
            users_code="123456",
        )

        User.objects.create_user(
            first_name="Existing",
            last_name="User",
            email="human@example.com",
        )

        with self.assertRaises(ValidationError):
            complete_registration(
                verification_id=self.verification.pk,
                first_name="My",
                last_name="Human",
            )

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Human.objects.count(), 0)
        self.assertEqual(EmailVerification.objects.count(), 1)