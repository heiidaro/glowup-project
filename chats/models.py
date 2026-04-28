from django.db import models
from django.conf import settings
from clients.models import ClientProfile
from masters.models import MasterProfile


class Chat(models.Model):
    client = models.ForeignKey(
        ClientProfile,
        on_delete=models.CASCADE,
        db_column='client_id',
        related_name='chats'
    )
    master = models.ForeignKey(
        MasterProfile,
        on_delete=models.CASCADE,
        db_column='master_id',
        related_name='chats'
    )
    last_message = models.ForeignKey(
        'ChatMessage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='last_message_id',
        related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chats'
        managed = False


class ChatMessage(models.Model):
    chat = models.ForeignKey(
        Chat,
        on_delete=models.CASCADE,
        db_column='chat_id',
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column='sender_id'
    )
    attachment = models.FileField(
        upload_to='chat_attachments/',
        db_column='attachment',
        blank=True,
        null=True
    )

    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='reply_to_id',
        related_name='replies'
    )

    content = models.TextField(db_column='content')
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_for_sender = models.BooleanField(default=False)
    deleted_for_receiver = models.BooleanField(default=False)
    deleted_for_all = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'messages'
        managed = False
        ordering = ['created_at']
