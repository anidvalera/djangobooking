from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .forms import BookingForm
from .models import Booking, Room, RoomType

# Робочі години, що показуються в сітці календаря.
CALENDAR_START_HOUR = 8
CALENDAR_END_HOUR = 20


def room_list(request):
    """Головна сторінка: каталог кімнат з фільтрацією за типом і вмістимістю."""
    rooms = Room.objects.filter(is_active=True).select_related('room_type')

    type_slug = request.GET.get('type')
    if type_slug:
        rooms = rooms.filter(room_type__slug=type_slug)

    min_capacity = request.GET.get('capacity')
    if min_capacity and min_capacity.isdigit():
        rooms = rooms.filter(capacity__gte=int(min_capacity))

    context = {
        'rooms': rooms.prefetch_related('features'),
        'room_types': RoomType.objects.all(),
        'active_type': type_slug or '',
        'active_capacity': min_capacity or '',
    }
    return render(request, 'bookings/room_list.html', context)


def room_detail(request, pk):
    """Деталі кімнати + майбутні бронювання + форма бронювання."""
    room = get_object_or_404(Room.objects.select_related('room_type'), pk=pk, is_active=True)
    upcoming = room.bookings.exclude(status=Booking.Status.CANCELLED).filter(
        end_time__gte=timezone.now()
    ).order_by('start_time')

    form = BookingForm(initial={'room': room})
    context = {
        'room': room,
        'upcoming': upcoming,
        'form': form,
    }
    return render(request, 'bookings/room_detail.html', context)


def create_booking(request):
    """Обробка форми бронювання та надсилання підтвердження на пошту."""
    if request.method != 'POST':
        return redirect('bookings:room_list')

    form = BookingForm(request.POST)
    if form.is_valid():
        booking = form.save()
        _send_confirmation_email(booking)
        messages.success(
            request,
            f'Бронювання створено. Лист із підтвердженням надіслано на {booking.email}.',
        )
        return redirect('bookings:booking_success', pk=booking.pk)

    # Якщо форма невалідна — повертаємо користувача на сторінку кімнати з помилками.
    room = form.cleaned_data.get('room') or Room.objects.filter(
        pk=request.POST.get('room')
    ).first()
    if room is None:
        messages.error(request, 'Не вдалося визначити кімнату. Спробуйте ще раз.')
        return redirect('bookings:room_list')

    upcoming = room.bookings.exclude(status=Booking.Status.CANCELLED).filter(
        end_time__gte=timezone.now()
    ).order_by('start_time')
    return render(request, 'bookings/room_detail.html', {
        'room': room,
        'upcoming': upcoming,
        'form': form,
    })


