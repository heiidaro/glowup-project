from django.urls import path
from . import views

urlpatterns = [
    path('', views.chats_list, name='chats_list'),
    path('<int:chat_id>/', views.chat_detail, name='chat_detail'),
    path('master/<int:master_id>/', views.start_chat_with_master,
         name='start_chat_with_master'),
    path('client/<int:client_id>/', views.start_chat_with_client,
         name='start_chat_with_client'),
]
