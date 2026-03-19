from django.db import models
from django.conf import settings
from datetime import timedelta
from django.utils import timezone


class Booking(models.Model):
    """Запись на услугу"""
    STATUS_CHOICES = [
        ('pending', 'В ожидании'),
        ('approved', 'Подтвержден'),
        ('declined', 'Отклонен'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]

    client = models.ForeignKey(
        'clients.ClientProfile',
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    master = models.ForeignKey(
        'masters.MasterProfile',
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    service = models.CharField(max_length=200)
    date = models.DateField()
    time = models.TimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bookings_booking'
        ordering = ['date', 'time']

    def __str__(self):
        return f"{self.client.full_name} - {self.service} - {self.date}"

    @property
    def time_until(self):
        """Возвращает время до записи в читаемом формате"""
        now = timezone.now()
        booking_datetime = timezone.make_aware(
            datetime.combine(self.date, self.time)
        )

        if booking_datetime < now:
            return "Запись прошла"

        delta = booking_datetime - now

        if delta.days > 0:
            return f"{delta.days} д {delta.seconds // 3600} ч"
        elif delta.seconds // 3600 > 0:
            return f"{delta.seconds // 3600} ч {delta.seconds % 3600 // 60} мин"
        else:
            return f"{delta.seconds // 60} мин"

    @property
    def can_cancel(self):
        """Можно ли отменить запись (не позднее чем за 24 часа)"""
        now = timezone.now()
        booking_datetime = timezone.make_aware(
            datetime.combine(self.date, self.time)
        )
        return (booking_datetime - now) > timedelta(hours=24)

    @property
    def can_reschedule(self):
        """Можно ли перенести запись (не позднее чем за 24 часа)"""
        return self.can_cancel  # То же условие


# class BookingResponse(models.Model):
#     """Отклик мастера на пост клиента"""
#     STATUS_CHOICES = [
#         ('pending', 'В ожидании'),
#         ('approved', 'Подтвержден'),
#         ('declined', 'Отклонен'),
#     ]

#     # Используем строку вместо прямого импорта
#     post = models.ForeignKey(
#         'clients.ClientPost', on_delete=models.CASCADE, related_name='responses')
#     master = models.ForeignKey(
#         'masters.MasterProfile', on_delete=models.CASCADE, related_name='responses')
#     message = models.TextField()
#     proposed_price = models.DecimalField(max_digits=10, decimal_places=2)
#     proposed_date = models.DateField()
#     proposed_time = models.TimeField()
#     status = models.CharField(
#         max_length=20, choices=STATUS_CHOICES, default='pending')
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.master.display_name} -> {self.post.title}"
