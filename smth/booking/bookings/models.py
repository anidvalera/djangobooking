from django.db import models
from django.urls import reverse
from django.utils import timezone


class RoomType(models.Model):
    """Тип простору: переговорна, конференц-зала, коворкінг тощо.

    Винесений в окрему модель, щоб давати змогу фільтрувати кімнати за типом
    (вимога ТЗ: «Фільтрація за типами кімнат/місць»).
    """
    name = models.CharField('Назва типу', max_length=80, unique=True)
    slug = models.SlugField('Ідентифікатор', max_length=80, unique=True)

    class Meta:
        verbose_name = 'Тип простору'
        verbose_name_plural = 'Типи простору'
        ordering = ['name']

    def __str__(self):
        return self.name


class Room(models.Model):
    """Кімната / місце, яке можна забронювати."""
    name = models.CharField('Назва', max_length=120)
    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rooms',
        verbose_name='Тип',
    )
    description = models.TextField('Опис', blank=True)
    capacity = models.PositiveIntegerField('Вмістимість, осіб')
    price_per_hour = models.DecimalField('Ціна за годину', max_digits=10, decimal_places=2)
    is_active = models.BooleanField('Доступна для бронювання', default=True)

    class Meta:
        verbose_name = 'Кімната / місце'
        verbose_name_plural = 'Кімнати / місця'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('bookings:room_detail', args=[self.pk])

    def is_available(self, start_time, end_time, exclude_booking_id=None):
        """Чи вільна кімната у вказаному проміжку.

        Два бронювання перетинаються, якщо start < other.end та end > other.start.
        Скасовані бронювання не блокують слот.
        """
        overlapping = self.bookings.filter(
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).exclude(status=Booking.Status.CANCELLED)
        if exclude_booking_id is not None:
            overlapping = overlapping.exclude(pk=exclude_booking_id)
        return not overlapping.exists()


class RoomFeature(models.Model):
    """Особливість кімнати: проєктор, дошка, кавомашина тощо."""
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='features',
        verbose_name='Кімната',
    )
    name = models.CharField('Особливість', max_length=120)

    class Meta:
        verbose_name = 'Особливість'
        verbose_name_plural = 'Особливості'

    def __str__(self):
        return self.name


class Booking(models.Model):
    """Бронювання кімнати конкретним користувачем на проміжок часу."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Очікує підтвердження'
        CONFIRMED = 'confirmed', 'Підтверджено'
        CANCELLED = 'cancelled', 'Скасовано'

    user_name = models.CharField("Ім'я", max_length=120)
    email = models.EmailField('Електронна пошта')
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name='Кімната',
    )
    start_time = models.DateTimeField('Початок')
    end_time = models.DateTimeField('Завершення')
    status = models.CharField(
        'Статус', max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField('Створено', auto_now_add=True)

    class Meta:
        verbose_name = 'Бронювання'
        verbose_name_plural = 'Бронювання'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user_name} — {self.room.name}"

    @property
    def duration_hours(self):
        delta = self.end_time - self.start_time
        return round(delta.total_seconds() / 3600, 2)

    @property
    def total_price(self):
        return round(self.duration_hours * float(self.room.price_per_hour), 2)

    @property
    def is_past(self):
        return self.end_time < timezone.now()
