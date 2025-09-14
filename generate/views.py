from django.shortcuts import render, redirect, get_object_or_404
from rest_framework.templatetags.rest_framework import data
from generate.forms import GradientForm, get_gradient_colors
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter
from generate.models import ColorPalette
from generate.serializers import GradientSerializer


# Create your views here.
def generate_gradient(request):
    colors = []
    direction = request.GET.get('direction', 'to top')

    if request.method == 'GET': 
        if 'random' in request.GET and request.GET['random'] == 'true': 
            colors = get_gradient_colors()
            form = GradientForm(initial={
                f'color{i + 1}': colors[i] for i in range(6)
            })
        else: 
            form = GradientForm(request.GET)
            if form.is_valid(): 
                colors = [form.cleaned_data[f'color{i + 1}'] for i in range(6)]
            else: 
                colors = get_gradient_colors()
                form = GradientForm(initial={
                    f'color{i + 1}': colors[i] for i in range(6)
                })

    elif request.method == 'POST': 
        form = GradientForm(request.POST)
        if form.is_valid(): 
            colors = [form.cleaned_data[f'color{i + 1}'] for i in range(6)]
            ColorPalette.objects.create(colors=colors)
            return redirect(f'/gradient/?{request.POST.urlencode()}')

    gradient = f'linear-gradient({direction}, {", ".join(colors)})'
    css_code = f'background: {gradient};'

    context = {
        'form': form,
        'gradient': gradient,
        'css_code': css_code,
        'direction': direction,
        'colors': colors,
    }
    return render(request, 'index.html', context)

def get_palette(request, palette_id):
    palette = get_object_or_404(ColorPalette, id=palette_id)
    colors = palette.colors
    direction = 'to top'

    form = GradientForm(initial={f'color{i + 1}': colors[i] for i in range(len(colors))})

    saved_palettes = ColorPalette.objects.all().order_by('-created_at')
    gradient = f'linear-gradient({direction}, {", ".join(colors)})'
    css_code = f'background: {gradient};'

    context = {
        'form': form,
        'gradient': gradient,
        'css_code': css_code,
        'colors': colors,
        'saved_palettes': saved_palettes,
    }
    return render(request, 'index.html', context)

class GradientAPIView(APIView):
    def get(self, request, palette_id=None, *args, **kwargs): 
        if palette_id: 
            palette = get_object_or_404(ColorPalette, id=palette_id)
            colors = palette.colors
            direction = request.GET.get('direction', 'to top')

            data = {
                'direction': direction,
                'colors': colors,
                'gradient': f'linear-gradient({direction}, {", ".join(colors)})',
                'css_code': f'background: linear-gradient({direction}, {", ".join(colors)});'
            }
            serializer = GradientSerializer(data=data)
            if serializer.is_valid(): 
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else: 
            palettes = ColorPalette.objects.all().order_by('-created_at')
            serialized_palettes = []
            for palette in palettes: 
                direction = request.GET.get('direction', 'to top')
                data = {
                    'id': palette.id,  # Include the palette ID for reference
                    'direction': direction,
                    'colors': palette.colors,
                    'gradient': f'linear-gradient({direction}, {", ".join(palette.colors)})',
                    'css_code': f'background: linear-gradient({direction}, {", ".join(palette.colors)});'
                }
                serialized_palettes.append(data)
            return Response(serialized_palettes)

    def post(self, request, *args, **kwargs): 
        serializer = GradientSerializer(data=request.data)
        if serializer.is_valid(): 
            colors = serializer.validated_data['colors']
            ColorPalette.objects.create(colors=colors)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)