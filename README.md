# BeforeBed — Django evening planner

A local application for students who want to finish essential tasks before their chosen bedtime and prepare for the next morning.

## Run on Windows

Requires Python 3.12 or newer. Open PowerShell in this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

Open http://localhost:8000/ and register a student account. The superuser can use the Admin overview and `/admin/`. No shared passwords or seeded users are included.

If the included `.venv` points to a Python installation from another computer or Windows account, rename it and create a fresh one:

```powershell
Rename-Item .venv .venv-broken
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py test planner
```

After confirming the new environment works, you can remove `.venv-broken`. Virtual environments are machine-specific and should never be copied or committed.

## Implemented features

- Registration, login, logout, and student/staff roles.
- Task CRUD with deadlines, estimated duration, priority, and completion status.
- Bedtime planner with an explainable schedule and reasons for tasks that do not fit.
- Morning packing checklist.
- Manual sleep diary with validated bedtime/wake-up times.
- Local reference-photo uploads (no paid storage service).
- Printable plans, plain-text downloads, and `.ics` calendar downloads.
- Staff aggregate dashboard and Django administration.
- Responsive pages, CSRF protection, and record ownership checks.

The planner starts now and uses the next occurrence of the chosen bedtime, including after midnight. It orders by earliest deadline, with priority for ties, and schedules only tasks that fit their deadline and bedtime. It is a greedy planner, not an optimal schedule. Skipped tasks remain active; they are not automatically postponed. This app does not track sleep automatically or provide medical recommendations.

## Free integrations and exports

| Service | Action | Required setup |
| --- | --- | --- |
| Google OAuth / OpenID userinfo | Sign in or link an existing account | Client ID, secret, callback URI |
| Google Calendar API | Read events for the next two days | Enable API and grant read-only access |
| Open-Meteo Geocoding API | Convert a city search into coordinates | No key |
| Open-Meteo | Morning weather forecast | Saved coordinates; no key |
| Local Django media storage | Attach task reference photos | No account or API key |
| Text and print export | Save or print the current plan | No account or API key |
| iCalendar export | Import the plan into a calendar app | No account or API key |

Google remains optional. Local accounts, uploads, plan downloads, and calendar-file exports work without paid APIs or external credentials.

### Environment configuration

`.env.example` lists settings. It is documentation, not an automatically loaded file. Set environment variables in the PowerShell session that starts Django or in your hosting platform. Keep credentials outside Git and do not paste them into chat.

### Google

1. Create a Google Cloud project and enable Google Calendar API.
2. Configure OAuth consent in testing mode and add your account as a test user.
3. Create a Web application OAuth client with the exact authorized redirect URI `http://localhost:8000/google/callback/`.
4. Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REDIRECT_URI`. Restart Django.
5. Register locally, then select Connect Google to link your existing account. An unlinked Google login creates a separate account; matching email addresses do not automatically merge accounts.
6. Grant identity and read-only event permissions. Tokens remain in the server-side Django session; reconnect after expiry. Automatic refresh is not implemented.

References: [Google OAuth](https://developers.google.com/identity/protocols/oauth2/web-server), [Calendar events](https://developers.google.com/workspace/calendar/api/v3/reference/events/list).

### Weather

Open **My routine** and search for a city or postal code. The Open-Meteo Geocoding API saves the first matching place and its coordinates; include the country name to make the result more precise. You can also enter coordinates manually. Open **Morning weather** to request a forecast; failures do not prevent local features from working.

Data and usage terms: [Open-Meteo](https://open-meteo.com/). Geocoding location data is based on GeoNames. Attribution is displayed in the app.

### Local photos and plan exports

Expand **Attach a reference photo** on a task. JPEG, PNG, and WebP uploads are limited to 5 MB and saved under `media/task_photos/`. Replacing a photo or deleting its task removes the old file. Do not commit the `media/` directory.

Use **Print plan** for the browser print dialog, **Download text** for a portable text copy, or **Download calendar** for an `.ics` file. Open the `.ics` file with Google Calendar, Outlook, Apple Calendar, or another compatible calendar application.

## Verification

```powershell
python manage.py check
python manage.py test planner
```

Tests cover task CRUD, ownership, CSRF, staff permissions, midnight scheduling, expired deadlines, sleep validation, registration, weather behavior, local photo cleanup, and plan/calendar downloads. Browser visual QA and live Google OAuth tests remain necessary.

## Code map

- `config/`: settings and URLs.
- `planner/models.py`: database records.
- `planner/forms.py`: validation.
- `planner/planning.py`: schedule calculation.
- `planner/views.py`: application flows and authorization.
- `planner/integrations.py`: external requests.
- `templates/` and `static/`: interface.
- `planner/tests.py`: tests.

## Deployment and submission

This local build is not yet an online deployment or a complete submission. Create your own GitHub/GitLab repository and make regular commits as you understand and extend the project. Follow your course rules about assistance and be ready to explain the code.

On a Python-capable Linux host, install requirements, run migrations and `collectstatic`, then start `gunicorn config.wsgi:application`. Set `DJANGO_DEBUG=0`, a random `DJANGO_SECRET_KEY`, your host in `DJANGO_ALLOWED_HOSTS`, and an HTTPS Google callback in both Google Console and the app. Production settings require HTTPS. Arrange static-file serving through your host. SQLite requires persistent storage; PostgreSQL deployment requires additional driver and settings configuration. Hosting plan availability is not verified here.

Before submission: configure and demonstrate all five integrations, deploy online, document your design and objectives, and rehearse with your test accounts.
