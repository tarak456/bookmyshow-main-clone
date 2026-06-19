# Data migration: assign language to existing theaters and create
# language-specific duplicates with fresh seats.
#
# Why a data migration (not a management command)?
# ------------------------------------------------
# build.sh already runs `python manage.py migrate` on every Vercel deploy.
# A data migration runs exactly once (Django tracks it in django_migrations),
# is idempotent by design, and requires no shell access.
#
# Safety rules
# ------------
# 1. All DB writes are inside the forwards() function which runs inside
#    Django's migration transaction, so any error rolls back cleanly.
# 2. Existing Theater rows (ids 1-4) are ONLY updated with language=english.
#    Their seats and bookings are NOT touched.
# 3. New Theater rows are created only if they don't already exist
#    (checked by movie + name + time + language uniqueness), so the
#    migration is safe to re-run manually without creating duplicates.
# 4. The reverse (backwards) function is a no-op — we don't auto-delete
#    theaters on rollback since real bookings may have been made against them.

from django.db import migrations

ROWS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
SEATS_PER_ROW = 20
DEFAULT_LANGUAGE_NAME = 'english'


def _generate_seats(Theater, Seat, theater):
    for row in ROWS:
        for num in range(1, SEATS_PER_ROW + 1):
            Seat.objects.create(theater=theater, seat_number=f"{row}{num}")


def seed_theaters_forward(apps, schema_editor):
    Theater  = apps.get_model('movies', 'Theater')
    Seat     = apps.get_model('movies', 'Seat')
    Language = apps.get_model('movies', 'Language')

    try:
        default_lang = Language.objects.get(name__iexact=DEFAULT_LANGUAGE_NAME)
    except Language.DoesNotExist:
        # No english language in DB yet — nothing to seed. This is safe;
        # the admin can set up theaters manually via the admin panel.
        return

    original_theaters = list(Theater.objects.all())

    for theater in original_theaters:
        # Step 1: stamp the existing theater with English (no seat/booking touch)
        if theater.language_id is None:
            theater.language = default_lang
            theater.save(update_fields=['language'])

        # Step 2: create one new Theater row per other language the movie supports
        try:
            other_languages = theater.movie.languages.exclude(
                name__iexact=DEFAULT_LANGUAGE_NAME
            )
        except Exception:
            continue  # movie has no languages M2M — skip

        for lang in other_languages:
            already = Theater.objects.filter(
                movie=theater.movie,
                name=theater.name,
                time=theater.time,
                language=lang,
            ).exists()
            if already:
                continue  # idempotent guard

            new_theater = Theater.objects.create(
                name=theater.name,
                movie=theater.movie,
                time=theater.time,
                language=lang,
            )
            _generate_seats(Theater, Seat, new_theater)


def seed_theaters_backward(apps, schema_editor):
    # Intentionally a no-op: we never auto-delete theaters on rollback
    # because real bookings may exist against the new rows.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('movies', '0002_add_language_to_theater'),
    ]

    operations = [
        migrations.RunPython(
            seed_theaters_forward,
            seed_theaters_backward,
        ),
    ]
