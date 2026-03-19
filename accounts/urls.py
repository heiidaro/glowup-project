from django.urls import path
from .views import register_view, login_view, verify_view, resend_code_view
from .views import (
    password_reset_request_view,
    password_reset_confirm_view,
)

urlpatterns = [
    path("register/", register_view, name="register"),
    path("login/", login_view, name="login"),
    path("verify/", verify_view, name="verify"),
    path("verify/resend/", resend_code_view, name="resend_code"),
    path("password-reset/", password_reset_request_view, name="password_reset"),
    path("password-reset/confirm/<uuid:token>/", password_reset_confirm_view, name="password_reset_confirm"),
]
