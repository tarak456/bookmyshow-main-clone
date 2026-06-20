# BookMySeat 🎬

A full-stack movie ticket booking platform built with Django, extending a base training project into a production-grade system with six advanced feature modules.

**Live URL:** https://bookmyshow-main-clone.vercel.app  
**Stack:** Django · PostgreSQL (Neon) · Razorpay · Vercel · Cloudinary

---

## Admin Access

| Field    | Value                        |
|----------|------------------------------|
| URL      | `/admin/`                    |
| Username | `*******`                      |
| Password | `*******`            |

---

## Six Internship Tasks

### Task 1 — Secure YouTube Trailer Embedding
- `MovieTrailer` model stores one trailer URL per `(movie, language)` pair — Telugu users see the Telugu trailer, English users see the English trailer
- URLs validated server-side with regex before any DB write
- Embedded via `youtube-nocookie.com` with `loading="lazy"`, `sandbox`, and `referrerpolicy` attributes
- Graceful fallback placeholder if no trailer is configured

### Task 2 — Concurrency-Safe Seat Reservation
- `SeatReservation` model locks seats for 2 minutes during checkout
- `select_for_update()` inside `transaction.atomic()` prevents race conditions — two concurrent requests for the same seat cannot both succeed
- `OneToOneField(seat)` provides a DB-level UNIQUE constraint as a final safety net
- Background scheduler releases expired holds every 30 seconds
- Seat map grouped by row (A–J) with zone-based pricing: Premium (A–C), Standard (D–G), Economy (H–J)

### Task 3 — Payment Gateway with Idempotency
- Razorpay integration with server-side order creation — client never controls the amount
- HMAC-SHA256 signature verification before any booking row is created
- `Payment` model with unique `razorpay_order_id` prevents duplicate processing if webhook and browser callback both fire
- Amount mismatch check in webhook handler
- First-booking discount (FIRSTSHOW coupon, ₹50 off) applied server-side

### Task 4 — Admin Analytics Dashboard
- Restricted to `is_staff` users via `@staff_member_required`
- All aggregation at DB level using Django ORM: `Sum`, `Count`, `ExtractHour` — no full table scans
- 5-minute in-memory cache (`LocMemCache`) prevents repeated heavy queries
- Charts: daily/weekly/monthly revenue, popular movies, theater occupancy, peak booking hours, payment breakdown

### Task 5 — Genre and Language Filtering
- Multi-select genre and language filters with `__in` lookups on indexed M2M junction tables
- Filter counts computed at DB level — no Python loops
- Pagination and sorting compose cleanly with all filter combinations
- Language-gated theater list: users must select a language before theaters are shown, preventing cross-language seat confusion

### Task 6 — Automated Email Confirmation
- Non-blocking: email is sent in a background daemon thread, booking response returns immediately
- HTML email rendered via Django template engine with full booking details
- Up to 3 retry attempts with exponential backoff (2s, 4s) for transient SMTP failures
- Every attempt logged in `EmailLog` model with status (`pending`/`sent`/`failed`), attempt count, and error message

---

## Architecture

```
Movie ──┬── Theater (language=Telugu)  ── Seat A1..J20  (independent)
        └── Theater (language=English) ── Seat A1..J20  (independent)
```

Each `Theater` row owns its own `Seat` rows. Booking A1 in a Telugu show never touches the A1 in an English show — they are separate database rows.

---

## Deployment

| Component     | Service                  | Notes                                      |
|---------------|--------------------------|--------------------------------------------|
| Hosting       | Vercel (serverless)      | Auto-deploys from `main` branch            |
| Database      | Neon (PostgreSQL)        | Pooled connection via `dj-database-url`    |
| Media/Images  | Cloudinary               | Required because Vercel FS is read-only    |
| Static files  | WhiteNoise               | Collected at build time                    |
| Payments      | Razorpay                 | Test mode keys in environment variables    |

### Deployment challenges resolved
- Vercel's read-only filesystem broke Django's default media storage → integrated Cloudinary
- `bulk_create` used for seat generation to avoid thousands of individual round-trips to Neon
- Python 3.11 + Django SMTP incompatibility on serverless → custom email backend
- Migration 0003 initially used per-row INSERTs (too slow over Neon) → replaced with `bulk_create`

---

## Local Setup

```bash
# Clone
git clone https://github.com/tarak456/bookmyshow-main-clone
cd bookmyshow-main-clone

# Virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Set environment variables
set DATABASE_URL=your_neon_postgres_url
set RAZORPAY_KEY_ID=your_key
set RAZORPAY_KEY_SECRET=your_secret
set CLOUDINARY_URL=your_cloudinary_url

# Migrate and run
python manage.py migrate
python manage.py runserver
```

---

## Project Structure

```
movies/
├── models.py          # Movie, Theater, Seat, Booking, Payment, SeatReservation, EmailLog, MovieTrailer
├── views.py           # All 6 task views + shared helpers
├── services.py        # Business logic layer
├── admin.py           # Multi-language theater creation, seat generation
├── analytics.py       # Task 4 aggregation queries with caching
├── scheduler.py       # Background seat reservation cleanup
├── email_service.py   # Task 6 non-blocking email with retry
├── razorpay_client.py # Task 3 payment client wrapper
├── templatetags/
│   └── movie_tags.py  # Secure YouTube embed filter
└── migrations/
    ├── 0001_initial_complete.py
    ├── 0002_add_language_to_theater.py
    ├── 0003_seed_language_theaters.py
    └── 0004_movietrailer.py
```

---

*Internship project — Elevance Skills Full-Stack Development Track*  
*Submitted by: Tarak Ratna | B.Tech CSE*
