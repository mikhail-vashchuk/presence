from django.conf import settings
from django.core.mail import send_mail


def send_verification_code(*, email, code):
    send_mail(
        subject="Presence verification code",
        message=f"Your Presence verification code is: {code}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )
