from django import forms
from django.core.validators import RegexValidator

from generate.colors import DEFAULT_COLORS, HEX_COLOR_RE, MAX_COLORS, clamp_count

COLOR_FIELD_NAMES = [f'color{i}' for i in range(1, MAX_COLORS + 1)]


def count_color_fields(values):
    """How many of color1, color2, ... are given, counting up from color1 until one is missing."""
    count = 0
    while count < MAX_COLORS and COLOR_FIELD_NAMES[count] in values:
        count += 1
    return count


class HexColorField(forms.CharField):
    default_validators = [RegexValidator(HEX_COLOR_RE, 'Enter a colour in the form #rrggbb.')]

    def __init__(self, **kwargs):
        kwargs.setdefault('max_length', 7)
        kwargs.setdefault('widget', forms.TextInput(attrs={'type': 'color'}))
        super().__init__(**kwargs)

    def to_python(self, value):
        return super().to_python(value).lower()


class GradientForm(forms.Form):
    """One colour field per gradient stop, color1 to colorN, with N between MIN_COLORS and MAX_COLORS.

    N is `count` when given, otherwise the number of colours in the submitted data or the initial values.
    """

    def __init__(self, *args, count=None, **kwargs):
        super().__init__(*args, **kwargs)
        if count is None:
            given = count_color_fields(self.data) if self.is_bound else count_color_fields(self.initial)
            count = given or DEFAULT_COLORS
        self.color_names = COLOR_FIELD_NAMES[:clamp_count(count)]
        for name in self.color_names:
            self.fields[name] = HexColorField()

    @staticmethod
    def initial_for(colors):
        return dict(zip(COLOR_FIELD_NAMES, colors))

    @property
    def colors(self):
        return [self.cleaned_data[name] for name in self.color_names]
