from datetime import timedelta
from secrets import randbelow

from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import User, EmailVerification


VERIFICATION_CODE_LIFETIME = timedelta(minutes=5)


def _create_email_verification(email):
    code = f"{randbelow(1_000_000):06d}"

    verification = EmailVerification.objects.create(
        email=email,
        code_hash=make_password(code),
        expires_at=timezone.now() + VERIFICATION_CODE_LIFETIME,
    )

    return verification, code

def start_registration(email):
    if User.objects.filter(email=email).exists():
        raise ValidationError("Email already registered")

    verification, code = _create_email_verification(email)

    # TODO: send the verification code through the email provider.

    return verification

def start_login(email):
    if not User.objects.filter(email=email).exists():
        raise ValidationError("Email is not registered")

    verification, code = _create_email_verification(email)

    # TODO: send the verification code through the email provider.

    return verification

@transaction.atomic
def _verify_code(*, verification_id, code):
    verification = (
        EmailVerification.objects
        .select_for_update()
        .get(pk=verification_id)
    )

    if verification.expires_at <= timezone.now():
        raise ValidationError("Code expired")

    if verification.verified_at is not None:
        raise ValidationError("Code was already verified")

    if verification.failed_attempts >= 3:
        raise ValidationError("Too many failed attempts")

    if not check_password(code, verification.code_hash):
        verification.failed_attempts += 1
        verification.save(update_fields=["failed_attempts"])

        return None

    verification.verified_at = timezone.now()
    verification.save(update_fields=["verified_at"])

    return verification

def verify_login_code(*, verification_id, code):
    verification = _verify_code(
        verification_id=verification_id,
        code=code,
    )

    if verification is None:
        raise ValidationError("Invalid verification code")

    try:
        user = User.objects.get(
            email=verification.email,
        )
    except User.DoesNotExist as error:
        verification.delete()

        raise ValidationError(
            "User does not exist"
        ) from error

    verification.delete()

    return user

def verify_registration_code(*, verification_id, code):
    verification = _verify_code(
        verification_id=verification_id,
        code=code,
    )

    if verification is None:
        raise ValidationError("Invalid verification code")

    return verification
