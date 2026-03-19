from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.master_dashboard, name='master_dashboard'),
    path('complete-profile/', views.complete_profile,
         name='master_complete_profile'),
    path('update-profile/', views.update_profile, name='master_update_profile'),
]
