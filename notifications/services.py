from django.conf import settings
from django.core.mail import send_mail

from .models import Notification


def create_notification(user, notification_type, title, message, link=None, send_email=False):
    """
    Создает уведомление на сайте и при необходимости отправляет письмо на почту.
    """

    if not user:
        return None

    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link
    )

    if send_email and getattr(user, 'email', None):
        try:
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)

            if not from_email:
                from_email = getattr(settings, 'EMAIL_HOST_USER', None)

            send_mail(
                subject=title,
                message=message,
                from_email=from_email,
                recipient_list=[user.email],
                fail_silently=False
            )

            print(f'Email уведомление отправлено: {user.email}')

        except Exception as error:
            print('Ошибка отправки email-уведомления:', error)

    return notification
