from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Avg
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.models import User
from clients.models import ClientProfile, ClientPost
from masters.models import MasterProfile, Portfolio, Service, ServiceCategory
from bookings.models import Booking, PostResponse
from reviews.models import Review
from notifications.models import Notification
from .models import AdminAuditLog, Complaint, SupportTicket, SupportMessage, NotificationCampaign, UserNotification


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'admin':
            messages.error(
                request, 'У вас нет доступа к панели администратора')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


def write_admin_log(request, action, object_type, object_id=None, comment=''):
    AdminAuditLog.objects.create(
        admin_user=request.user,
        action=action,
        object_type=object_type,
        object_id=str(object_id) if object_id else None,
        comment=comment
    )


def sync_past_bookings():
    today = timezone.localdate()
    now_time = timezone.localtime().time()

    past_bookings = Booking.objects.filter(
        status='active',
        date__lt=today
    )

    today_finished_bookings = Booking.objects.filter(
        status='active',
        date=today,
        end_time__isnull=False,
        end_time__lt=now_time
    )

    updated_1 = past_bookings.update(status='completed')
    updated_2 = today_finished_bookings.update(status='completed')

    return updated_1 + updated_2


@admin_required
def admin_dashboard(request):
    sync_past_bookings()
    today = timezone.localdate()

    stats = {
        'users_count': User.objects.count(),
        'clients_count': ClientProfile.objects.count(),
        'masters_count': MasterProfile.objects.count(),
        'active_users_count': User.objects.filter(is_active=True).count(),
        'blocked_users_count': User.objects.filter(is_active=False).count(),

        'pending_masters_count': MasterProfile.objects.filter(is_approved=False).count(),
        'approved_masters_count': MasterProfile.objects.filter(is_approved=True).count(),

        'posts_count': ClientPost.objects.count(),
        'active_posts_count': ClientPost.objects.filter(is_active=True).count(),

        'portfolio_count': Portfolio.objects.count(),

        'bookings_count': Booking.objects.count(),
        'today_bookings_count': Booking.objects.filter(date=today).count(),
        'active_bookings_count': Booking.objects.filter(status='active').count(),

        'reviews_count': Review.objects.count(),
        'pending_reviews_count': Review.objects.filter(is_approved=False, is_blocked=False).count(),

        'avg_rating': Review.objects.filter(is_blocked=False).aggregate(avg=Avg('rating'))['avg'] or 0,
    }

    recent_users = User.objects.order_by('-date_joined')[:5]
    recent_bookings = Booking.objects.select_related(
        'client', 'master').order_by('-created_at')[:5]
    recent_reviews = Review.objects.select_related(
        'client', 'master').order_by('-created_at')[:5]

    popular_services = (
        Booking.objects
        .values('service')
        .annotate(total=Count('id'))
        .order_by('-total')[:5]
    )

    return render(request, 'adminpanel/dashboard.html', {
        'stats': stats,
        'recent_users': recent_users,
        'recent_bookings': recent_bookings,
        'recent_reviews': recent_reviews,
        'popular_services': popular_services,
    })


