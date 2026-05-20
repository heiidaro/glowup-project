from django.urls import path
from . import views

urlpatterns = [
    path('', views.user_notifications, name='notifications_list'),

    path(
        'read/<int:notification_id>/',
        views.mark_notification_read,
        name='notifications_mark_read'
    ),

    path(
        'read-all/',
        views.mark_all_notifications_read,
        name='notifications_mark_all_read'
    ),
]
