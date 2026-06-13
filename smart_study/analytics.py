"""
Burnout detection + study/grade correlation helpers.
"""
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum
from .models import PomodoroSession, StudyBlock, Course
from .grades import letter_grade


BURNOUT_HOURS_48H = 8.0         
CONSECUTIVE_DAY_LIMIT = 4        


def get_burnout_warnings(user):
    """Returns a list of warning dicts: {'type': ..., 'message': ...}"""
    warnings = []
    now = timezone.now()

    cutoff = now - timedelta(hours=48)
    recent_minutes = (
        PomodoroSession.objects
        .filter(user=user, completed=True, started_at__gte=cutoff)
        .aggregate(total=Sum('duration_minutes'))['total'] or 0
    )
    recent_hours = recent_minutes / 60
    if recent_hours >= BURNOUT_HOURS_48H:
        warnings.append({
            'type': 'overwork',
            'message': (
                f"You've logged {recent_hours:.1f} hours of focused study in the "
                f"last 48 hours. Consider taking a longer break or a lighter day."
            ),
        })

    today = timezone.localdate()
    streak = 0
    check_day = today
    while True:
        has_block = StudyBlock.objects.filter(
            course__user=user, date=check_day
        ).exists()
        if not has_block:
            break
        streak += 1
        check_day += timedelta(days=1)
        if streak > 14: 
            break

    if streak >= CONSECUTIVE_DAY_LIMIT:
        warnings.append({
            'type': 'consecutive_days',
            'message': (
                f"You have study blocks scheduled for {streak} days in a row "
                f"starting today. Consider spreading some sessions out or "
                f"adding a rest day."
            ),
        })

    return warnings


def get_study_vs_grade_data(user):
    """
    Returns chart-ready data: per-course total study hours (pomodoro)
    vs current weighted grade.
    """
    courses = Course.objects.filter(user=user)
    labels, hours, grades = [], [], []

    for course in courses:
        total_minutes = (
            PomodoroSession.objects
            .filter(user=user, course=course, completed=True)
            .aggregate(total=Sum('duration_minutes'))['total'] or 0
        )
        grade = course.current_weighted_grade()
        labels.append(course.name)
        hours.append(round(total_minutes / 60, 1))
        grades.append(grade if grade is not None else None)

    return {
        'labels': labels,
        'hours': hours,
        'grades': grades,
    }