@admin_required
def admin_users(request):
    users = User.objects.all().order_by('-date_joined')

    q = request.GET.get('q', '').strip()
    role = request.GET.get('role', '').strip()
    active = request.GET.get('active', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    if q:
        users = users.filter(
            Q(email__icontains=q) |
            Q(phone__icontains=q)
        )

    if role:
        users = users.filter(role=role)

    if active == 'active':
        users = users.filter(is_active=True)

    if active == 'blocked':
        users = users.filter(is_active=False)

    if date_from:
        users = users.filter(date_joined__date__gte=date_from)

    if date_to:
        users = users.filter(date_joined__date__lte=date_to)

    if request.method == 'POST':
        email = request.POST.get('email', '').strip() or None
        phone = request.POST.get('phone', '').strip() or None
        password = request.POST.get('password', '').strip()
        new_role = request.POST.get('role', 'client')

        if not email and not phone:
            messages.error(request, 'Укажите email или телефон')
            return redirect('admin_users')

        if not password:
            messages.error(request, 'Укажите пароль')
            return redirect('admin_users')

        if email and User.objects.filter(email=email).exists():
            messages.error(
                request, 'Пользователь с таким email уже существует')
            return redirect('admin_users')

        if phone and User.objects.filter(phone=phone).exists():
            messages.error(
                request, 'Пользователь с таким телефоном уже существует')
            return redirect('admin_users')

        user = User.objects.create_user(
            email=email,
            phone=phone,
            password=password,
            role=new_role
        )
        user.is_verified = True
        user.is_staff = new_role == 'admin'
        user.is_superuser = new_role == 'admin'
        user.save()

        if new_role == 'client':
            ClientProfile.objects.get_or_create(user=user)

        if new_role == 'master':
            MasterProfile.objects.get_or_create(
                user=user,
                defaults={
                    'display_name': 'Новый мастер',
                    'address_text': ''
                }
            )

        write_admin_log(request, 'create_user', 'user', user.id,
                        f'Создан пользователь {new_role}')
        messages.success(request, 'Пользователь создан')
        return redirect('admin_users')

    return render(request, 'adminpanel/users.html', {
        'users': users,
        'q': q,
        'role': role,
        'active': active,
        'date_from': date_from,
        'date_to': date_to,
    })


@admin_required
def admin_user_action(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if user == request.user and action in ['block', 'delete']:
            messages.error(
                request, 'Нельзя заблокировать или удалить самого себя')
            return redirect('admin_users')

        if action == 'block':
            user.is_active = False
            user.save(update_fields=['is_active'])
            write_admin_log(request, 'block_user', 'user', user.id)
            messages.success(request, 'Пользователь заблокирован')

        elif action == 'unblock':
            user.is_active = True
            user.save(update_fields=['is_active'])
            write_admin_log(request, 'unblock_user', 'user', user.id)
            messages.success(request, 'Пользователь разблокирован')

        elif action == 'deactivate':
            user.is_active = False
            user.save(update_fields=['is_active'])
            write_admin_log(request, 'deactivate_user', 'user', user.id)
            messages.success(request, 'Аккаунт деактивирован')

        elif action == 'change_role':
            new_role = request.POST.get('role')

            if new_role in ['client', 'master', 'admin']:
                user.role = new_role
                user.is_staff = new_role == 'admin'
                user.is_superuser = new_role == 'admin'
                user.save(update_fields=['role', 'is_staff', 'is_superuser'])

                if new_role == 'client':
                    ClientProfile.objects.get_or_create(user=user)

                if new_role == 'master':
                    MasterProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            'display_name': 'Новый мастер',
                            'address_text': ''
                        }
                    )

                write_admin_log(request, 'change_role', 'user',
                                user.id, f'Новая роль: {new_role}')
                messages.success(request, 'Роль изменена')

    return redirect('admin_users')


@admin_required
def admin_masters(request):
    masters = MasterProfile.objects.select_related(
        'user').order_by('-created_at')

    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    active = request.GET.get('active', '').strip()

    if q:
        masters = masters.filter(
            Q(display_name__icontains=q) |
            Q(address_text__icontains=q) |
            Q(user__email__icontains=q) |
            Q(user__phone__icontains=q)
        )

    if status == 'approved':
        masters = masters.filter(is_approved=True)

    if status == 'pending':
        masters = masters.filter(is_approved=False)

    if active == 'active':
        masters = masters.filter(user__is_active=True)

    if active == 'blocked':
        masters = masters.filter(user__is_active=False)

    return render(request, 'adminpanel/masters.html', {
        'masters': masters,
        'q': q,
        'status': status,
        'active': active,
    })


