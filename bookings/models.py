from django.db import models
from django.conf import settings


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
