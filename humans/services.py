from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import EmailVerification, User
from accounts.services import (
    create_email_verification,
    verify_email_verification,
)
from humans.models import Human


def start_registration(email):
    if User.objects.filter(email=email).exists():
        raise ValidationError("Email already registered")

    verification, code = create_email_verification(
        email=email,
        purpose=EmailVerification.Purpose.REGISTRATION,
    )

    # TODO: send the verification code through the email provider.

    return verification


def verify_registration_code(*, verification_id, code):
    verification = verify_email_verification(
        verification_id=verification_id,
        code=code,
        purpose=EmailVerification.Purpose.REGISTRATION,
    )

    if verification is None:
        raise ValidationError("Invalid verification code")

    return verification


@transaction.atomic
def create_human(*, first_name, last_name, email):
    user = User.objects.create_user(
        email=email,
        password=None,
    )

    return Human.objects.create(
        user=user,
        first_name=first_name,
        last_name=last_name,
    )


@transaction.atomic
def complete_registration(*, verification_id, first_name, last_name):
    verification = (
        EmailVerification.objects
        .select_for_update()
        .get(pk=verification_id)
    )

    if verification.purpose != EmailVerification.Purpose.REGISTRATION:
        raise ValidationError(
            "Verification purpose does not match"
        )

    if verification.verified_at is None:
        raise ValidationError(
            "Email verification is incomplete"
        )

    if User.objects.filter(email=verification.email).exists():
        raise ValidationError(
            "User with such email address already exists"
        )

    human = create_human(
        first_name=first_name,
        last_name=last_name,
        email=verification.email,
    )

    verification.delete()

    return human