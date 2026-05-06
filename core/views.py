from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.models import User
from adminpanel.models import SupportTicket, SupportMessage, Complaint
from clients.models import ClientProfile, ClientPost
from masters.models import MasterProfile
from reviews.models import Review


def home(request):
    return render(request, 'core/home.html')


@login_required
def user_support(request):
    tickets = SupportTicket.objects.filter(
        user=request.user
    ).order_by('-updated_at')

    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        message_text = request.POST.get('message', '').strip()
        priority = 'normal'

        if not subject:
            messages.error(request, 'Укажите тему обращения')
            return redirect('user_support')

        if not message_text:
            messages.error(request, 'Опишите проблему')
            return redirect('user_support')

        ticket = SupportTicket.objects.create(
            user=request.user,
            subject=subject,
            status='open',
            priority=priority
        )

        SupportMessage.objects.create(
            ticket=ticket,
            sender=request.user,
            message=message_text
        )

        messages.success(request, 'Обращение отправлено в поддержку')
        return redirect('user_support_detail', ticket_id=ticket.id)

    return render(request, 'core/support.html', {
        'tickets': tickets,
    })


@login_required
def user_support_detail(request, ticket_id):
    ticket = get_object_or_404(
        SupportTicket.objects.select_related('user'),
        id=ticket_id,
        user=request.user
    )

    ticket_messages = ticket.messages.select_related(
        'sender').order_by('created_at')

    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()

        if ticket.status == 'closed':
            messages.error(
                request, 'Обращение закрыто. Создайте новое обращение.')
            return redirect('user_support_detail', ticket_id=ticket.id)

        if message_text:
            SupportMessage.objects.create(
                ticket=ticket,
                sender=request.user,
                message=message_text
            )

            ticket.updated_at = timezone.now()
            ticket.save(update_fields=['updated_at'])

            messages.success(request, 'Сообщение отправлено')
            return redirect('user_support_detail', ticket_id=ticket.id)

    return render(request, 'core/support_detail.html', {
        'ticket': ticket,
        'ticket_messages': ticket_messages,
    })


@login_required
def create_complaint(request):
    complaint_type = request.GET.get('type', '').strip()
    post_id = request.GET.get('post_id')
    review_id = request.GET.get('review_id')
    master_id = request.GET.get('master_id')

    selected_post = None
    selected_review = None
    selected_master = None

    available_masters = []
    available_clients = []

    # Клиент может жаловаться только на мастеров, к которым он записывался
    if request.user.role == 'client':
        try:
            client_profile = request.user.client_profile

            available_masters = MasterProfile.objects.filter(
                bookings__client=client_profile
            ).select_related('user').distinct().order_by('display_name')

        except ClientProfile.DoesNotExist:
            client_profile = None

    # Мастер может жаловаться только на клиентов, которые были к нему записаны
    elif request.user.role == 'master':
        try:
            master_profile = request.user.master_profile

            available_clients = ClientProfile.objects.filter(
                bookings__master=master_profile
            ).select_related('user').distinct().order_by('full_name')

        except MasterProfile.DoesNotExist:
            master_profile = None

    # Превью поста
    if complaint_type == 'post' and post_id:
        selected_post = ClientPost.objects.select_related(
            'client',
            'client__user'
        ).filter(
            id=post_id
        ).first()

    # Превью отзыва
    if complaint_type == 'review' and review_id:
        selected_review = Review.objects.select_related(
            'client',
            'client__user',
            'master',
            'master__user'
        ).filter(
            id=review_id
        ).first()

    # Превью мастера, если перешли сразу с профиля мастера
    if complaint_type == 'master' and master_id and request.user.role == 'client':
        selected_master = available_masters.filter(id=master_id).first()

    if request.method == 'POST':
        complaint_type = request.POST.get('complaint_type', 'other')
        reason = request.POST.get('reason', '').strip()

        if not reason:
            messages.error(request, 'Опишите причину жалобы')
            return redirect('create_complaint')

        target_user = None
        master = None
        post = None
        review = None

        if complaint_type == 'master':
            if request.user.role != 'client':
                messages.error(
                    request, 'Жалобу на мастера может отправить только клиент')
                return redirect('create_complaint')

            client_profile = request.user.client_profile
            master_id = request.POST.get('master_id')

            master = MasterProfile.objects.filter(
                id=master_id,
                bookings__client=client_profile
            ).select_related('user').distinct().first()

            if not master:
                messages.error(
                    request, 'Вы можете пожаловаться только на мастера, к которому ранее записывались')
                return redirect('create_complaint')

            target_user = master.user

        elif complaint_type == 'client':
            if request.user.role != 'master':
                messages.error(
                    request, 'Жалобу на клиента может отправить только мастер')
                return redirect('create_complaint')

            master_profile = request.user.master_profile
            client_profile_id = request.POST.get('client_profile_id')

            client_profile = ClientProfile.objects.filter(
                id=client_profile_id,
                bookings__master=master_profile
            ).select_related('user').distinct().first()

            if not client_profile:
                messages.error(
                    request, 'Вы можете пожаловаться только на клиента, который был к вам записан')
                return redirect('create_complaint')

            target_user = client_profile.user

        elif complaint_type == 'post':
            post_id = request.POST.get('post_id')

            post = ClientPost.objects.select_related(
                'client',
                'client__user'
            ).filter(
                id=post_id
            ).first()

            if not post:
                messages.error(request, 'Пост не найден')
                return redirect('create_complaint')

            target_user = post.client.user

        elif complaint_type == 'review':
            review_id = request.POST.get('review_id')

            review = Review.objects.select_related(
                'client',
                'client__user',
                'master',
                'master__user'
            ).filter(
                id=review_id
            ).first()

            if not review:
                messages.error(request, 'Отзыв не найден')
                return redirect('create_complaint')

            if request.user.role == 'master':
                try:
                    master_profile = request.user.master_profile
                except MasterProfile.DoesNotExist:
                    messages.error(request, 'Профиль мастера не найден')
                    return redirect('create_complaint')

                if review.master_id != master_profile.id:
                    messages.error(
                        request, 'Вы можете пожаловаться только на отзыв к вашему профилю')
                    return redirect('create_complaint')

                master = review.master
                target_user = review.client.user

            elif request.user.role == 'client':
                target_user = review.master.user
                master = review.master

            else:
                target_user = review.client.user
                master = review.master

        Complaint.objects.create(
            reporter=request.user,
            target_user=target_user,
            master=master,
            post=post,
            review=review,
            complaint_type=complaint_type,
            reason=reason,
            status='new'
        )

        messages.success(request, 'Жалоба отправлена администратору')
        return redirect('user_support')

    return render(request, 'core/complaint_create.html', {
        'complaint_type': complaint_type,
        'available_masters': available_masters,
        'available_clients': available_clients,
        'selected_post': selected_post,
        'selected_review': selected_review,
        'selected_master': selected_master,
    })
