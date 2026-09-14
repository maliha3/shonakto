# শনাক্ত (Shonakto) — Backend

Django REST API for **Shonakto**, an AI-assisted platform for identifying and
reuniting missing and unidentified persons in Bangladesh. It serves a
bilingual (Bangla/English) Flutter app across iOS, Android, and Web.

Two feeds sit at the core of the system:

- **Found / unidentified persons** — reported by hospitals, morgues, or the
  general public.
- **Lost persons** — reported by families of someone missing.

A photo search compares against **both** feeds' facial embeddings at once,
so a query can surface either "this person has already been found" or
"another family already reported this person missing."

## Tech stack

| Layer | Choice |
|---|---|
| API | Django 4.2 + Django REST Framework, JWT auth (`djangorestframework-simplejwt`) |
| Database | PostgreSQL (developed against a [Supabase](https://supabase.com) Postgres instance) |
| AI / face matching | [`face_recognition`](https://github.com/ageitgey/face_recognition) (dlib ResNet) — 128-d embeddings, cosine similarity |
| Async tasks | Celery + Redis — embedding generation and face-match search run off the request path |
| Photo storage | Supabase Storage (or local disk / S3, see `.env.example`) |
| Email | Any SMTP relay (OTP verification codes) |
| Deployment | [Render](https://render.com) (see `render.yaml`) |

## Project layout

```
backend/
├── apps/
│   ├── accounts/        # Users, auth, OTP email verification, roles/authority types
│   ├── found_persons/   # FoundPerson + LostPerson models, uploads, embeddings
│   └── search/           # SearchQuery, MatchResult, matching pipeline, dashboard, notifications
├── config/               # Django settings, URLs, Celery app
├── manage.py
├── requirements.txt
├── render.yaml           # Render Blueprint (free tier)
└── .env.example
```

## Getting started

**Prerequisites:** Python 3.11, PostgreSQL (or a free Supabase project), Redis, and `cmake` +
a C++ compiler (needed to build `dlib` — see the note in `requirements.txt`).

```bash
git clone https://github.com/maliha3/shonakto.git
cd shonakto
python3.11 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install face_recognition==1.3.0 --no-deps   # see requirements.txt for why this is separate

cp .env.example .env            # then fill in your own values (see below)

python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

In a second terminal, run the Celery worker (required for photo embeddings
and face-match search to actually process — without it, uploads are saved
but never get compared):

```bash
source venv/bin/activate
celery -A config worker --loglevel=info
```

The API is now available at `http://127.0.0.1:8000/api/`.

### Environment variables

Copy `.env.example` to `.env` and fill in:

- **Django**: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
- **Database**: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- **Photo storage**: `USE_SUPABASE_STORAGE` + `SUPABASE_URL` / `SUPABASE_KEY` / `SUPABASE_BUCKET` (or leave off to store locally, or set `USE_S3=True` with AWS credentials)
- **Celery**: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` (a local Redis instance by default). Set `CELERY_TASK_ALWAYS_EAGER=True` to run tasks inline instead of needing a separate worker (used on Render's free tier).
- **Email**: `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` — used to send OTP verification codes
- **Face matching**: `FACE_MATCH_THRESHOLD` (default `50.0`, a cosine-similarity percentage — see note below), `FOUND_RECORD_RETENTION_DAYS` (default `30`, auto-purges found-person records)
- `FRONTEND_URL` — used in outgoing email links

## API overview

All endpoints are JSON over HTTP, authenticated with a JWT bearer token
(6h access / 14-day refresh) unless noted.

| Endpoint | Purpose |
|---|---|
| `POST /api/auth/register/`, `/login/`, `/verify-otp/`, `/resend-otp/` | Account creation and email-OTP verification |
| `GET /api/auth/me/` | Current user profile |
| `GET/POST /api/found-persons/`, `GET/PATCH/DELETE /api/found-persons/{id}/` | Found / unidentified-person reports |
| `GET/POST /api/lost-persons/`, `GET/PATCH/DELETE /api/lost-persons/{id}/` | Missing-person reports |
| `POST /api/search/queries/`, `GET /api/search/queries/{id}/` | Upload a photo to search; poll for AI match results |
| `GET /api/search/dashboard/`, `GET /api/search/matches/pending/`, `PATCH /api/search/matches/{id}/review/` | Law-enforcement-only case dashboard and match review (approve/reject) |
| `POST /api/search/matches/{id}/notify-uploader/` | Notify whoever reported the matched record |
| `GET/PATCH/DELETE /api/search/notifications/...` | A user's own notification inbox |

Only the original uploader/reporter can edit or delete their own found/lost
report (enforced server-side, not just in the client).

## How the AI matching works

1. On upload, a Celery task detects the face in the photo and encodes it as
   a 128-dimension vector (`apps/search/face_utils.py`).
2. A search query's vector is compared — via cosine similarity — against
   every active `FoundPerson` **and** `LostPerson` embedding.
3. Anything above `FACE_MATCH_THRESHOLD` becomes a `MatchResult`, ranked and
   shown to the searcher (with the reporter's contact details) and to
   law-enforcement reviewers on the dashboard.
4. Approving a match marks a found-person record `reunited` or a lost-person
   record `found`; nothing is confirmed automatically — a human always
   reviews it.

**Note on the threshold:** cosine similarity on these 128-d embeddings tends
to run high even between different people, so the default `50.0` is
deliberately permissive — it favors surfacing candidates for a human
reviewer over silently hiding possible matches. Treat the ranking as the
signal, not the raw percentage as a certainty score. Tune
`FACE_MATCH_THRESHOLD` if you need a stricter cutoff.

## Deployment

`render.yaml` defines a free-tier Render Blueprint: `pip install`, a
`dlib-bin`-based workaround for `face_recognition`'s native dependency,
`collectstatic`, `migrate`, then `gunicorn`. Sensitive values (`DB_*`,
`SUPABASE_*`, `EMAIL_*`) are marked `sync: false` and must be set manually
in Render's dashboard after the first deploy. `CELERY_TASK_ALWAYS_EAGER=True`
is set so face matching runs inline, since the free tier has no separate
worker dyno.

## License

Not yet specified.
