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
            email="human@example.com",
        )

        response = self.client.post(
            reverse("accounts_api:login-start"),
            {
                "email": "human@example.com",
            },
            format="json",
        )

        verification = EmailVerification.objects.get()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data["verification_id"],
            verification.pk,
        )
        self.assertEqual(
            verification.purpose,
            EmailVerification.Purpose.LOGIN,
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
                "email": "human@example.com",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


class VerifyLoginCodeAPITests(APITestCase):
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
            response.data["user_id"],
            self.user.pk,
        )
        self.assertFalse(
            EmailVerification.objects.filter(
                pk=self.verification.pk,
            ).exists()
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

    def test_verify_login_code_returns_bad_request_when_verification_does_not_exist(self):
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
            status.HTTP_400_BAD_REQUEST,
        )


class LogoutAPITests(APITestCase):
    def test_logout_ends_authenticated_session(self):
        user = User.objects.create_user(
            email="human@example.com",
        )

        verification = EmailVerification.objects.create(
            email=user.email,
            purpose=EmailVerification.Purpose.LOGIN,
            code_hash=make_password("123456"),
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        login_response = self.client.post(
            reverse(
                "accounts_api:login-verify",
                kwargs={
                    "verification_id": verification.pk,
                },
            ),
            {
                "code": "123456",
            },
            format="json",
        )

        self.assertEqual(
            login_response.status_code,
            status.HTTP_200_OK,
        )

        logout_response = self.client.post(
            reverse("accounts_api:logout"),
        )

        self.assertEqual(
            logout_response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        second_logout_response = self.client.post(
            reverse("accounts_api:logout"),
        )

        self.assertEqual(
            second_logout_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )