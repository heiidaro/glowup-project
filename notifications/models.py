from django.db import models
from django.conf import settings


class Notification(models.Model):
    """Модель уведомлений"""
    NOTIFICATION_TYPES = [
        ('response', 'Отклик на пост'),
        ('response_accepted', 'Отклик принят'),
        ('response_rejected', 'Отклик отклонен'),
        ('system', 'Системное уведомление'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(
        max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications_notification'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.title}"
