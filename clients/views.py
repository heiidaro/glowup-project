from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import ClientProfile, ClientPost, ServiceTag
from django.contrib import messages
from datetime import datetime, date, timedelta
import calendar
from bookings.models import Booking
from django.utils import timezone
from .forms import ClientPostForm
from django.db.models import Q
from datetime import datetime
from bookings.models import PostResponse
from notifications.models import Notification
from django.db import transaction
from django.http import JsonResponse
import json
from masters.models import MasterProfile
from django.contrib.auth import update_session_auth_hash
from calendar import monthrange


def get_calendar_days(year, month, active_bookings, archived_bookings):
    """Генерирует дни месяца для календаря с отметками о записях"""
    first_day = date(year, month, 1)
    _, num_days = calendar.monthrange(year, month)
    first_weekday = first_day.weekday()

    # Создаем множества дат для активных и архивных записей
    active_dates = {booking.date for booking in active_bookings}
    archived_dates = {booking.date for booking in archived_bookings}

    days = []

    # Пустые ячейки для дней предыдущего месяца
    for _ in range(first_weekday):
        days.append({'date': None, 'day': '',
                    'has_booking': False, 'type': None})

    # Дни текущего месяца
    for day in range(1, num_days + 1):
        current_date = date(year, month, day)
        day_data = {
            'date': current_date,
            'day': day,
            'has_booking': current_date in active_dates or current_date in archived_dates,
            'type': None,
            'is_today': current_date == date.today(),
        }

        if current_date in active_dates:
            day_data['type'] = 'active'
        elif current_date in archived_dates:
            day_data['type'] = 'archived'

        days.append(day_data)

    return days


def get_dashboard_calendar_days(year, month, bookings):
    """Генерирует дни месяца для календаря на главной (только активные)"""
    first_day = date(year, month, 1)
    _, num_days = calendar.monthrange(year, month)
    first_weekday = first_day.weekday()

    booking_dates = {booking.date for booking in bookings}

    days = []

    for _ in range(first_weekday):
        days.append({'date': None, 'day': '', 'has_booking': False})

    for day in range(1, num_days + 1):
        current_date = date(year, month, day)
        days.append({
            'date': current_date,
            'day': day,
            'has_booking': current_date in booking_dates,
            'is_today': current_date == date.today(),
        })

    return days


def get_bookings_calendar_days(year, month, active_bookings, archived_bookings):
    """Генерирует дни месяца для календаря на странице записей (активные и архивные)"""
    first_day = date(year, month, 1)
    _, num_days = calendar.monthrange(year, month)
    first_weekday = first_day.weekday()

    active_dates = {booking.date for booking in active_bookings}
    archived_dates = {booking.date for booking in archived_bookings}

    days = []

    for _ in range(first_weekday):
        days.append({'date': None, 'day': '',
                    'has_booking': False, 'type': None})

    for day in range(1, num_days + 1):
        current_date = date(year, month, day)
        day_data = {
            'date': current_date,
            'day': day,
            'has_booking': current_date in active_dates or current_date in archived_dates,
            'type': None,
            'is_today': current_date == date.today(),
        }

        if current_date in active_dates:
            day_data['type'] = 'active'
        elif current_date in archived_dates:
            day_data['type'] = 'archived'

        days.append(day_data)

    return days


def get_month_name(month):
    months = [
        'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
    ]
    return months[month - 1]


