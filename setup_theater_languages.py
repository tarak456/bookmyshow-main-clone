"""
One-off data setup script (NOT a Django migration — run manually via shell).

What it does
------------
1. Existing 4 Theater rows are left completely untouched in terms of id,
   seats, and bookings. Each one is simply assigned language='english'
   (a safe default since English already existed as the implicit-only
   language for all of them, and 'english' is in every movie's language
   list). No Seat or Booking row is touched.

2. For every OTHER language each movie supports, a brand new Theater row
   is created (same name/time as the original) with its own fresh set of
   200 seats (A1-J20), all initially unbooked.

Run with:
    python manage.py shell < setup_theater_languages.py
"""
from movies.models import Theater, Seat, Language

ROWS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
SEATS_PER_ROW = 20

DEFAULT_LANGUAGE_NAME = 'english'

def generate_seats(theater):
    created = 0
    for row in ROWS:
        for num in range(1, SEATS_PER_ROW + 1):
            Seat.objects.create(theater=theater, seat_number=f"{row}{num}")
            created += 1
    return created


def run():
    default_lang = Language.objects.filter(name__iexact=DEFAULT_LANGUAGE_NAME).first()
    if not default_lang:
        print(f"!! Language with name='{DEFAULT_LANGUAGE_NAME}' not found. Aborting.")
        return

    original_theaters = list(Theater.objects.select_related('movie').all())
    print(f"Found {len(original_theaters)} existing theaters.\n")

    for theater in original_theaters:
        # Step 1: assign default language to the ORIGINAL row. No seats/bookings touched.
        if theater.language_id is None:
            theater.language = default_lang
            theater.save(update_fields=['language'])
            print(f"[KEEP]   Theater #{theater.id} '{theater.name}' ({theater.movie.name}) "
                  f"-> language set to '{default_lang.name}' (seats/bookings untouched)")
        else:
            print(f"[SKIP]   Theater #{theater.id} already has language={theater.language.name}, leaving as-is")

        # Step 2: for every OTHER language the movie supports, create a new theater+seats.
        other_languages = theater.movie.languages.exclude(name__iexact=DEFAULT_LANGUAGE_NAME)
        for lang in other_languages:
            already_exists = Theater.objects.filter(
                movie=theater.movie, name=theater.name, time=theater.time, language=lang,
            ).exists()
            if already_exists:
                print(f"         -> {lang.name} version already exists, skipping")
                continue

            new_theater = Theater.objects.create(
                name=theater.name,
                movie=theater.movie,
                time=theater.time,
                language=lang,
            )
            seat_count = generate_seats(new_theater)
            print(f"[CREATE] Theater #{new_theater.id} '{new_theater.name}' "
                  f"({theater.movie.name}) [{lang.name}] -> {seat_count} fresh seats")

    print("\nDone. Summary:")
    for t in Theater.objects.select_related('movie', 'language').order_by('movie_id', 'time', 'language_id'):
        print(f"  #{t.id:>3} | {t.movie.name:<55} | {t.name:<22} | {t.time} | "
              f"{(t.language.name if t.language else 'NONE'):<10} | seats={t.seats.count()}")


run()
