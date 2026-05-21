from datetime import time, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

from accounts.forms import normalize_contact, russian_password_errors
from bookings.models import Booking, PostResponse
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
