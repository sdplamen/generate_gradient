import random
from django import forms


def get_gradient_colors(num_colors=6, max_step=50) :
    def clamp(value) :
        return max(0, min(255, value))

    def rgb_to_hex(r, g, b) :
        return f'#{r:02x}{g:02x}{b:02x}'

    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)

    colors = [rgb_to_hex(r, g, b)]

    for _ in range(num_colors - 1) :
        r = clamp(r + random.randint(-max_step, max_step))
        g = clamp(g + random.randint(-max_step, max_step))
        b = clamp(b + random.randint(-max_step, max_step))
        colors.append(rgb_to_hex(r, g, b))

    return colors

class GradientForm(forms.Form) :
    DIRECTION_CHOICES = [
        ('to right', 'To Right'),
        ('to left', 'To Left'),
        ('to bottom', 'To Bottom'),
        ('to top', 'To Top'),
    ]

    initial_colors = get_gradient_colors()
    direction = forms.ChoiceField(choices=DIRECTION_CHOICES, initial='to top')
    color1 = forms.CharField(max_length=7, initial=initial_colors[0], widget=forms.TextInput(attrs={'type': 'color'}))
    color2 = forms.CharField(max_length=7, initial=initial_colors[1], widget=forms.TextInput(attrs={'type': 'color'}))
    color3 = forms.CharField(max_length=7, initial=initial_colors[2], widget=forms.TextInput(attrs={'type': 'color'}))
    color4 = forms.CharField(max_length=7, initial=initial_colors[3], widget=forms.TextInput(attrs={'type': 'color'}))
    color5 = forms.CharField(max_length=7, initial=initial_colors[4], widget=forms.TextInput(attrs={'type': 'color'}))
    color6 = forms.CharField(max_length=7, initial=initial_colors[5], widget=forms.TextInput(attrs={'type': 'color'}))
    random = forms.BooleanField(required=False, widget=forms.HiddenInput())