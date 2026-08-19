from accounts.models import User
from humans.models import Human


def create_test_human(
    *,
    email="human@test.com",
    first_name="My",
    last_name="Human",
):
    user = User.objects.create_user(
        email=email,
        password=None,
    )

    return Human.objects.create(
        user=user,
        first_name=first_name,
        last_name=last_name,
    )