from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import User, EmailVerification
from accounts.services import (
    create_email_verification,
    start_login,
    verify_email_verification,
    verify_login_code,
)


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


class StartLoginTests(TestCase):
    def test_start_login_creates_email_verification(self):
        User.objects.create_user(
            email="human@example.com",
        )

        verification = start_login(email="human@example.com")

        self.assertEqual(EmailVerification.objects.count(), 1)
        self.assertEqual(verification.email, "human@example.com")
        self.assertEqual(
            verification.purpose,
            EmailVerification.Purpose.LOGIN,
        )

    def test_start_login_raises_when_email_is_not_registered(self):
        with self.assertRaises(ValidationError):
            start_login(email="human@example.com")

        self.assertEqual(EmailVerification.objects.count(), 0)


class VerifyLoginCodeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="human@example.com",
        )

        self.verification = EmailVerification.objects.create(
            email=self.user.email,
            purpose=EmailVerification.Purpose.LOGIN,
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

    def test_verify_login_code_rejects_registration_verification(self):
        verification = EmailVerification.objects.create(
            email=self.user.email,
            purpose=EmailVerification.Purpose.REGISTRATION,
            code_hash=make_password("123456"),
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        with self.assertRaises(ValidationError):
            verify_login_code(
                verification_id=verification.pk,
                code="123456",
            )

    def test_verify_login_code_raises_when_verification_does_not_exist(self):
        with self.assertRaises(ValidationError):
            verify_login_code(
                verification_id=999999,
                code="123456",
            )
