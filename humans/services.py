from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from accounts.models import User

from .models import Human


@transaction.atomic
def register_human(*, first_name, last_name, email, password):
    user_for_validation = User(
        first_name=first_name,
        last_name=last_name,
        email=User.objects.normalize_email(email),
    )

    validate_password(
        password,
        user=user_for_validation,
    )

    user = User.objects.create_user(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=password,
    )

    return Human.objects.create(user=user)