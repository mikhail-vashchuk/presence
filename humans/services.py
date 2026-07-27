from django.db import transaction

from accounts.models import User

from .models import Human


@transaction.atomic
def register_human(*, first_name, last_name, email, password,):
    user = User.objects.create_user(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=password,
    )

    return Human.objects.create(user=user)