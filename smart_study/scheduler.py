"""
Automated Study Scheduler
Distributes preparation time for upcoming assignments into daily study slots,
respecting the user's preferred daily study hours and time window.
"""
import math
from datetime import date, timedelta, time
from django.utils import timezone
from .models import StudyBlock


def generate_study_blocks(assignment, prefs):
    """
    Given an Assignment and UserStudyPrefs, generate StudyBlock objects
    in the days leading up to the due date.

    Strategy:
    - Spread `assignment.estimated_hours` across available days before due date.
    - Skip today if the due date is today.
    - Respect daily_study_hours cap per day.
    - Delete any previous auto-generated blocks for this assignment first.
    """
    if not assignment.due_date:
        return []

    today = date.today()
    due = assignment.due_date.date()
    days_available = (due - today).days  # exclusive of due date itself

    if days_available <= 0:
        return []

    total_minutes = float(assignment.estimated_hours) * 60
    # How many minutes per day (capped by daily pref)
    max_daily = float(prefs.daily_study_hours) * 60
    days_needed = math.ceil(total_minutes / max_daily)
    days_needed = min(days_needed, days_available)

    # Distribute evenly across the last `days_needed` days before due
    start_offset = days_available - days_needed
    minutes_per_day = math.ceil(total_minutes / days_needed)

    # Delete old auto blocks
    StudyBlock.objects.filter(assignment=assignment, auto_generated=True).delete()

    blocks = []
    for i in range(days_needed):
        block_date = today + timedelta(days=start_offset + i)
        start = time(prefs.study_start_hour, 0)
        block = StudyBlock(
            assignment=assignment,
            course=assignment.course,
            date=block_date,
            start_time=start,
            duration_minutes=int(minutes_per_day),
            auto_generated=True,
        )
        blocks.append(block)

    StudyBlock.objects.bulk_create(blocks)
    return blocks


def get_schedule_for_user(user, days_ahead=14):
    """Returns all study blocks for a user in the next N days."""
    today = date.today()
    end = today + timedelta(days=days_ahead)
    return (
        StudyBlock.objects
        .filter(course__user=user, date__range=[today, end])
        .select_related('course', 'assignment')
        .order_by('date', 'start_time')
    )
