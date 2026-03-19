from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from .forms import RegisterForm, LoginForm
from .models import User
from django.contrib import messages
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.hashers import make_password

from .forms import RegisterForm, LoginForm, VerifyCodeForm
from .models import User, VerificationCode, PendingSignup, PasswordResetToken
from .services import create_pending_signup, verify_pending_code, generate_code, send_verification_email, send_verification_sms_stub
from .forms import PasswordResetRequestForm, SetNewPasswordForm
from .services import create_and_send_password_reset
from django.contrib.auth.decorators import login_required


def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            contact = form.cleaned_data["contact"]
            role = form.cleaned_data["role"]
            password = form.cleaned_data["password1"]

            is_email = "@" in contact
            email = contact.lower() if is_email else None
            phone = None if is_email else contact

            # проверяем, что такого пользователя ещё нет
            if email and User.objects.filter(email=email).exists():
                form.add_error(
                    "contact", "Пользователь с таким email уже существует")
            elif phone and User.objects.filter(phone=phone).exists():
                form.add_error(
                    "contact", "Пользователь с таким телефоном уже существует")
            else:
                channel = PendingSignup.CHANNEL_EMAIL if email else PendingSignup.CHANNEL_PHONE

                pending = create_pending_signup(
                    channel=channel,
                    email=email,
                    phone=phone,
                    role=role,
                    raw_password=password,
                )

                pid = urlsafe_base64_encode(force_bytes(str(pending.id)))
                return redirect(f"/verify/?pid={pid}")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            contact = form.cleaned_data["contact"]
            password = form.cleaned_data["password"]

            if "@" in contact:
                user = User.objects.filter(email=contact).first()
            else:
                user = User.objects.filter(phone=contact).first()

            if user and user.check_password(password):
                login(request, user)

                # Перенаправление в зависимости от роли
                if user.role == 'client':
                    return redirect('client_dashboard')
                elif user.role == 'master':
                    return redirect('master_dashboard')
                else:
                    return redirect('home')

            form.add_error(None, "Неверные данные")
    else:
        form = LoginForm()

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    """Выход из системы"""
    logout(request)
    return redirect('login')


def verify_view(request):
    pid = request.GET.get("pid", "")

    try:
        pending_id = force_str(urlsafe_base64_decode(pid))
        pending = PendingSignup.objects.get(id=pending_id)
    except Exception:
        return redirect("register")

    contact = pending.email or pending.phone

    if request.method == "POST":
        form = VerifyCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"]

            if verify_pending_code(pending, code):
                # на этом шаге создаём пользователя
                user = User.objects.create(
                    email=pending.email,
                    phone=pending.phone,
                    role=pending.role,
                    is_verified=True,
                    verified_channel=pending.channel,
                )
                # выставляем пароль из хэша (готовый хэш)
                user.password = pending.password_hash
                user.save()

                # удаляем черновик регистрации
                pending.delete()

                login(request, user)

                # Перенаправление в зависимости от роли
                if user.role == 'client':
                    return redirect('client_dashboard')
                elif user.role == 'master':
                    return redirect('master_dashboard')
                else:
                    return redirect('home')

            form.add_error("code", "Неверный или просроченный код")
    else:
        form = VerifyCodeForm()

    return render(request, "accounts/verify.html", {"form": form, "contact": contact, "pid": pid})


def resend_code_view(request):
    pid = request.GET.get("pid", "")

    try:
        pending_id = force_str(urlsafe_base64_decode(pid))
        pending = PendingSignup.objects.get(id=pending_id)
    except Exception:
        return redirect("register")

    if pending.is_expired():
        # можно создать новый pending, но проще отправить на регистрацию заново
        pending.delete()
        return redirect("register")

    code = generate_code(6)
    pending.code_hash = make_password(code)
    pending.attempts = 0
    pending.expires_at = PendingSignup.default_expires()
    pending.save(update_fields=["code_hash", "attempts", "expires_at"])

    if pending.channel == PendingSignup.CHANNEL_EMAIL:
        send_verification_email(pending.email, code)
    else:
        send_verification_sms_stub(pending.phone, code)

    return redirect(f"/verify/?pid={pid}")


def password_reset_request_view(request):
    """
    Страница: ввод email/телефона → отправка ссылки.
    Важно: не раскрываем, существует ли пользователь (безопасность).
    """
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            contact = form.cleaned_data["contact"]

            if "@" in contact:
                user = User.objects.filter(email=contact).first()
                channel = PasswordResetToken.CHANNEL_EMAIL
            else:
                user = User.objects.filter(phone=contact).first()
                channel = PasswordResetToken.CHANNEL_PHONE

            if user:
                create_and_send_password_reset(
                    user, channel=channel, request=request)

            # Всегда одинаковый ответ
            return render(request, "accounts/password_reset_sent.html", {"contact": contact})
    else:
        form = PasswordResetRequestForm()

    return render(request, "accounts/password_reset_request.html", {"form": form})


def password_reset_confirm_view(request, token):
    prt = PasswordResetToken.objects.filter(
        token=token, is_used=False).select_related("user").first()
    if not prt or prt.is_expired():
        return render(request, "accounts/password_reset_invalid.html")

    if request.method == "POST":
        form = SetNewPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data["password1"]
            user = prt.user
            user.password = make_password(new_password)
            user.save(update_fields=["password"])

            prt.is_used = True
            prt.save(update_fields=["is_used"])

            return render(request, "accounts/password_reset_done.html")
    else:
        form = SetNewPasswordForm()

    return render(request, "accounts/password_reset_confirm.html", {"form": form})
