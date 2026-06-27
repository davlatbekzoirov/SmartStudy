from django.core.mail import send_mail
from django.conf import settings


def send_email_change_code(user, new_email, code):
    subject = 'Confirm your new email address'
    message = (
        f'Hi {user.username},\n\n'
        f'Use this code to confirm your new email address: {code}\n\n'
        f'This code expires in 15 minutes. If you did not request this, ignore this email.'
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [new_email])