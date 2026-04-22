from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.master_dashboard, name='master_dashboard'),
    path('bookings/', views.master_bookings, name='master_bookings'),
    path('cancel-booking/<int:booking_id>/',
         views.cancel_booking, name='master_cancel_booking'),
    path('reschedule-booking/<int:booking_id>/',
         views.reschedule_booking, name='master_reschedule_booking'),
    path('responses/', views.master_responses, name='master_responses'),
    path('update-response/<int:response_id>/',
         views.update_response, name='update_response'),
    path('cancel-response/<int:response_id>/',
         views.cancel_response, name='cancel_response'),
    path('clients/', views.master_clients, name='master_clients'),
    path('portfolio/', views.master_portfolio, name='master_portfolio'),
    path('reviews/', views.master_reviews, name='master_reviews'),
    path('list/', views.masters_list, name='masters_list'),
    path('complete-profile/', views.complete_profile,
         name='master_complete_profile'),
    path('update-profile/', views.update_profile, name='master_update_profile'),
]
