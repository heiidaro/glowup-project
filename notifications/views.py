from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .models import Notification


def get_dashboard_redirect_name(user):
    role = getattr(user, 'role', None)

    if role == 'client':
        return 'client_dashboard'

    if role == 'master':
        return 'master_dashboard'

    if role == 'admin':
        return 'admin_dashboard'

    return 'home'


def is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


@login_required
def user_notifications(request):
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')

    unread_notifications_count = notifications.filter(is_read=False).count()

    return render(request, 'core/notifications.html', {
        'notifications': notifications,
        'latest_user_notifications': notifications[:10],
        'unread_notifications_count': unread_notifications_count,
    })


@login_required
@require_http_methods(["GET", "POST"])
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        user=request.user
    )

    notification.is_read = True
    notification.save(update_fields=['is_read'])

    if is_ajax(request):
        return JsonResponse({
            'success': True,
            'updated': 1,
            'unread_count': Notification.objects.filter(
                user=request.user,
                is_read=False
            ).count()
        })

    return redirect(request.META.get('HTTP_REFERER') or 'notifications_list')


@login_required
@require_http_methods(["GET", "POST"])
def mark_all_notifications_read(request):
    updated = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True)

    if is_ajax(request):
        return JsonResponse({
            'success': True,
            'updated': updated,
            'unread_count': 0
        })

    return redirect(request.META.get('HTTP_REFERER') or get_dashboard_redirect_name(request.user))
