from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from bookings.models import Booking, Room, RoomFeature, RoomType


class Command(BaseCommand):
    help = 'Наповнює базу демонстраційними даними для перевірки.'

    def handle(self, *args, **options):
        Booking.objects.all().delete()
        RoomFeature.objects.all().delete()
        Room.objects.all().delete()
        RoomType.objects.all().delete()

        meeting = RoomType.objects.create(name='Переговорна', slug='meeting')
        conf = RoomType.objects.create(name='Конференц-зала', slug='conference')
        cowork = RoomType.objects.create(name='Коворкінг', slug='coworking')

        data = [
            ('Альфа', meeting, 'Затишна переговорна для невеликих команд.', 6, 180,
             ['Проєктор', 'Маркерна дошка', 'Wi-Fi']),
            ('Меридіан', conf, 'Простора зала для презентацій і тренінгів.', 40, 600,
             ['Сцена', 'Мікрофони', 'Проєктор 4K', 'Кондиціонер']),
            ('Лофт', cowork, 'Відкритий простір з гнучким розсадженням.', 20, 250,
             ['Wi-Fi', 'Кавомашина', 'Зони відпочинку']),
            ('Бета', meeting, 'Мінімалістична кімната для дзвінків.', 4, 120,
             ['ТВ-екран', 'Wi-Fi']),
        ]
        rooms = []
        for name, rtype, desc, cap, price, feats in data:
            room = Room.objects.create(
                name=name, room_type=rtype, description=desc,
                capacity=cap, price_per_hour=price,
            )
            for f in feats:
                RoomFeature.objects.create(room=room, name=f)
            rooms.append(room)

        # Кілька бронювань на найближчі дні.
        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        Booking.objects.create(
            user_name='Команда продукту', email='product@example.com', room=rooms[0],
            start_time=now + timedelta(days=1, hours=2),
            end_time=now + timedelta(days=1, hours=4),
            status=Booking.Status.CONFIRMED,
        )
        Booking.objects.create(
            user_name='HR-онбординг', email='hr@example.com', room=rooms[1],
            start_time=now + timedelta(days=2, hours=3),
            end_time=now + timedelta(days=2, hours=6),
            status=Booking.Status.PENDING,
        )
        self.stdout.write(self.style.SUCCESS(
            f'Готово: {RoomType.objects.count()} типів, {Room.objects.count()} кімнат, '
            f'{Booking.objects.count()} бронювань.'
        ))
