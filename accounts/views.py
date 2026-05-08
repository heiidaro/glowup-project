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

from django.utils import timezone
from datetime import timedelta

import secrets
import requests
from urllib.parse import urlencode

from django.conf import settings
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .models import SocialAccount
from .forms import SocialRoleForm


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

            channel = PendingSignup.CHANNEL_EMAIL if email else PendingSignup.CHANNEL_PHONE

            try:
                pending = create_pending_signup(
                    channel=channel,
                    email=email,
                    phone=phone,
                    role=role,
                    raw_password=password,
                )
            except RuntimeError:
                form.add_error(
                    "contact",
                    "Не удалось отправить код подтверждения. Проверьте интернет, VPN или настройки почты."
                )
                return render(request, "accounts/register.html", {"form": form})

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

            if not user:
                form.add_error(None, "Неверные данные")
                return render(request, "accounts/login.html", {"form": form})

            if not user.is_active:
                form.add_error(
                    None,
                    "Ваш аккаунт заблокирован администратором. Обратитесь в поддержку."
                )
                return render(request, "accounts/login.html", {"form": form})

            if getattr(user, "is_deleted", False):
                form.add_error(
                    None,
                    "Аккаунт деактивирован. Обратитесь в поддержку."
                )
                return render(request, "accounts/login.html", {"form": form})

            if user.check_password(password):
                login(request, user)

                if user.role == 'client':
                    return redirect('client_dashboard')
                elif user.role == 'master':
                    return redirect('master_dashboard')
                elif user.role == 'admin':
                    return redirect('admin_dashboard')
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


def redirect_user_by_role(user):
    if user.role == User.ROLE_CLIENT:
        return redirect("client_dashboard")

    if user.role == User.ROLE_MASTER:
        return redirect("master_dashboard")

    if user.role == User.ROLE_ADMIN:
        return redirect("admin_dashboard")

    return redirect("home")


def social_login_allowed(user):
    if not user.is_active:
        return False

    if getattr(user, "is_deleted", False):
        return False

    return True


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
                elif user.role == 'admin':
                    return redirect('admin_dashboard')
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
        pending.delete()
        return redirect("register")

    if pending.created_at and timezone.now() - pending.created_at < timedelta(seconds=60):
        messages.error(request, "Повторно отправить код можно через 1 минуту")
        return redirect(f"/verify/?pid={pid}")

    code = generate_code(6)
    pending.code_hash = make_password(code)
    pending.attempts = 0
    pending.expires_at = PendingSignup.default_expires()
    pending.created_at = timezone.now()
    pending.save(update_fields=["code_hash",
                 "attempts", "expires_at", "created_at"])

    if pending.channel == PendingSignup.CHANNEL_EMAIL:
        send_verification_email(pending.email, code)
    else:
        send_verification_sms_stub(pending.phone, code)

    messages.success(request, "Код отправлен повторно")
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


def yandex_redirect_uri(request):
    return request.build_absolute_uri("/accounts/oauth/yandex/callback/")


def social_login_start(request, provider):
    provider = provider.lower()

    if provider != "yandex":
        messages.error(request, "Этот способ входа пока не подключён")
        return redirect("login")

    state = secrets.token_urlsafe(32)
    request.session["oauth_state_yandex"] = state

    params = {
        "response_type": "code",
        "client_id": settings.YANDEX_OAUTH_CLIENT_ID,
        "redirect_uri": yandex_redirect_uri(request),
        "state": state,
    }

    url = "https://oauth.yandex.com/authorize?" + urlencode(params)
    return redirect(url)


