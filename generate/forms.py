import random
from django import forms


def get_random_color() :
    random_hex = format(random.randint(0, 0xffffff), '06x')
    return f"#{random_hex}"


class GradientForm(forms.Form) :
    DIRECTION_CHOICES = [
        ('to right', 'To Right'),
        ('to left', 'To Left'),
        ('to bottom', 'To Bottom'),
        ('to top', 'To Top'),
    ]

    direction = forms.ChoiceField(choices=DIRECTION_CHOICES, initial='to right')
    color1 = forms.CharField(max_length=7, initial=get_random_color, widget=forms.TextInput(attrs={'type': 'color'}))
    color2 = forms.CharField(max_length=7, initial=get_random_color, widget=forms.TextInput(attrs={'type': 'color'}))
    color3 = forms.CharField(max_length=7, initial=get_random_color, widget=forms.TextInput(attrs={'type': 'color'}))
    color4 = forms.CharField(max_length=7, initial=get_random_color, widget=forms.TextInput(attrs={'type': 'color'}))
    color5 = forms.CharField(max_length=7, initial=get_random_color, widget=forms.TextInput(attrs={'type': 'color'}))
    color6 = forms.CharField(max_length=7, initial=get_random_color, widget=forms.TextInput(attrs={'type': 'color'}))
    random = forms.BooleanField(required=False, widget=forms.HiddenInput())