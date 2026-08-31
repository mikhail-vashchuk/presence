from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import (
    EmailVerification,
    User,
)

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
            response.data,
            {
                "verification_id": verification.pk,
            },
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
        self.assertEqual(
            response.data["detail"],
            "Email is already registered",
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

    def test_verify_registration_code_returns_not_found_when_verification_does_not_exist(self):
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
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            response.data["detail"],
            "Verification does not exist",
        )

    def test_verify_registration_code_returns_bad_request_when_verification_has_wrong_purpose(self):
        self.verification.purpose = EmailVerification.Purpose.LOGIN
        self.verification.save(
            update_fields=["purpose"],
        )

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
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Verification cannot be used for registration",
        )

    def test_verify_registration_code_returns_bad_request_when_verification_is_expired(self):
        self.verification.expires_at = timezone.now() - timedelta(seconds=1)
        self.verification.save(
            update_fields=["expires_at"],
        )

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
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Verification code has expired",
        )

    def test_verify_registration_code_returns_bad_request_when_verification_is_already_used(self):
        self.verification.verified_at = timezone.now()
        self.verification.save(
            update_fields=["verified_at"],
        )

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
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Verification has already been used",
        )

    def test_verify_registration_code_returns_bad_request_when_attempts_are_exceeded(self):
        self.verification.failed_attempts = 3
        self.verification.save(
            update_fields=["failed_attempts"],
        )

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
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Too many failed verification attempts",
        )

    def test_verify_registration_code_returns_bad_request_when_code_is_invalid(self):
        response = self.client.post(
            reverse(
                "humans_api:registration-verify",
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

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        human = Human.objects.get(
            pk=response.data["human_id"],
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

    def test_complete_registration_returns_not_found_when_verification_does_not_exist(self):
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
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            response.data["detail"],
            "Verification does not exist",
        )

    def test_complete_registration_returns_bad_request_when_verification_has_wrong_purpose(self):
        self.verification.purpose = EmailVerification.Purpose.LOGIN
        self.verification.save(
            update_fields=["purpose"],
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
            response.data["detail"],
            "Verification cannot be used for registration",
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
            response.data["detail"],
            "Email verification is incomplete",
        )

    def test_complete_registration_returns_bad_request_when_email_is_already_registered(self):
        User.objects.create_user(
            email=self.verification.email,
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
            response.data["detail"],
            "Email is already registered",
        )


class CurrentHumanAPITests(APITestCase):
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
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("humans_api:me"),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data,
            {
                "id": self.human.pk,
                "first_name": "My",
                "last_name": "Human",
                "email": "human@example.com",
            },
        )

    def test_get_current_human_requires_authentication(self):
        response = self.client.get(
            reverse("humans_api:me"),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_get_current_human_returns_not_found_when_user_has_no_human(self):
        user = User.objects.create_user(
            email="user@example.com",
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse("humans_api:me"),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            response.data["detail"],
            "Human does not exist",
        )
