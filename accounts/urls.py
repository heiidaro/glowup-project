from django.urls import path
from .views import register_view, login_view, verify_view, resend_code_view
from .views import (
    password_reset_request_view,
    password_reset_confirm_view,
)
from . import views

urlpatterns = [
    path("register/", register_view, name="register"),
    path("login/", login_view, name="login"),
    path('logout/', views.logout_view, name='logout'),
    path("verify/", verify_view, name="verify"),
    path("verify/resend/", resend_code_view, name="resend_code"),
    path("password-reset/", password_reset_request_view, name="password_reset"),
    path("password-reset/confirm/<uuid:token>/",
         password_reset_confirm_view, name="password_reset_confirm"),
    path("oauth/<str:provider>/start/",
         views.social_login_start, name="social_login_start"),
    path("oauth/<str:provider>/callback/",
         views.social_login_callback, name="social_login_callback"),
    path("oauth/choose-role/", views.social_choose_role_view,
         name="social_choose_role"),
]
