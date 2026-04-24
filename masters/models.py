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
    master = models.ForeignKey(
        MasterProfile,
        on_delete=models.CASCADE,
        related_name='portfolio'
    )
    image = models.ImageField(upload_to='portfolio/')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'masters_portfolio'
        ordering = ['-created_at']


class ServiceCategory(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'service_categories'
        managed = False
        ordering = ['name']

    def __str__(self):
        return self.name


class Service(models.Model):
    master = models.ForeignKey(
        MasterProfile,
        on_delete=models.CASCADE,
        related_name='services'
    )
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='category_id',
        related_name='master_services'
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    duration_minutes = models.PositiveIntegerField(default=60)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'services'
        ordering = ['-created_at']