@login_required
def client_dashboard(request):
    # Получаем или создаем профиль
    client_profile, created = ClientProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'full_name': request.user.email,
            'is_profile_completed': False
        }
    )

    # Данные для календаря
    today = datetime.now()

    try:
        current_month = int(request.GET.get('month', today.month))
        current_year = int(request.GET.get('year', today.year))
        selected_date = request.GET.get('date')
    except ValueError:
        current_month = today.month
        current_year = today.year
        selected_date = None

    # Получаем записи клиента за выбранный месяц
    month_bookings = Booking.objects.filter(
        client=client_profile,
        date__year=current_year,
        date__month=current_month
    ).select_related('master')

    # Получаем записи на выбранный день
    selected_date_bookings = []
    if selected_date:
        try:
            selected_date_obj = datetime.strptime(
                selected_date, '%Y-%m-%d').date()
            selected_date_bookings = Booking.objects.filter(
                client=client_profile,
                date=selected_date_obj
            ).select_related('master')
        except (ValueError, TypeError):
            selected_date_bookings = []
    else:
        selected_date_bookings = Booking.objects.filter(
            client=client_profile,
            date=today.date()
        ).select_related('master')
        selected_date = today.date().isoformat()

    # Генерируем дни для календаря
    calendar_days = get_dashboard_calendar_days(
        current_year, current_month, month_bookings)

    # Получаем последних мастеров, к которым записывался клиент
    recent_masters = MasterProfile.objects.filter(
        bookings__client=client_profile
    ).distinct()[:3]

    # ПОЛУЧАЕМ ОТКЛИКИ НА ПОСТЫ КЛИЕНТА (Добавьте это)
    recent_responses = PostResponse.objects.filter(
        post__client=client_profile
    ).select_related('master', 'post').order_by('-created_at')[:3]

    upcoming_bookings = Booking.objects.filter(
        client=client_profile,
        date__gte=timezone.now().date(),
        status='active'
    ).order_by('date', 'time')[:5]

    context = {
        'client': client_profile,
        'user': request.user,
        'show_profile_modal': not client_profile.is_profile_completed,
        'recent_messages': [],
        'recent_masters': recent_masters,
        'recent_responses': recent_responses,  # Добавьте это
        'selected_date_bookings': selected_date_bookings,
        'selected_date': selected_date,
        'calendar_days': calendar_days,
        'current_month': current_month,
        'current_year': current_year,
        'month_name': get_month_name(current_month),
        'upcoming_bookings': upcoming_bookings,
    }

    return render(request, 'clients/dashboard.html', context)


@login_required
def complete_profile(request):
    if request.method == 'POST':
        client_profile = ClientProfile.objects.get(user=request.user)

        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')

        if full_name:
            client_profile.full_name = full_name

        user = request.user
        if phone and phone != user.phone:
            user.phone = phone
        if email and email != user.email:
            user.email = email

        client_profile.is_profile_completed = True
        client_profile.save()
        user.save()

        messages.success(request, 'Профиль успешно заполнен!')
        return redirect('client_dashboard')

    return redirect('client_dashboard')


@login_required
def update_profile(request):
    if request.method == 'POST':
        client_profile = ClientProfile.objects.get(user=request.user)
        user = request.user

        # Получаем данные из формы
        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        # Обновляем имя
        if full_name:
            client_profile.full_name = full_name

        # Обновляем телефон
        if phone and phone != user.phone:
            user.phone = phone

        # Обновляем email
        if email and email != user.email:
            # Проверяем, не занят ли email
            from django.contrib.auth import get_user_model
            User = get_user_model()
            if not User.objects.exclude(id=user.id).filter(email=email).exists():
                user.email = email
            else:
                messages.error(request, 'Этот email уже используется')
                return redirect('client_dashboard')

        # Обновляем пароль
        if new_password and confirm_password and new_password == confirm_password:
            user.set_password(new_password)
            # Важно! Чтобы не разлогинить пользователя
            update_session_auth_hash(request, user)
            messages.success(request, 'Пароль успешно изменен')
        elif new_password or confirm_password:
            if new_password != confirm_password:
                messages.error(request, 'Пароли не совпадают')
                return redirect('client_dashboard')

        # Сохраняем изменения
        client_profile.save()
        user.save()

        messages.success(request, 'Профиль успешно обновлен!')
        return redirect('client_dashboard')

    return redirect('client_dashboard')


# @login_required
# def client_bookings(request):
#     # Проверяем роль
#     if request.user.role != 'client':
#         messages.error(request, 'У вас нет доступа к этой странице')
#         return redirect('home')

#     # Получаем профиль клиента
#     client_profile = ClientProfile.objects.get(user=request.user)

#     # Текущая дата и время
#     now = timezone.now()
#     today = now.date()

