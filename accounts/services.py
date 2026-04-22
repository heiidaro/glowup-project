import random
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.urls import reverse

from .models import VerificationCode
from .models import PendingSignup
from .models import PasswordResetToken


def generate_code(length=6) -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(length))


def send_verification_email(email: str, code: str) -> None:
    subject = "Glow Up — код подтверждения"
    message = f"Ваш код подтверждения: {code}\nКод действует 10 минут."
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL",
                         None) or "no-reply@glowup.local"
    send_mail(subject, message, from_email, [email], fail_silently=False)


def send_verification_sms_stub(phone: str, code: str) -> None:
    print(f"[SMS STUB] Send to {phone}: code={code}")


def create_pending_signup(*, channel: str, email: str | None, phone: str | None, role: str, raw_password: str) -> PendingSignup:
    code = generate_code(6)

    pending = PendingSignup.objects.create(
        channel=channel,
        email=email,
        phone=phone,
        role=role,
        password_hash=make_password(raw_password),
        code_hash=make_password(code),
        expires_at=timezone.now() + timedelta(minutes=10),
    )

    if channel == PendingSignup.CHANNEL_EMAIL:
        send_verification_email(email, code)
    else:
        send_verification_sms_stub(phone, code)

    return pending


def verify_pending_code(pending: PendingSignup, code: str) -> bool:
    if pending.is_expired():
        return False

    pending.attempts += 1
    pending.save(update_fields=["attempts"])

    if pending.attempts > 8:
        return False

    return check_password(code, pending.code_hash)


def send_verification_email(email: str, code: str) -> None:
    subject = "Glow Up — код подтверждения"
    message = f"Ваш код подтверждения: {code}\nКод действует 10 минут."
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL",
                         None) or "no-reply@glowup.local"
    send_mail(subject, message, from_email, [email], fail_silently=False)


def send_verification_sms_stub(phone: str, code: str) -> None:
    # ЗАГЛУШКА: в консоль (пока не подключили SMS провайдера)
    # На проде замените на реальную отправку
    print(f"[SMS STUB] Send to {phone}: code={code}")


def verify_code(user, channel: str, code: str, purpose: str = "register") -> bool:
    vc = (
        VerificationCode.objects
        .filter(user=user, channel=channel, purpose=purpose, is_used=False)
        .order_by("-created_at")
        .first()
    )
    if not vc:
        return False
    if vc.is_expired():
        return False

    vc.attempts += 1
    vc.save(update_fields=["attempts"])

    if vc.attempts > 8:
        return False

    ok = check_password(code, vc.code_hash)
    if ok:
        vc.is_used = True
        vc.save(update_fields=["is_used"])
    return ok


def send_password_reset_email(email: str, reset_link: str) -> None:
    subject = "Glow Up — восстановление пароля"
    message = f"Чтобы сменить пароль, перейдите по ссылке:\n{reset_link}\n\nСсылка действует 20 минут."
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL",
                         None) or "no-reply@glowup.local"
    send_mail(subject, message, from_email, [email], fail_silently=False)


def send_password_reset_sms_stub(phone: str, reset_link: str) -> None:
    print(f"[SMS STUB] Send to {phone}: reset_link={reset_link}")


def create_and_send_password_reset(user, channel: str, request) -> None:
    # пометить старые как использованные (опционально)
    PasswordResetToken.objects.filter(
        user=user, is_used=False).update(is_used=True)

    prt = PasswordResetToken.objects.create(
        user=user,
        channel=channel,
        expires_at=PasswordResetToken.default_expires(),
    )

    path = reverse("password_reset_confirm", kwargs={"token": str(prt.token)})
    reset_link = request.build_absolute_uri(path)

    if channel == PasswordResetToken.CHANNEL_EMAIL:
        send_password_reset_email(user.email, reset_link)
    else:
        send_password_reset_sms_stub(user.phone, reset_link)
