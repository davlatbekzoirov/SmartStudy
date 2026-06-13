from collections import Counter
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Course(models.Model):
    """A class/subject the student is enrolled in."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses')
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20, blank=True)
    color = models.CharField(max_length=7, default='#534AB7')  # hex
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} – {self.name}" if self.code else self.name

    def current_weighted_grade(self):
        """Returns overall weighted grade 0-100 or None if no grades yet."""
        total_weight = 0
        weighted_sum = 0
        for cat in self.categories.all():
            grade = cat.computed_grade()
            if grade is not None:
                weighted_sum += grade * (cat.weight / 100)
                total_weight += cat.weight / 100
        if total_weight == 0:
            return None
        # Normalise to whatever weight has been graded so far
        return round(weighted_sum / total_weight, 2)

    class Meta:
        ordering = ['name']


class GradeCategory(models.Model):
    """E.g. Finals 30%, Quizzes 10%, Homework 20% …"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=80)       # "Finals", "Midterm", "Homework"
    weight = models.DecimalField(max_digits=5, decimal_places=2)  # 0-100

    def __str__(self):
        return f"{self.name} ({self.weight}%)"

    def computed_grade(self):
        """Average of all graded assignments in this category."""
        graded = self.assignments.filter(score__isnull=False, max_score__gt=0)
        if not graded.exists():
            return None
        scores = [(a.score / a.max_score * 100) for a in graded]
        return round(sum(scores) / len(scores), 2)

    class Meta:
        ordering = ['-weight']


class Assignment(models.Model):
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
    ]

    category = models.ForeignKey(GradeCategory, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    due_date = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    max_score = models.DecimalField(max_digits=6, decimal_places=2, default=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    notes = models.TextField(blank=True)
    estimated_hours = models.DecimalField(max_digits=4, decimal_places=1, default=1.0,
                                          help_text="Hours needed to prepare")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    @property
    def percentage(self):
        if self.score is not None and self.max_score:
            return round(float(self.score) / float(self.max_score) * 100, 1)
        return None

    @property
    def days_until_due(self):
        if self.due_date:
            delta = self.due_date - timezone.now()
            return delta.days
        return None

    @property
    def course(self):
        return self.category.course

    class Meta:
        ordering = ['due_date']


class StudyBlock(models.Model):
    """Auto-generated (or manually created) study slots."""
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE,
                                   related_name='study_blocks', null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='study_blocks')
    date = models.DateField()
    start_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    completed = models.BooleanField(default=False)
    auto_generated = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.course.name} – {self.date} {self.start_time}"

    class Meta:
        ordering = ['date', 'start_time']


class PomodoroSession(models.Model):
    """A single completed Pomodoro work interval."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pomodoro_sessions')
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='pomodoro_sessions')
    assignment = models.ForeignKey(Assignment, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='pomodoro_sessions')
    started_at = models.DateTimeField(default=timezone.now)
    duration_minutes = models.PositiveIntegerField(default=25)
    completed = models.BooleanField(default=True)
    notes = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Pomodoro {self.started_at:%Y-%m-%d %H:%M} ({self.duration_minutes}min)"

    class Meta:
        ordering = ['-started_at']


class UserStudyPrefs(models.Model):
    """Per-user scheduler preferences."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='study_prefs')
    daily_study_hours = models.DecimalField(max_digits=3, decimal_places=1, default=3.0)
    pomodoro_work_minutes = models.PositiveIntegerField(default=25)
    pomodoro_break_minutes = models.PositiveIntegerField(default=5)
    study_start_hour = models.PositiveIntegerField(default=9)   # 9 AM
    study_end_hour = models.PositiveIntegerField(default=22)    # 10 PM

    def __str__(self):
        return f"{self.user.username} prefs"


class SharedCourse(models.Model):
    """A canonical course definition shared across all users (e.g. 'CS101')."""
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ['name', 'code']
        ordering = ['name']

    def __str__(self):
        return f"{self.code} – {self.name}" if self.code else self.name


class StudyGroup(models.Model):
    shared_course = models.ForeignKey(SharedCourse, on_delete=models.CASCADE, related_name='groups')
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups')
    members = models.ManyToManyField(User, through='GroupMembership', related_name='study_groups')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def consensus_exam_date(self):
        """Most commonly submitted upcoming exam date, or None."""
        votes = list(self.exam_votes.filter(exam_date__gte=timezone.now()).values_list('exam_date', flat=True))
        if not votes:
            return None
        dates = [v.date() for v in votes]
        most_common_date, _ = Counter(dates).most_common(1)[0]
        return most_common_date


class GroupMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_memberships')
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name='memberships')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'group']


class ExamDateVote(models.Model):
    """A member's submitted guess/announcement for the next exam date."""
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name='exam_votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exam_votes')
    exam_date = models.DateTimeField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['group', 'user']  


class FriendRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_friend_requests')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_friend_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['from_user', 'to_user']

    def __str__(self):
        return f"{self.from_user} → {self.to_user} ({self.status})"