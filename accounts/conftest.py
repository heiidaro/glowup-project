import pytest
from django.test import Client
from django.utils import timezone
from datetime import timedelta
from .models import User, PendingSignup


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def test_user():
    return User.objects.create_user(
        email='test@example.com',
        password='TestPassword123',
        role='client'
    )


@pytest.fixture
def test_master():
    return User.objects.create_user(
        phone='+79161234567',
        password='TestPassword123',
        role='master'
    )


@pytest.fixture
def pending_signup():
    return PendingSignup.objects.create(
        channel=PendingSignup.CHANNEL_EMAIL,
        email='test@example.com',
        role='client',
        code_hash='pbkdf2_sha256$12345$hash',
        expires_at=timezone.now() + timedelta(hours=1)
    )
