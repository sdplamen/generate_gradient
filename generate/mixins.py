from django.core.paginator import Paginator
from generate.forms import get_gradient_colors, GradientForm
from generate.models import ColorPalette


class GradientContextMixin:
    paginate_by = 20
    def get_gradient_context(self, request, colors, active_palette_id=None):
        if not colors:
            colors = get_gradient_colors()

        form = GradientForm(initial={f'color{i + 1}': colors[i] for i in range(len(colors))})

        gradient = f'linear-gradient(to top, {", ".join(colors)})'
        css_code = f'background: {gradient};'

        saved_palettes_queryset = ColorPalette.objects.all().order_by('-created_at')
        paginator = Paginator(saved_palettes_queryset, self.paginate_by)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        return {
            'form': form,
            'gradient': gradient,
            'css_code': css_code,
            'colors': colors,
            'saved_palettes': page_obj,
            'active_palette_id': active_palette_id,
        }

    def get_colors_from_form(self, form):
        return [form.cleaned_data[f'color{i + 1}'] for i in range(6)]