from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.password_validation import validate_password
from .models import User
import re


def normalize_contact(value):
    contact = (value or "").strip()

    if not contact:
        raise ValidationError("Введите email или телефон")

    if "@" in contact:
        email = contact.lower()

        try:
            validate_email(email)
        except ValidationError:
            raise ValidationError("Введите корректный email")

        return email

    digits = re.sub(r"\D", "", contact)

    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]

    if len(digits) == 10:
        digits = "7" + digits

    if not (digits.startswith("7") and len(digits) == 11):
        raise ValidationError(
            "Телефон должен быть в формате +7 (___) ___-__-__")

    return f"+{digits}"


def russian_password_errors(password):
    errors = []

    if len(password) < 8:
        errors.append("Пароль должен содержать минимум 8 символов.")

    if password.isdigit():
        errors.append("Пароль не должен состоять только из цифр.")

    common_passwords = {
        "password",
        "qwerty",
        "qwerty123",
        "12345678",
        "123456789",
        "11111111",
        "00000000",
        "admin123",
        "adminadmin",
        "пароль",
    }

    if password.lower() in common_passwords:
        errors.append(
            "Пароль слишком простой. Придумайте более надёжный пароль.")

    try:
        validate_password(password)
    except ValidationError as error:
        for message in error.messages:
            text = str(message)

            if "too similar" in text.lower():
                errors.append("Пароль слишком похож на ваши личные данные.")
            elif "too short" in text.lower():
                errors.append("Пароль слишком короткий.")
            elif "too common" in text.lower():
                errors.append("Пароль слишком распространённый.")
            elif "entirely numeric" in text.lower():
                errors.append("Пароль не должен состоять только из цифр.")
            else:
                errors.append(text)

    return list(dict.fromkeys(errors))


class RegisterForm(forms.Form):
    contact = forms.CharField(
        label="Email или телефон",
        widget=forms.TextInput(attrs={
            "placeholder": "Email или телефон",
            "autocomplete": "username",
        })
    )

    role = forms.ChoiceField(
        label="Кем вы хотите стать?",
        choices=[
            (User.ROLE_CLIENT, "Клиент"),
            (User.ROLE_MASTER, "Мастер"),
        ],
        widget=forms.RadioSelect
    )

    password1 = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={
            "placeholder": "Минимум 8 символов",
            "autocomplete": "new-password",
        })
    )

    password2 = forms.CharField(
        label="Повтор пароля",
        widget=forms.PasswordInput(attrs={
            "placeholder": "Повторите пароль",
            "autocomplete": "new-password",
        })
    )

    def clean_contact(self):
        contact = normalize_contact(self.cleaned_data.get("contact"))

        if "@" in contact:
            if User.objects.filter(email=contact).exists():
                raise ValidationError(
                    "Пользователь с таким email уже существует")
        else:
            if User.objects.filter(phone=contact).exists():
                raise ValidationError(
                    "Пользователь с таким телефоном уже существует")

        return contact

    def clean_role(self):
        role = self.cleaned_data.get("role")

        if role not in [User.ROLE_CLIENT, User.ROLE_MASTER]:
            raise ValidationError("Выберите роль: клиент или мастер")

        return role

    def clean_password1(self):
        password = self.cleaned_data.get("password1") or ""

        errors = russian_password_errors(password)

        if errors:
            raise ValidationError(errors)

        return password

    def clean(self):
        cleaned = super().clean()

        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")

        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Пароли не совпадают")

        return cleaned


class LoginForm(forms.Form):
    contact = forms.CharField(
        label="Email или телефон",
        widget=forms.TextInput(attrs={
            "placeholder": "Email или телефон",
            "autocomplete": "username",
        })
    )

    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={
            "placeholder": "Введите пароль",
            "autocomplete": "current-password",
        })
    )

    def clean_contact(self):
        return normalize_contact(self.cleaned_data.get("contact"))


class VerifyCodeForm(forms.Form):
    code = forms.CharField(
        label="Код",
        max_length=6,
        widget=forms.TextInput(attrs={
            "placeholder": "Введите 6 цифр",
            "inputmode": "numeric",
            "autocomplete": "one-time-code",
        })
    )

    def clean_code(self):
        code = (self.cleaned_data.get("code") or "").strip()

        if not code.isdigit() or len(code) != 6:
            raise ValidationError("Введите 6-значный код")

        return code


class PasswordResetRequestForm(forms.Form):
    contact = forms.CharField(
        label="Email или телефон",
        widget=forms.TextInput(attrs={
            "placeholder": "Email или телефон",
            "autocomplete": "username",
        })
    )

    def clean_contact(self):
        return normalize_contact(self.cleaned_data.get("contact"))


class SetNewPasswordForm(forms.Form):
    password1 = forms.CharField(
        label="Новый пароль",
        widget=forms.PasswordInput(attrs={
            "placeholder": "Новый пароль",
            "autocomplete": "new-password",
        })
    )

    password2 = forms.CharField(
        label="Повтор пароля",
        widget=forms.PasswordInput(attrs={
            "placeholder": "Повторите пароль",
            "autocomplete": "new-password",
        })
    )

    def clean_password1(self):
        password = self.cleaned_data.get("password1") or ""

        errors = russian_password_errors(password)

        if errors:
            raise ValidationError(errors)

        return password

    def clean(self):
        cleaned = super().clean()

        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")

        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Пароли не совпадают")

        return cleaned


class SocialRoleForm(forms.Form):
    role = forms.ChoiceField(
        label="Кем вы хотите стать?",
        choices=[
            (User.ROLE_CLIENT, "Клиент"),
            (User.ROLE_MASTER, "Мастер"),
        ],
        widget=forms.RadioSelect
    )

    email = forms.EmailField(
        label="Email",
        required=False,
        widget=forms.EmailInput(attrs={
            "placeholder": "Введите email",
            "autocomplete": "email",
        })
    )

    def __init__(self, *args, require_email=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.require_email = require_email

        if require_email:
            self.fields["email"].required = True

    def clean_role(self):
        role = self.cleaned_data.get("role")

        if role not in [User.ROLE_CLIENT, User.ROLE_MASTER]:
            raise ValidationError("Выберите роль: клиент или мастер")

        return role

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()

        if self.require_email and not email:
            raise ValidationError("Введите email для завершения регистрации")

        if email:
            try:
                validate_email(email)
            except ValidationError:
                raise ValidationError("Введите корректный email")

            if User.objects.filter(email=email).exists():
                raise ValidationError(
                    "Пользователь с таким email уже существует")

        return email
