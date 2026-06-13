"""
Helpers for accountability partners (friends) — weekly study stats and streaks.
"""
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Q
from .models import PomodoroSession, FriendRequest


def get_friends(user):
    """Returns a list of User objects that are accepted friends of `user`."""
    accepted = FriendRequest.objects.filter(
        Q(from_user=user) | Q(to_user=user),
        status='accepted',
    )
    friends = []
    for req in accepted:
        friends.append(req.to_user if req.from_user_id == user.id else req.from_user)
    return friends


def get_weekly_hours(user):
    """Total completed pomodoro hours for the last 7 days."""
    cutoff = timezone.now() - timedelta(days=7)
    minutes = (
        PomodoroSession.objects
        .filter(user=user, completed=True, started_at__gte=cutoff)
        .aggregate(total=Sum('duration_minutes'))['total'] or 0
    )
    return round(minutes / 60, 1)


def get_streak(user):
    """Number of consecutive days (including today) with at least one completed pomodoro."""
    today = timezone.localdate()
    streak = 0
    day = today
    while True:
        exists = PomodoroSession.objects.filter(
            user=user, completed=True,
            started_at__date=day,
        ).exists()
        if not exists:
            break
        streak += 1
        day -= timedelta(days=1)
        if streak > 365:
            break
    return streak


def get_leaderboard(user):
    """Returns list of {'user': ..., 'weekly_hours': ..., 'streak': ...} for user + friends."""
    people = [user] + get_friends(user)
    board = [
        {'user': p, 'weekly_hours': get_weekly_hours(p), 'streak': get_streak(p)}
        for p in people
    ]
    return sorted(board, key=lambda x: x['weekly_hours'], reverse=True)