import random
from urllib.parse import urlencode
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import UpdateView, DeleteView, CreateView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from generate.colors import DIRECTION, build_gradient, normalize_colors
from generate.forms import GradientForm
from generate.mixins import GradientContextMixin
from generate.models import ColorPalette
from generate.serializers import GradientSerializer


def colors_from_query(query):
    """Colours from a ?color1=...&color6=... query, or None for random ones (?random=true, missing or invalid colours)."""
    if query.get('random') == 'true':
        return None
    form = GradientForm(query or None)
    return form.colors if form.is_valid() else None


class GradientGeneratorView(View, GradientContextMixin):
    template_name = 'index.html'

    def get(self, request, palette_id=None):
        if palette_id:
            colors = get_object_or_404(ColorPalette, id=palette_id).colors
        else:
            colors = colors_from_query(request.GET)

        context = self.get_gradient_context(request, colors, active_palette_id=palette_id)
        return render(request, self.template_name, context)

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('login')

        form = GradientForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Palette not saved: the colours were not valid.')
            return redirect('generate_gradient')

        ColorPalette.objects.create(user=request.user, colors=form.colors)
        messages.success(request, 'Palette saved', extra_tags='palette-saved')
        return redirect(f'{reverse("generate_gradient")}?{urlencode(GradientForm.initial_for(form.colors))}')


generate_gradient = GradientGeneratorView.as_view()
get_palette = GradientGeneratorView.as_view()

def get_saved_palette(request):
    all_palette_ids = list(ColorPalette.objects.values_list('id', flat=True))
    if not all_palette_ids:
        return redirect('generate_gradient')
    return redirect('get_palette', palette_id=random.choice(all_palette_ids))

class PaletteDeleteView(LoginRequiredMixin, DeleteView):
    model = ColorPalette
    template_name = 'delete-palette.html'
    success_url = reverse_lazy('generate_gradient')

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user)


class PaletteUpdateView(LoginRequiredMixin, UpdateView) :
    model = ColorPalette
    form_class = GradientForm
    template_name = 'edit-palette.html'
    success_url = reverse_lazy('generate_gradient')

    def get_queryset(self) :
        return self.model.objects.filter(user=self.request.user)

    def get_initial(self) :
        initial = super().get_initial()
        initial.update(GradientForm.initial_for(normalize_colors(self.object.colors)))
        return initial

    def get_form_kwargs(self) :
        kwargs = super().get_form_kwargs()
        kwargs.pop('instance', None)
        return kwargs

    def form_valid(self, form):
        self.object.colors = form.colors
        self.object.save()
        return redirect(self.get_success_url())

class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = 'register.html'
    success_url = reverse_lazy('generate_gradient')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


def gradient_data(colors):
    gradient, css_code = build_gradient(colors)
    return GradientSerializer({
        'direction': DIRECTION,
        'colors': colors,
        'gradient': gradient,
        'css_code': css_code,
    }).data


class GradientAPIView(APIView, GradientContextMixin):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        context = self.get_gradient_context(request, colors_from_query(request.query_params))

        response_data = gradient_data(context['colors'])
        response_data['saved_palettes'] = [
            {'id': palette.id, 'colors': palette.colors} for palette in context['saved_palettes']
        ]
        return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request):
        form = GradientForm(request.data)
        if not form.is_valid():
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)

        ColorPalette.objects.create(user=request.user, colors=form.colors)
        return Response(gradient_data(form.colors), status=status.HTTP_201_CREATED)
