from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db.models import Q
from django.conf import settings
from django.utils import timezone
import uuid
from datetime import timedelta


class UserManager(BaseUserManager):
    def create_user(self, email=None, phone=None, password=None, role="client", **extra_fields):
        if not email and not phone:
            raise ValueError("Нужно указать email или телефон")

        if email:
            email = self.normalize_email(email)

        user = self.model(email=email, phone=phone, role=role, **extra_fields)
        user.set_password(password)
        user.is_active = True
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        user = self.create_user(email=email, phone=None,
                                password=password, role="admin", **extra_fields)
        user.is_staff = True
        user.is_superuser = True
        user.is_verified = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CLIENT = "client"
    ROLE_MASTER = "master"
    ROLE_ADMIN = "admin"
    ROLE_CHOICES = [
        (ROLE_CLIENT, "Клиент"),
        (ROLE_MASTER, "Мастер"),
        (ROLE_ADMIN, "Администратор"),
    ]

    email = models.EmailField(null=True, blank=True, unique=True)
    phone = models.CharField(max_length=32, null=True, blank=True, unique=True)

    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default=ROLE_CLIENT)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # доступ в Django admin
    is_verified = models.BooleanField(default=False)
    verified_channel = models.CharField(
        max_length=10, null=True, blank=True)  # email/phone

    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    # логин через email (если у кого-то только phone — всё равно будем логинить через свою форму)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(email__isnull=False) | Q(phone__isnull=False),
                name="user_email_or_phone_required",
            )
        ]

    def __str__(self):
        return self.email or self.phone or str(self.pk)


class VerificationCode(models.Model):
    CHANNEL_EMAIL = "email"
    CHANNEL_PHONE = "phone"
    CHANNEL_CHOICES = [
        (CHANNEL_EMAIL, "Email"),
        (CHANNEL_PHONE, "Phone"),
    ]

    PURPOSE_REGISTER = "register"
    PURPOSE_CHOICES = [
        (PURPOSE_REGISTER, "Register"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="verification_codes")
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    purpose = models.CharField(
        max_length=20, choices=PURPOSE_CHOICES, default=PURPOSE_REGISTER)

    code_hash = models.CharField(max_length=128)  # хранить не код, а хэш
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def default_expires():
        return timezone.now() + timedelta(minutes=10)

    def is_expired(self):
        return timezone.now() >= self.expires_at


class PendingSignup(models.Model):
    CHANNEL_EMAIL = "email"
    CHANNEL_PHONE = "phone"
    CHANNEL_CHOICES = [
        (CHANNEL_EMAIL, "Email"),
        (CHANNEL_PHONE, "Phone"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=32, null=True, blank=True)

    role = models.CharField(max_length=20)  # "client" / "master"

    password_hash = models.CharField(max_length=128)  # хэш пароля Django
    code_hash = models.CharField(max_length=128)      # хэш кода
    expires_at = models.DateTimeField()

    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() >= self.expires_at

    @staticmethod
    def default_expires():
        return timezone.now() + timedelta(minutes=10)


class PasswordResetToken(models.Model):
    CHANNEL_EMAIL = "email"
    CHANNEL_PHONE = "phone"
    CHANNEL_CHOICES = [(CHANNEL_EMAIL, "Email"), (CHANNEL_PHONE, "Phone")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="password_reset_tokens")

    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def default_expires():
        return timezone.now() + timedelta(minutes=20)

    def is_expired(self):
        return timezone.now() >= self.expires_at
