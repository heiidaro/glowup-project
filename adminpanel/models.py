from django.db import models
from django.conf import settings

from clients.models import ClientPost
from masters.models import MasterProfile
from reviews.models import Review


class AdminAuditLog(models.Model):
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='admin_user_id',
        related_name='admin_logs'
    )
    action = models.CharField(max_length=100)
    object_type = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin_audit_logs'
        managed = False
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.action} — {self.object_type}'


class Complaint(models.Model):
    COMPLAINT_TYPES = [
        ('master', 'На мастера'),
        ('client', 'На клиента'),
        ('post', 'На пост'),
        ('review', 'На отзыв'),
        ('other', 'Другое'),
    ]

    STATUSES = [
        ('new', 'Новая'),
        ('in_progress', 'В работе'),
        ('resolved', 'Решена'),
        ('rejected', 'Отклонена'),
    ]

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='reporter_id',
        related_name='created_complaints'
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='target_user_id',
        related_name='received_complaints'
    )
    master = models.ForeignKey(
        MasterProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='master_id',
        related_name='complaints'
    )
    post = models.ForeignKey(
        ClientPost,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='post_id',
        related_name='complaints'
    )
    review = models.ForeignKey(
        Review,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='review_id',
        related_name='complaints'
    )

    complaint_type = models.CharField(
        max_length=50, choices=COMPLAINT_TYPES, default='other')
    reason = models.TextField()
    status = models.CharField(max_length=30, choices=STATUSES, default='new')
    admin_comment = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'complaints'
        managed = False
        ordering = ['-created_at']


class SupportTicket(models.Model):
    STATUSES = [
        ('open', 'Открыто'),
        ('in_progress', 'В работе'),
        ('closed', 'Закрыто'),
    ]

    PRIORITIES = [
        ('low', 'Низкий'),
        ('normal', 'Обычный'),
        ('high', 'Высокий'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='user_id',
        related_name='support_tickets'
    )

    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=30, choices=STATUSES, default='open')
    priority = models.CharField(
        max_length=30, choices=PRIORITIES, default='normal')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'support_tickets'
        managed = False
        ordering = ['-updated_at']


class SupportMessage(models.Model):
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        db_column='ticket_id',
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='sender_id',
        related_name='support_messages'
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'support_messages'
        managed = False
        ordering = ['created_at']
