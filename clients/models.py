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


class ServiceTag(models.Model):
    """Модель тегов услуг"""
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'clients_servicetag'
        ordering = ['name']

    def __str__(self):
        return self.name


class ClientPost(models.Model):
    """Пост клиента"""
    client = models.ForeignKey(
        'ClientProfile',
        on_delete=models.CASCADE,
        related_name='posts'
    )
    description = models.TextField()
    tags = models.ManyToManyField(ServiceTag, related_name='posts', blank=True)
    preferred_date = models.DateField()
    preferred_time = models.TimeField(null=True, blank=True)
    budget = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    image = models.ImageField(upload_to='posts/', blank=True, null=True)
    is_anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    service_category = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'clients_clientpost'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.client.full_name} - {self.description[:50]}"

    @property
    def time_ago(self):
        from django.utils import timezone
        now = timezone.now()
        delta = now - self.created_at

        if delta.days > 7:
            return self.created_at.strftime('%d %B %Y г.')
        elif delta.days >= 1:
            return f"{delta.days} дн назад"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            return f"{hours} ч {delta.seconds % 3600 // 60} мин назад"
        elif delta.seconds >= 60:
            return f"{delta.seconds // 60} мин назад"
        else:
            return "только что"
