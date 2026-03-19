from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.client_dashboard, name='client_dashboard'),
    path('complete-profile/', views.complete_profile, name='complete_profile'),
    path('update-profile/', views.update_profile, name='update_profile'),
]
