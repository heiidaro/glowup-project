from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from .models import MasterProfile
from bookings.models import Booking
from datetime import datetime, date, time, timedelta
import calendar
from django.utils import timezone
from reviews.models import Review
from bookings.models import PostResponse
import json
from django.db.models import Avg
from notifications.models import Notification
from .models import MasterProfile
import requests
from django.conf import settings
from .models import MasterProfile, Portfolio, Service, ServiceCategory, MasterScheduleSlot
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST


def geocode_yandex_address(address: str):
    if not address:
        return None, None

    full_address = f"Тюмень, {address}" if "тюмень" not in address.lower(
    ) else address

    url = "https://geocode-maps.yandex.ru/1.x/"
    params = {
        "apikey": settings.YANDEX_GEOCODER_API_KEY,
        "geocode": full_address,
        "format": "json",
        "results": 1,
        "lang": "ru_RU",
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(
            url, params=params, headers=headers, timeout=10)

        if response.status_code != 200:
            print("❌ Ошибка геокодера:", response.status_code)
            print(response.text)
            return None, None

        data = response.json()
        members = data["response"]["GeoObjectCollection"]["featureMember"]

        if not members:
            return None, None

        pos = members[0]["GeoObject"]["Point"]["pos"]
        lng, lat = pos.split()

        return float(lat), float(lng)

    except Exception as e:
        print("❌ Exception:", str(e))
        return None, None


@login_required
def masters_list(request):
    """Список всех мастеров"""

    masters = MasterProfile.objects.filter(
        is_approved=True,
        user__is_active=True
    ).select_related('user')

    masters_data = []
    masters_map_data = []

    for master in masters:
        portfolio = list(
            Portfolio.objects.filter(
                master=master,
                is_hidden=False
            ).order_by('-created_at')[:3]
        )

        try:
            services = master.services.filter(is_active=True)[:3]
        except Exception:
            services = []

        try:
            avg_price = master.services.filter(is_active=True).aggregate(
                Avg('price')
            )['price__avg'] or 0
        except Exception:
            avg_price = 0

        try:
            reviews = Review.objects.filter(
                master=master,
                is_approved=True,
                is_blocked=False
            )
            rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
            reviews_count = reviews.count()
        except Exception:
            rating = 0
            reviews_count = 0

        masters_data.append({
            'id': master.id,
            'display_name': master.display_name or "Мастер",
            'address': master.address_text or "Адрес не указан",
            'avatar': master.avatar,
            'bio': master.bio,
            'portfolio': portfolio,
            'services': services,
            'avg_price': avg_price,
            'rating': rating,
            'reviews_count': reviews_count,
            'user': master.user,
        })

        if master.latitude is not None and master.longitude is not None:
            masters_map_data.append({
                'id': master.id,
                'name': master.display_name or "Мастер",
                'address': master.address_text or "Адрес не указан",
                'lat': float(master.latitude),
                'lng': float(master.longitude),
                'price': round(avg_price) if avg_price else None,
            })

    context = {
        'masters': masters_data,
        'masters_map_data': masters_map_data,
        'yandex_maps_api_key': settings.YANDEX_MAPS_API_KEY,
    }

    return render(request, 'masters/masters_list.html', context)


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


def get_month_name(month):
    months = [
        'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
    ]
    return months[month - 1]


def round_duration_to_slot(duration_minutes):
    """
    Округляет длительность услуги вверх до шага 30 минут.
    80 минут -> 90 минут.
    """
    step = 30
    return ((int(duration_minutes) + step - 1) // step) * step


def time_to_minutes(value):
    return value.hour * 60 + value.minute


def minutes_to_time(value):
    return time(value // 60, value % 60)


def generate_available_slots(master, service, selected_date):
    """
    Генерирует доступные времена записи по свободным интервалам мастера
    и уже существующим активным записям.
    """
    rounded_duration = round_duration_to_slot(service.duration_minutes)

    schedule_slots = MasterScheduleSlot.objects.filter(
        master=master,
        date=selected_date,
        is_available=True
    ).order_by('start_time')

    active_bookings = Booking.objects.filter(
        master=master,
        date=selected_date,
        status='active'
    )

    busy_ranges = []

    for booking in active_bookings:
        start = time_to_minutes(booking.time)

        if booking.end_time:
            end = time_to_minutes(booking.end_time)
        else:
            end = start + 60

        busy_ranges.append((start, end))

    result = []

    for slot in schedule_slots:
        slot_start = time_to_minutes(slot.start_time)
        slot_end = time_to_minutes(slot.end_time)

        current = slot_start

        while current + rounded_duration <= slot_end:
            candidate_start = current
            candidate_end = current + rounded_duration

            has_conflict = False

            for busy_start, busy_end in busy_ranges:
                if candidate_start < busy_end and candidate_end > busy_start:
                    has_conflict = True
                    break

            if not has_conflict:
                result.append({
                    'start': minutes_to_time(candidate_start),
                    'end': minutes_to_time(candidate_end),
                    'duration': rounded_duration,
                })

            current += 30

    return result


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


def get_month_name(month):
    months = [
        'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
    ]
    return months[month - 1]


@login_required
def master_dashboard(request):
    # Проверяем роль
    if request.user.role != 'master':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('home')

    # Получаем или создаем профиль
    master_profile, created = MasterProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'display_name': request.user.email,
            'address_text': 'Адрес не указан',
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

    # Получаем записи мастера за выбранный месяц
    month_bookings = Booking.objects.filter(
        master=master_profile,
        date__year=current_year,
        date__month=current_month
    ).select_related('client')

    # Получаем записи на выбранный день
    selected_date_bookings = []
    if selected_date:
        try:
            selected_date_obj = datetime.strptime(
                selected_date, '%Y-%m-%d').date()
            selected_date_bookings = Booking.objects.filter(
                master=master_profile,
                date=selected_date_obj
            ).select_related('client')
        except (ValueError, TypeError):
            selected_date_bookings = []
    else:
        selected_date_bookings = Booking.objects.filter(
            master=master_profile,
            date=today.date()
        ).select_related('client')
        selected_date = today.date().isoformat()

    # Генерируем дни для календаря
    calendar_days = get_dashboard_calendar_days(
        current_year, current_month, month_bookings)

    # Получаем последние отклики на посты (заглушка)
    recent_responses = []

    # Получаем последних клиентов
    recent_clients = []
    for booking in Booking.objects.filter(master=master_profile).select_related('client')[:5]:
        if booking.client not in recent_clients:
            recent_clients.append(booking.client)

    recent_responses = PostResponse.objects.filter(
        master=master_profile
    ).select_related('post', 'post__client').order_by('-created_at')[:3]

    upcoming_bookings = Booking.objects.filter(
        master=master_profile,
        date__gte=timezone.now().date(),
        status='active'
    ).order_by('date', 'time')[:5]

    portfolio_items = Portfolio.objects.filter(
        master=master_profile,
        is_hidden=False
    ).order_by('-created_at')[:3]

    master_services = Service.objects.filter(
        master=master_profile,
        is_active=True
    ).select_related('category').order_by('created_at')

    service_categories = ServiceCategory.objects.all()

    reviews = Review.objects.filter(
        master=master_profile,
        is_approved=True,
        is_blocked=False
    ).select_related('client').order_by('-created_at')[:3]

    context = {
        'master': master_profile,
        'user': request.user,
        'show_profile_modal': not master_profile.is_profile_completed,
        'recent_responses': recent_responses,
        'recent_clients': recent_clients[:3],
        'selected_date_bookings': selected_date_bookings,
        'selected_date': selected_date,
        'calendar_days': calendar_days,
        'current_month': current_month,
        'current_year': current_year,
        'month_name': get_month_name(current_month),
        'upcoming_bookings': upcoming_bookings,
        'yandex_maps_api_key': settings.YANDEX_MAPS_API_KEY,
        'portfolio_items': portfolio_items,
        'master_services': master_services,
        'service_categories': service_categories,
        'reviews': reviews,
    }

    return render(request, 'masters/dashboard.html', context)


@login_required
def complete_profile(request):
    if request.method == 'POST':
        master_profile = MasterProfile.objects.get(user=request.user)

        display_name = request.POST.get('display_name')
        address_text = request.POST.get('address_text')
        bio = request.POST.get('bio')
        phone = request.POST.get('phone')
        email = request.POST.get('email')

        if display_name:
            master_profile.display_name = display_name

        if address_text:
            master_profile.address_text = address_text

            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')

            if latitude and longitude:
                try:
                    master_profile.latitude = float(latitude)
                    master_profile.longitude = float(longitude)
                except ValueError:
                    messages.error(request, 'Некорректные координаты адреса')
                    return redirect('master_dashboard')
            else:
                messages.error(
                    request, 'Выберите адрес из подсказок Яндекс Карт')
                return redirect('master_dashboard')

            if bio:
                master_profile.bio = bio

        user = request.user
        if phone and phone != user.phone:
            user.phone = phone
        if email and email != user.email:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            if not User.objects.exclude(id=user.id).filter(email=email).exists():
                user.email = email
            else:
                messages.error(request, 'Этот email уже используется')
                return redirect('master_dashboard')

        master_profile.is_profile_completed = True
        master_profile.save()
        user.save()

        messages.success(request, 'Профиль успешно заполнен!')
        return redirect('master_dashboard')

    return redirect('master_dashboard')


@login_required
def update_profile(request):
    if request.method == 'POST':
        master_profile = MasterProfile.objects.get(user=request.user)
        user = request.user

        display_name = request.POST.get('display_name')
        address_text = request.POST.get('address_text')
        bio = request.POST.get('bio')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if display_name:
            master_profile.display_name = display_name

        if address_text:
            master_profile.address_text = address_text

            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')

        if latitude and longitude:
            try:
                master_profile.latitude = float(latitude)
                master_profile.longitude = float(longitude)
            except ValueError:
                messages.error(request, 'Некорректные координаты адреса')
                return redirect('master_dashboard')
        else:
            messages.error(request, 'Выберите адрес из подсказок Яндекс Карт')
            return redirect('master_dashboard')

        if bio:
            master_profile.bio = bio

        if phone and phone != user.phone:
            user.phone = phone

        if email and email != user.email:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            if not User.objects.exclude(id=user.id).filter(email=email).exists():
                user.email = email
            else:
                messages.error(request, 'Этот email уже используется')
                return redirect('master_dashboard')

        if new_password and confirm_password and new_password == confirm_password:
            user.set_password(new_password)
            update_session_auth_hash(request, user)
            messages.success(request, 'Пароль успешно изменен')
        elif new_password or confirm_password:
            if new_password != confirm_password:
                messages.error(request, 'Пароли не совпадают')
                return redirect('master_dashboard')

        master_profile.save()
        user.save()

        messages.success(request, 'Профиль успешно обновлен!')
        return redirect('master_dashboard')

    return redirect('master_dashboard')


@login_required
def master_bookings(request):
    """Страница всех записей мастера"""
    # Проверяем роль
    if request.user.role != 'master':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('home')

    # Получаем профиль мастера
    try:
        master_profile = MasterProfile.objects.get(user=request.user)
    except MasterProfile.DoesNotExist:
        messages.error(request, 'Профиль мастера не найден')
        return redirect('home')

    # Текущая дата и время
    now = timezone.now()
    today = now.date()

    # Получаем месяц и год из GET параметров
    try:
        current_month = int(request.GET.get('month', now.month))
        current_year = int(request.GET.get('year', now.year))
    except ValueError:
        current_month = now.month
        current_year = now.year

    # Все записи мастера
    all_bookings = Booking.objects.filter(
        master=master_profile
    ).select_related('client', 'client__user').order_by('date', 'time')

    # Разделяем на активные и архивные
    active_bookings = []
    archived_bookings = []

    for booking in all_bookings:
        # Запись считается активной, если:
        # 1. Статус 'active'
        # 2. Дата сегодня или позже (или сегодня и время еще не прошло)
        if booking.status == 'active':
            if booking.date > today or (booking.date == today and booking.time > now.time()):
                active_bookings.append(booking)
            else:
                archived_bookings.append(booking)
        else:
            archived_bookings.append(booking)

    # Получаем записи для календаря за выбранный месяц
    month_active = [b for b in active_bookings if b.date.year ==
                    current_year and b.date.month == current_month]
    month_archived = [b for b in archived_bookings if b.date.year ==
                      current_year and b.date.month == current_month]

    # Генерируем дни для календаря
    calendar_days = get_calendar_days(
        current_year, current_month, month_active, month_archived)

    context = {
        'active_bookings': active_bookings,
        'archived_bookings': archived_bookings,
        'calendar_days': calendar_days,
        'current_month': current_month,
        'current_year': current_year,
        'month_name': get_month_name(current_month),
        'now': now,
        'today': today,
    }

    return render(request, 'masters/bookings.html', context)


@login_required
def cancel_booking(request, booking_id):
    """Отмена записи мастером"""
    if request.method == 'POST':
        booking = get_object_or_404(Booking, id=booking_id)

        # Проверяем, что мастер имеет отношение к записи
        if booking.master.user != request.user:
            messages.error(request, 'У вас нет прав для отмены этой записи')
            return redirect('master_bookings')

        # Проверяем, можно ли отменить
        if not booking.can_cancel:
            messages.error(
                request, 'Нельзя отменить запись менее чем за 24 часа')
            return redirect('master_bookings')

        booking.status = 'cancelled'
        booking.save()

        messages.success(request, 'Запись успешно отменена')

    return redirect('master_bookings')


@login_required
def reschedule_booking(request, booking_id):
    """Перенос записи мастером"""
    if request.method == 'POST':
        booking = get_object_or_404(Booking, id=booking_id)

        # Проверяем права
        if booking.master.user != request.user:
            messages.error(request, 'У вас нет прав для переноса этой записи')
            return redirect('master_bookings')

        # Проверяем, можно ли перенести
        if not booking.can_cancel:
            messages.error(
                request, 'Нельзя перенести запись менее чем за 24 часа')
            return redirect('master_bookings')

        new_date = request.POST.get('new_date')
        new_time = request.POST.get('new_time')

        if new_date and new_time:
            booking.date = new_date
            booking.time = new_time
            booking.save()
            messages.success(request, 'Запись успешно перенесена')
        else:
            messages.error(request, 'Укажите новую дату и время')

    return redirect('master_bookings')


@login_required
def master_responses(request):
    """Страница всех откликов мастера"""
    if request.user.role != 'master':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('home')

    master_profile = request.user.master_profile
    responses = PostResponse.objects.filter(
        master=master_profile
    ).select_related('post', 'post__client').order_by('-created_at')

    context = {
        'responses': responses,
        'master': master_profile,
    }

    return render(request, 'masters/responses.html', context)


@login_required
def update_response(request, response_id):
    """Обновить отклик (изменить предложение)"""
    if request.method == 'POST':
        response = get_object_or_404(PostResponse, id=response_id)

        if response.master.user != request.user:
            messages.error(request, 'У вас нет прав')
            return redirect('master_responses')

        # Проверяем, можно ли редактировать
        if not response.can_edit:
            messages.error(
                request, 'Нельзя редактировать уже обработанный отклик')
            return redirect('master_responses')

        response.message = request.POST.get('message', response.message)
        response.proposed_price = request.POST.get(
            'proposed_price', response.proposed_price)
        response.proposed_date = request.POST.get(
            'proposed_date', response.proposed_date)
        response.proposed_time = request.POST.get(
            'proposed_time', response.proposed_time)
        response.save()

        messages.success(request, 'Отклик обновлен')

    return redirect('master_responses')


@login_required
def cancel_response(request, response_id):
    """Отменить отклик (мастером)"""
    if request.method == 'POST':
        response = get_object_or_404(PostResponse, id=response_id)

        if response.master.user != request.user:
            messages.error(request, 'У вас нет прав')
            return redirect('master_responses')

        # Меняем статус на cancelled вместо удаления
        response.status = 'cancelled'
        response.save()

        # Создаем уведомление для клиента
        Notification.objects.create(
            user=response.post.client.user,
            notification_type='response_rejected',
            title='Отклик отменен',
            message=f'Мастер {response.master.display_name} отменил свой отклик на ваш пост',
            link=f'/client/responses/'
        )

        messages.success(request, 'Отклик отменен')

    return redirect('master_responses')


@login_required
def master_clients(request):
    """Страница всех клиентов мастера"""
    if request.user.role != 'master':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('home')

    master_profile = MasterProfile.objects.get(user=request.user)

    # Получаем уникальных клиентов из записей
    bookings = Booking.objects.filter(
        master=master_profile
    ).select_related('client').order_by('-created_at')

    clients = {}
    for booking in bookings:
        if booking.client.id not in clients:
            clients[booking.client.id] = {
                'client': booking.client,
                'last_booking': booking,
                'total_bookings': 1,
                'total_spent': booking.price
            }
        else:
            clients[booking.client.id]['total_bookings'] += 1
            clients[booking.client.id]['total_spent'] += booking.price

    context = {
        'clients': list(clients.values()),
        'master': master_profile,
    }

    return render(request, 'masters/clients.html', context)


@login_required
def master_portfolio(request):
    if request.user.role != 'master':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('home')

    master_profile = MasterProfile.objects.get(user=request.user)
    portfolio_items = Portfolio.objects.filter(
        master=master_profile,
        is_hidden=False
    ).order_by('-created_at')

    context = {
        'portfolio_items': portfolio_items,
        'master': master_profile,
    }

    return render(request, 'masters/portfolio.html', context)


@login_required
def add_portfolio_item(request):
    if request.user.role != 'master':
        messages.error(request, 'У вас нет доступа')
        return redirect('home')

    if request.method == 'POST':
        master_profile = MasterProfile.objects.get(user=request.user)

        image = request.FILES.get('image')
        description = request.POST.get('description', '').strip()

        if not image:
            messages.error(request, 'Выберите фотографию')
            return redirect('master_portfolio')

        Portfolio.objects.create(
            master=master_profile,
            image=image,
            description=description
        )

        messages.success(request, 'Фото добавлено в портфолио')

    return redirect('master_portfolio')


@login_required
def delete_portfolio_item(request, item_id):
    if request.user.role != 'master':
        messages.error(request, 'У вас нет доступа')
        return redirect('home')

    master_profile = MasterProfile.objects.get(user=request.user)
    item = get_object_or_404(Portfolio, id=item_id, master=master_profile)

    if request.method == 'POST':
        item.image.delete(save=False)
        item.delete()
        messages.success(request, 'Фото удалено')

    return redirect('master_portfolio')


@login_required
def master_reviews(request):
    """Страница всех отзывов о мастере"""
    if request.user.role != 'master':
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('home')

    master_profile = MasterProfile.objects.get(user=request.user)

    reviews = Review.objects.filter(
        master=master_profile,
        is_approved=True,
        is_blocked=False
    ).select_related('client').order_by('-created_at')

    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0

    context = {
        'reviews': reviews,
        'master': master_profile,
        'avg_rating': avg_rating,
    }

    return render(request, 'masters/reviews.html', context)


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
def save_master_services(request):
    if request.user.role != 'master':
        messages.error(request, 'У вас нет доступа')
        return redirect('home')

    if request.method != 'POST':
        return redirect('master_dashboard')

    master_profile = MasterProfile.objects.get(user=request.user)

    service_ids = request.POST.getlist('service_id[]')
    names = request.POST.getlist('service_name[]')
    categories = request.POST.getlist('category_id[]')
    durations = request.POST.getlist('duration_minutes[]')
    prices = request.POST.getlist('price[]')
    descriptions = request.POST.getlist('description[]')

    saved_ids = []

    for index, raw_name in enumerate(names):
        name = raw_name.strip()

        if not name:
            continue

        service_id = service_ids[index] if index < len(service_ids) else ''
        category_id = categories[index] if index < len(categories) else ''
        duration = durations[index] if index < len(durations) else '60'
        price = prices[index] if index < len(prices) else ''
        description = descriptions[index] if index < len(descriptions) else ''

        if not category_id:
            messages.error(request, f'Выберите категорию для услуги: {name}')
            return redirect('master_dashboard')

        if not price:
            messages.error(request, f'Укажите стоимость для услуги: {name}')
            return redirect('master_dashboard')

        if service_id:
            service = get_object_or_404(
                Service, id=service_id, master=master_profile)
        else:
            service = Service(master=master_profile)

        service.name = name
        service.category_id = int(category_id)
        service.duration_minutes = int(duration or 60)
        service.price = price
        service.description = description
        service.is_active = True
        service.save()

        saved_ids.append(service.id)

    if not saved_ids:
        messages.error(request, 'Добавьте хотя бы одну услугу')
        return redirect('master_dashboard')

    Service.objects.filter(
        master=master_profile
    ).exclude(id__in=saved_ids).update(is_active=False)

    messages.success(request, 'Услуги сохранены')
    return redirect('master_dashboard')


@login_required
def master_public_profile(request, master_id):
    master = get_object_or_404(MasterProfile, id=master_id)

    services = Service.objects.filter(
        master=master,
        is_active=True
    ).select_related('category').order_by('price')

    portfolio_items = Portfolio.objects.filter(
        master=master,
        is_hidden=False
    ).order_by('-created_at')

    reviews = Review.objects.filter(
        master=master,
        is_approved=True,
        is_blocked=False
    ).select_related('client').order_by('-created_at')

    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    reviews_count = reviews.count()

    avg_price = services.aggregate(Avg('price'))['price__avg'] or 0

    categories = []
    category_ids = set()

    for service in services:
        if service.category and service.category_id not in category_ids:
            categories.append(service.category)
            category_ids.add(service.category_id)

    context = {
        'master': master,
        'services': services,
        'portfolio_items': portfolio_items,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'reviews_count': reviews_count,
        'avg_price': avg_price,
        'categories': categories,
    }

    return render(request, 'masters/public_profile.html', context)


@login_required
def add_master_review(request, master_id):
    if request.user.role != 'client':
        messages.error(request, 'Оставлять отзывы могут только клиенты')
        return redirect('master_public_profile', master_id=master_id)

    master = get_object_or_404(MasterProfile, id=master_id)

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '').strip()

        if not rating or not comment:
            messages.error(request, 'Укажите оценку и текст отзыва')
            return redirect('master_public_profile', master_id=master.id)

        client_profile = request.user.client_profile

        Review.objects.create(
            master=master,
            client=client_profile,
            rating=int(rating),
            comment=comment,
            is_approved=True,
            is_blocked=False
        )

        messages.success(request, 'Отзыв добавлен')

    return redirect('master_public_profile', master_id=master.id)


@login_required
def master_schedule(request):
    if request.user.role != 'master':
        messages.error(request, 'У вас нет доступа')
        return redirect('home')

    master_profile = MasterProfile.objects.get(user=request.user)

    selected_date = request.GET.get('date')
    if selected_date:
        try:
            selected_date_obj = datetime.strptime(
                selected_date, '%Y-%m-%d').date()
        except ValueError:
            selected_date_obj = timezone.now().date()
    else:
        selected_date_obj = timezone.now().date()

    week_start = selected_date_obj - \
        timedelta(days=selected_date_obj.weekday())
    week_day_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

    week_days = []
    for i in range(7):
        day_date = week_start + timedelta(days=i)
        week_days.append({
            'date': day_date,
            'name': week_day_names[i],
        })

    week_end = week_start + timedelta(days=6)

    prev_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)

    slots = MasterScheduleSlot.objects.filter(
        master=master_profile,
        date__range=[week_start, week_end]
    ).order_by('date', 'start_time')

    bookings = Booking.objects.filter(
        master=master_profile,
        date__range=[week_start, week_end],
        status='active'
    ).select_related('client').order_by('date', 'time')

    context = {
        'master': master_profile,
        'selected_date': selected_date_obj,
        'week_start': week_start,
        'week_end': week_end,
        'week_days': week_days,
        'slots': slots,
        'bookings': bookings,
        'prev_week': prev_week,
        'next_week': next_week,
    }

    return render(request, 'masters/schedule.html', context)


@login_required
@require_POST
def ajax_delete_schedule_slot(request, slot_id):
    if request.user.role != 'master':
        return JsonResponse({'success': False, 'error': 'Нет доступа'}, status=403)

    master_profile = MasterProfile.objects.get(user=request.user)

    slot = get_object_or_404(
        MasterScheduleSlot,
        id=slot_id,
        master=master_profile
    )

    slot.delete()

    return JsonResponse({'success': True})


@login_required
@require_POST
def ajax_copy_schedule_slot(request, slot_id):
    if request.user.role != 'master':
        return JsonResponse({'success': False, 'error': 'Нет доступа'}, status=403)

    master_profile = MasterProfile.objects.get(user=request.user)

    slot = get_object_or_404(
        MasterScheduleSlot,
        id=slot_id,
        master=master_profile
    )

    dates = request.POST.getlist('dates[]')
    created = []

    for raw_date in dates:
        try:
            target_date = datetime.strptime(raw_date, '%Y-%m-%d').date()
        except ValueError:
            continue

        new_slot = MasterScheduleSlot.objects.create(
            master=master_profile,
            date=target_date,
            start_time=slot.start_time,
            end_time=slot.end_time,
            is_available=True
        )

        created.append({
            'id': new_slot.id,
            'date': str(new_slot.date),
            'start_time': new_slot.start_time.strftime('%H:%M'),
            'end_time': new_slot.end_time.strftime('%H:%M'),
        })

    return JsonResponse({
        'success': True,
        'created': created
    })


@login_required
@require_POST
def ajax_create_schedule_slot(request):
    if request.user.role != 'master':
        return JsonResponse({'success': False, 'error': 'Нет доступа'}, status=403)

    master_profile = MasterProfile.objects.get(user=request.user)

    slot_date = request.POST.get('date')
    start_time_raw = request.POST.get('start_time')
    end_time_raw = request.POST.get('end_time')

    if not slot_date or not start_time_raw or not end_time_raw:
        return JsonResponse({'success': False, 'error': 'Не заполнены данные'}, status=400)

    start_time_obj = datetime.strptime(start_time_raw, '%H:%M').time()
    end_time_obj = datetime.strptime(end_time_raw, '%H:%M').time()

    if end_time_obj <= start_time_obj:
        return JsonResponse({'success': False, 'error': 'Конец интервала должен быть позже начала'}, status=400)

    slot = MasterScheduleSlot.objects.create(
        master=master_profile,
        date=slot_date,
        start_time=start_time_obj,
        end_time=end_time_obj,
        is_available=True
    )

    return JsonResponse({
        'success': True,
        'slot': {
            'id': slot.id,
            'date': str(slot.date),
            'start_time': start_time_obj.strftime('%H:%M'),
            'end_time': end_time_obj.strftime('%H:%M'),
        }
    })


@login_required
def add_schedule_slot(request):
    if request.user.role != 'master':
        messages.error(request, 'У вас нет доступа')
        return redirect('home')

    if request.method == 'POST':
        master_profile = MasterProfile.objects.get(user=request.user)

        slot_date = request.POST.get('date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')

        if not slot_date or not start_time or not end_time:
            messages.error(request, 'Заполните дату, начало и конец интервала')
            return redirect('master_schedule')

        MasterScheduleSlot.objects.create(
            master=master_profile,
            date=slot_date,
            start_time=start_time,
            end_time=end_time,
            is_available=True
        )

        messages.success(request, 'Интервал добавлен')

    return redirect(f"{request.META.get('HTTP_REFERER', '/master/schedule/')}")


@login_required
def delete_schedule_slot(request, slot_id):
    if request.user.role != 'master':
        messages.error(request, 'У вас нет доступа')
        return redirect('home')

    master_profile = MasterProfile.objects.get(user=request.user)

    slot = get_object_or_404(
        MasterScheduleSlot,
        id=slot_id,
        master=master_profile
    )

    if request.method == 'POST':
        selected_date = slot.date
        slot.delete()
        messages.success(request, 'Интервал удалён')
        return redirect(f'/master/schedule/?date={selected_date}')

    return redirect('master_schedule')


@login_required
def book_master(request, master_id):
    if request.user.role != 'client':
        messages.error(request, 'Записываться могут только клиенты')
        return redirect('master_public_profile', master_id=master_id)

    master = get_object_or_404(MasterProfile, id=master_id)

    services = Service.objects.filter(
        master=master,
        is_active=True
    ).select_related('category').order_by('price')

    selected_service_id = request.GET.get('service')
    selected_date = request.GET.get('date')

    selected_service = None
    selected_date_obj = None
    available_slots = []

    if selected_service_id:
        selected_service = get_object_or_404(
            Service,
            id=selected_service_id,
            master=master,
            is_active=True
        )

    if selected_date:
        try:
            selected_date_obj = datetime.strptime(
                selected_date, '%Y-%m-%d').date()
        except ValueError:
            selected_date_obj = None

    if selected_service and selected_date_obj:
        available_slots = generate_available_slots(
            master,
            selected_service,
            selected_date_obj
        )

    context = {
        'master': master,
        'services': services,
        'selected_service': selected_service,
        'selected_date': selected_date_obj,
        'available_slots': available_slots,
    }

    return render(request, 'masters/book_master.html', context)


@login_required
def create_master_booking(request, master_id):
    if request.user.role != 'client':
        messages.error(request, 'Записываться могут только клиенты')
        return redirect('master_public_profile', master_id=master_id)

    master = get_object_or_404(MasterProfile, id=master_id)

    if request.method != 'POST':
        return redirect('book_master', master_id=master.id)

    service_id = request.POST.get('service_id')
    booking_date = request.POST.get('date')
    start_time = request.POST.get('start_time')
    end_time = request.POST.get('end_time')
    client_note = request.POST.get('client_note', '').strip()
    client_photo = request.FILES.get('client_photo')

    service = get_object_or_404(
        Service,
        id=service_id,
        master=master,
        is_active=True
    )

    if not booking_date or not start_time or not end_time:
        messages.error(request, 'Выберите дату и свободное время')
        return redirect('book_master', master_id=master.id)

    booking_date_obj = datetime.strptime(booking_date, '%Y-%m-%d').date()
    start_time_obj = datetime.strptime(start_time, '%H:%M').time()
    end_time_obj = datetime.strptime(end_time, '%H:%M').time()

    # Повторная серверная проверка: слот всё ещё свободен
    available_slots = generate_available_slots(
        master, service, booking_date_obj)
    is_available = any(
        slot['start'] == start_time_obj and slot['end'] == end_time_obj
        for slot in available_slots
    )

    if not is_available:
        messages.error(request, 'Это время уже занято. Выберите другой слот')
        return redirect(
            f'/master/profile/{master.id}/book/?service={service.id}&date={booking_date}'
        )

    client_profile = request.user.client_profile

    Booking.objects.create(
        client=client_profile,
        master=master,
        service=service.name,
        service_ref=service,
        date=booking_date_obj,
        time=start_time_obj,
        end_time=end_time_obj,
        price=service.price,
        status='active',
        client_note=client_note,
        client_photo=client_photo
    )

    messages.success(request, 'Вы успешно записались к мастеру')
    return redirect('client_bookings')
