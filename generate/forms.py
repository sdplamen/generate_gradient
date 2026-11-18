from django import forms
from django.core.validators import RegexValidator

from generate.colors import HEX_COLOR_RE, NUM_COLORS

COLOR_FIELD_NAMES = [f'color{i}' for i in range(1, NUM_COLORS + 1)]


class HexColorField(forms.CharField):
    default_validators = [RegexValidator(HEX_COLOR_RE, 'Enter a colour in the form #rrggbb.')]

    def __init__(self, **kwargs):
        kwargs.setdefault('max_length', 7)
        kwargs.setdefault('widget', forms.TextInput(attrs={'type': 'color'}))
        super().__init__(**kwargs)

    def to_python(self, value):
        return super().to_python(value).lower()


class GradientForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in COLOR_FIELD_NAMES:
            self.fields[name] = HexColorField()

    @staticmethod
    def initial_for(colors):
        return dict(zip(COLOR_FIELD_NAMES, colors))

    @property
    def colors(self):
        return [self.cleaned_data[name] for name in COLOR_FIELD_NAMES]
