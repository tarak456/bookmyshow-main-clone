from django.db import migrations


def seed_theaters_forward(apps, schema_editor):
    Theater = apps.get_model('movies', 'Theater')
    Seat = apps.get_model('movies', 'Seat')
    Language = apps.get_model('movies', 'Language')

    ROWS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
    SEATS_PER_ROW = 20

    def bulk_generate_seats(theater):
        Seat.objects.bulk_create([
            Seat(theater=theater, seat_number=f"{row}{num}")
            for row in ROWS
            for num in range(1, SEATS_PER_ROW + 1)
        ])

    existing_theaters = list(Theater.objects.select_related('movie').all())

    for theater in existing_theaters:
        # Skip if already has a language assigned
        if theater.language_id is not None:
            continue

        # Get languages available for this movie
        movie_languages = list(theater.movie.languages.all())
        if not movie_languages:
            continue

        # Assign the first language to the existing theater
        first_lang = movie_languages[0]
        theater.language = first_lang
        theater.save(update_fields=['language'])

        # For remaining languages, create new theater rows with their own seats
        for lang in movie_languages[1:]:
            already_exists = Theater.objects.filter(
                movie=theater.movie,
                time=theater.time,
                language=lang,
            ).exists()
            if already_exists:
                continue

            new_theater = Theater.objects.create(
                name=theater.name,
                movie=theater.movie,
                time=theater.time,
                language=lang,
            )
            bulk_generate_seats(new_theater)

        # Generate seats for the original theater if it has none
        if not Seat.objects.filter(theater=theater).exists():
            bulk_generate_seats(theater)


def seed_theaters_backward(apps, schema_editor):
    # On rollback: clear language from all theaters (seats stay)
    Theater = apps.get_model('movies', 'Theater')
    Theater.objects.update(language=None)


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
