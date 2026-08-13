from datetime import timedelta

from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.utils import timezone

from accounts.models import User, EmailVerification

from humans.models import Human
from humans.services import (
    complete_registration,
    create_human,
    start_registration,
    verify_registration_code,
)


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
            human.first_name,
            "My",
        )
        self.assertEqual(
            human.last_name,
            "Human",
        )
        self.assertFalse(
            human.user.has_usable_password(),
        )


class StartRegistrationTests(TestCase):
    def test_start_registration_creates_email_verification(self):
        verification = start_registration(
            email="human@example.com",
        )

        self.assertEqual(EmailVerification.objects.count(), 1)
        self.assertEqual(verification.email, "human@example.com")
        self.assertEqual(
            verification.purpose,
            EmailVerification.Purpose.REGISTRATION,
        )
        self.assertGreater(verification.expires_at, timezone.now(),
        )
        self.assertTrue(verification.code_hash)

    def test_start_registration_raises_when_email_is_already_registered(self):
        User.objects.create_user(
            email="human@example.com",
        )

        with self.assertRaises(ValidationError):
            start_registration(email="human@example.com")

        self.assertEqual(EmailVerification.objects.count(), 0)


class VerifyRegistrationCodeTests(TestCase):
    def test_verify_registration_code(self):
        verification = EmailVerification.objects.create(
            email="human@example.com",
            purpose=EmailVerification.Purpose.REGISTRATION,
            code_hash=make_password("123456"),
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        verify_registration_code(
            verification_id=verification.pk,
            code="123456",
        )

        verification.refresh_from_db()

        self.assertIsNotNone(verification.verified_at)
        self.assertEqual(User.objects.count(), 0)

    def test_verify_registration_code_raises_when_code_is_expired(self):
        verification = EmailVerification.objects.create(
            email="human@example.com",
            purpose=EmailVerification.Purpose.REGISTRATION,
            code_hash=make_password("123456"),
            expires_at=timezone.now() - timedelta(seconds=1),
        )

        with self.assertRaises(ValidationError):
            verify_registration_code(
                verification_id=verification.pk,
                code="123456",
            )

        verification.refresh_from_db()

        self.assertIsNone(verification.verified_at)

    def test_verify_registration_code_raises_when_code_was_already_verified(self):
        verification = EmailVerification.objects.create(
            email="human@example.com",
            purpose=EmailVerification.Purpose.REGISTRATION,
            code_hash=make_password("123456"),
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        verify_registration_code(
            verification_id=verification.pk,
            code="123456",
        )

        verification.refresh_from_db()

        self.assertIsNotNone(verification.verified_at)

        with self.assertRaises(ValidationError):
            verify_registration_code(
                verification_id=verification.pk,
                code="123456",
            )

    def test_verify_registration_code_raises_and_increments_failed_attempts_when_code_is_invalid(self):
        verification = EmailVerification.objects.create(
            email="human@example.com",
            purpose=EmailVerification.Purpose.REGISTRATION,
            code_hash=make_password("123456"),
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        with self.assertRaises(ValidationError):
            verify_registration_code(
                verification_id=verification.pk,
                code="123457",
            )

        verification.refresh_from_db()

        self.assertIsNone(verification.verified_at)
        self.assertEqual(verification.failed_attempts, 1)

    def test_verify_registration_code_raises_when_failed_attempts_limit_is_reached(self):
        verification = EmailVerification.objects.create(
            email="human@example.com",
            purpose=EmailVerification.Purpose.REGISTRATION,
            code_hash=make_password("123456"),
            expires_at=timezone.now() + timedelta(minutes=5),
            failed_attempts=3,
        )

        with self.assertRaises(ValidationError):
            verify_registration_code(
                verification_id=verification.pk,
                code="123456",
            )

        verification.refresh_from_db()

        self.assertIsNone(verification.verified_at)
        self.assertEqual(verification.failed_attempts, 3)

    def test_verify_registration_code_rejects_login_verification(self):
        verification = EmailVerification.objects.create(
            email="human@example.com",
            purpose=EmailVerification.Purpose.LOGIN,
            code_hash=make_password("123456"),
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        with self.assertRaises(ValidationError):
            verify_registration_code(
                verification_id=verification.pk,
                code="123456",
            )


class CompleteRegistrationTests(TestCase):
    def setUp(self):
       self.verification = EmailVerification.objects.create(
           email="human@example.com",
           purpose=EmailVerification.Purpose.REGISTRATION,
           code_hash=make_password("123456"),
           expires_at=timezone.now() + timedelta(minutes=5),
       )

    def test_complete_registration_creates_user_and_human(self):
        verify_registration_code(
            verification_id=self.verification.pk,
            code="123456"
        )

        human =  complete_registration(
            verification_id=self.verification.pk,
            first_name="My",
            last_name="Human",
        )

        self.assertEqual(Human.objects.count(), 1)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(human.user.email, "human@example.com")
        self.assertEqual(human.first_name, "My")
        self.assertEqual(human.last_name, "Human")
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
            code="123456",
        )

        User.objects.create_user(
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