# Hand-written migration (Task: add language to Theater).
#
# Scope kept intentionally minimal — only the `language` field + its index
# are added here. An unrelated pre-existing drift was found between
# models.py (Movie.image already has blank=True, null=True) and the
# 0001 migration (Movie.image required) — that is NOT touched by this
# migration so the working project's existing behaviour is undisturbed.
#
# Safety: language is nullable + on_delete=SET_NULL, so:
#   - existing Theater rows get language=NULL automatically, no data loss.
#   - deleting a Language later never cascades and deletes Theaters/Seats.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('movies', '0001_initial_complete'),
    ]

    operations = [
        migrations.AddField(
            model_name='theater',
            name='language',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='theaters',
                to='movies.language',
                help_text='Language of THIS specific show. Each language gets its own seats.',
            ),
        ),
        migrations.AddIndex(
            model_name='theater',
            index=models.Index(fields=['movie', 'language'], name='theater_movie_lang_idx'),
        ),
    ]
