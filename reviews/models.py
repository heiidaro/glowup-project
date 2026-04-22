from django.db import models
from django.conf import settings


class Review(models.Model):
    """Модель отзыва о мастере"""
    client = models.ForeignKey(
        'clients.ClientProfile',
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    master = models.ForeignKey(
        'masters.MasterProfile',
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.CASCADE,
        related_name='reviews',
        null=True,
        blank=True
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        verbose_name="Оценка"
    )
    comment = models.TextField(
        blank=True, null=True, verbose_name="Комментарий")
    is_approved = models.BooleanField(default=False, verbose_name="Проверен")
    is_blocked = models.BooleanField(
        default=False, verbose_name="Заблокирован")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reviews_review'
        ordering = ['-created_at']
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"

    def __str__(self):
        return f"{self.client.full_name} -> {self.master.display_name}: {self.rating}"
