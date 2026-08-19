import random
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import UpdateView, DeleteView, CreateView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from generate.forms import GradientForm, get_gradient_colors
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from generate.mixins import GradientContextMixin
from generate.models import ColorPalette
from generate.serializers import GradientSerializer


# Create your views here.
# def _prepare_context(request, colors): 
#     form = GradientForm(initial={f'color{i + 1}': colors[i] for i in range(len(colors))})
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
#         'form': form,
#         'css_code': css_code,
#         'colors': colors,
#         'saved_palettes': page_obj,
#     }
#
# def generate_gradient(request): 
#     colors = []
#
#     if request.method == 'POST': 
#         form = GradientForm(request.POST)
#         if form.is_valid(): 
#             colors = [form.cleaned_data[f'color{i + 1}'] for i in range(6)]
#             ColorPalette.objects.create(colors=colors)
#             return redirect(f'/gradient/?{request.POST.urlencode()}')
#
#     form = GradientForm(request.GET or None)
#     if form.is_valid(): 
#         colors = [form.cleaned_data[f'color{i + 1}'] for i in range(6)]
#     else: 
#         colors = get_gradient_colors()
#         form = GradientForm(initial={f'color{i + 1}': colors[i] for i in range(6)})
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

class GradientGeneratorView(View, GradientContextMixin): 
    template_name = 'index.html'

    def get(self, request, palette_id=None): 
        colors = []
        active_palette_id = None
        form = None

        if palette_id: 
            palette = get_object_or_404(ColorPalette, id=palette_id)
            colors = palette.colors
            active_palette_id = palette_id
        elif request.GET.get('random') == 'true': 
            colors = get_gradient_colors()
        else: 
            form = GradientForm(request.GET or None)
            if form.is_valid(): 
                colors = self.get_colors_from_form(form)
            else: 
                colors = get_gradient_colors()

        if not form: 
            form = GradientForm(initial={f'color{i + 1}': colors[i] for i in range(6)})

        context = self.get_gradient_context(request, colors, active_palette_id)
        context['form'] = form

        return render(request, self.template_name, context)

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('login')

        form = GradientForm(request.POST)
        if form.is_valid():
            colors = self.get_colors_from_form(form)
            ColorPalette.objects.create(user=request.user, colors=colors)

            return redirect(f'{reverse_lazy("generate_gradient")}?{request.POST.urlencode()}')

        colors = self.get_colors_from_form(form) if any(f'color{i + 1}' in request.POST for i in range(6)) else get_gradient_colors()
        context = self.get_gradient_context(request, colors)
        context['form'] = form
        return render(request, self.template_name, context)


generate_gradient = GradientGeneratorView.as_view()
get_palette = GradientGeneratorView.as_view()

def get_saved_palette(request):
    try:
        # all_palette_ids = ColorPalette.objects.values_list('id', flat=True)
        all_palette_ids = list(ColorPalette.objects.values_list('id', flat=True))
        if not all_palette_ids:
            raise IndexError('No palettes found.')
        random_id = random.choice(all_palette_ids)

        return redirect('get_palette', palette_id=random_id)

    except IndexError:
        return redirect('generate_gradient')

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
        palette = self.get_object()
        for i, color_value in enumerate(palette.colors, 1) :
            initial[f'color{i}'] = color_value
        return initial

    def get_form_kwargs(self) :
        kwargs = super().get_form_kwargs()
        if 'instance' in kwargs:
            del kwargs['instance']

        return kwargs

    def form_valid(self, form):
        palette = self.get_object()
        updated_colors = [form.cleaned_data[f'color{i}'] for i in range(1, 7)]
        palette.colors = updated_colors
        palette.save()
        return redirect(self.get_success_url())

class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = 'register.html'
    success_url = reverse_lazy('generate_gradient')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class UserLoginView(LoginView) :
    template_name = 'login.html'
    form_class = AuthenticationForm
    success_url = reverse_lazy('generate_gradient')

