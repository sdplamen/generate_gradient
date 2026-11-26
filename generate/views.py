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
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.exceptions import NotAuthenticated
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from generate.colors import (
    DEFAULT_COLORS, DIRECTION, HEX_COLOR_RE, MAX_COLORS, MIN_COLORS, build_gradient, normalize_colors, random_colors,
    resize_colors,
)
from generate.forms import GradientForm, PaletteForm
from generate.mixins import GradientContextMixin
from generate.models import NAME_MAX_LENGTH, ColorPalette
from generate.renderers import CSSRenderer, SVGRenderer
from generate.serializers import GradientQuerySerializer, GradientSerializer, PaletteSerializer
from generate.throttles import PaletteCreateThrottle


def count_from_query(query):
    """The number of colours asked for with ?count=N (MIN_COLORS to MAX_COLORS), or None."""
    count = query.get('count', '')
    if count.isdigit() and MIN_COLORS <= int(count) <= MAX_COLORS:
        return int(count)
    return None


def locked_slots_from_query(query, colors=None):
    """Slot numbers (1-based) from ?lock=1,3, keeping only those that also have a valid colorN in the query.

    With `colors`, a slot also has to exist there and still hold its colorN (resizing to fewer colours can drop it).
    """
    slots = set()
    for part in query.get('lock', '').split(','):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= MAX_COLORS:
            color = query.get(f'color{part}', '')
            if HEX_COLOR_RE.match(color):
                if colors is None or (int(part) <= len(colors) and colors[int(part) - 1] == color.lower()):
                    slots.add(int(part))
    return sorted(slots)


def colors_from_query(query):
    """Colours from a ?color1=...&colorN=... query, or None for random ones (missing or invalid colours).

    ?count=N picks how many colours (2–6): the given colours are blended or sampled to that many.
    ?random=true gives random colours, except in the slots locked with ?lock=1,3, which keep their colorN.
    """
    count = count_from_query(query)
    if query.get('random') == 'true':
        locked = {slot - 1: query[f'color{slot}'].lower() for slot in locked_slots_from_query(query)}
        if not locked and count is None:
            return None
        return random_colors(count or DEFAULT_COLORS, locked=locked)

    form = GradientForm(query or None)
    if not form.is_valid():
        return random_colors(count) if count else None
    return resize_colors(form.colors, count) if count else form.colors


class GradientGeneratorView(View, GradientContextMixin):
    template_name = 'index.html'

    def get(self, request, palette_id=None):
        if palette_id:
            colors = get_object_or_404(ColorPalette, id=palette_id).colors
        else:
            colors = colors_from_query(request.GET)

        context = self.get_gradient_context(request, colors, active_palette_id=palette_id)
        context['locked_slots'] = locked_slots_from_query(request.GET, context['colors'])
        return render(request, self.template_name, context)

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('login')

        form = PaletteForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Palette not saved: the colours or name were not valid.')
            return redirect('generate_gradient')

        ColorPalette.objects.create(user=request.user, colors=form.colors, name=form.cleaned_data['name'])
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['colors'] = normalize_colors(self.object.colors)
        return context


class PaletteUpdateView(LoginRequiredMixin, UpdateView) :
    model = ColorPalette
    form_class = PaletteForm
    template_name = 'edit-palette.html'
    success_url = reverse_lazy('generate_gradient')

    def get_queryset(self) :
        return self.model.objects.filter(user=self.request.user)

    def get_initial(self) :
        initial = super().get_initial()
        initial.update(GradientForm.initial_for(normalize_colors(self.object.colors)))
        initial['name'] = self.object.name
        return initial

    def get_form_kwargs(self) :
        kwargs = super().get_form_kwargs()
        kwargs.pop('instance', None)
        return kwargs

    def form_valid(self, form):
        self.object.colors = form.colors
        self.object.name = form.cleaned_data['name']
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


def gradient_data(colors, direction=DIRECTION):
    gradient, css_code = build_gradient(colors, direction)
    return GradientSerializer({
        'direction': direction,
        'colors': colors,
        'gradient': gradient,
        'css_code': css_code,
    }).data


GRADIENT_RENDERERS = [JSONRenderer, BrowsableAPIRenderer, CSSRenderer, SVGRenderer]

FORMAT_PARAMETER = OpenApiParameter(
    'format', str, enum=['json', 'css', 'svg'],
    description='Response format: JSON (default), the CSS declaration as text/css, or a square SVG image. '
                'An Accept header of application/json, text/css or image/svg+xml does the same.',
)
COLOR_PARAMETERS = [
    OpenApiParameter(f'color{i}', str, description=f'Colour {i} as #rrggbb. Give color1 to colorN to set N colours; '
                                                   'if any is missing or invalid, random colours are used.')
    for i in range(1, MAX_COLORS + 1)
]
RANDOM_PARAMETERS = [
    OpenApiParameter('random', str, enum=['true'], description='Random colours, except in the slots given by lock.'),
    OpenApiParameter('lock', str, description='With random=true: comma-separated slots (e.g. 1,3) that keep their colorN.'),
]


class GradientAPIView(APIView):
    """A gradient (GET), or save its colours as a palette (POST). Saved palettes are listed at /api/palettes/."""

    permission_classes = [IsAuthenticatedOrReadOnly]
    renderer_classes = GRADIENT_RENDERERS
    throttle_classes = [PaletteCreateThrottle]

    @extend_schema(
        parameters=[GradientQuerySerializer, *COLOR_PARAMETERS, *RANDOM_PARAMETERS, FORMAT_PARAMETER],
        responses={200: GradientSerializer, 400: OpenApiResponse(description='Invalid direction or count.')},
    )
    def get(self, request):
        query = GradientQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        colors = colors_from_query(request.query_params)
        colors = normalize_colors(colors) if colors else random_colors()
        return Response(gradient_data(colors, query.validated_data['direction']), status=status.HTTP_200_OK)

    @extend_schema(
        request=inline_serializer('PaletteCreate', {
            **{f'color{i}': serializers.CharField(required=i <= MIN_COLORS, help_text='#rrggbb')
               for i in range(1, MAX_COLORS + 1)},
            'name': serializers.CharField(required=False, max_length=NAME_MAX_LENGTH),
        }),
        parameters=[FORMAT_PARAMETER],
        responses={
            201: GradientSerializer,
            400: OpenApiResponse(description='Invalid colours or name.'),
            429: OpenApiResponse(description='Too many palettes saved; retry after the Retry-After header.'),
        },
        description='Save color1 to colorN (and an optional name) as a palette. '
                    'Requires login; each user can save a limited number of palettes per hour.',
    )
    def post(self, request):
        form = PaletteForm(request.data)
        if not form.is_valid():
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)

        ColorPalette.objects.create(user=request.user, colors=form.colors, name=form.cleaned_data['name'])
        return Response(gradient_data(form.colors), status=status.HTTP_201_CREATED)


class PalettePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@extend_schema(parameters=[
    OpenApiParameter('mine', str, enum=['true'], description="Only the logged-in user's palettes (requires login)."),
])
class PaletteListAPIView(ListAPIView):
    """Saved palettes, oldest first, 20 per page (?page=N, ?page_size= up to 100)."""

    permission_classes = [AllowAny]
    serializer_class = PaletteSerializer
    pagination_class = PalettePagination

    def get_queryset(self):
        palettes = ColorPalette.objects.order_by('id')
        if self.request.query_params.get('mine') == 'true':
            if not self.request.user.is_authenticated:
                raise NotAuthenticated('Log in to list your own palettes.')
            palettes = palettes.filter(user=self.request.user)
        return palettes
