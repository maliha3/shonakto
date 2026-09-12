from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


@shared_task
def send_otp_email(email, name, otp_code):
    subject = "Verify your Missing Persons Finder account"
    message = (
        f"Hi {name},\n\n"
        f"Your verification code is: {otp_code}\n"
        f"This code expires in 10 minutes.\n\n"
        f"If you did not request this, please ignore this email."
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=True)
