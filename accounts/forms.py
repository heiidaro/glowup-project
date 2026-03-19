from django import forms
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from .models import User
import re

phone_validator = RegexValidator(
    r"^\+?\d{10,15}$",
    "Телефон должен быть в формате +79991234567"
)


class RegisterForm(forms.Form):
    contact = forms.CharField(label="Email или телефон")
    role = forms.ChoiceField(
        label="Кем вы хотите стать?",
        choices=[
            (User.ROLE_CLIENT, "Клиент"),
            (User.ROLE_MASTER, "Мастер"),
        ],
        widget=forms.RadioSelect
    )
    password1 = forms.CharField(label="Пароль", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Повтор пароля", widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            raise ValidationError("Пароли не совпадают")
        return cleaned

    def clean_contact(self):
        contact = (self.cleaned_data.get("contact") or "").strip()
        if not contact:
            raise forms.ValidationError("Введите email или телефон")

        if "@" in contact:
            return contact.lower()

        digits = re.sub(r"\D", "", contact)

        # 8XXXXXXXXXX -> 7XXXXXXXXXX
        if digits.startswith("8") and len(digits) == 11:
            digits = "7" + digits[1:]

        # 10 цифр -> добавим 7
        if len(digits) == 10:
            digits = "7" + digits

        if not (digits.startswith("7") and len(digits) == 11):
            raise forms.ValidationError("Телефон должен быть в формате +7 (___) ___-__-__")

        return f"+{digits}"


class LoginForm(forms.Form):
    contact = forms.CharField(label="Email или телефон")
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput)

    def clean_contact(self):
        contact = (self.cleaned_data.get("contact") or "").strip()
        if not contact:
            raise ValidationError("Введите email или телефон")

        if "@" in contact:
            return contact.lower()

        phone_validator(contact)
        return contact


class VerifyCodeForm(forms.Form):
    code = forms.CharField(label="Код", max_length=6)

    def clean_code(self):
        code = (self.cleaned_data.get("code") or "").strip()
        if not code.isdigit() or len(code) != 6:
            raise ValidationError("Введите 6-значный код")
        return code


phone_re = re.compile(r"^\+?\d{10,15}$")


class PasswordResetRequestForm(forms.Form):
    contact = forms.CharField(label="Email или телефон")

    def clean_contact(self):
        contact = (self.cleaned_data.get("contact") or "").strip()
        if not contact:
            raise ValidationError("Введите email или телефон")

        if "@" in contact:
            return contact.lower()

        # допускаем +7999... или 7999... или 8999...
        digits = re.sub(r"\D", "", contact)
        if digits.startswith("8") and len(digits) == 11:
            digits = "7" + digits[1:]
        if len(digits) == 10:
            digits = "7" + digits
        if not (digits.startswith("7") and len(digits) == 11):
            raise ValidationError("Введите телефон в формате +7XXXXXXXXXX")

        return f"+{digits}"


class SetNewPasswordForm(forms.Form):
    password1 = forms.CharField(label="Новый пароль", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Повтор пароля", widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            raise ValidationError("Пароли не совпадают")
        return cleaned
