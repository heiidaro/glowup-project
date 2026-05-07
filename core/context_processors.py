from adminpanel.models import UserNotification


def notifications_counter(request):
    if not request.user.is_authenticated:
        return {
            'unread_notifications_count': 0,
            'latest_user_notifications': [],
        }

    notifications = UserNotification.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return {
        'unread_notifications_count': notifications.filter(is_read=False).count(),
        'latest_user_notifications': notifications[:8],
    }
