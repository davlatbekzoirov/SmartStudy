from django import forms
from .models import Course, GradeCategory, Assignment, PomodoroSession, UserStudyPrefs


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name', 'code', 'color']
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color'}),
        }


class GradeCategoryForm(forms.ModelForm):
    class Meta:
        model = GradeCategory
        fields = ['name', 'weight']


class AssignmentForm(forms.ModelForm):
    due_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        input_formats=['%Y-%m-%dT%H:%M'],
    )

    class Meta:
        model = Assignment
        fields = ['category', 'title', 'due_date', 'score', 'max_score',
                  'status', 'notes', 'estimated_hours']

    def __init__(self, *args, course=None, **kwargs):
        super().__init__(*args, **kwargs)
        if course:
            self.fields['category'].queryset = GradeCategory.objects.filter(course=course)


class WhatIfForm(forms.Form):
    """Hypothetical score input for a single assignment."""
    assignment_id = forms.IntegerField(widget=forms.HiddenInput)
    hypothetical_score = forms.DecimalField(
        max_digits=6, decimal_places=2,
        label="Hypothetical Score",
        min_value=0,
    )


class PomodoroLogForm(forms.ModelForm):
    class Meta:
        model = PomodoroSession
        fields = ['course', 'assignment', 'duration_minutes', 'notes']

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['course'].queryset = Course.objects.filter(user=user)
            self.fields['assignment'].queryset = Assignment.objects.filter(
                category__course__user=user
            )
        self.fields['assignment'].required = False
        self.fields['course'].required = False


class StudyPrefsForm(forms.ModelForm):
    class Meta:
        model = UserStudyPrefs
        fields = ['daily_study_hours', 'pomodoro_work_minutes',
                  'pomodoro_break_minutes', 'study_start_hour', 'study_end_hour']
        labels = {
            'daily_study_hours': 'Available Study Hours / Day',
            'pomodoro_work_minutes': 'Work Interval (min)',
            'pomodoro_break_minutes': 'Break Interval (min)',
            'study_start_hour': 'Study Window Start (24h)',
            'study_end_hour': 'Study Window End (24h)',
        }
