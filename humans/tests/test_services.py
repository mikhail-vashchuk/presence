from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.core import mail
from django.test import TestCase
from django.utils import timezone

from accounts.exceptions import (
    InvalidVerificationCode,
    VerificationNotFound,
    VerificationPurposeMismatch,
)
from accounts.models import User, EmailVerification

from humans.exceptions import (
    EmailAlreadyRegistered,
    HumanNotFound,
    RegistrationNotVerified,
)
from humans.models import Human
from humans.services import (
    get_current_human,
    complete_registration,
    start_registration,
    verify_registration_code,
)


class StartRegistrationTests(TestCase):
    def test_start_registration(self):
        verification = start_registration(
            email="human@example.com",
        )

        self.assertEqual(EmailVerification.objects.count(), 1)
        self.assertEqual(verification.email, "human@example.com")
        self.assertEqual(
            verification.purpose,
            EmailVerification.Purpose.REGISTRATION,
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

    def test_start_registration_raises_when_email_is_already_registered(self):
        User.objects.create_user(
            email="human@example.com",
        )

        with self.assertRaises(EmailAlreadyRegistered):
            start_registration(email="human@example.com")

        self.assertEqual(EmailVerification.objects.count(), 0)
        self.assertEqual(
            len(mail.outbox),
            0,
        )


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

    def test_verify_registration_code_raises_when_code_is_invalid(self):
        verification = EmailVerification.objects.create(
            email="human@example.com",
            purpose=EmailVerification.Purpose.REGISTRATION,
            code_hash=make_password("123456"),
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        with self.assertRaises(InvalidVerificationCode):
            verify_registration_code(
                verification_id=verification.pk,
                code="123457",
            )

        verification.refresh_from_db()

        self.assertEqual(
            verification.failed_attempts,
            1,
        )

    def test_verify_registration_code_rejects_login_verification(self):
        verification = EmailVerification.objects.create(
            email="human@example.com",
            purpose=EmailVerification.Purpose.LOGIN,
            code_hash=make_password("123456"),
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        with self.assertRaises(VerificationPurposeMismatch):
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

        with self.assertRaises(RegistrationNotVerified):
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

        with self.assertRaises(EmailAlreadyRegistered):
            complete_registration(
                verification_id=self.verification.pk,
                first_name="My",
                last_name="Human",
            )

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Human.objects.count(), 0)
        self.assertEqual(EmailVerification.objects.count(), 1)

    def test_complete_registration_raises_when_verification_does_not_exist(self):
        with self.assertRaises(VerificationNotFound):
            complete_registration(
                verification_id=999999,
                first_name="My",
                last_name="Human",
            )

    def test_complete_registration_rejects_login_verification(self):
        self.verification.purpose = (
            EmailVerification.Purpose.LOGIN
        )
        self.verification.verified_at = timezone.now()

        self.verification.save(
            update_fields=[
                "purpose",
                "verified_at",
            ]
        )

        with self.assertRaises(VerificationPurposeMismatch):
            complete_registration(
                verification_id=self.verification.pk,
                first_name="My",
                last_name="Human",
            )

        self.assertEqual(
            Human.objects.count(),
            0,
        )


class GetCurrentHumanTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="human@example.com",
        )

        self.human = Human.objects.create(
            user=self.user,
            first_name="My",
            last_name="Human",
        )

    def test_get_current_human(self):
        human = get_current_human(
            user_id=self.user.pk,
        )

        self.assertEqual(
            human,
            self.human,
        )

    def test_get_current_human_raises_when_human_does_not_exist(self):
        user = User.objects.create_user(
            email="account@example.com",
        )

        with self.assertRaises(HumanNotFound):
            get_current_human(
                user_id=user.pk,
            )
