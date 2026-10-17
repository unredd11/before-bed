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

## Implemented features

- Registration, login, logout, and student/staff roles.
- Task CRUD with deadlines, estimated duration, priority, and completion status.
- Bedtime planner with an explainable schedule and reasons for tasks that do not fit.
- Morning packing checklist.
- Manual sleep diary with validated bedtime/wake-up times.
- Staff aggregate dashboard and Django administration.
- Responsive pages, CSRF protection, and record ownership checks.

The planner starts now and uses the next occurrence of the chosen bedtime, including after midnight. It orders by earliest deadline, with priority for ties, and schedules only tasks that fit their deadline and bedtime. It is a greedy planner, not an optimal schedule. Skipped tasks remain active; they are not automatically postponed. This app does not track sleep automatically or provide medical recommendations.

## Five external integrations

| Service | Action | Required setup |
| --- | --- | --- |
| Google OAuth / OpenID userinfo | Sign in or link an existing account | Client ID, secret, callback URI |
| Google Calendar API | Read events for the next two days | Enable API and grant read-only access |
| Open-Meteo | Morning weather forecast | Saved coordinates; no key |
| Cloudinary Upload API | Attach task reference photos | Cloud name, key, secret |
| Resend Email API | Email the current plan on demand | Key and permitted sender |

Request paths are implemented, but credentialed services have not been tested live. Local accounts and core features work independently. Confirm your instructor counts Google Identity and Google Calendar as separate APIs. Fonts and local libraries do not count.

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

Set your coordinates in My routine. Defaults are Singapore coordinates. City text is a display label, not a location lookup. Open Morning weather to request a forecast; failures do not prevent local features from working.

Data and usage terms: [Open-Meteo](https://open-meteo.com/). Attribution is displayed in the app.

### Photos

Set `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET`. Expand Attach a reference photo on a task. JPEG, PNG, and WebP uploads are limited to 5 MB and signed server-side. Photos use public URLs; use non-sensitive reference material. Deleting a task does not delete its remote asset; asset cleanup is a future enhancement.

Reference: [Cloudinary uploads](https://cloudinary.com/documentation/upload_images).

### Email

Set `RESEND_API_KEY` and `RESEND_FROM`. Save a recipient email in My routine and select Email this plan. Test senders may restrict recipients; arbitrary recipients require a verified sending domain. Sending is on demand; scheduled reminders are not implemented.

Reference: [Resend email API](https://resend.com/docs/api-reference/emails/send-email).

## Verification

```powershell
python manage.py check
python manage.py test planner
```

Tests cover task CRUD, ownership, CSRF, staff permissions, midnight scheduling, expired deadlines, sleep validation, registration, and mocked weather/email behavior. Mocked responses do not validate live accounts. Browser visual QA and live OAuth/upload/email tests remain necessary.

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
