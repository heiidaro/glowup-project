from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),

    path('users/', views.admin_users, name='admin_users'),
    path('users/<int:user_id>/action/',
         views.admin_user_action, name='admin_user_action'),

    path('masters/', views.admin_masters, name='admin_masters'),
    path('masters/<int:master_id>/', views.admin_master_detail,
         name='admin_master_detail'),
    path('masters/<int:master_id>/action/',
         views.admin_master_action, name='admin_master_action'),

    path('bookings/', views.admin_bookings, name='admin_bookings'),
    path('bookings/<int:booking_id>/action/',
         views.admin_booking_action, name='admin_booking_action'),

    path('posts/', views.admin_posts, name='admin_posts'),
    path('posts/<int:post_id>/action/',
         views.admin_post_action, name='admin_post_action'),

    path('portfolio/', views.admin_portfolio, name='admin_portfolio'),
    path('portfolio/<int:item_id>/action/',
         views.admin_portfolio_action, name='admin_portfolio_action'),

    path('reviews/', views.admin_reviews, name='admin_reviews'),
    path('reviews/<int:review_id>/action/',
         views.admin_review_action, name='admin_review_action'),

    path('directories/', views.admin_directories, name='admin_directories'),
    path('directories/categories/<int:category_id>/delete/',
         views.admin_delete_category, name='admin_delete_category'),

    path('notifications/', views.admin_notifications, name='admin_notifications'),

    path('audit/', views.admin_audit, name='admin_audit'),
    path('complaints/', views.admin_complaints, name='admin_complaints'),
    path('complaints/<int:complaint_id>/action/',
         views.admin_complaint_action, name='admin_complaint_action'),

    path('support/', views.admin_support, name='admin_support'),
    path('support/<int:ticket_id>/', views.admin_support_detail,
         name='admin_support_detail'),
    path('support/<int:ticket_id>/action/',
         views.admin_support_action, name='admin_support_action'),
]
