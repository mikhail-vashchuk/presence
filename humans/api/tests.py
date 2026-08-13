from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import EmailVerification, User
from humans.models import Human


class StartRegistrationAPITests(APITestCase):
    def test_start_registration(self):
        response = self.client.post(
            reverse("humans_api:registration-start"),
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
            EmailVerification.Purpose.REGISTRATION,
        )

    def test_start_registration_returns_bad_request_when_email_is_invalid(self):
        response = self.client.post(
            reverse("humans_api:registration-start"),
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

    def test_start_registration_returns_bad_request_when_email_is_registered(self):
        User.objects.create_user(
            email="human@example.com",
        )

        response = self.client.post(
            reverse("humans_api:registration-start"),
            {
                "email": "human@example.com",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


class VerifyRegistrationCodeAPITests(APITestCase):
    def setUp(self):
        self.verification = EmailVerification.objects.create(
            email="human@example.com",
            purpose=EmailVerification.Purpose.REGISTRATION,
            code_hash=make_password("123456"),
            expires_at=timezone.now() + timedelta(minutes=5),
        )

    def test_verify_registration_code(self):
        response = self.client.post(
            reverse(
                "humans_api:registration-verify",
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
            status.HTTP_204_NO_CONTENT,
        )

        self.verification.refresh_from_db()

        self.assertIsNotNone(
            self.verification.verified_at,
        )

    def test_verify_registration_code_returns_bad_request_when_code_format_is_invalid(self):
        response = self.client.post(
            reverse(
                "humans_api:registration-verify",
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

    def test_verify_registration_code_returns_bad_request_when_code_is_wrong(self):
        response = self.client.post(
            reverse(
                "humans_api:registration-verify",
                kwargs={
                    "verification_id": self.verification.pk,
                },
            ),
            {
                "code": "654321",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_verify_registration_code_returns_bad_request_when_verification_does_not_exist(self):
        response = self.client.post(
            reverse(
                "humans_api:registration-verify",
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


class CompleteRegistrationAPITests(APITestCase):
    def setUp(self):
        self.verification = EmailVerification.objects.create(
            email="human@example.com",
            purpose=EmailVerification.Purpose.REGISTRATION,
            code_hash=make_password("123456"),
            expires_at=timezone.now() + timedelta(minutes=5),
            verified_at=timezone.now(),
        )

    def test_complete_registration(self):
        response = self.client.post(
            reverse(
                "humans_api:registration-complete",
                kwargs={
                    "verification_id": self.verification.pk,
                },
            ),
            {
                "first_name": "My",
                "last_name": "Human",
            },
            format="json",
        )

        human = Human.objects.get()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data["human_id"],
            human.pk,
        )
        self.assertEqual(
            human.first_name,
            "My",
        )
        self.assertEqual(
            human.last_name,
            "Human",
        )
        self.assertEqual(
            human.user.email,
            "human@example.com",
        )
        self.assertFalse(
            EmailVerification.objects.filter(
                pk=self.verification.pk,
            ).exists()
        )
        self.assertEqual(
            self.client.session["_auth_user_id"],
            str(human.user_id),
        )

    def test_complete_registration_returns_bad_request_when_name_is_invalid(self):
        response = self.client.post(
            reverse(
                "humans_api:registration-complete",
                kwargs={
                    "verification_id": self.verification.pk,
                },
            ),
            {
                "first_name": "",
                "last_name": "Human",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            Human.objects.count(),
            0,
        )

    def test_complete_registration_returns_bad_request_when_verification_is_not_verified(self):
        self.verification.verified_at = None
        self.verification.save(
            update_fields=["verified_at"],
        )

        response = self.client.post(
            reverse(
                "humans_api:registration-complete",
                kwargs={
                    "verification_id": self.verification.pk,
                },
            ),
            {
                "first_name": "My",
                "last_name": "Human",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            Human.objects.count(),
            0,
        )

    def test_complete_registration_returns_bad_request_when_verification_does_not_exist(self):
        response = self.client.post(
            reverse(
                "humans_api:registration-complete",
                kwargs={
                    "verification_id": 999999,
                },
            ),
            {
                "first_name": "My",
                "last_name": "Human",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )