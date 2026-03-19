from django.db import models
from django.conf import settings


class ClientProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='client_profile'
    )
    full_name = models.CharField(max_length=255, blank=True, null=True)
    is_profile_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'clients_clientprofile'

    @property
    def phone(self):
        return self.user.phone

    @property
    def email(self):
        return self.user.email

    def __str__(self):
        return self.full_name or f"Клиент {self.user_id}"


# class ClientPost(models.Model):
#     """Пост клиента"""
#     client = models.ForeignKey(
#         ClientProfile, on_delete=models.CASCADE, related_name='posts')
#     title = models.CharField(max_length=200)
#     description = models.TextField()
#     service_category = models.CharField(max_length=100)
#     preferred_date = models.DateField(null=True, blank=True)
#     budget = models.DecimalField(
#         max_digits=10, decimal_places=2, null=True, blank=True)
#     city = models.CharField(max_length=100)
#     created_at = models.DateTimeField(auto_now_add=True)
#     is_active = models.BooleanField(default=True)

#     def __str__(self):
#         return f"{self.client.full_name} - {self.title}"