@admin_required
def admin_master_detail(request, master_id):
    master = get_object_or_404(
        MasterProfile.objects.select_related('user'),
        id=master_id
    )

    services = Service.objects.filter(
        master=master
    ).select_related('category').order_by('-created_at')

    portfolio = Portfolio.objects.filter(
        master=master
    ).order_by('-created_at')

    reviews = Review.objects.filter(
        master=master
    ).select_related('client').order_by('-created_at')

    visible_reviews = reviews.filter(
        is_approved=True,
        is_blocked=False
    )

    avg_rating = visible_reviews.aggregate(
        avg=Avg('rating')
    )['avg'] or 0

    stats = {
        'services_count': services.count(),
        'active_services_count': services.filter(is_active=True).count(),
        'portfolio_count': portfolio.count(),
        'visible_portfolio_count': portfolio.filter(is_hidden=False).count(),
        'reviews_count': reviews.count(),
        'visible_reviews_count': visible_reviews.count(),
        'avg_rating': avg_rating,
    }

    return render(request, 'adminpanel/master_detail.html', {
        'master': master,
        'services': services,
        'portfolio': portfolio,
        'reviews': reviews,
        'stats': stats,
    })


@admin_required
def admin_master_action(request, master_id):
    master = get_object_or_404(MasterProfile, id=master_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'approve':
            master.is_approved = True
            master.save(update_fields=['is_approved'])
            write_admin_log(request, 'approve_master', 'master', master.id)
            messages.success(request, 'Мастер подтверждён')

        elif action == 'hide':
            master.is_approved = False
            master.save(update_fields=['is_approved'])
            write_admin_log(request, 'hide_master', 'master', master.id)
            messages.success(request, 'Мастер скрыт из общего списка')

        elif action == 'block':
            master.user.is_active = False
            master.user.save(update_fields=['is_active'])
            write_admin_log(request, 'block_master', 'master', master.id)
            messages.success(request, 'Мастер заблокирован')

        elif action == 'unblock':
            master.user.is_active = True
            master.user.save(update_fields=['is_active'])
            write_admin_log(request, 'unblock_master', 'master', master.id)
            messages.success(request, 'Мастер разблокирован')

        elif action == 'edit_public':
            master.display_name = request.POST.get(
                'display_name', master.display_name)
            master.address_text = request.POST.get(
                'address_text', master.address_text)
            master.bio = request.POST.get('bio', master.bio)
            master.save(update_fields=['display_name', 'address_text', 'bio'])
            write_admin_log(request, 'edit_master_public_info',
                            'master', master.id)
            messages.success(request, 'Публичная информация мастера изменена')

    return redirect('admin_masters')


@admin_required
def admin_bookings(request):
    sync_past_bookings()
    bookings = Booking.objects.select_related(
        'client', 'master').order_by('-created_at')

    status = request.GET.get('status', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    q = request.GET.get('q', '').strip()

    if status:
        bookings = bookings.filter(status=status)

    if date_from:
        bookings = bookings.filter(date__gte=date_from)

    if date_to:
        bookings = bookings.filter(date__lte=date_to)

    if q:
        bookings = bookings.filter(
            Q(client__full_name__icontains=q) |
            Q(master__display_name__icontains=q) |
            Q(service__icontains=q)
        )

    return render(request, 'adminpanel/bookings.html', {
        'bookings': bookings,
        'status': status,
        'date_from': date_from,
        'date_to': date_to,
        'q': q,
    })


@admin_required
def admin_booking_action(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'change_status':
            new_status = request.POST.get('status')
            if new_status in ['active', 'completed', 'cancelled']:
                booking.status = new_status
                booking.save(update_fields=['status'])
                write_admin_log(request, 'change_booking_status',
                                'booking', booking.id, f'Статус: {new_status}')
                messages.success(request, 'Статус записи изменён')

        elif action == 'cancel':
            booking.status = 'cancelled'
            booking.save(update_fields=['status'])
            write_admin_log(request, 'cancel_booking', 'booking', booking.id)
            messages.success(request, 'Запись отменена')

    return redirect('admin_bookings')


@admin_required
def admin_posts(request):
    posts = ClientPost.objects.select_related(
        'client').prefetch_related('tags').order_by('-created_at')

    status = request.GET.get('status', '').strip()
    q = request.GET.get('q', '').strip()

    if status == 'active':
        posts = posts.filter(is_active=True)

    if status == 'hidden':
        posts = posts.filter(is_active=False)

    if q:
        posts = posts.filter(
            Q(description__icontains=q) |
            Q(client__full_name__icontains=q)
        )

    return render(request, 'adminpanel/posts.html', {
        'posts': posts,
        'status': status,
        'q': q,
    })


@admin_required
def admin_post_action(request, post_id):
    post = get_object_or_404(ClientPost, id=post_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'hide':
            post.is_active = False
            post.save(update_fields=['is_active'])
            write_admin_log(request, 'hide_post', 'client_post', post.id)
            messages.success(request, 'Пост скрыт')

        elif action == 'restore':
            post.is_active = True
            post.save(update_fields=['is_active'])
            write_admin_log(request, 'restore_post', 'client_post', post.id)
            messages.success(request, 'Пост восстановлен')

        elif action == 'delete':
            post_id_value = post.id
            post.delete()
            write_admin_log(request, 'delete_post',
                            'client_post', post_id_value)
            messages.success(request, 'Пост удалён')

    return redirect('admin_posts')


@admin_required
def admin_portfolio(request):
    master_id = request.GET.get('master_id', '').strip()

    portfolio_items = Portfolio.objects.select_related(
        'master',
        'master__user'
    ).order_by('master__display_name', '-created_at')

    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    selected_master = None

    if master_id:
        selected_master = MasterProfile.objects.select_related(
            'user').filter(id=master_id).first()
        portfolio_items = portfolio_items.filter(master_id=master_id)

    if q:
        portfolio_items = portfolio_items.filter(
            Q(master__display_name__icontains=q) |
            Q(master__user__email__icontains=q) |
            Q(master__user__phone__icontains=q) |
            Q(description__icontains=q)
        )

    if status == 'visible':
        portfolio_items = portfolio_items.filter(is_hidden=False)

    elif status == 'hidden':
        portfolio_items = portfolio_items.filter(is_hidden=True)

    grouped = {}

    for item in portfolio_items:
        item_master_id = item.master_id

        if item_master_id not in grouped:
            grouped[item_master_id] = {
                'master': item.master,
                'items': [],
                'total_count': 0,
                'visible_count': 0,
                'hidden_count': 0,
            }

        grouped[item_master_id]['items'].append(item)
        grouped[item_master_id]['total_count'] += 1

        if item.is_hidden:
            grouped[item_master_id]['hidden_count'] += 1
        else:
            grouped[item_master_id]['visible_count'] += 1

    grouped_masters = list(grouped.values())

    return render(request, 'adminpanel/portfolio.html', {
        'grouped_masters': grouped_masters,
        'q': q,
        'status': status,
        'master_id': master_id,
        'selected_master': selected_master,
    })


@admin_required
def admin_portfolio_action(request, item_id):
    item = get_object_or_404(Portfolio, id=item_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'hide':
            item.is_hidden = True
            item.save(update_fields=['is_hidden'])
            write_admin_log(request, 'hide_portfolio', 'portfolio', item.id)
            messages.success(request, 'Работа скрыта')

        elif action == 'restore':
            item.is_hidden = False
            item.save(update_fields=['is_hidden'])
            write_admin_log(request, 'restore_portfolio', 'portfolio', item.id)
            messages.success(request, 'Работа восстановлена')

        elif action == 'delete':
            item_id_value = item.id
            item.delete()
            write_admin_log(request, 'delete_portfolio',
                            'portfolio', item_id_value)
            messages.success(request, 'Работа удалена')

    return redirect('admin_portfolio')


@admin_required
def admin_reviews(request):
    master_id = request.GET.get('master_id', '').strip()

    reviews = Review.objects.select_related(
        'client',
        'master',
        'master__user'
    ).order_by('-created_at')

    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    selected_master = None

    if master_id:
        selected_master = MasterProfile.objects.select_related(
            'user').filter(id=master_id).first()
        reviews = reviews.filter(master_id=master_id)

    if q:
        reviews = reviews.filter(
            Q(comment__icontains=q) |
            Q(client__full_name__icontains=q) |
            Q(master__display_name__icontains=q) |
            Q(master__user__email__icontains=q) |
            Q(master__user__phone__icontains=q)
        )

    if status == 'pending':
        reviews = reviews.filter(is_approved=False, is_blocked=False)

    elif status == 'approved':
        reviews = reviews.filter(is_approved=True, is_blocked=False)

    elif status == 'blocked':
        reviews = reviews.filter(is_blocked=True)

    return render(request, 'adminpanel/reviews.html', {
        'reviews': reviews,
        'q': q,
        'status': status,
        'master_id': master_id,
        'selected_master': selected_master,
    })


@admin_required
def admin_review_action(request, review_id):
    review = get_object_or_404(Review, id=review_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'approve':
            review.is_approved = True
            review.is_blocked = False
            review.save(update_fields=['is_approved', 'is_blocked'])

            write_admin_log(
                request,
                'approve_review',
                'review',
                review.id,
                'Отзыв опубликован'
            )

            messages.success(request, 'Отзыв опубликован')

        elif action in ['hide', 'block']:
            review.is_approved = False
            review.is_blocked = True
            review.save(update_fields=['is_approved', 'is_blocked'])

            write_admin_log(
                request,
                'hide_review',
                'review',
                review.id,
                'Отзыв скрыт'
            )

            messages.success(request, 'Отзыв скрыт')

        elif action == 'restore':
            review.is_approved = False
            review.is_blocked = False
            review.save(update_fields=['is_approved', 'is_blocked'])

            write_admin_log(
                request,
                'restore_review',
                'review',
                review.id,
                'Отзыв возвращён на проверку'
            )

            messages.success(request, 'Отзыв возвращён на проверку')

    return redirect('admin_reviews')


@admin_required
def admin_directories(request):
    categories = ServiceCategory.objects.all().order_by('name')
    services = Service.objects.select_related(
        'master', 'category').order_by('-created_at')[:200]

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_category':
            name = request.POST.get('name', '').strip()
            if name:
                ServiceCategory.objects.create(name=name)
                write_admin_log(request, 'create_service_category',
                                'service_category', comment=name)
                messages.success(request, 'Категория создана')

        elif action == 'create_service':
            master_id = request.POST.get('master_id')
            category_id = request.POST.get('category_id')
            name = request.POST.get('name', '').strip()
            price = request.POST.get('price') or 0
            duration_minutes = request.POST.get('duration_minutes') or 60

            master = MasterProfile.objects.filter(id=master_id).first()
            category = ServiceCategory.objects.filter(id=category_id).first()

            if master and name:
                service = Service.objects.create(
                    master=master,
                    category=category,
                    name=name,
                    price=price,
                    duration_minutes=duration_minutes,
                    is_active=True
                )
                write_admin_log(request, 'create_service',
                                'service', service.id)
                messages.success(request, 'Услуга создана')

        return redirect('admin_directories')

    masters = MasterProfile.objects.filter(
        user__is_active=True).order_by('display_name')

    return render(request, 'adminpanel/directories.html', {
        'categories': categories,
        'services': services,
        'masters': masters,
    })


@admin_required
def admin_delete_category(request, category_id):
    category = get_object_or_404(ServiceCategory, id=category_id)

    if request.method == 'POST':
        category_name = category.name
        category.delete()
        write_admin_log(request, 'delete_service_category',
                        'service_category', category_id, category_name)
        messages.success(request, 'Категория удалена')

    return redirect('admin_directories')


@admin_required
def admin_notifications(request):
    campaigns = NotificationCampaign.objects.select_related(
        'sender'
    ).order_by('-created_at')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        message_text = request.POST.get('message', '').strip()

        target = (
            request.POST.get('target')
            or request.POST.get('recipient_group')
            or request.POST.get('role')
            or 'all'
        ).strip()

        if not title:
            messages.error(request, 'Укажите заголовок уведомления')
            return redirect('admin_notifications')

        if not message_text:
            messages.error(request, 'Введите текст уведомления')
            return redirect('admin_notifications')

        users = User.objects.filter(is_active=True)

        if target in ['clients', 'client']:
            users = users.filter(role='client')
            target = 'clients'

        elif target in ['masters', 'master']:
            users = users.filter(role='master')
            target = 'masters'

        elif target in ['admins', 'admin']:
            users = users.filter(role='admin')
            target = 'admins'

        else:
            target = 'all'

        users = list(users)

        campaign = NotificationCampaign.objects.create(
            sender=request.user,
            title=title,
            message=message_text,
            target=target,
            sent_count=len(users)
        )

        notifications = [
            UserNotification(
                user=user,
                campaign=campaign,
                title=title,
                message=message_text,
                notification_type='system',
                is_read=False
            )
            for user in users
        ]

        if notifications:
            UserNotification.objects.bulk_create(notifications, batch_size=500)

        write_admin_log(
            request,
            'send_notification_campaign',
            'notification_campaign',
            campaign.id,
            f'Рассылка: {title}. Получателей: {len(users)}'
        )

        messages.success(
            request,
            f'Уведомление отправлено. Получателей: {len(users)}'
        )

        return redirect('admin_notifications')

    return render(request, 'adminpanel/notifications.html', {
        'campaigns': campaigns,
    })


@admin_required
def admin_audit(request):
    logs = AdminAuditLog.objects.select_related(
        'admin_user').order_by('-created_at')

    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    q = request.GET.get('q', '').strip()

    if date_from:
        logs = logs.filter(created_at__date__gte=date_from)

    if date_to:
        logs = logs.filter(created_at__date__lte=date_to)

    if q:
        logs = logs.filter(
            Q(action__icontains=q) |
            Q(object_type__icontains=q) |
            Q(comment__icontains=q) |
            Q(admin_user__email__icontains=q) |
            Q(admin_user__phone__icontains=q)
        )

    logs = logs[:300]

    return render(request, 'adminpanel/audit.html', {
        'logs': logs,
        'date_from': date_from,
        'date_to': date_to,
        'q': q,
    })


@admin_required
def admin_complaints(request):
    complaints = Complaint.objects.select_related(
        'reporter',
        'target_user',
        'master',
        'master__user',
        'post',
        'review'
    ).order_by('-created_at')

    status = request.GET.get('status', '').strip()
    complaint_type = request.GET.get('type', '').strip()
    q = request.GET.get('q', '').strip()

    if status:
        complaints = complaints.filter(status=status)

    if complaint_type:
        complaints = complaints.filter(complaint_type=complaint_type)

    if q:
        complaints = complaints.filter(
            Q(reason__icontains=q) |
            Q(admin_comment__icontains=q) |
            Q(reporter__email__icontains=q) |
            Q(reporter__phone__icontains=q) |
            Q(target_user__email__icontains=q) |
            Q(target_user__phone__icontains=q) |
            Q(master__display_name__icontains=q)
        )

    return render(request, 'adminpanel/complaints.html', {
        'complaints': complaints,
        'status': status,
        'complaint_type': complaint_type,
        'q': q,
    })


@admin_required
def admin_complaint_action(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        admin_comment = request.POST.get('admin_comment', '').strip()

        if action == 'in_progress':
            complaint.status = 'in_progress'
            complaint.admin_comment = admin_comment
            complaint.save(update_fields=['status', 'admin_comment'])
            write_admin_log(request, 'complaint_in_progress',
                            'complaint', complaint.id, admin_comment)
            messages.success(request, 'Жалоба переведена в работу')

        elif action == 'resolved':
            complaint.status = 'resolved'
            complaint.admin_comment = admin_comment
            complaint.resolved_at = timezone.now()
            complaint.save(
                update_fields=['status', 'admin_comment', 'resolved_at'])
            write_admin_log(request, 'complaint_resolved',
                            'complaint', complaint.id, admin_comment)
            messages.success(request, 'Жалоба решена')

        elif action == 'rejected':
            complaint.status = 'rejected'
            complaint.admin_comment = admin_comment
            complaint.resolved_at = timezone.now()
            complaint.save(
                update_fields=['status', 'admin_comment', 'resolved_at'])
            write_admin_log(request, 'complaint_rejected',
                            'complaint', complaint.id, admin_comment)
            messages.success(request, 'Жалоба отклонена')

        elif action == 'block_target':
            if complaint.target_user:
                complaint.target_user.is_active = False
                complaint.target_user.save(update_fields=['is_active'])

                complaint.status = 'resolved'
                complaint.admin_comment = admin_comment or 'Пользователь заблокирован по жалобе'
                complaint.resolved_at = timezone.now()
                complaint.save(
                    update_fields=['status', 'admin_comment', 'resolved_at'])

                write_admin_log(
                    request,
                    'block_user_by_complaint',
                    'user',
                    complaint.target_user.id,
                    complaint.admin_comment
                )
                messages.success(request, 'Пользователь заблокирован')
            else:
                messages.error(
                    request, 'У жалобы не указан пользователь для блокировки')

        elif action == 'hide_master':
            if complaint.master:
                complaint.master.is_approved = False
                complaint.master.save(update_fields=['is_approved'])

                complaint.status = 'resolved'
                complaint.admin_comment = admin_comment or 'Мастер скрыт по жалобе'
                complaint.resolved_at = timezone.now()
                complaint.save(
                    update_fields=['status', 'admin_comment', 'resolved_at'])

                write_admin_log(request, 'hide_master_by_complaint',
                                'master', complaint.master.id, complaint.admin_comment)
                messages.success(request, 'Мастер скрыт')
            else:
                messages.error(request, 'У жалобы не указан мастер')

        elif action == 'hide_post':
            if complaint.post:
                complaint.post.is_active = False
                complaint.post.save(update_fields=['is_active'])

                complaint.status = 'resolved'
                complaint.admin_comment = admin_comment or 'Пост скрыт по жалобе'
                complaint.resolved_at = timezone.now()
                complaint.save(
                    update_fields=['status', 'admin_comment', 'resolved_at'])

                write_admin_log(request, 'hide_post_by_complaint',
                                'client_post', complaint.post.id, complaint.admin_comment)
                messages.success(request, 'Пост скрыт')
            else:
                messages.error(request, 'У жалобы не указан пост')

        elif action == 'hide_review':
            if complaint.review:
                complaint.review.is_approved = False
                complaint.review.is_blocked = True
                complaint.review.save(
                    update_fields=['is_approved', 'is_blocked'])

                complaint.status = 'resolved'
                complaint.admin_comment = admin_comment or 'Отзыв скрыт по жалобе'
                complaint.resolved_at = timezone.now()
                complaint.save(
                    update_fields=['status', 'admin_comment', 'resolved_at'])

                write_admin_log(request, 'hide_review_by_complaint',
                                'review', complaint.review.id, complaint.admin_comment)
                messages.success(request, 'Отзыв скрыт')
            else:
                messages.error(request, 'У жалобы не указан отзыв')

    return redirect('admin_complaints')


@admin_required
def admin_support(request):
    tickets = SupportTicket.objects.select_related(
        'user',
        'assigned_admin'
    ).order_by('-updated_at')

    status = request.GET.get('status', '').strip()
    assigned = request.GET.get('assigned', '').strip()
    q = request.GET.get('q', '').strip()

    if status:
        tickets = tickets.filter(status=status)

    if assigned == 'me':
        tickets = tickets.filter(assigned_admin=request.user)

    elif assigned == 'unassigned':
        tickets = tickets.filter(assigned_admin__isnull=True)

    if q:
        tickets = tickets.filter(
            Q(subject__icontains=q) |
            Q(user__email__icontains=q) |
            Q(user__phone__icontains=q)
        )

    return render(request, 'adminpanel/support.html', {
        'tickets': tickets,
        'status': status,
        'assigned': assigned,
        'q': q,
    })


@admin_required
def admin_support_detail(request, ticket_id):
    ticket = get_object_or_404(
        SupportTicket.objects.select_related('user', 'assigned_admin'),
        id=ticket_id
    )

    ticket_messages = ticket.messages.select_related(
        'sender').order_by('created_at')

    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()

        if ticket.status == 'closed':
            messages.error(request, 'Обращение закрыто')
            return redirect('admin_support_detail', ticket_id=ticket.id)

        if ticket.assigned_admin and ticket.assigned_admin != request.user:
            messages.error(
                request,
                'Обращение уже закреплено за другим администратором'
            )
            return redirect('admin_support_detail', ticket_id=ticket.id)

        if message_text:
            SupportMessage.objects.create(
                ticket=ticket,
                sender=request.user,
                message=message_text
            )

            update_fields = ['status', 'updated_at']

            ticket.status = 'in_progress'
            ticket.updated_at = timezone.now()

            if not ticket.assigned_admin:
                ticket.assigned_admin = request.user
                update_fields.append('assigned_admin')

            ticket.save(update_fields=update_fields)

            write_admin_log(
                request,
                'support_reply',
                'support_ticket',
                ticket.id,
                message_text[:120]
            )

            messages.success(request, 'Ответ отправлен')

        return redirect('admin_support_detail', ticket_id=ticket.id)

    return render(request, 'adminpanel/support_detail.html', {
        'ticket': ticket,
        'ticket_messages': ticket_messages,
    })


@admin_required
def admin_support_action(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, id=ticket_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'in_progress':
            update_fields = ['status', 'updated_at']

            ticket.status = 'in_progress'
            ticket.updated_at = timezone.now()

            if not ticket.assigned_admin:
                ticket.assigned_admin = request.user
                update_fields.append('assigned_admin')

            ticket.save(update_fields=update_fields)

            write_admin_log(request, 'support_in_progress',
                            'support_ticket', ticket.id)
            messages.success(request, 'Обращение переведено в работу')

        elif action == 'close':
            if ticket.assigned_admin and ticket.assigned_admin != request.user:
                messages.error(
                    request, 'Закрыть обращение может закреплённый администратор')
                return redirect('admin_support')

            ticket.status = 'closed'
            ticket.closed_at = timezone.now()
            ticket.updated_at = timezone.now()
            ticket.save(update_fields=['status', 'closed_at', 'updated_at'])

            write_admin_log(request, 'support_closed',
                            'support_ticket', ticket.id)
            messages.success(request, 'Обращение закрыто')

        elif action == 'open':
            ticket.status = 'open'
            ticket.closed_at = None
            ticket.updated_at = timezone.now()
            ticket.save(update_fields=['status', 'closed_at', 'updated_at'])

            write_admin_log(request, 'support_reopened',
                            'support_ticket', ticket.id)
            messages.success(request, 'Обращение снова открыто')

    return redirect('admin_support')
