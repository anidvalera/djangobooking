from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import BookingForm
from .models import Booking, Room, RoomType


class RoomModelTest(TestCase):
    def setUp(self):
        self.room = Room.objects.create(name='Тестова', capacity=10, price_per_hour=100)
        self.start = timezone.now() + timedelta(days=1)
        self.end = self.start + timedelta(hours=2)

    def test_str(self):
        self.assertEqual(str(self.room), 'Тестова')

    def test_available_when_empty(self):
        self.assertTrue(self.room.is_available(self.start, self.end))

    def test_overlap_blocks_slot(self):
        Booking.objects.create(
            user_name='A', email='a@x.com', room=self.room,
            start_time=self.start, end_time=self.end,
            status=Booking.Status.CONFIRMED,
        )
        # Перетин у середині існуючого бронювання.
        self.assertFalse(
            self.room.is_available(self.start + timedelta(hours=1),
                                   self.end + timedelta(hours=1))
        )

    def test_cancelled_does_not_block(self):
        Booking.objects.create(
            user_name='A', email='a@x.com', room=self.room,
            start_time=self.start, end_time=self.end,
            status=Booking.Status.CANCELLED,
        )
        self.assertTrue(self.room.is_available(self.start, self.end))

    def test_adjacent_slot_is_free(self):
        Booking.objects.create(
            user_name='A', email='a@x.com', room=self.room,
            start_time=self.start, end_time=self.end,
        )
        # Бронювання впритул після — не перетин.
        self.assertTrue(self.room.is_available(self.end, self.end + timedelta(hours=1)))


class BookingFormTest(TestCase):
    def setUp(self):
        self.room = Room.objects.create(name='Зала', capacity=20, price_per_hour=200)

    def _data(self, start, end):
        return {
            'user_name': 'Іван', 'email': 'ivan@example.com', 'room': self.room.pk,
            'start_time': start.strftime('%Y-%m-%dT%H:%M'),
            'end_time': end.strftime('%Y-%m-%dT%H:%M'),
        }

    def test_valid_future_booking(self):
        start = timezone.localtime(timezone.now()) + timedelta(days=2)
        form = BookingForm(data=self._data(start, start + timedelta(hours=1)))
        self.assertTrue(form.is_valid(), form.errors)

    def test_end_before_start_invalid(self):
        start = timezone.localtime(timezone.now()) + timedelta(days=2)
        form = BookingForm(data=self._data(start, start - timedelta(hours=1)))
        self.assertFalse(form.is_valid())

    def test_past_booking_invalid(self):
        start = timezone.localtime(timezone.now()) - timedelta(days=1)
        form = BookingForm(data=self._data(start, start + timedelta(hours=1)))
        self.assertFalse(form.is_valid())


class ViewsTest(TestCase):
    def setUp(self):
        self.rtype = RoomType.objects.create(name='Переговорна', slug='meeting')
        self.room = Room.objects.create(
            name='Альфа', room_type=self.rtype, capacity=8, price_per_hour=150
        )

    def test_room_list_ok(self):
        resp = self.client.get(reverse('bookings:room_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Альфа')

    def test_calendar_ok(self):
        resp = self.client.get(reverse('bookings:calendar'))
        self.assertEqual(resp.status_code, 200)

    def test_check_availability_json(self):
        start = (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        end = (timezone.now() + timedelta(days=1, hours=1)).strftime('%Y-%m-%dT%H:%M')
        resp = self.client.get(reverse('bookings:check_availability'), {
            'room': self.room.pk, 'start': start, 'end': end
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['available'])

    def test_create_booking_sends_email(self):
        from django.core import mail
        start = timezone.localtime(timezone.now()) + timedelta(days=3)
        resp = self.client.post(reverse('bookings:create_booking'), {
            'user_name': 'Олена', 'email': 'olena@example.com', 'room': self.room.pk,
            'start_time': start.strftime('%Y-%m-%dT%H:%M'),
            'end_time': (start + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'),
        })
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertRedirects(resp, reverse('bookings:booking_success',
                                           args=[Booking.objects.first().pk]))
