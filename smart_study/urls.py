from django.urls import path
from . import views

app_name = "smart_study"

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    path('courses/', views.course_list, name='course_list'),
    path('courses/new/', views.course_create, name='course_create'),
    path('courses/<int:pk>/', views.course_detail, name='course_detail'),
    path('courses/<int:pk>/edit/', views.course_edit, name='course_edit'),
    path('courses/<int:pk>/delete/', views.course_delete, name='course_delete'),

    path('courses/<int:course_pk>/categories/new/', views.category_create, name='category_create'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    path('courses/<int:course_pk>/assignments/new/', views.assignment_create, name='assignment_create'),
    path('assignments/<int:pk>/edit/', views.assignment_edit, name='assignment_edit'),
    path('assignments/<int:pk>/delete/', views.assignment_delete, name='assignment_delete'),

    path('schedule/', views.schedule_view, name='schedule'),
    path('schedule/block/<int:pk>/toggle/', views.toggle_block, name='toggle_block'),

    path('pomodoro/', views.pomodoro_view, name='pomodoro'),
    path('pomodoro/log/', views.pomodoro_log, name='pomodoro_log'),

    path('analytics/', views.study_analytics, name='analytics'),

    path('groups/', views.group_list, name='group_list'),
    path('groups/new/', views.group_create, name='group_create'),
    path('groups/<int:pk>/', views.group_detail, name='group_detail'),
    path('groups/<int:pk>/leave/', views.group_leave, name='group_leave'),

    path('friends/', views.friends_view, name='friends'),
    path('friends/request/<int:pk>/<str:action>/', views.friend_request_respond, name='friend_request_respond'),
]
