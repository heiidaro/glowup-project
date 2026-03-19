from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import ClientProfile
from django.contrib import messages
from datetime import datetime, date, timedelta
import calendar
from bookings.models import Booking  # Добавьте импорт


def get_calendar_days(year, month, bookings):
    """Генерирует дни месяца для календаря с отметками о записях"""
    first_day = date(year, month, 1)
    _, num_days = calendar.monthrange(year, month)
    first_weekday = first_day.weekday()

    # Создаем множество дат, на которые есть записи
    booking_dates = {booking.date for booking in bookings}

    days = []

    # Пустые ячейки для дней предыдущего месяца
    for _ in range(first_weekday):
        days.append({'date': None, 'day': '', 'has_booking': False})

    # Дни текущего месяца
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
def client_dashboard(request):
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
        # Если дата не выбрана, показываем записи на сегодня
        selected_date_bookings = Booking.objects.filter(
            client=client_profile,
            date=today.date()
        ).select_related('master')
        selected_date = today.date().isoformat()

    # Генерируем дни для календаря
    calendar_days = get_calendar_days(
        current_year, current_month, month_bookings)

    context = {
        'client': client_profile,
        'user': request.user,
        'show_profile_modal': not client_profile.is_profile_completed,
        'recent_messages': [],
        'recent_masters': [],
        'responses': [],
        'selected_date_bookings': selected_date_bookings,
        'selected_date': selected_date,
        'calendar_days': calendar_days,
        'current_month': current_month,
        'current_year': current_year,
        'month_name': get_month_name(current_month),
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
