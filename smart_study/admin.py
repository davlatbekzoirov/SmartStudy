from django.contrib import admin
from .models import Course, GradeCategory, Assignment, StudyBlock, PomodoroSession, UserStudyPrefs


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'user', 'created_at']
    list_filter = ['user']


@admin.register(GradeCategory)
class GradeCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'course', 'weight']


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'due_date', 'score', 'max_score', 'status']
    list_filter = ['status', 'category__course']


@admin.register(StudyBlock)
class StudyBlockAdmin(admin.ModelAdmin):
    list_display = ['course', 'assignment', 'date', 'start_time', 'duration_minutes', 'completed', 'auto_generated']


@admin.register(PomodoroSession)
class PomodoroSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'started_at', 'duration_minutes', 'completed']


@admin.register(UserStudyPrefs)
class UserStudyPrefsAdmin(admin.ModelAdmin):
    list_display = ['user', 'daily_study_hours', 'pomodoro_work_minutes', 'pomodoro_break_minutes']
