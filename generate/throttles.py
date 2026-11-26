from django.core.cache import caches
from rest_framework.throttling import UserRateThrottle


class PaletteCreateThrottle(UserRateThrottle):
    """Limits how many palettes each user can save through the API (rate: REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']).

    Only POST is counted; reads are not throttled. The counts live in the database cache so that every
    gunicorn worker sees the same numbers.
    """

    scope = 'palette_create'
    cache = caches['throttle']

    def allow_request(self, request, view):
        if request.method != 'POST':
            return True
        return super().allow_request(request, view)
