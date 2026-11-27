from urllib.parse import urlencode

from django.core.paginator import Paginator
from generate.colors import EASING_LABELS, GRADIENT_TYPES, INTERPOLATION_LABELS, MAX_ANGLE, MAX_COLORS, MIN_COLORS, build_gradient, normalize_colors, random_colors
from generate.forms import GradientForm, style_from_query, style_params
from generate.models import ColorPalette


class GradientContextMixin:
    paginate_by = 20

    def get_gradient_context(self, request, colors=None, active_palette_id=None):
        colors = normalize_colors(colors) if colors else random_colors()
        gradient_type, angle, interpolation, easing = style_from_query(request.GET)
        direction = f'{angle}deg'
        gradient, css_code = build_gradient(colors, direction, gradient_type, interpolation, easing)

        saved_palettes_queryset = ColorPalette.objects.all().order_by('id')
        paginator = Paginator(saved_palettes_queryset, self.paginate_by)
        page_obj = paginator.get_page(request.GET.get('page'))

        return {
            'form': GradientForm(initial=GradientForm.initial_for(colors)),
            'gradient': gradient,
            'direction': direction,
            'gradient_type': gradient_type,
            'gradient_types': GRADIENT_TYPES,
            'angle': angle,
            'max_angle': MAX_ANGLE,
            'interpolation': interpolation,
            'interpolations': INTERPOLATION_LABELS.items(),
            'easing': easing,
            'easings': EASING_LABELS.items(),
            # Added to links that leave this page (saved palettes, pagination), so they keep the gradient style
            'style_query': urlencode(style_params(gradient_type, angle, interpolation, easing)),
            'css_code': css_code,
            'colors': colors,
            'color_counts': range(MIN_COLORS, MAX_COLORS + 1),
            'saved_palettes': page_obj,
            'active_palette_id': active_palette_id,
        }
