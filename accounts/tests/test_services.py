from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.core import mail
from django.test import TestCase
from django.utils import timezone

from accounts.exceptions import (
    EmailNotRegistered,
    InvalidVerificationCode,
    VerificationAlreadyUsed,
    VerificationAttemptsExceeded,
    VerificationExpired,
    VerificationNotFound,
    VerificationPurposeMismatch,
    VerificationUserNotFound,
)
from accounts.models import User, EmailVerification
from accounts.services import (
    create_email_verification,
    start_login,
    verify_email_verification,
    verify_login_code,
)

class CreateEmailVerificationTests(TestCase):
    def test_create_email_verification(self):
        before = timezone.now()

        verification, code = create_email_verification(
            email="human@example.com",
            purpose=EmailVerification.Purpose.LOGIN,
        )

        after = timezone.now()

        self.assertEqual(verification.email, "human@example.com")
        self.assertEqual(
            verification.purpose,
            EmailVerification.Purpose.LOGIN,
        )
        self.assertTrue(code.isdigit())
        self.assertEqual(len(code), 6)
        self.assertTrue(
            check_password(code, verification.code_hash)
        )
        self.assertGreaterEqual(
            verification.expires_at,
            before + timedelta(minutes=5),
        )
        self.assertLessEqual(
            verification.expires_at,
            after + timedelta(minutes=5),
        )


class StartLoginTests(TestCase):
    def test_start_login(self):
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
        self.assertEqual(
            len(mail.outbox),
            1,
        )
        self.assertEqual(
            mail.outbox[0].to,
            ["human@example.com"],
        )
        self.assertEqual(
            mail.outbox[0].subject,
            "Mirror Presence Layer verification code",
        )
        self.assertRegex(
            mail.outbox[0].body,
            r"\b\d{6}\b",
        )

    def test_start_login_raises_when_email_is_not_registered(self):
        with self.assertRaises(EmailNotRegistered):
            start_login(email="human@example.com")

        self.assertEqual(EmailVerification.objects.count(), 0)
        self.assertEqual(
            len(mail.outbox),
            0,
        )


class VerifyEmailVerificationTests(TestCase):
    def setUp(self):
        self.verification = EmailVerification.objects.create(
            email="human@example.com",
            purpose=EmailVerification.Purpose.LOGIN,
            code_hash=make_password("123456"),
            expires_at=timezone.now() + timedelta(minutes=5),
        )

    def test_verify_email_verification(self):
        verification = verify_email_verification(
            verification_id=self.verification.pk,
            code="123456",
            purpose=EmailVerification.Purpose.LOGIN,
        )

        self.assertEqual(verification, self.verification)

        self.verification.refresh_from_db()

        self.assertIsNotNone(
            self.verification.verified_at,
        )

    def test_wrong_code_returns_none_and_increments_failed_attempts(self):
        result = verify_email_verification(
            verification_id=self.verification.pk,
            code="123457",
            purpose=EmailVerification.Purpose.LOGIN,
        )

        self.assertIsNone(result)

        self.verification.refresh_from_db()

        self.assertEqual(
            self.verification.failed_attempts,
            1,
        )

    def test_expired_verification_is_rejected(self):
        self.verification.expires_at = (
            timezone.now() - timedelta(seconds=1)
        )
        self.verification.save(
            update_fields=["expires_at"],
        )

        with self.assertRaises(VerificationExpired):
            verify_email_verification(
                verification_id=self.verification.pk,
                code="123456",
                purpose=EmailVerification.Purpose.LOGIN,
            )

    def test_already_verified_verification_is_rejected(self):
        self.verification.verified_at = timezone.now()
        self.verification.save(
            update_fields=["verified_at"],
        )

        with self.assertRaises(VerificationAlreadyUsed):
            verify_email_verification(
                verification_id=self.verification.pk,
                code="123456",
                purpose=EmailVerification.Purpose.LOGIN,
            )

    def test_verification_is_rejected_after_too_many_failed_attempts(self):
        self.verification.failed_attempts = 3
        self.verification.save(
            update_fields=["failed_attempts"],
        )

        with self.assertRaises(VerificationAttemptsExceeded):
            verify_email_verification(
                verification_id=self.verification.pk,
                code="123456",
                purpose=EmailVerification.Purpose.LOGIN,
            )

    def test_wrong_purpose_is_rejected(self):
        with self.assertRaises(VerificationPurposeMismatch):
            verify_email_verification(
                verification_id=self.verification.pk,
                code="123456",
                purpose=EmailVerification.Purpose.REGISTRATION,
            )

    def test_missing_verification_is_rejected(self):
        with self.assertRaises(VerificationNotFound):
            verify_email_verification(
                verification_id=999999,
                code="123456",
                purpose=EmailVerification.Purpose.LOGIN,
            )


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

        with self.assertRaises(VerificationUserNotFound):
            verify_login_code(
                verification_id=self.verification.pk,
                code="123456",
            )

        self.assertEqual(
            EmailVerification.objects.count(),
            0,
        )

    def test_verify_login_code_raises_when_code_is_invalid(self):
        with self.assertRaises(InvalidVerificationCode):
            verify_login_code(
                verification_id=self.verification.pk,
                code="123457",
            )

        self.verification.refresh_from_db()

        self.assertEqual(
            self.verification.failed_attempts,
            1,
        )
