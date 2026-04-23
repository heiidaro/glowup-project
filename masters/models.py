from django.db import models
from django.conf import settings


class MasterProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='master_profile'
    )
    display_name = models.CharField(
        max_length=255, verbose_name="Имя или название студии")
    address_text = models.CharField(max_length=255, verbose_name="Адрес")
    bio = models.TextField(blank=True, null=True, verbose_name="О себе")
    is_approved = models.BooleanField(
        default=False, verbose_name="Подтвержден")
    is_profile_completed = models.BooleanField(
        default=False, verbose_name="Профиль заполнен")
    avatar = models.ImageField(
        upload_to='masters/avatars/', blank=True, null=True, verbose_name="Аватар")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        db_table = 'masters_masterprofile'
        verbose_name = "Профиль мастера"
        verbose_name_plural = "Профили мастеров"

    @property
    def phone(self):
        return self.user.phone

    @property
    def email(self):
        return self.user.email

    def __str__(self):
        return self.display_name or f"Мастер {self.user_id}"


class Portfolio(models.Model):
    """Портфолио мастера"""
    master = models.ForeignKey(
        'MasterProfile',
        on_delete=models.CASCADE,
        related_name='portfolio'
    )
    image = models.ImageField(upload_to='portfolio/', blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'masters_portfolio'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.master.display_name} - {self.description or 'фото'}"
