from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.client_dashboard, name='client_dashboard'),
    path('bookings/', views.client_bookings, name='client_bookings'),
    path('cancel-booking/<int:booking_id>/',
         views.cancel_booking, name='client_cancel_booking'),
    path('reschedule-booking/<int:booking_id>/',
         views.reschedule_booking, name='client_reschedule_booking'),
    path('complete-profile/', views.complete_profile, name='complete_profile'),
    path('update-profile/', views.update_profile, name='update_profile'),
]
