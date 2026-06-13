from django import forms
from django.utils import timezone

from .models import Booking, Room


class _DateTimeLocalInput(forms.DateTimeInput):
    """Віджет HTML5 <input type="datetime-local"> з потрібним форматом."""
    input_type = 'datetime-local'

    def __init__(self, attrs=None):
        attrs = {'class': 'field-input', **(attrs or {})}
        super().__init__(attrs=attrs, format='%Y-%m-%dT%H:%M')


class BookingForm(forms.ModelForm):
    """Форма реєстрації бронювання з перевіркою доступності проміжку."""

    class Meta:
        model = Booking
        fields = ['user_name', 'email', 'room', 'start_time', 'end_time']
        widgets = {
            'user_name': forms.TextInput(attrs={'class': 'field-input', 'placeholder': "Ваше ім'я"}),
            'email': forms.EmailInput(attrs={'class': 'field-input', 'placeholder': 'you@example.com'}),
            'room': forms.Select(attrs={'class': 'field-input'}),
            'start_time': _DateTimeLocalInput(),
            'end_time': _DateTimeLocalInput(),
        }
        labels = {
            'user_name': "Ім'я",
            'email': 'Електронна пошта',
            'room': 'Кімната / місце',
            'start_time': 'Початок',
            'end_time': 'Завершення',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Пропонуємо лише активні кімнати.
        self.fields['room'].queryset = Room.objects.filter(is_active=True)

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_time')
        end = cleaned.get('end_time')
        room = cleaned.get('room')

        if start and end:
            if end <= start:
                self.add_error('end_time', 'Час завершення має бути пізніше за час початку.')
            if start < timezone.now():
                self.add_error('start_time', 'Не можна бронювати час у минулому.')

        if room and start and end and end > start:
            exclude_id = self.instance.pk if self.instance and self.instance.pk else None
            if not room.is_available(start, end, exclude_booking_id=exclude_id):
                raise forms.ValidationError(
                    'Цей проміжок уже зайнятий для обраної кімнати. '
                    'Оберіть інший час або іншу кімнату.'
                )
        return cleaned
