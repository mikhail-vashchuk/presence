from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.models import User, EmailVerification
from accounts.services import start_registration, start_login, verify_registration_code, verify_login_code


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

class StartRegistrationTests(TestCase):
    def test_start_registration_creates_email_verification(self):
        verification = start_registration(
            email="human@example.com",
        )

        self.assertEqual(EmailVerification.objects.count(), 1)
        self.assertEqual(verification.email, "human@example.com")
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


class StartLoginTests(TestCase):
    def test_start_login_creates_email_verification(self):
        User.objects.create_user(
            email="human@example.com",
        )

        verification = start_login(email="human@example.com")

        self.assertEqual(EmailVerification.objects.count(), 1)
        self.assertEqual(verification.email, "human@example.com")

    def test_start_login_raises_when_email_is_not_registered(self):
        with self.assertRaises(ValidationError):
            start_login(email="human@example.com")

        self.assertEqual(EmailVerification.objects.count(), 0)


class VerifyRegistrationCodeTests(TestCase):
    def test_verify_registration_code(self):
        verification = EmailVerification.objects.create(
            email="human@example.com",
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


class VerifyLoginCodeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="human@example.com",
        )

        self.verification = EmailVerification.objects.create(
            email=self.user.email,
            code_hash=make_password("123456"),
            expires_at=timezone.now() + timedelta(minutes=5),
        )

    def test_verify_login_code_returns_existing_user(self):
        verified_user = verify_login_code(
            verification_id=self.verification.pk,
            code="123456",
        )

        self.assertEqual(self.user, verified_user)
        self.assertEqual(EmailVerification.objects.count(), 0)

    def test_verify_login_code_raises_when_user_no_longer_exists(self):
        self.user.delete()

        with self.assertRaises(ValidationError):
            verify_login_code(
                verification_id=self.verification.pk,
                code="123456",
            )

        self.assertEqual(
            EmailVerification.objects.count(),
            0,
        )