login_user = UserLoginView.as_view()

class BaseGradientAPIView(APIView, GradientContextMixin):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_pagination_data(self, page_obj):
        return [
            {'id': palette.id, 'colors': palette.colors} for palette in page_obj
        ]


class GradientAPIView(BaseGradientAPIView): 
    def get(self, request): 
        colors = []
        form = None

        if request.query_params.get('random') == 'true': 
            colors = get_gradient_colors()
        else: 
            form = GradientForm(request.query_params or None)
            if form.is_valid(): 
                colors = self.get_colors_from_form(form)
            else: 
                colors = get_gradient_colors()

        context = self.get_gradient_context(request, colors)

        data = {
            'direction': 'to top',
            'colors': context['colors'],
            'gradient': context['gradient'],
            'css_code': context['css_code'],
        }

        serializer = GradientSerializer(data)
        response_data = serializer.data
        response_data['saved_palettes'] = self.get_pagination_data(context['saved_palettes'])

        return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request): 
        if not request.user.is_authenticated: 
            return Response({'detail': 'Authentication credentials were not provided.'},
                            status=status.HTTP_401_UNAUTHORIZED)

        form = GradientForm(request.data)
        if not form.is_valid(): 
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)

        colors = self.get_colors_from_form(form)
        ColorPalette.objects.create(user=request.user, colors=colors)

        data = {
            'direction': 'to top',
            'colors': colors,
            'gradient': f'linear-gradient(to top, {", ".join(colors)})',
            'css_code': f'background: linear-gradient(to top, {", ".join(colors)});',
        }
        serializer = GradientSerializer(data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PaletteAPIView(BaseGradientAPIView): 
    def get_object(self, palette_id):
        palette = get_object_or_404(ColorPalette, id=palette_id)
        return palette

    def check_ownership(self, request, palette):
        if palette.user != request.user: 
            return Response(
                {'detail': 'You do not have permission to perform this action.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return None

    def get(self, request, palette_id): 
        palette = self.get_object(palette_id)
        colors = palette.colors

        context = self.get_gradient_context(request, colors, active_palette_id=palette_id)

        data = {
            'direction': 'to top',
            'colors': context['colors'],
            'gradient': context['gradient'],
            'css_code': context['css_code'],
        }

        serializer = GradientSerializer(data)
        response_data = serializer.data
        response_data['saved_palettes'] = self.get_pagination_data(context['saved_palettes'])

        return Response(response_data, status=status.HTTP_200_OK)

    def put(self, request, palette_id): 
        return self._handle_update(request, palette_id, partial=False)

    def patch(self, request, palette_id): 
        return self._handle_update(request, palette_id, partial=True)

    def _handle_update(self, request, palette_id, partial=False): 
        if not request.user.is_authenticated: 
            return Response({'detail': 'Authentication credentials were not provided.'},
                            status=status.HTTP_401_UNAUTHORIZED)

        palette = self.get_object(palette_id)

        ownership_error = self.check_ownership(request, palette)
        if ownership_error: 
            return ownership_error

        form = GradientForm(request.data)
        if not form.is_valid(): 
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)

        updated_colors = self.get_colors_from_form(form)
        palette.colors = updated_colors
        palette.save()

        data = {
            'direction': 'to top',
            'colors': updated_colors,
            'gradient': f'linear-gradient(to top, {", ".join(updated_colors)})',
            'css_code': f'background: linear-gradient(to top, {", ".join(updated_colors)});',
        }
        serializer = GradientSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, palette_id): 
        if not request.user.is_authenticated: 
            return Response({'detail': 'Authentication credentials were not provided.'},
                            status=status.HTTP_401_UNAUTHORIZED)

        palette = self.get_object(palette_id)

        ownership_error = self.check_ownership(request, palette)
        if ownership_error: 
            return ownership_error

        palette.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)