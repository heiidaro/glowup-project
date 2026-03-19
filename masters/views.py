from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from .models import MasterProfile
from bookings.models import Booking
from datetime import datetime, date
import calendar


def get_calendar_days(year, month, bookings):
    """Генерирует дни месяца для календаря"""
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
    calendar_days = get_calendar_days(
        current_year, current_month, month_bookings)

    # Получаем последние отклики на посты (заглушка)
    recent_responses = []

    # Получаем последних клиентов
    recent_clients = []
    for booking in Booking.objects.filter(master=master_profile).select_related('client')[:5]:
        if booking.client not in recent_clients:
            recent_clients.append(booking.client)

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
