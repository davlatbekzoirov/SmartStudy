from django import forms
from .models import StudyGroup, SharedCourse, ExamDateVote, FriendRequest


class StudyGroupForm(forms.ModelForm):
    shared_course_name = forms.CharField(label="Course name")
    shared_course_code = forms.CharField(label="Course code", required=False)

    class Meta:
        model = StudyGroup
        fields = ['name']

    def save(self, user, commit=True):
        shared_course, _ = SharedCourse.objects.get_or_create(
            name=self.cleaned_data['shared_course_name'],
            code=self.cleaned_data.get('shared_course_code', '') or '',
        )
        group = super().save(commit=False)
        group.shared_course = shared_course
        group.created_by = user
        if commit:
            group.save()
        return group


class ExamDateVoteForm(forms.ModelForm):
    class Meta:
        model = ExamDateVote
        fields = ['exam_date']
        widgets = {
            'exam_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
        input_formats = {'exam_date': ['%Y-%m-%dT%H:%M']}


class FriendRequestForm(forms.Form):
    username = forms.CharField(label="Friend's username")