from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.client_dashboard, name='client_dashboard'),
    path('bookings/', views.client_bookings, name='client_bookings'),
    path('posts/', views.posts_list, name='posts_list'),
    path('create-post/', views.create_post, name='create_post'),
    path('delete-post/<int:post_id>/', views.delete_post, name='delete_post'),
    path('report-post/<int:post_id>/', views.report_post, name='report_post'),
    path('responses/', views.client_responses, name='client_responses'),
    path('accept-response/<int:response_id>/',
         views.accept_response, name='accept_response'),
    path('reject-response/<int:response_id>/',
         views.reject_response, name='reject_response'),
    path('complete-profile/', views.complete_profile, name='complete_profile'),
    path('update-profile/', views.update_profile, name='update_profile'),
    path('cancel-booking/<int:booking_id>/',
         views.cancel_booking, name='cancel_booking'),
    path('reschedule-booking/<int:booking_id>/',
         views.reschedule_booking, name='reschedule_booking'),
    path('toggle-response/<int:post_id>/',
         views.toggle_response, name='toggle_response'),
]
