from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import User, EmailVerification

from humans.models import Human


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
    verification = EmailVerification.objects.select_for_update().get(pk=verification_id)

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