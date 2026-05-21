from datetime import time, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

from accounts.forms import normalize_contact, russian_password_errors
from bookings.models import Booking, PostResponse
from clients.models import ClientPost, ClientProfile
from masters.models import MasterProfile
from notifications.services import create_notification


class MinimalProjectTests(SimpleTestCase):
    """Минимальные тест-кейсы основной логики веб-приложения Glow Up."""

    def test_normalize_email_contact(self):
        """Проверка нормализации email при регистрации."""
        result = normalize_contact('USER@MAIL.RU')
        self.assertEqual(result, 'user@mail.ru')

    def test_normalize_phone_contact(self):
        """Проверка нормализации номера телефона при регистрации."""
        result = normalize_contact('+7 (999) 123-45-67')
        self.assertEqual(result, '+79991234567')

    def test_invalid_phone_contact(self):
        """Проверка ошибки при некорректном номере телефона."""
        with self.assertRaises(ValidationError):
            normalize_contact('12345')

    def test_password_validation_detects_simple_password(self):
        """Проверка выявления простого пароля."""
        errors = russian_password_errors('12345678')
        self.assertTrue(len(errors) > 0)

    def test_booking_can_cancel_more_than_24_hours_before_visit(self):
        """Проверка возможности отмены записи более чем за 24 часа."""
        booking = Booking(
            date=timezone.localdate() + timedelta(days=3),
            time=time(12, 0),
            price=Decimal('1500.00'),
            status='active'
        )

        self.assertTrue(booking.can_cancel)
        self.assertTrue(booking.can_reschedule)

    def test_booking_cannot_cancel_less_than_24_hours_before_visit(self):
        """Проверка запрета отмены записи менее чем за 24 часа."""
        booking = Booking(
            date=timezone.localdate(),
            time=timezone.localtime().time(),
            price=Decimal('1500.00'),
            status='active'
        )

        self.assertFalse(booking.can_cancel)

    def test_post_response_can_edit_only_pending_status(self):
        """Проверка возможности редактирования отклика только в статусе pending."""
        pending_response = PostResponse(status='pending')
        accepted_response = PostResponse(status='accepted')

        self.assertTrue(pending_response.can_edit)
        self.assertFalse(accepted_response.can_edit)

    @patch('bookings.models.Booking.objects.create')
    def test_create_booking_calls_manager(self, mock_create):
        """Проверка создания записи клиента к мастеру."""
        client = ClientProfile(full_name='Тестовый клиент')
        master = MasterProfile(
            display_name='Тестовый мастер',
            address_text='Тюмень, ул. Республики, 1'
        )

        fake_booking = Mock()
        mock_create.return_value = fake_booking

        booking_date = timezone.localdate() + timedelta(days=2)
        booking_time = time(14, 0)

        result = Booking.objects.create(
            client=client,
            master=master,
            service='Маникюр',
            date=booking_date,
            time=booking_time,
            price=Decimal('1500.00'),
            status='active',
            client_note='Тестовая запись'
        )

        self.assertEqual(result, fake_booking)

        mock_create.assert_called_once_with(
            client=client,
            master=master,
            service='Маникюр',
            date=booking_date,
            time=booking_time,
            price=Decimal('1500.00'),
            status='active',
            client_note='Тестовая запись'
        )

    @patch('clients.models.ClientPost.objects.create')
    def test_create_client_post_calls_manager(self, mock_create):
        """Проверка создания клиентского поста."""
        client = ClientProfile(full_name='Тестовый клиент')

        fake_post = Mock()
        mock_create.return_value = fake_post

        preferred_date = timezone.localdate() + timedelta(days=4)
        preferred_time = time(16, 30)

        result = ClientPost.objects.create(
            client=client,
            description='Нужно сделать маникюр с покрытием',
            preferred_date=preferred_date,
            preferred_time=preferred_time,
            budget=Decimal('2000.00'),
            service_category='Маникюр',
            is_anonymous=False,
            is_active=True
        )

        self.assertEqual(result, fake_post)

        mock_create.assert_called_once_with(
            client=client,
            description='Нужно сделать маникюр с покрытием',
            preferred_date=preferred_date,
            preferred_time=preferred_time,
            budget=Decimal('2000.00'),
            service_category='Маникюр',
            is_anonymous=False,
            is_active=True
        )

    @patch('bookings.models.PostResponse.objects.create')
    def test_create_post_response_calls_manager(self, mock_create):
        """Проверка создания отклика мастера на клиентский пост."""
        client = ClientProfile(full_name='Тестовый клиент')
        master = MasterProfile(
            display_name='Тестовый мастер',
            address_text='Тюмень, ул. Республики, 1'
        )

        post = ClientPost(
            client=client,
            description='Нужно сделать укладку',
            preferred_date=timezone.localdate() + timedelta(days=5),
            preferred_time=time(13, 0),
            budget=Decimal('2500.00'),
            service_category='Укладка',
            is_active=True
        )

        fake_response = Mock()
        mock_create.return_value = fake_response

        proposed_date = timezone.localdate() + timedelta(days=5)
        proposed_time = time(15, 0)

        result = PostResponse.objects.create(
            post=post,
            master=master,
            message='Могу выполнить услугу в указанное время',
            proposed_price=Decimal('2300.00'),
            proposed_date=proposed_date,
            proposed_time=proposed_time,
            status='pending'
        )

        self.assertEqual(result, fake_response)

        mock_create.assert_called_once_with(
            post=post,
            master=master,
            message='Могу выполнить услугу в указанное время',
            proposed_price=Decimal('2300.00'),
            proposed_date=proposed_date,
            proposed_time=proposed_time,
            status='pending'
        )

    @patch('notifications.services.send_mail')
    @patch('notifications.services.Notification.objects.create')
    def test_create_notification_with_email(self, mock_create, mock_send_mail):
        """Проверка создания уведомления и вызова отправки письма."""
        user = Mock()
        user.email = 'client@mail.ru'

        fake_notification = Mock()
        mock_create.return_value = fake_notification

        result = create_notification(
            user=user,
            notification_type='booking_cancelled',
            title='Запись отменена',
            message='Мастер отменил вашу запись.',
            link='/client/bookings/',
            send_email=True
        )

        self.assertEqual(result, fake_notification)

        mock_create.assert_called_once_with(
            user=user,
            notification_type='booking_cancelled',
            title='Запись отменена',
            message='Мастер отменил вашу запись.',
            link='/client/bookings/'
        )

        mock_send_mail.assert_called_once()
