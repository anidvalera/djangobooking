from django.contrib import admin
from django.utils import timezone

from .models import Booking, Room, RoomFeature, RoomType


class RoomFeatureInline(admin.TabularInline):
    model = RoomFeature
    extra = 1


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'room_type', 'capacity', 'price_per_hour', 'is_active')
    list_filter = ('room_type', 'is_active')
    search_fields = ('name', 'description')
    inlines = [RoomFeatureInline]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user_name', 'room', 'start_time', 'end_time', 'status', 'created_at')
    list_filter = ('status', 'room__room_type', 'room')
    search_fields = ('user_name', 'email')
    date_hierarchy = 'start_time'
    list_editable = ('status',)
    actions = ['confirm_bookings', 'cancel_bookings']

    @admin.action(description='Підтвердити обрані бронювання')
    def confirm_bookings(self, request, queryset):
        updated = queryset.update(status=Booking.Status.CONFIRMED)
        self.message_user(request, f'Підтверджено бронювань: {updated}.')

    @admin.action(description='Скасувати обрані бронювання')
    def cancel_bookings(self, request, queryset):
        updated = queryset.update(status=Booking.Status.CANCELLED)
        self.message_user(request, f'Скасовано бронювань: {updated}.')


admin.site.site_header = 'Адміністрування системи бронювання'
admin.site.site_title = 'Бронювання'
admin.site.index_title = 'Керування'
