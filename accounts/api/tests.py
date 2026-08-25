from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import EmailVerification, User


class StartLoginAPITests(APITestCase):
    def test_start_login(self):
        User.objects.create_user(
            email="human@test.com",
        )

        response = self.client.post(
            reverse("accounts_api:login-start"),
            {
                "email": "human@test.com",
            },
            format="json",
        )

        verification = EmailVerification.objects.get()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data,
            {
                "verification_id": verification.pk,
            },
        )

    def test_start_login_returns_bad_request_when_email_is_invalid(self):
        response = self.client.post(
            reverse("accounts_api:login-start"),
            {
                "email": "not-an-email",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            EmailVerification.objects.count(),
            0,
        )

    def test_start_login_returns_bad_request_when_email_is_not_registered(self):
        response = self.client.post(
            reverse("accounts_api:login-start"),
            {
                "email": "human@test.com",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Email is not registered",
        )


class VerifyLoginCodeAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="human@test.com",
        )

        self.verification = EmailVerification.objects.create(
            email=self.user.email,
            purpose=EmailVerification.Purpose.LOGIN,
            code_hash=make_password("123456"),
            expires_at=timezone.now() + timedelta(minutes=5),
        )

    def test_verify_login_code(self):
        response = self.client.post(
            reverse(
                "accounts_api:login-verify",
                kwargs={
                    "verification_id": self.verification.pk,
                },
            ),
            {
                "code": "123456",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data,
            {
                "user_id": self.user.pk,
            },
        )
        self.assertEqual(
            self.client.session["_auth_user_id"],
            str(self.user.pk),
        )
        self.assertFalse(
            EmailVerification.objects.filter(
                pk=self.verification.pk,
            ).exists()
        )

    def test_verify_login_code_returns_bad_request_when_code_format_is_invalid(self):
        response = self.client.post(
            reverse(
                "accounts_api:login-verify",
                kwargs={
                    "verification_id": self.verification.pk,
                },
            ),
            {
                "code": "abcdef",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.verification.refresh_from_db()

        self.assertEqual(
            self.verification.failed_attempts,
            0,
        )

    def test_verify_login_code_returns_not_found_when_verification_does_not_exist(self):
        response = self.client.post(
            reverse(
                "accounts_api:login-verify",
                kwargs={
                    "verification_id": 999999,
                },
            ),
            {
                "code": "123456",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            response.data["detail"],
            "Verification does not exist",
        )

    def test_verify_login_code_returns_bad_request_when_verification_has_wrong_purpose(self):
        self.verification.purpose = EmailVerification.Purpose.REGISTRATION
        self.verification.save(
            update_fields=["purpose"],
        )

        response = self.client.post(
            reverse(
                "accounts_api:login-verify",
                kwargs={
                    "verification_id": self.verification.pk,
                },
            ),
            {
                "code": "123456",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Verification cannot be used for login",
        )

    def test_verify_login_code_returns_bad_request_when_verification_is_expired(self):
        self.verification.expires_at = timezone.now() - timedelta(seconds=1)
        self.verification.save(
            update_fields=["expires_at"],
        )

        response = self.client.post(
            reverse(
                "accounts_api:login-verify",
                kwargs={
                    "verification_id": self.verification.pk,
                },
            ),
            {
                "code": "123456",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Verification code has expired",
        )

    def test_verify_login_code_returns_bad_request_when_verification_is_already_used(self):
        self.verification.verified_at = timezone.now()
        self.verification.save(
            update_fields=["verified_at"],
        )

        response = self.client.post(
            reverse(
                "accounts_api:login-verify",
                kwargs={
                    "verification_id": self.verification.pk,
                },
            ),
            {
                "code": "123456",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Verification has already been used",
        )

    def test_verify_login_code_returns_bad_request_when_attempts_are_exceeded(self):
        self.verification.failed_attempts = 3
        self.verification.save(
            update_fields=["failed_attempts"],
        )

        response = self.client.post(
            reverse(
                "accounts_api:login-verify",
                kwargs={
                    "verification_id": self.verification.pk,
                },
            ),
            {
                "code": "123456",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Too many failed verification attempts",
        )

    def test_verify_login_code_returns_bad_request_when_code_is_invalid(self):
        response = self.client.post(
            reverse(
                "accounts_api:login-verify",
                kwargs={
                    "verification_id": self.verification.pk,
                },
            ),
            {
                "code": "123457",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Invalid verification code",
        )

    def test_verify_login_code_returns_not_found_when_user_does_not_exist(self):
        self.user.delete()

        response = self.client.post(
            reverse(
                "accounts_api:login-verify",
                kwargs={
                    "verification_id": self.verification.pk,
                },
            ),
            {
                "code": "123456",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            response.data["detail"],
            "User does not exist",
        )


class LogoutAPITests(APITestCase):
    def test_logout(self):
        user = User.objects.create_user(
            email="human@test.com",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("accounts_api:logout"),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_logout_requires_authentication(self):
        response = self.client.post(
            reverse("accounts_api:logout"),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
