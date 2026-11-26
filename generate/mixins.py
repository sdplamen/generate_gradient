from django.core.paginator import Paginator
from generate.colors import DIRECTION, MAX_COLORS, MIN_COLORS, build_gradient, normalize_colors, random_colors
from generate.forms import GradientForm
from generate.models import ColorPalette


class GradientContextMixin:
    paginate_by = 20

    def get_gradient_context(self, request, colors=None, active_palette_id=None):
        colors = normalize_colors(colors) if colors else random_colors()
        gradient, css_code = build_gradient(colors)

        saved_palettes_queryset = ColorPalette.objects.all().order_by('id')
        paginator = Paginator(saved_palettes_queryset, self.paginate_by)
        page_obj = paginator.get_page(request.GET.get('page'))

        return {
            'form': GradientForm(initial=GradientForm.initial_for(colors)),
            'gradient': gradient,
            'direction': DIRECTION,
            'css_code': css_code,
            'colors': colors,
            'color_counts': range(MIN_COLORS, MAX_COLORS + 1),
            'saved_palettes': page_obj,
            'active_palette_id': active_palette_id,
        }
