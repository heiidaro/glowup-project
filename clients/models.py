from django.db import models
from django.conf import settings

class ClientProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="client_profile")
    full_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.full_name or str(self.user)

