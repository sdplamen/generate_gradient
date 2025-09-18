from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from generate.forms import GradientForm, get_gradient_colors
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from generate.models import ColorPalette
from generate.serializers import GradientSerializer


# Create your views here.
# def _prepare_context(request, colors) :
#     form = GradientForm(initial={f'color{i + 1}' :colors[i] for i in range(len(colors))})
#
#     gradient = f'linear-gradient(to top, {", ".join(colors)})'
#     css_code = f'background: {gradient};'
#
#     saved_palettes = ColorPalette.objects.all().order_by('created_at')
#     paginator = Paginator(saved_palettes, 10)
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)
#
#     return {
#         'form' :form,
#         'css_code' :css_code,
#         'colors' :colors,
#         'saved_palettes' :page_obj,
#     }
#
# def generate_gradient(request) :
#     colors = []
#
#     if request.method == 'POST' :
#         form = GradientForm(request.POST)
#         if form.is_valid() :
#             colors = [form.cleaned_data[f'color{i + 1}'] for i in range(6)]
#             ColorPalette.objects.create(colors=colors)
#             return redirect(f'/gradient/?{request.POST.urlencode()}')
#
#     form = GradientForm(request.GET or None)
#     if form.is_valid() :
#         colors = [form.cleaned_data[f'color{i + 1}'] for i in range(6)]
#     else :
#         colors = get_gradient_colors()
#         form = GradientForm(initial={f'color{i + 1}' :colors[i] for i in range(6)})
#
#     context = _prepare_context(request, colors)
#     context['form'] = form
#     return render(request, 'index.html', context)
#
# def get_palette(request, palette_id):
#     palette = get_object_or_404(ColorPalette, id=palette_id)
#     colors = palette.colors
#     context = _prepare_context(request, colors)
#     return render(request, 'index.html', context)

def generate_gradient(request):
    colors = []

    if request.method == 'GET':
        if 'random' in request.GET and request.GET['random'] == 'true':
            colors = get_gradient_colors()
            form = GradientForm(initial={
                f'color{i + 1}': colors[i] for i in range(6)
            })
        else:
            form = GradientForm(request.GET or None)
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

    gradient = f'linear-gradient(to top, {", ".join(colors)})'
    css_code = f'background: {gradient};'

    saved_palettes = ColorPalette.objects.all().order_by('created_at')
    paginator = Paginator(saved_palettes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'form': form,
        'gradient': gradient,
        'css_code': css_code,
        'colors': colors,
        'saved_palettes': page_obj,
    }
    return render(request, 'index.html', context)

def get_palette(request, palette_id):
    palette = get_object_or_404(ColorPalette, id=palette_id)
    colors = palette.colors
    form = GradientForm(initial={f'color{i + 1}': colors[i] for i in range(len(colors))})
    saved_palettes = ColorPalette.objects.all().order_by('created_at')
    paginator = Paginator(saved_palettes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    gradient = f'linear-gradient(to top, {", ".join(colors)})'
    css_code = f'background: {gradient};'

    context = {
        'form': form,
        'css_code': css_code,
        'colors': colors,
        'saved_palettes': page_obj,
    }
    return render(request, 'index.html', context)

class GradientAPIView(APIView):
    def get(self, request):
        colors = []
        if request.query_params.get('random') == 'true':
            colors = get_gradient_colors()
        else:
            form = GradientForm(request.query_params or None)
            if form.is_valid():
                colors = [form.cleaned_data[f'color{i + 1}'] for i in range(6)]
            else:
                colors = get_gradient_colors()

        gradient = f'linear-gradient(to top, {", ".join(colors)})'
        css_code = f'background: {gradient};'

        saved_palettes = ColorPalette.objects.all().order_by('created_at')
        paginator = Paginator(saved_palettes, 20)
        page_number = request.query_params.get('page')
        page_obj = paginator.get_page(page_number)

        data = {
            'direction': 'to top',
            'colors': colors,
            'gradient': gradient,
            'css_code': css_code,
        }
        serializer = GradientSerializer(data)
        response_data = serializer.data
        response_data['saved_palettes'] = [
            {'id': palette.id, 'colors': palette.colors} for palette in page_obj
        ]
        return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request):
        form = GradientForm(request.data)
        if not form.is_valid():
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)

        colors = [form.cleaned_data[f'color{i + 1}'] for i in range(6)]
        gradient = f'linear-gradient(to top, {", ".join(colors)})'
        css_code = f'background: {gradient};'
        ColorPalette.objects.create(colors=colors)

        data = {
            'direction': 'to top',
            'colors': colors,
            'gradient': gradient,
            'css_code': css_code,
        }
        serializer = GradientSerializer(data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class PaletteAPIView(APIView):
    def get(self, request, palette_id):
        palette = get_object_or_404(ColorPalette, id=palette_id)
        colors = palette.colors
        gradient = f'linear-gradient(to top, {", ".join(colors)})'
        css_code = f'background: {gradient};'

        saved_palettes = ColorPalette.objects.all().order_by('created_at')
        paginator = Paginator(saved_palettes, 20)
        page_number = request.query_params.get('page')
        page_obj = paginator.get_page(page_number)

        data = {
            'direction': 'to top',
            'colors': colors,
            'gradient': gradient,
            'css_code': css_code,
        }
        serializer = GradientSerializer(data)
        response_data = serializer.data
        response_data['saved_palettes'] = [
            {'id': palette.id, 'colors': palette.colors} for palette in page_obj
        ]
        return Response(response_data, status=status.HTTP_200_OK)