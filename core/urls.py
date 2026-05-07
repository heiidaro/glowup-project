from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    path('support/', views.user_support, name='user_support'),
    path('support/<int:ticket_id>/', views.user_support_detail,
         name='user_support_detail'),

    path('complaints/create/', views.create_complaint, name='create_complaint'),
    path('notifications/', views.user_notifications, name='user_notifications'),
    path('notifications/<int:notification_id>/read/',
         views.mark_notification_read, name='mark_notification_read'),
    path('notifications/read-all/', views.mark_all_notifications_read,
         name='mark_all_notifications_read'),
]
