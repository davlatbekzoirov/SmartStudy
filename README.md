# SmartStudy

SmartStudy is a Django web app that helps students track courses and grades,
automatically schedule study time before deadlines, log focused work with a
Pomodoro timer, monitor burnout risk, and stay accountable with friends and
study groups.

## Features

### Courses & Grades
- Create courses with custom colors and grade categories (e.g. Homework 20%,
  Midterm 30%, Finals 50%).
- Log assignment scores and see a live weighted grade per course, converted
  to a letter grade.
- **What-If Calculator** — enter hypothetical scores for ungraded assignments
  and see the projected effect on your overall grade.
- **Target Grade Solver** — tell SmartStudy your goal grade and it calculates
  the score you need on your next assignment to get there.

### Smart Scheduler
- Add an assignment with an estimated prep time, and SmartStudy automatically
  distributes that time into daily study blocks leading up to the due date,
  respecting your preferred daily study hours and time window.
- View your schedule for the next two weeks, grouped by day, and mark blocks
  as completed.

### Pomodoro Tracker
- Run focused work sessions linked to a specific course or assignment.
- View total hours studied, session counts, and a breakdown of time spent
  per course.

### Burnout Prevention Analytics
- A study-vs-grade chart shows how many hours you've put into each course
  compared to your current grade, helping you spot subjects where your study
  approach isn't paying off.
- Automatic alerts on your dashboard if you've logged a heavy amount of
  focused study in the last 48 hours, or if your schedule has too many
  consecutive study days in a row — with a suggestion to ease off.

### Study Groups
- Create or join a study group for a shared course.
- Members can submit the date of the next exam, and the group sees a
  crowd-sourced "consensus" exam date based on everyone's submissions.

### Accountability Partners
- Send and accept friend requests to connect with other students.
- See a weekly leaderboard comparing your study hours and daily streaks
  against your accountability partners.

## Tech Stack

- **Backend:** Django 5, Python 3.12
- **Database:** SQLite (default, swappable via `core/settings.py`)
- **Frontend:** Django templates with custom CSS (no JS framework required)
- **Charts:** Chart.js (loaded via CDN on the Analytics page)

## Getting Started

### 1. Clone and set up a virtual environment

```bash
git clone git@github.com:davlatbekzoirov/SmartStudy.git
cd "Smart Study"
python -m venv venv
source venv/bin/activate   # on Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Apply migrations

```bash
python manage.py migrate
```

### 4. Create a superuser (optional, for admin access)

```bash
python manage.py createsuperuser
```

### 5. Run the development server

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` and create an account to get started.

## Project Structure

```
.
├── accounts/        # Authentication (signup, login, logout)
├── core/            # Project settings, root URLs
├── smart_study/     # Main app: courses, grades, scheduler, pomodoro,
│                     groups, friends, analytics
├── templates/        # HTML templates
├── manage.py
└── requirements.txt
```

## Key Modules

| File | Purpose |
|---|---|
| `smart_study/models.py` | Course, GradeCategory, Assignment, StudyBlock, PomodoroSession, UserStudyPrefs, StudyGroup, FriendRequest, etc. |
| `smart_study/grades.py` | Letter grade conversion, what-if and target grade calculations |
| `smart_study/scheduler.py` | Generates study blocks for assignments based on user preferences |
| `smart_study/analytics.py` | Burnout warnings and study-vs-grade chart data |
| `smart_study/social.py` | Friend list, weekly hours, and streak calculations |
| `smart_study/views.py` | All app views |
| `smart_study/forms.py` / `group_forms.py` | Forms for courses, assignments, prefs, groups, and friend requests |

## Configuring Study Preferences

Each user has a `UserStudyPrefs` record (created automatically on first use)
that controls:

- Daily available study hours (used by the scheduler)
- Pomodoro work/break interval lengths
- Preferred study window (start/end hour)

These can be adjusted from the **Schedule** page, which also regenerates all
upcoming study blocks when saved.

## Notes

- The scheduler only generates blocks for assignments with a due date in the
  future and no recorded score. Editing an assignment's due date or estimated
  hours regenerates its study blocks automatically.
- Study groups use a shared course record (`SharedCourse`) matched by exact
  name and code, so make sure to use consistent naming when creating or
  joining a group for a course.