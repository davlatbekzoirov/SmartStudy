from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('profile/', views.profile_view, name='profile'),
    path('profile/email/change/', views.email_change_request_view, name='email_change_request'),
    path('profile/email/confirm/', views.email_change_confirm_view, name='email_change_confirm'),
    path('profile/password/', views.password_change_view, name='password_change'),
]