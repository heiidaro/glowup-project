from django.db import models
from django.conf import settings


class MasterProfile(models.Model):
    """Профиль мастера"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='master_profile')
    display_name = models.CharField(max_length=255)
    address_text = models.CharField(max_length=255)
    bio = models.TextField(blank=True, null=True)
    # avatar = models.ImageField(
    #     upload_to='masters/avatars/', blank=True, null=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name
