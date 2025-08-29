from django.shortcuts import render
from generate.forms import GradientForm, get_random_color

# Create your views here.
def generate_gradient(request):
    form = GradientForm(request.GET or None)
    direction = 'to right'

    if form.is_valid() :
        direction = form.cleaned_data['direction']
        if form.cleaned_data['random']:
            colors = [get_random_color() for _ in range(6)]
        else :
            colors = [
                form.cleaned_data[f'color{i + 1}'] or get_random_color()
                for i in range(6)
            ]

    colors = [get_random_color() for _ in range(6)]
    gradient = f"linear-gradient({direction}, {', '.join(colors)})"

    context = {
        'form': form,
        'gradient': gradient,
        'css_code': f"background: {gradient};"
    }

    return render(request, 'index.html', context)