#     # Получаем месяц и год из GET параметров
#     try:
#         current_month = int(request.GET.get('month', now.month))
#         current_year = int(request.GET.get('year', now.year))
#     except ValueError:
#         current_month = now.month
#         current_year = now.year

#     # Все записи клиента
#     all_bookings = Booking.objects.filter(
#         client=client_profile).select_related('master')
#     print(
#         f"=== Всего записей для клиента {client_profile.id}: {all_bookings.count()} ===")
#     for b in all_bookings:
#         print(
#             f"  Запись {b.id}: дата={b.date}, статус={b.status}, мастер={b.master.display_name}")

#     # Разделяем на активные и архивные
#     active_bookings = []
#     archived_bookings = []

#     for booking in all_bookings:
#         booking_datetime = datetime.combine(booking.date, booking.time)
#         booking_datetime = timezone.make_aware(booking_datetime)

#         if booking.date > today or (booking.date == today and booking.time > now.time()):
#             if booking.status == 'active':
#                 active_bookings.append(booking)
#             else:
#                 archived_bookings.append(booking)
#         else:
#             archived_bookings.append(booking)

#     # Фильтруем для отображения в списках
#     active_display = [b for b in active_bookings if b.date >= today]
#     archived_display = [
#         b for b in archived_bookings if b.date < today or b.status != 'active']

#     # Получаем записи для календаря за выбранный месяц
#     month_active = [b for b in active_bookings if b.date.year ==
#                     current_year and b.date.month == current_month]
#     month_archived = [b for b in archived_bookings if b.date.year ==
#                       current_year and b.date.month == current_month]

#     # Генерируем дни для календаря
#     calendar_days = get_calendar_days(
#         current_year, current_month, month_active, month_archived)

#     context = {
#         'active_bookings': active_display,
#         'archived_bookings': archived_display,
#         'calendar_days': calendar_days,
#         'current_month': current_month,
#         'current_year': current_year,
#         'month_name': get_month_name(current_month),
#         'now': now,
#         'today': today,
#     }

#     return render(request, 'clients/bookings.html', context)


@login_required
def client_bookings(request):
    client_profile = get_object_or_404(ClientProfile, user=request.user)

    active_bookings = Booking.objects.filter(
        client=client_profile,
        status='active'
    ).select_related(
        'master', 'master__user'
    ).order_by('date', 'time')

    archived_bookings = Booking.objects.filter(
        client=client_profile,
        status__in=['completed', 'cancelled', 'expired']
    ).select_related(
        'master', 'master__user'
    ).order_by('-date', '-time')

    # Текущий месяц/год для календаря
    today = timezone.localdate()
    current_month = int(request.GET.get('month', today.month))
    current_year = int(request.GET.get('year', today.year))

    month_names = {
        1: 'Январь',
        2: 'Февраль',
        3: 'Март',
        4: 'Апрель',
        5: 'Май',
        6: 'Июнь',
        7: 'Июль',
        8: 'Август',
        9: 'Сентябрь',
        10: 'Октябрь',
        11: 'Ноябрь',
        12: 'Декабрь',
    }

    # Все записи клиента за выбранный месяц
    month_bookings = Booking.objects.filter(
        client=client_profile,
        date__year=current_year,
        date__month=current_month
    )

    # Если в один день несколько записей — приоритет у active
    bookings_by_day = {}
    for booking in month_bookings:
        day_num = booking.date.day

        booking_type = 'active' if booking.status == 'active' else 'archived'

        if day_num not in bookings_by_day:
            bookings_by_day[day_num] = booking_type
        elif bookings_by_day[day_num] != 'active' and booking_type == 'active':
            bookings_by_day[day_num] = 'active'

    first_weekday, days_in_month = monthrange(current_year, current_month)
    # monthrange: Monday=0 ... Sunday=6
    leading_empty_days = first_weekday

    calendar_days = []

    for _ in range(leading_empty_days):
        calendar_days.append({
            'date': None
        })

    for day in range(1, days_in_month + 1):
        current_date = date(current_year, current_month, day)
        booking_type = bookings_by_day.get(day)

        calendar_days.append({
            'day': day,
            'date': current_date,
            'has_booking': booking_type is not None,
            'type': booking_type,
            'is_today': current_date == today,
        })

    return render(request, 'clients/bookings.html', {
        'active_bookings': active_bookings,
        'archived_bookings': archived_bookings,
        'calendar_days': calendar_days,
        'month_name': month_names[current_month],
        'current_month': current_month,
        'current_year': current_year,
        'now': timezone.now(),
    })


