from django.db import transaction

from accounts.emails import send_verification_code
from accounts.exceptions import (
    InvalidVerificationCode,
    VerificationNotFound,
    VerificationPurposeMismatch,
)
from accounts.models import EmailVerification, User
from accounts.services import (
    create_email_verification,
    verify_email_verification,
)

from humans.exceptions import (
    EmailAlreadyRegistered,
    HumanNotFound,
    RegistrationNotVerified,
)
from humans.models import Human


def start_registration(email):
    if User.objects.filter(email=email).exists():
        raise EmailAlreadyRegistered

    verification, code = create_email_verification(
        email=email,
        purpose=EmailVerification.Purpose.REGISTRATION,
    )

    send_verification_code(
        email=email,
        code=code,
    )

    return verification


def verify_registration_code(*, verification_id, code):
    verification = verify_email_verification(
        verification_id=verification_id,
        code=code,
        purpose=EmailVerification.Purpose.REGISTRATION,
    )

    if verification is None:
        raise InvalidVerificationCode

    return verification


@transaction.atomic
def complete_registration(*, verification_id, first_name, last_name):
    try:
        verification = (
            EmailVerification.objects
            .select_for_update()
            .get(pk=verification_id)
        )
    except EmailVerification.DoesNotExist as error:
        raise VerificationNotFound from error

    if verification.purpose != EmailVerification.Purpose.REGISTRATION:
        raise VerificationPurposeMismatch

    if verification.verified_at is None:
        raise RegistrationNotVerified

    if User.objects.filter(email=verification.email).exists():
        raise EmailAlreadyRegistered

    user = User.objects.create_user(
        email=verification.email,
        password=None,
    )

    human = Human.objects.create(
        user=user,
        first_name=first_name,
        last_name=last_name,
    )

    verification.delete()

    return human

def get_current_human(*, user_id):
    try:
        return (
            Human.objects.select_related("user").get(user_id=user_id)
        )
    except Human.DoesNotExist as error:
        raise HumanNotFound from error
