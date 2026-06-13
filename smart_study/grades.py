"""
Grade calculation helpers.
"""
from decimal import Decimal


def letter_grade(pct):
    """Convert a percentage to a letter grade."""
    if pct is None:
        return '–'
    if pct >= 93: return 'A'
    if pct >= 90: return 'A-'
    if pct >= 87: return 'B+'
    if pct >= 83: return 'B'
    if pct >= 80: return 'B-'
    if pct >= 77: return 'C+'
    if pct >= 73: return 'C'
    if pct >= 70: return 'C-'
    if pct >= 67: return 'D+'
    if pct >= 60: return 'D'
    return 'F'


def what_if_grade(course, hypothetical_scores: dict):
    """
    Compute projected overall grade given a dict of
    { assignment_id: hypothetical_score }.

    Returns: dict with per-category projected grade and overall projected grade.
    """
    results = {}
    total_weight = Decimal('0')
    weighted_sum = Decimal('0')

    for cat in course.categories.prefetch_related('assignments').all():
        scores = []
        for a in cat.assignments.all():
            if a.id in hypothetical_scores:
                hyp = Decimal(str(hypothetical_scores[a.id]))
                scores.append(float(hyp / a.max_score * 100))
            elif a.score is not None:
                scores.append(float(a.score / a.max_score * 100))

        if scores:
            cat_grade = Decimal(str(round(sum(scores) / len(scores), 2)))
        else:
            cat_grade = None

        results[cat.id] = {
            'name': cat.name,
            'weight': float(cat.weight),
            'grade': float(cat_grade) if cat_grade is not None else None,
        }

        if cat_grade is not None:
            weighted_sum += cat_grade * (cat.weight / 100)
            total_weight += cat.weight / 100

    overall = round(float(weighted_sum / total_weight), 2) if total_weight else None
    return {'categories': results, 'overall': overall, 'letter': letter_grade(overall)}


def needed_score(course, target_pct: float):
    """
    Calculate what score is needed on the NEXT ungraded assignment
    to reach `target_pct` overall.

    Returns a dict: { 'possible': bool, 'needed': float|None, 'next_assignment': Assignment|None }
    """
    # Find first ungraded assignment
    from .models import Assignment
    next_a = (
        Assignment.objects
        .filter(category__course=course, score__isnull=True)
        .order_by('due_date')
        .select_related('category')
        .first()
    )

    if not next_a:
        return {'possible': False, 'needed': None, 'next_assignment': None}

    cat = next_a.category
    current_overall = course.current_weighted_grade() or 0.0
    cat_weight = float(cat.weight) / 100.0

    # Current contribution of this category (without next assignment)
    cat_current_grade = cat.computed_grade() or 0.0

    # Solve: target = current_overall_without_cat + (new_cat_grade * cat_weight)
    # where new_cat_grade factors in the new score
    # Simplified: find the score needed in the category to hit target

    # Overall = sum of all category contributions
    # We need to find x such that including x in this category gives target_pct
    # Let other_contribution = sum of other categories' contributions
    other_contribution = 0.0
    other_weight = 0.0
    for c in course.categories.all():
        if c.id == cat.id:
            continue
        g = c.computed_grade()
        if g is not None:
            other_contribution += g * (float(c.weight) / 100.0)
            other_weight += float(c.weight) / 100.0

    # assignments already graded in this category
    graded_in_cat = list(cat.assignments.filter(score__isnull=False))
    n_graded = len(graded_in_cat)
    sum_pct_graded = sum(float(a.score / a.max_score * 100) for a in graded_in_cat)

    # new_cat_avg = (sum_pct_graded + needed_pct_on_next) / (n_graded + 1)
    # target = other_contribution + new_cat_avg * cat_weight
    # → new_cat_avg = (target - other_contribution) / cat_weight
    if cat_weight == 0:
        return {'possible': False, 'needed': None, 'next_assignment': next_a}

    needed_cat_avg = (target_pct - other_contribution) / cat_weight
    needed_on_next = needed_cat_avg * (n_graded + 1) - sum_pct_graded

    return {
        'possible': 0 <= needed_on_next <= 100,
        'needed': round(needed_on_next, 1),
        'needed_points': round(needed_on_next / 100 * float(next_a.max_score), 1),
        'next_assignment': next_a,
        'max_score': float(next_a.max_score),
    }
