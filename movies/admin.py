from django import forms
from django.contrib import admin, messages
from django.db import transaction

from .models import (
    Genre, Language, Movie, MovieTrailer,
    Theater, Seat, Booking, SeatReservation, Payment,
)

ROWS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
SEATS_PER_ROW = 20


def _bulk_create_seats(theater):
    """Create 200 seats (A1-J20) for a theater in one DB query."""
    Seat.objects.bulk_create([
        Seat(theater=theater, seat_number=f"{row}{num}")
        for row in ROWS
        for num in range(1, SEATS_PER_ROW + 1)
    ])


# ── Genre & Language ──────────────────────────────────────────────────────────

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']


# ── Movie & per-language trailers ─────────────────────────────────────────────

class MovieTrailerInline(admin.TabularInline):
    """
    Edit language-specific trailers directly on the Movie page.
    Add one row per language version you want a different trailer for.
    Leave a language out and it will fall back to Movie.trailer_url.
    """
    model = MovieTrailer
    extra = 1
    fields = ['language', 'url']


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display  = ['name', 'rating', 'trailer_url']
    filter_horizontal = ['genres', 'languages']
    search_fields = ['name', 'cast']
    list_filter   = ['genres', 'languages']
    inlines       = [MovieTrailerInline]


# ── Theater — multi-language creation form ────────────────────────────────────

class MultiLanguageTheaterForm(forms.ModelForm):
    """
    Custom Theater creation form.

    Key field: `languages` (multi-select).
    On save, the admin view creates ONE Theater + 200 seats per selected
    language automatically — you never have to add theaters one-by-one.

    The `language` FK on Theater is hidden here; it is set programmatically
    inside TheaterAdmin.save_model().
    """
    languages = forms.ModelMultipleChoiceField(
        queryset=Language.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label='Languages',
        help_text=(
            'Tick every language this show runs in. '
            'A separate Theater row with 200 independent seats '
            'will be created for each language you select.'
        ),
    )

    class Meta:
        model  = Theater
        fields = ['name', 'movie', 'time']
        # `language` is intentionally excluded — set per-row in save_model()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # When editing an existing theater, pre-select its language
        if self.instance.pk and self.instance.language_id:
            self.fields['languages'].initial = [self.instance.language_id]


@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    form         = MultiLanguageTheaterForm
    list_display = ['name', 'movie', 'language', 'seat_count', 'time']
    list_filter  = ['language', 'movie']
    list_select_related = ['movie', 'language']
    actions      = ['generate_seats']

    @admin.display(description='Seats')
    def seat_count(self, obj):
        return obj.seats.count()

    def get_fields(self, request, obj=None):
        # Show the languages multi-select only on the ADD form.
        # On the change form show the single language FK instead
        # (editing language on an existing row is a one-off operation).
        if obj is None:
            return ['name', 'movie', 'time', 'languages']
        return ['name', 'movie', 'time', 'language']

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        """
        On ADD: create one Theater + 200 seats per selected language.
        On CHANGE: normal single-object save.
        """
        if change:
            # Editing an existing theater — plain save
            super().save_model(request, obj, form, change)
            return

        selected_languages = form.cleaned_data['languages']
        created_theaters = 0

        for lang in selected_languages:
            # Skip if a theater for this movie+time+language already exists
            if Theater.objects.filter(
                movie=obj.movie, time=obj.time, language=lang
            ).exists():
                messages.warning(
                    request,
                    f'⚠ A {lang.name} theater for {obj.movie.name} at '
                    f'{obj.time:%d %b %H:%M} already exists — skipped.',
                )
                continue

            theater = Theater.objects.create(
                name=obj.name,
                movie=obj.movie,
                time=obj.time,
                language=lang,
            )
            _bulk_create_seats(theater)
            created_theaters += 1

        if created_theaters:
            messages.success(
                request,
                f'✅ Created {created_theaters} theater(s) with '
                f'{created_theaters * SEATS_PER_ROW * len(ROWS)} seats total '
                f'({", ".join(l.name for l in selected_languages)}).',
            )

    def response_add(self, request, obj, post_url_continue=None):
        """
        After multi-theater creation, redirect to the theater list
        instead of the (non-existent) detail page for obj.
        """
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        messages_storage = messages.get_messages(request)
        # Consume messages so they show on the list page
        list(messages_storage)
        return HttpResponseRedirect(reverse('admin:movies_theater_changelist'))

    def generate_seats(self, request, queryset):
        """Regenerate seats for selected theaters (replaces existing seats)."""
        created = 0
        for theater in queryset:
            theater.seats.all().delete()
            _bulk_create_seats(theater)
            created += SEATS_PER_ROW * len(ROWS)
        self.message_user(request, f'✅ {created} seats created!', messages.SUCCESS)

    generate_seats.short_description = '🎭 Regenerate 200 seats (A1–J20)'


# ── Seat ──────────────────────────────────────────────────────────────────────

@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ['seat_number', 'theater', 'is_booked']
    list_filter  = ['is_booked']
    list_select_related = ['theater']


# ── Booking ───────────────────────────────────────────────────────────────────

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['user', 'movie', 'theater', 'seat', 'booked_at']
    list_select_related = ['user', 'movie', 'theater', 'seat']
    readonly_fields = ['booked_at']


# ── SeatReservation ───────────────────────────────────────────────────────────

@admin.register(SeatReservation)
class SeatReservationAdmin(admin.ModelAdmin):
    list_display = ['seat', 'user', 'theater', 'expires_at']
    list_select_related = ['seat', 'user', 'theater']


# ── Payment ───────────────────────────────────────────────────────────────────

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display    = ['booking_ref', 'user', 'status', 'amount_inr_display', 'created_at']
    list_filter     = ['status']
    search_fields   = ['razorpay_order_id', 'razorpay_payment_id']
    readonly_fields = ['booking_ref', 'created_at', 'updated_at', 'webhook_received_at']
    list_select_related = ['user', 'theater__movie']

    @admin.display(description='Amount (INR)')
    def amount_inr_display(self, obj):
        return f'₹{obj.amount_paise // 100}'
