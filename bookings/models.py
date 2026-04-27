from django.db import models
from django.conf import settings
from datetime import timedelta, datetime
from django.utils import timezone


class Booking(models.Model):
    """Запись на услугу"""
    STATUS_CHOICES = [
        ('active', 'Активная'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
        ('expired', 'Просрочена'),
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
    service_ref = models.ForeignKey(
        'masters.Service',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='service_id',
        related_name='bookings'
    )
    date = models.DateField()
    time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    client_note = models.TextField(blank=True, null=True)
    client_photo = models.ImageField(
        upload_to='bookings/client_photos/',
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='active')
    response = models.OneToOneField(
        'PostResponse',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='booking'
    )
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
        return self.can_cancel


class BookingResponse(models.Model):
    """Отклик мастера на пост клиента"""
    STATUS_CHOICES = [
        ('pending', 'В ожидании'),
        ('approved', 'Подтвержден'),
        ('declined', 'Отклонен'),
    ]

    post = models.ForeignKey(
        'clients.ClientPost',
        on_delete=models.CASCADE,
        related_name='booking_responses'
    )
    master = models.ForeignKey(
        'masters.MasterProfile',
        on_delete=models.CASCADE,
        related_name='booking_responses'
    )
    message = models.TextField()
    proposed_price = models.DecimalField(max_digits=10, decimal_places=2)
    proposed_date = models.DateField()
    proposed_time = models.TimeField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bookings_bookingresponse'
        ordering = ['-created_at']


class PostResponse(models.Model):
    """Отклик мастера на пост клиента"""
    STATUS_CHOICES = [
        ('pending', 'В ожидании'),
        ('accepted', 'Принят'),
        ('rejected', 'Отклонен'),
        ('cancelled', 'Отменен мастером'),
    ]

    post = models.ForeignKey(
        'clients.ClientPost',
        on_delete=models.CASCADE,
        related_name='responses'
    )
    master = models.ForeignKey(
        'masters.MasterProfile',
        on_delete=models.CASCADE,
        related_name='post_responses'
    )
    message = models.TextField(blank=True, null=True)
    proposed_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    proposed_date = models.DateField(null=True, blank=True)
    proposed_time = models.TimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bookings_postresponse'
        unique_together = ['post', 'master']
        ordering = ['-created_at']

    @property
    def can_edit(self):
        return self.status == 'pending'

    @property
    def time_ago(self):
        now = timezone.now()
        delta = now - self.created_at

        if delta.days > 7:
            return self.created_at.strftime('%d %B %Y г.')
        elif delta.days >= 1:
            return f"{delta.days} дн назад"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            return f"{hours} ч {delta.seconds % 3600 // 60} мин назад"
        elif delta.seconds >= 60:
            return f"{delta.seconds // 60} мин назад"
        else:
            return "только что"

    def create_booking(self):
        """Создать запись из принятого отклика"""
        if self.status != 'accepted':
            return None

        if hasattr(self, 'booking'):
            return self.booking

        service_name = "Услуга"
        if self.post.tags.exists():
            service_name = self.post.tags.first().name
        elif self.post.service_category:
            service_name = self.post.service_category

        booking = Booking.objects.create(
            client=self.post.client,
            master=self.master,
            service=service_name,
            date=self.proposed_date or self.post.preferred_date,
            time=self.proposed_time or self.post.preferred_time,
            price=self.proposed_price or self.post.budget or 0,
            status='active',
            response=self
        )
        return booking

    def __str__(self):
        return f"{self.master.display_name} -> {self.post.id}"
