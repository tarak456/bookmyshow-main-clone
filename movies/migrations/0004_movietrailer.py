from django.db import migrations, models
import django.db.models.deletion
import movies.models


class Migration(migrations.Migration):

    dependencies = [
        ('movies', '0003_seed_language_theaters'),
    ]

    operations = [
        migrations.CreateModel(
            name='MovieTrailer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(help_text='YouTube trailer URL for this specific language version.', validators=[movies.models.validate_youtube_url])),
                ('language', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trailers', to='movies.language')),
                ('movie', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trailers', to='movies.movie')),
            ],
            options={
                'verbose_name': 'Movie Trailer',
                'unique_together': {('movie', 'language')},
            },
        ),
    ]
