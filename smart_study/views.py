import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone

from .models import Course, GradeCategory, Assignment, StudyBlock, PomodoroSession, UserStudyPrefs, StudyGroup, GroupMembership, ExamDateVote, FriendRequest, SharedCourse
from .forms import CourseForm, GradeCategoryForm, AssignmentForm, PomodoroLogForm, StudyPrefsForm
from .group_forms import StudyGroupForm, ExamDateVoteForm, FriendRequestForm
from .social import get_leaderboard
from .grades import letter_grade, what_if_grade, needed_score
from .scheduler import generate_study_blocks, get_schedule_for_user
from .analytics import get_burnout_warnings, get_study_vs_grade_data

def get_or_create_prefs(user):
    prefs, _ = UserStudyPrefs.objects.get_or_create(user=user)
    return prefs

User = get_user_model()

# ─── Dashboard ────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    courses = Course.objects.filter(user=request.user).prefetch_related('categories__assignments')
    upcoming = (
        Assignment.objects
        .filter(category__course__user=request.user, due_date__gte=timezone.now(), score__isnull=True)
        .order_by('due_date')[:5]
    )
    schedule = get_schedule_for_user(request.user, days_ahead=7)
    today_blocks = [b for b in schedule if b.date == timezone.localdate()]

    total_courses = courses.count()
    total_assignments = Assignment.objects.filter(category__course__user=request.user).count()
    graded = Assignment.objects.filter(category__course__user=request.user, score__isnull=False)
    avg_grade = None
    burnout_warnings = get_burnout_warnings(request.user)

    if graded.exists():
        scores = [float(a.score / a.max_score * 100) for a in graded if a.max_score]
        avg_grade = round(sum(scores) / len(scores), 1) if scores else None

    pomodoro_count = PomodoroSession.objects.filter(user=request.user, completed=True).count()

    # Grade summaries per course
    course_summaries = []
    for c in courses:
        g = c.current_weighted_grade()
        course_summaries.append({
            'course': c,
            'grade': g,
            'letter': letter_grade(g),
        })

    return render(request, 'smartstudy/dashboard.html', {
        'course_summaries': course_summaries,
        'upcoming': upcoming,
        'today_blocks': today_blocks,
        'total_courses': total_courses,
        'total_assignments': total_assignments,
        'avg_grade': avg_grade,
        'avg_letter': letter_grade(avg_grade),
        'burnout_warnings': burnout_warnings,
        'pomodoro_count': pomodoro_count,
    })


# ─── Courses ──────────────────────────────────────────────────────────────────

@login_required
def course_list(request):
    courses = Course.objects.filter(user=request.user).prefetch_related('categories__assignments')
    summaries = []
    for c in courses:
        g = c.current_weighted_grade()
        summaries.append({'course': c, 'grade': g, 'letter': letter_grade(g)})
    return render(request, 'smartstudy/course_list.html', {'summaries': summaries})


@login_required
def course_create(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.user = request.user
            course.save()
            messages.success(request, f'Course "{course.name}" created.')
            return redirect('smart_study:course_detail', pk=course.pk)
    else:
        form = CourseForm()
    return render(request, 'smartstudy/course_form.html', {'form': form, 'action': 'Create'})


@login_required
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk, user=request.user)
    categories = course.categories.prefetch_related('assignments').all()
    grade = course.current_weighted_grade()

    # What-If
    what_if_result = None
    hypotheticals = {}
    if request.method == 'POST' and 'what_if' in request.POST:
        for key, val in request.POST.items():
            if key.startswith('hyp_') and val:
                try:
                    a_id = int(key.split('_')[1])
                    hypotheticals[a_id] = float(val)
                except (ValueError, IndexError):
                    pass
        if hypotheticals:
            what_if_result = what_if_grade(course, hypotheticals)

    # Needed score for target
    target_grade = None
    needed_result = None
    if request.method == 'POST' and 'target_grade' in request.POST:
        try:
            target_grade = float(request.POST['target_grade'])
            needed_result = needed_score(course, target_grade)
        except ValueError:
            pass

    return render(request, 'smartstudy/course_detail.html', {
        'course': course,
        'categories': categories,
        'grade': grade,
        'letter': letter_grade(grade),
        'what_if_result': what_if_result,
        'hypotheticals': hypotheticals,
        'target_grade': target_grade,
        'needed_result': needed_result,
    })


@login_required
def course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk, user=request.user)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course updated.')
            return redirect('smart_study:course_detail', pk=course.pk)
    else:
        form = CourseForm(instance=course)
    return render(request, 'smartstudy/course_form.html', {'form': form, 'action': 'Edit', 'course': course})


@login_required
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk, user=request.user)
    if request.method == 'POST':
        name = course.name
        course.delete()
        messages.success(request, f'"{name}" deleted.')
        return redirect('smart_study:course_list')
    return render(request, 'smartstudy/confirm_delete.html', {'object': course, 'type': 'Course'})


