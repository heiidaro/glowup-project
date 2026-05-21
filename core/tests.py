from datetime import time, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.forms import RegisterForm
from accounts.models import User
from bookings.models import Booking, PostResponse
from clients.models import ClientPost
from masters.models import MasterProfile
from notifications.models import Notification


class GlowUpMainFunctionalityTests(TestCase):
    """Тестирование основных сценариев работы веб-приложения Glow Up."""

    def test_client_user_creation_creates_client_profile(self):
        """Проверка создания клиента и автоматического создания профиля клиента."""
        user = User.objects.create_user(
            email='client_test@mail.ru',
            password='StrongPass123!',
            role='client'
        )

        self.assertEqual(user.role, 'client')
        self.assertTrue(hasattr(user, 'client_profile'))
        self.assertEqual(user.client_profile.user, user)

    def test_master_user_creation_creates_master_profile(self):
        """Проверка создания мастера и автоматического создания профиля мастера."""
        user = User.objects.create_user(
            email='master_test@mail.ru',
            password='StrongPass123!',
            role='master'
        )

        self.assertEqual(user.role, 'master')
        self.assertTrue(hasattr(user, 'master_profile'))
        self.assertEqual(user.master_profile.user, user)

    def test_register_form_validates_phone_and_passwords(self):
        """Проверка валидации формы регистрации."""
        form = RegisterForm(data={
            'contact': '+7 (999) 123-45-67',
            'role': 'client',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['contact'], '+79991234567')

        invalid_form = RegisterForm(data={
            'contact': 'wrong-email',
            'role': 'client',
            'password1': 'StrongPass123!',
            'password2': 'AnotherPass123!',
        })

        self.assertFalse(invalid_form.is_valid())
        self.assertTrue(
            'contact' in invalid_form.errors or 'password2' in invalid_form.errors
        )

    def test_booking_can_be_cancelled_more_than_24_hours_before_visit(self):
        """Проверка возможности отмены записи более чем за 24 часа."""
        client_user = User.objects.create_user(
            email='booking_client@mail.ru',
            password='StrongPass123!',
            role='client'
        )
        master_user = User.objects.create_user(
            email='booking_master@mail.ru',
            password='StrongPass123!',
            role='master'
        )

        booking = Booking.objects.create(
            client=client_user.client_profile,
            master=master_user.master_profile,
            service='Маникюр',
            date=timezone.localdate() + timedelta(days=3),
            time=time(12, 0),
            price=Decimal('1500.00'),
            status='active'
        )

        self.assertTrue(booking.can_cancel)
        self.assertTrue(booking.can_reschedule)

    def test_accepted_post_response_creates_booking(self):
        """Проверка создания записи на основе принятого отклика мастера."""
        client_user = User.objects.create_user(
            email='post_client@mail.ru',
            password='StrongPass123!',
            role='client'
        )
        master_user = User.objects.create_user(
            email='post_master@mail.ru',
            password='StrongPass123!',
            role='master'
        )

        post = ClientPost.objects.create(
            client=client_user.client_profile,
            description='Нужно сделать маникюр',
            preferred_date=timezone.localdate() + timedelta(days=2),
            preferred_time=time(14, 0),
            budget=Decimal('1800.00'),
            service_category='Маникюр',
            is_active=True
        )

        response = PostResponse.objects.create(
            post=post,
            master=master_user.master_profile,
            message='Могу принять вас в это время',
            proposed_price=Decimal('1700.00'),
            proposed_date=timezone.localdate() + timedelta(days=2),
            proposed_time=time(15, 0),
            status='accepted'
        )

        booking = response.create_booking()

        self.assertIsNotNone(booking)
        self.assertEqual(booking.client, client_user.client_profile)
        self.assertEqual(booking.master, master_user.master_profile)
        self.assertEqual(booking.status, 'active')
        self.assertEqual(Booking.objects.count(), 1)

    def test_all_notifications_can_be_marked_as_read(self):
        """Проверка отметки всех уведомлений пользователя как прочитанных."""
        user = User.objects.create_user(
            email='notify_user@mail.ru',
            password='StrongPass123!',
            role='client'
        )

        Notification.objects.create(
            user=user,
            notification_type='system',
            title='Первое уведомление',
            message='Текст первого уведомления'
        )
        Notification.objects.create(
            user=user,
            notification_type='system',
            title='Второе уведомление',
            message='Текст второго уведомления'
        )

        unread_before = Notification.objects.filter(
            user=user,
            is_read=False
        ).count()

        Notification.objects.filter(
            user=user,
            is_read=False
        ).update(is_read=True)

        unread_after = Notification.objects.filter(
            user=user,
            is_read=False
        ).count()

        self.assertEqual(unread_before, 2)
        self.assertEqual(unread_after, 0)