def get_month_name(month):
    months = [
        'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
    ]
    return months[month - 1]


@login_required
def cancel_booking(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(Booking, id=booking_id)

        # Проверяем, что пользователь имеет отношение к записи
        if request.user.role == 'client' and booking.client.user != request.user:
            messages.error(request, 'У вас нет прав для отмены этой записи')
            return redirect('client_bookings')
        elif request.user.role == 'master' and booking.master.user != request.user:
            messages.error(request, 'У вас нет прав для отмены этой записи')
            return redirect('master_bookings')

        # Проверяем, можно ли отменить
        if not booking.can_cancel:
            messages.error(
                request, 'Нельзя отменить запись менее чем за 24 часа')
            return redirect('client_bookings' if request.user.role == 'client' else 'master_bookings')

        booking.status = 'cancelled'
        booking.save()

        messages.success(request, 'Запись успешно отменена')

    return redirect('client_bookings' if request.user.role == 'client' else 'master_bookings')


@login_required
def reschedule_booking(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(Booking, id=booking_id)

        # Проверяем права
        if request.user.role == 'client' and booking.client.user != request.user:
            messages.error(request, 'У вас нет прав для переноса этой записи')
            return redirect('client_bookings')
        elif request.user.role == 'master' and booking.master.user != request.user:
            messages.error(request, 'У вас нет прав для переноса этой записи')
            return redirect('master_bookings')

        # Проверяем, можно ли перенести
        if not booking.can_reschedule:
            messages.error(
                request, 'Нельзя перенести запись менее чем за 24 часа')
            return redirect('client_bookings' if request.user.role == 'client' else 'master_bookings')

        new_date = request.POST.get('new_date')
        new_time = request.POST.get('new_time')

        if new_date and new_time:
            booking.date = new_date
            booking.time = new_time
            booking.save()
            messages.success(request, 'Запись успешно перенесена')
        else:
            messages.error(request, 'Укажите новую дату и время')

    return redirect('client_bookings' if request.user.role == 'client' else 'master_bookings')


@login_required
def posts_list(request):
    """Страница со всеми постами всех клиентов с фильтрацией"""

    # Базовый запрос
    posts = ClientPost.objects.filter(is_active=True).select_related(
        'client', 'client__user'
    ).prefetch_related('tags').order_by('-created_at')

    # Фильтрация по тегам
    tags_filter = request.GET.getlist('tags')
    if tags_filter:
        posts = posts.filter(tags__id__in=tags_filter).distinct()

    # Фильтрация по дате
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            posts = posts.filter(preferred_date__gte=date_from_obj)
        except:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            posts = posts.filter(preferred_date__lte=date_to_obj)
        except:
            pass

    # Фильтрация по цене
    price_from = request.GET.get('price_from')
    price_to = request.GET.get('price_to')

    if price_from:
        try:
            price_from_val = float(price_from)
            posts = posts.filter(budget__gte=price_from_val)
        except:
            pass

    if price_to:
        try:
            price_to_val = float(price_to)
            posts = posts.filter(budget__lte=price_to_val)
        except:
            pass

    # Получаем все теги для фильтра
    all_tags = ServiceTag.objects.all()

    # Сохраняем текущие параметры фильтрации для отображения в шаблоне
    current_filters = {
        'tags': request.GET.getlist('tags'),
        'date_from': date_from,
        'date_to': date_to,
        'price_from': price_from,
        'price_to': price_to,
    }

    user_responses = []
    if request.user.role == 'master':
        try:
            master = request.user.master_profile
            user_responses = PostResponse.objects.filter(
                master=master).values_list('post_id', flat=True)
        except:
            pass

    context = {
        'posts': posts,
        'user': request.user,
        'all_tags': all_tags,
        'current_filters': current_filters,
        'user_responses': list(user_responses),
        'is_master': request.user.role == 'master',
    }

    return render(request, 'clients/posts.html', context)


@login_required
def delete_post(request, post_id):
    """Удаление поста"""
    if request.method == 'POST':
        post = get_object_or_404(ClientPost, id=post_id)

        # Проверяем, что пост принадлежит текущему пользователю
        if post.client.user != request.user:
            messages.error(request, 'У вас нет прав для удаления этого поста')
            return redirect('posts_list')

        post.is_active = False
        post.save()
        messages.success(request, 'Пост успешно удален')

    return redirect('posts_list')


@login_required
def create_post(request):
    """Страница создания поста"""
    if request.method == 'POST':
        form = ClientPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.client = request.user.client_profile
            post.save()
            # Сохраняем теги (ManyToMany)
            form.save_m2m()
            messages.success(request, 'Пост успешно создан!')
            return redirect('posts_list')
    else:
        form = ClientPostForm()

    context = {
        'form': form,
    }

    return render(request, 'clients/create_post.html', context)


@login_required
def report_post(request, post_id):
    """Жалоба на пост"""
    if request.method == 'POST':
        post = get_object_or_404(ClientPost, id=post_id)
        reason = request.POST.get('reason')

        # Здесь можно сохранить жалобу в базу
        messages.success(request, 'Жалоба отправлена модератору')

    return redirect('posts_list')


@login_required
def toggle_response(request, post_id):
    """Добавить или удалить отклик на пост"""
    if request.method == 'POST':
        # Проверяем, что пользователь - мастер
        if request.user.role != 'master':
            return JsonResponse({'error': 'Только мастера могут откликаться'}, status=403)

        try:
            data = json.loads(request.body)
            message = data.get('message', '')
            proposed_price = data.get('proposed_price')
            proposed_date = data.get('proposed_date')
            proposed_time = data.get('proposed_time')

            post = ClientPost.objects.get(id=post_id, is_active=True)
            master = request.user.master_profile

            # Проверяем, что пост не принадлежит этому мастеру
            if post.client.user == request.user:
                return JsonResponse({'error': 'Нельзя откликаться на свой пост'}, status=403)

            # Проверяем, есть ли уже отклик
            existing_response = PostResponse.objects.filter(
                post=post, master=master).first()

            if existing_response:
                # Если отклик уже был, удаляем его
                existing_response.delete()
                action = 'removed'
            else:
                # Создаем новый отклик
                with transaction.atomic():
                    response = PostResponse.objects.create(
                        post=post,
                        master=master,
                        message=message,
                        proposed_price=proposed_price,
                        proposed_date=proposed_date,
                        proposed_time=proposed_time
                    )

                    # Создаем уведомление для клиента
                    Notification.objects.create(
                        user=post.client.user,
                        notification_type='response',
                        title='Новый отклик на пост',
                        message=f'{master.display_name} откликнулся на ваш пост "{post.description[:50]}..."',
                        link=f'/client/responses/'
                    )

                action = 'added'

            # Получаем актуальное количество откликов
            responses_count = post.responses.count()

            return JsonResponse({
                'action': action,
                'count': responses_count,
                'post_id': post_id
            })

        except ClientPost.DoesNotExist:
            return JsonResponse({'error': 'Пост не найден'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Метод не разрешен'}, status=405)


@login_required
def client_responses(request):
    """Страница откликов на посты клиента"""
    if request.user.role != 'client':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('home')

    client_profile = request.user.client_profile
    responses = PostResponse.objects.filter(
        post__client=client_profile
    ).select_related('master', 'post').order_by('-created_at')

    context = {
        'responses': responses,
        'client': client_profile,
    }

    return render(request, 'clients/responses.html', context)


@login_required
def accept_response(request, response_id):
    """Принять отклик и создать запись"""
    if request.method == 'POST':
        response = get_object_or_404(PostResponse, id=response_id)

        if response.post.client.user != request.user:
            messages.error(request, 'У вас нет прав')
            return redirect('client_responses')

        if response.status != 'pending':
            messages.error(request, 'Этот отклик уже обработан')
            return redirect('client_responses')

        # Подтверждаем отклик
        response.status = 'accepted'
        response.save()

        # Создаем запись через метод модели
        booking = response.create_booking()

        if not booking:
            messages.error(request, 'Не удалось создать запись')
            return redirect('client_responses')

        # Уведомление мастеру
        Notification.objects.create(
            user=response.master.user,
            notification_type='response_accepted',
            title='Ваш отклик принят',
            message=f'Клиент {response.post.client.full_name} принял ваш отклик. Создана запись на {booking.date} в {booking.time}',
            link='/master/bookings/'
        )

        messages.success(
            request,
            f'Отклик принят! Запись создана и добавлена во вкладку "Записи" на {booking.date} в {booking.time}'
        )

    return redirect('client_responses')


@login_required
def reject_response(request, response_id):
    """Отклонить отклик"""
    if request.method == 'POST':
        response = get_object_or_404(PostResponse, id=response_id)

        if response.post.client.user != request.user:
            messages.error(request, 'У вас нет прав')
            return redirect('client_responses')

        # Проверяем, можно ли отклонить (только если статус pending)
        if response.status != 'pending':
            messages.error(request, 'Этот отклик уже обработан')
            return redirect('client_responses')

        response.status = 'rejected'
        response.save()

        # Создаем уведомление для мастера
        Notification.objects.create(
            user=response.master.user,
            notification_type='response_rejected',
            title='Ваш отклик отклонен',
            message=f'Клиент {response.post.client.full_name} отклонил ваш отклик на пост',
            link=f'/master/responses/'
        )

        messages.success(request, 'Отклик отклонен')

    return redirect('client_responses')


@login_required
def reschedule_booking(request, booking_id):
    """Перенести запись"""
    if request.method == 'POST':
        booking = get_object_or_404(Booking, id=booking_id)

        # Проверяем права
        if request.user.role == 'client' and booking.client.user != request.user:
            messages.error(request, 'У вас нет прав')
            return redirect('client_bookings' if request.user.role == 'client' else 'master_bookings')
        elif request.user.role == 'master' and booking.master.user != request.user:
            messages.error(request, 'У вас нет прав')
            return redirect('master_bookings')

        # Проверяем, можно ли перенести
        if not booking.can_cancel:
            messages.error(
                request, 'Нельзя перенести запись менее чем за 24 часа')
            return redirect('client_bookings' if request.user.role == 'client' else 'master_bookings')

        new_date = request.POST.get('new_date')
        new_time = request.POST.get('new_time')

        if new_date and new_time:
            booking.date = new_date
            booking.time = new_time
            booking.save()

            # Создаем уведомление для другой стороны
            if request.user.role == 'client':
                Notification.objects.create(
                    user=booking.master.user,
                    notification_type='booking_rescheduled',
                    title='Запись перенесена',
                    message=f'Клиент {booking.client.full_name} перенес запись на {booking.date} в {booking.time}',
                    link=f'/master/bookings/'
                )
            else:
                Notification.objects.create(
                    user=booking.client.user,
                    notification_type='booking_rescheduled',
                    title='Запись перенесена',
                    message=f'Мастер {booking.master.display_name} перенес запись на {booking.date} в {booking.time}',
                    link=f'/client/bookings/'
                )

            messages.success(request, 'Запись успешно перенесена')
        else:
            messages.error(request, 'Укажите новую дату и время')

    return redirect('client_bookings' if request.user.role == 'client' else 'master_bookings')


@login_required
def client_masters(request):
    if request.user.role != 'client':
        messages.error(request, 'У вас нет доступа')
        return redirect('home')

    client_profile = request.user.client_profile

    bookings = Booking.objects.filter(
        client=client_profile
    ).select_related(
        'master',
        'master__user'
    ).order_by('-date', '-time')

    masters_data = {}

    for booking in bookings:
        master = booking.master

        if master.id not in masters_data:
            masters_data[master.id] = {
                'master': master,
                'last_booking': booking,
                'total_bookings': 1,
            }
        else:
            masters_data[master.id]['total_bookings'] += 1

    context = {
        'masters_data': list(masters_data.values()),
        'client': client_profile,
    }

    return render(request, 'clients/my_masters.html', context)