def booking_success(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    return render(request, 'bookings/booking_success.html', {'booking': booking})


def my_bookings(request):
    """Пошук бронювань за електронною поштою (без реєстрації акаунта)."""
    email = request.GET.get('email', '').strip()
    bookings = None
    if email:
        bookings = Booking.objects.filter(email__iexact=email).select_related('room')
    return render(request, 'bookings/my_bookings.html', {
        'email': email,
        'bookings': bookings,
    })


def cancel_booking(request, pk):
    """Скасування бронювання користувачем (підтвердження поштою у формі)."""
    booking = get_object_or_404(Booking, pk=pk)
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if email.lower() == booking.email.lower():
            booking.status = Booking.Status.CANCELLED
            booking.save(update_fields=['status'])
            messages.success(request, 'Бронювання скасовано.')
        else:
            messages.error(request, 'Електронна пошта не збігається з бронюванням.')
        return redirect('bookings:my_bookings')
    return redirect('bookings:my_bookings')


def availability_calendar(request):
    """Тижневий календар доступності: сітка днів × годин з вільними/зайнятими слотами."""
    rooms = Room.objects.filter(is_active=True).select_related('room_type')

    type_slug = request.GET.get('type')
    if type_slug:
        rooms = rooms.filter(room_type__slug=type_slug)

    room_id = request.GET.get('room')
    selected_room = None
    if room_id and room_id.isdigit():
        selected_room = rooms.filter(pk=int(room_id)).first()
    if selected_room is None:
        selected_room = rooms.first()

    # Визначаємо початок тижня (понеділок) з урахуванням зсуву.
    week_offset = int(request.GET.get('week', 0) or 0)
    today = timezone.localdate()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    days = [monday + timedelta(days=i) for i in range(7)]
    hours = list(range(CALENDAR_START_HOUR, CALENDAR_END_HOUR))

    # Збираємо зайняті інтервали для обраної кімнати в межах тижня.
    grid = []
    busy_intervals = []
    if selected_room:
        week_start = timezone.make_aware(datetime.combine(monday, datetime.min.time()))
        week_end = week_start + timedelta(days=7)
        bookings = selected_room.bookings.exclude(
            status=Booking.Status.CANCELLED
        ).filter(start_time__lt=week_end, end_time__gt=week_start)
        busy_intervals = [
            (timezone.localtime(b.start_time), timezone.localtime(b.end_time), b)
            for b in bookings
        ]

    for hour in hours:
        row = {'hour': hour, 'cells': []}
        for day in days:
            slot_start = timezone.make_aware(
                datetime.combine(day, datetime.min.time()).replace(hour=hour)
            )
            slot_end = slot_start + timedelta(hours=1)
            booking = None
            for b_start, b_end, b in busy_intervals:
                if b_start < slot_end and b_end > slot_start:
                    booking = b
                    break
            row['cells'].append({
                'day': day,
                'busy': booking is not None,
                'booking': booking,
                'is_past': slot_end < timezone.now(),
            })
        grid.append(row)

    context = {
        'rooms': rooms,
        'room_types': RoomType.objects.all(),
        'active_type': type_slug or '',
        'selected_room': selected_room,
        'days': days,
        'grid': grid,
        'week_offset': week_offset,
    }
    return render(request, 'bookings/calendar.html', context)


def check_availability(request):
    """JSON-ендпоінт для перевірки доступності в реальному часі (AJAX)."""
    room_id = request.GET.get('room')
    start_raw = request.GET.get('start')
    end_raw = request.GET.get('end')

    if not (room_id and start_raw and end_raw):
        return JsonResponse({'ok': False, 'error': 'Не вистачає параметрів.'}, status=400)

    room = Room.objects.filter(pk=room_id, is_active=True).first()
    start = parse_datetime(start_raw)
    end = parse_datetime(end_raw)

    if room is None or start is None or end is None:
        return JsonResponse({'ok': False, 'error': 'Некоректні дані.'}, status=400)

    if timezone.is_naive(start):
        start = timezone.make_aware(start)
    if timezone.is_naive(end):
        end = timezone.make_aware(end)

    if end <= start:
        return JsonResponse({'ok': True, 'available': False,
                             'message': 'Час завершення має бути пізніше за початок.'})
    if start < timezone.now():
        return JsonResponse({'ok': True, 'available': False,
                             'message': 'Цей час уже в минулому.'})

    available = room.is_available(start, end)
    return JsonResponse({
        'ok': True,
        'available': available,
        'message': 'Проміжок вільний — можна бронювати.' if available
                   else 'На жаль, цей проміжок уже зайнятий.',
    })


def _send_confirmation_email(booking):
    """Надсилає лист-підтвердження. У DEV використовується console backend."""
    subject = f'Підтвердження бронювання №{booking.pk} — {booking.room.name}'
    body = (
        f"Вітаємо, {booking.user_name}!\n\n"
        f"Ваше бронювання зареєстровано.\n\n"
        f"Кімната: {booking.room.name}\n"
        f"Початок: {timezone.localtime(booking.start_time):%d.%m.%Y %H:%M}\n"
        f"Завершення: {timezone.localtime(booking.end_time):%d.%m.%Y %H:%M}\n"
        f"Тривалість: {booking.duration_hours} год\n"
        f"Орієнтовна вартість: {booking.total_price} грн\n"
        f"Статус: {booking.get_status_display()}\n\n"
        f"Дякуємо, що обрали нас!"
    )
    send_mail(
        subject,
        body,
        getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@booking.local'),
        [booking.email],
        fail_silently=True,
    )