# ─── Grade Categories ─────────────────────────────────────────────────────────

@login_required
def category_create(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk, user=request.user)
    if request.method == 'POST':
        form = GradeCategoryForm(request.POST)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.course = course
            cat.save()
            messages.success(request, f'Category "{cat.name}" added.')
            return redirect('smart_study:course_detail', pk=course.pk)
    else:
        form = GradeCategoryForm()
    return render(request, 'smartstudy/category_form.html', {'form': form, 'course': course})


@login_required
def category_delete(request, pk):
    cat = get_object_or_404(GradeCategory, pk=pk, course__user=request.user)
    course_pk = cat.course.pk
    if request.method == 'POST':
        cat.delete()
        messages.success(request, 'Category deleted.')
        return redirect('smart_study:course_detail', pk=course_pk)
    return render(request, 'smartstudy/confirm_delete.html', {'object': cat, 'type': 'Category'})


# ─── Assignments ──────────────────────────────────────────────────────────────

@login_required
def assignment_create(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk, user=request.user)
    if request.method == 'POST':
        form = AssignmentForm(request.POST, course=course)
        if form.is_valid():
            a = form.save()
            prefs = get_or_create_prefs(request.user)
            generate_study_blocks(a, prefs)
            messages.success(request, f'Assignment "{a.title}" created with study blocks.')
            return redirect('smart_study:course_detail', pk=course.pk)
    else:
        form = AssignmentForm(course=course)
    return render(request, 'smartstudy/assignment_form.html', {'form': form, 'course': course, 'action': 'Create'})


@login_required
def assignment_edit(request, pk):
    a = get_object_or_404(Assignment, pk=pk, category__course__user=request.user)
    course = a.course
    if request.method == 'POST':
        form = AssignmentForm(request.POST, instance=a, course=course)
        if form.is_valid():
            a = form.save()
            prefs = get_or_create_prefs(request.user)
            generate_study_blocks(a, prefs)
            messages.success(request, 'Assignment updated.')
            return redirect('smart_study:course_detail', pk=course.pk)
    else:
        form = AssignmentForm(instance=a, course=course)
    return render(request, 'smartstudy/assignment_form.html', {'form': form, 'course': course, 'action': 'Edit'})


@login_required
def assignment_delete(request, pk):
    a = get_object_or_404(Assignment, pk=pk, category__course__user=request.user)
    course_pk = a.course.pk
    if request.method == 'POST':
        a.delete()
        messages.success(request, 'Assignment deleted.')
        return redirect('smart_study:course_detail', pk=course_pk)
    return render(request, 'smartstudy/confirm_delete.html', {'object': a, 'type': 'Assignment'})


# ─── Schedule ─────────────────────────────────────────────────────────────────

@login_required
def schedule_view(request):
    prefs = get_or_create_prefs(request.user)
    if request.method == 'POST':
        form = StudyPrefsForm(request.POST, instance=prefs)
        if form.is_valid():
            form.save()
            # Regenerate all blocks
            upcoming_assignments = Assignment.objects.filter(
                category__course__user=request.user,
                due_date__gte=timezone.now(),
                score__isnull=True,
            )
            for a in upcoming_assignments:
                generate_study_blocks(a, prefs)
            messages.success(request, 'Preferences saved and schedule regenerated.')
            return redirect('smart_study:schedule')
    else:
        form = StudyPrefsForm(instance=prefs)

    schedule = get_schedule_for_user(request.user, days_ahead=14)

    # Group by date
    from collections import defaultdict
    from datetime import date, timedelta
    grouped = defaultdict(list)
    for block in schedule:
        grouped[block.date].append(block)

    today = date.today()
    days = [(today + timedelta(days=i), grouped.get(today + timedelta(days=i), [])) for i in range(14)]

    return render(request, 'smartstudy/schedule.html', {
        'days': days,
        'form': form,
        'prefs': prefs,
    })


@login_required
@require_POST
def toggle_block(request, pk):
    block = get_object_or_404(StudyBlock, pk=pk, course__user=request.user)
    block.completed = not block.completed
    block.save()
    return JsonResponse({'completed': block.completed})


# ─── Pomodoro ─────────────────────────────────────────────────────────────────

@login_required
def pomodoro_view(request):
    prefs = get_or_create_prefs(request.user)
    form = PomodoroLogForm(user=request.user)

    # Stats
    from django.db.models import Sum, Count
    sessions = PomodoroSession.objects.filter(user=request.user, completed=True)
    total_minutes = sessions.aggregate(t=Sum('duration_minutes'))['t'] or 0
    by_course = (
        sessions.filter(course__isnull=False)
        .values('course__name', 'course__color')
        .annotate(total=Sum('duration_minutes'), count=Count('id'))
        .order_by('-total')
    )
    recent = sessions.select_related('course', 'assignment')[:20]

    return render(request, 'smartstudy/pomodoro.html', {
        'prefs': prefs,
        'form': form,
        'total_hours': round(total_minutes / 60, 1),
        'total_sessions': sessions.count(),
        'by_course': list(by_course),
        'recent': recent,
    })


