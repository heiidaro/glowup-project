from django.db import models
from django.conf import settings

class MasterProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="master_profile")
    display_name = models.CharField(max_length=255)
    address_text = models.CharField(max_length=255, blank=True, default="")
    bio = models.TextField(blank=True, null=True)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return self.display_name
