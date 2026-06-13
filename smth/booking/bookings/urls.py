from django.urls import path

from . import views

app_name = 'bookings'

urlpatterns = [
    path('', views.room_list, name='room_list'),
    path('rooms/<int:pk>/', views.room_detail, name='room_detail'),
    path('book/', views.create_booking, name='create_booking'),
    path('booking/<int:pk>/success/', views.booking_success, name='booking_success'),
    path('calendar/', views.availability_calendar, name='calendar'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('booking/<int:pk>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('api/check-availability/', views.check_availability, name='check_availability'),
]