def social_login_callback(request, provider):
    provider = provider.lower()

    if provider != "yandex":
        messages.error(request, "Этот способ входа пока не подключён")
        return redirect("login")

    error = request.GET.get("error")
    if error:
        messages.error(request, "Авторизация через Яндекс была отменена")
        return redirect("login")

    code = request.GET.get("code")
    state = request.GET.get("state")

    saved_state = request.session.pop("oauth_state_yandex", None)

    if not code or not state or state != saved_state:
        messages.error(
            request, "Ошибка проверки авторизации. Попробуйте ещё раз.")
        return redirect("login")

    try:
        token_response = requests.post(
            "https://oauth.yandex.com/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.YANDEX_OAUTH_CLIENT_ID,
                "client_secret": settings.YANDEX_OAUTH_CLIENT_SECRET,
                "redirect_uri": yandex_redirect_uri(request),
            },
            timeout=10,
        )

        token_response.raise_for_status()
        token_data = token_response.json()

        access_token = token_data.get("access_token")

        if not access_token:
            messages.error(request, "Яндекс не вернул токен авторизации")
            return redirect("login")

        info_response = requests.get(
            "https://login.yandex.ru/info",
            params={"format": "json"},
            headers={
                "Authorization": f"OAuth {access_token}"
            },
            timeout=10,
        )

        info_response.raise_for_status()
        profile = info_response.json()

    except requests.RequestException:
        messages.error(
            request, "Не удалось получить данные от Яндекса. Попробуйте позже.")
        return redirect("login")

    provider_user_id = str(profile.get("id") or "")
    email = (
        profile.get("default_email")
        or profile.get("email")
        or ""
    ).strip().lower()

    if not provider_user_id:
        messages.error(request, "Яндекс не вернул идентификатор пользователя")
        return redirect("login")

    social_account = SocialAccount.objects.select_related("user").filter(
        provider=SocialAccount.PROVIDER_YANDEX,
        provider_user_id=provider_user_id
    ).first()

    if social_account:
        user = social_account.user

        if not social_login_allowed(user):
            messages.error(
                request, "Ваш аккаунт заблокирован или деактивирован")
            return redirect("login")

        login(request, user)
        return redirect_user_by_role(user)

    if email:
        user = User.objects.filter(email=email).first()

        if user:
            if not social_login_allowed(user):
                messages.error(
                    request, "Ваш аккаунт заблокирован или деактивирован")
                return redirect("login")

            SocialAccount.objects.create(
                user=user,
                provider=SocialAccount.PROVIDER_YANDEX,
                provider_user_id=provider_user_id,
                email=email
            )

            if not user.is_verified:
                user.is_verified = True
                user.verified_channel = "email"
                user.save(update_fields=["is_verified", "verified_channel"])

            login(request, user)
            return redirect_user_by_role(user)

    request.session["pending_social_auth"] = {
        "provider": SocialAccount.PROVIDER_YANDEX,
        "provider_user_id": provider_user_id,
        "email": email,
    }

    return redirect("social_choose_role")


@require_http_methods(["GET", "POST"])
def social_choose_role_view(request):
    pending = request.session.get("pending_social_auth")

    if not pending:
        return redirect("login")

    email_from_provider = (pending.get("email") or "").strip().lower()
    require_email = not bool(email_from_provider)

    if request.method == "POST":
        form = SocialRoleForm(request.POST, require_email=require_email)

        if form.is_valid():
            role = form.cleaned_data["role"]
            email = email_from_provider or form.cleaned_data["email"]

            if not email:
                form.add_error(
                    "email", "Введите email для завершения регистрации")
                return render(request, "accounts/social_choose_role.html", {
                    "form": form,
                    "provider": pending.get("provider"),
                    "email_from_provider": email_from_provider,
                })

            if User.objects.filter(email=email).exists():
                form.add_error(
                    "email", "Пользователь с таким email уже существует")
                return render(request, "accounts/social_choose_role.html", {
                    "form": form,
                    "provider": pending.get("provider"),
                    "email_from_provider": email_from_provider,
                })

            user = User(
                email=email,
                role=role,
                is_active=True,
                is_verified=True,
                verified_channel="email",
            )
            user.set_unusable_password()
            user.save()

            SocialAccount.objects.create(
                user=user,
                provider=pending["provider"],
                provider_user_id=pending["provider_user_id"],
                email=email
            )

            request.session.pop("pending_social_auth", None)

            login(request, user)
            return redirect_user_by_role(user)
    else:
        form = SocialRoleForm(
            initial={"email": email_from_provider},
            require_email=require_email
        )

    return render(request, "accounts/social_choose_role.html", {
        "form": form,
        "provider": pending.get("provider"),
        "email_from_provider": email_from_provider,
    })