@login_required
@require_POST
def pomodoro_log(request):
    """AJAX endpoint to log a completed pomodoro session."""
    data = json.loads(request.body)
    course_id = data.get('course_id')
    assignment_id = data.get('assignment_id')
    duration = int(data.get('duration_minutes', 25))

    session = PomodoroSession(
        user=request.user,
        duration_minutes=duration,
        completed=True,
        notes=data.get('notes', ''),
    )
    if course_id:
        try:
            session.course = Course.objects.get(pk=course_id, user=request.user)
        except Course.DoesNotExist:
            pass
    if assignment_id:
        try:
            session.assignment = Assignment.objects.get(
                pk=assignment_id, category__course__user=request.user
            )
        except Assignment.DoesNotExist:
            pass
    session.save()
    return JsonResponse({'ok': True, 'session_id': session.pk})

@login_required
def study_analytics(request):
    data = get_study_vs_grade_data(request.user)
    return render(request, 'smartstudy/analytics.html', {
        'chart_data_json': json.dumps(data),
    })

@login_required
def group_list(request):
    my_groups = StudyGroup.objects.filter(members=request.user)
    other_groups = StudyGroup.objects.exclude(members=request.user)
    return render(request, 'smartstudy/group_list.html', {
        'my_groups': my_groups,
        'other_groups': other_groups,
    })


@login_required
def group_create(request):
    if request.method == 'POST':
        form = StudyGroupForm(request.POST)
        if form.is_valid():
            group = form.save(user=request.user)
            GroupMembership.objects.create(user=request.user, group=group)
            messages.success(request, f'Group "{group.name}" created.')
            return redirect('smart_study:group_detail', pk=group.pk)
    else:
        form = StudyGroupForm()
    return render(request, 'smartstudy/group_form.html', {'form': form})


@login_required
def group_detail(request, pk):
    group = get_object_or_404(StudyGroup, pk=pk)
    is_member = group.members.filter(pk=request.user.pk).exists()

    vote_form = ExamDateVoteForm()
    if request.method == 'POST':
        if 'join' in request.POST and not is_member:
            GroupMembership.objects.create(user=request.user, group=group)
            messages.success(request, f'Joined "{group.name}".')
            return redirect('smart_study:group_detail', pk=group.pk)

        if 'submit_exam_date' in request.POST and is_member:
            vote_form = ExamDateVoteForm(request.POST)
            if vote_form.is_valid():
                ExamDateVote.objects.update_or_create(
                    group=group, user=request.user,
                    defaults={'exam_date': vote_form.cleaned_data['exam_date']},
                )
                messages.success(request, 'Exam date submitted.')
                return redirect('smart_study:group_detail', pk=group.pk)

    my_vote = ExamDateVote.objects.filter(group=group, user=request.user).first()

    return render(request, 'smartstudy/group_detail.html', {
        'group': group,
        'is_member': is_member,
        'consensus_date': group.consensus_exam_date(),
        'vote_form': vote_form,
        'my_vote': my_vote,
        'members': group.members.all(),
    })


@login_required
@require_POST
def group_leave(request, pk):
    group = get_object_or_404(StudyGroup, pk=pk)
    GroupMembership.objects.filter(user=request.user, group=group).delete()
    ExamDateVote.objects.filter(user=request.user, group=group).delete()
    messages.success(request, f'Left "{group.name}".')
    return redirect('smart_study:group_list')


# ─── Accountability Partners ────────────────────────────────────────────────

@login_required
def friends_view(request):
    if request.method == 'POST':
        form = FriendRequestForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            try:
                target = User.objects.get(username=username)
                if target == request.user:
                    messages.error(request, "You can't add yourself.")
                else:
                    FriendRequest.objects.get_or_create(
                        from_user=request.user, to_user=target,
                        defaults={'status': 'pending'},
                    )
                    messages.success(request, f'Friend request sent to {username}.')
            except User.DoesNotExist:
                messages.error(request, f'No user named "{username}".')
            return redirect('smart_study:friends')
    else:
        form = FriendRequestForm()

    incoming = FriendRequest.objects.filter(to_user=request.user, status='pending')
    outgoing = FriendRequest.objects.filter(from_user=request.user, status='pending')
    leaderboard = get_leaderboard(request.user)

    return render(request, 'smartstudy/friends.html', {
        'form': form,
        'incoming': incoming,
        'outgoing': outgoing,
        'leaderboard': leaderboard,
    })


@login_required
@require_POST
def friend_request_respond(request, pk, action):
    req = get_object_or_404(FriendRequest, pk=pk, to_user=request.user, status='pending')
    if action == 'accept':
        req.status = 'accepted'
        req.save()
        messages.success(request, f'You are now accountability partners with {req.from_user.username}.')
    elif action == 'decline':
        req.status = 'declined'
        req.save()
    return redirect('smart_study:friends')