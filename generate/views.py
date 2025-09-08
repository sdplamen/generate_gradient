from django.shortcuts import render
from rest_framework.templatetags.rest_framework import data
from generate.forms import GradientForm, get_gradient_colors
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter
from generate.serializers import GradientSerializer


# Create your views here.
def generate_gradient(request):
    form = GradientForm(request.GET or None)
    direction = 'to top'
    colors = get_gradient_colors()

    if form.is_valid():
        direction = form.cleaned_data['direction']

        if form.cleaned_data['random']:
            form = GradientForm(initial={f'color{i + 1}': colors[i] for i in range(6)})
        else:
            colors = [form.cleaned_data[f'color{i + 1}'] for i in range(6)]

    gradient = f'linear-gradient({direction}, {", ".join(colors)})'
    css_code = f'background: {gradient};'

    context = {
        'form': form,
        'gradient': gradient,
        'css_code': css_code
    }

    return render(request, 'index.html', context)

class GradientAPIView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='direction',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Gradient direction (e.g., "to right", "to left", "to bottom", "to top")',
                enum=['to right', 'to left', 'to bottom', 'to top'],
                default='to top'
            ),
            OpenApiParameter(
                name='color1',
                type=str,
                location=OpenApiParameter.QUERY,
                description='First color in hex format (e.g., #FF0000)',
                default='#ffffff'
            ),
            OpenApiParameter(
                name='color2',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Second color in hex format (e.g., #00FF00)',
                default='#ffffff'
            ),
            OpenApiParameter(
                name='color3',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Third color in hex format',
                default='#ffffff'
            ),
            OpenApiParameter(
                name='color4',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Fourth color in hex format',
                default='#ffffff'
            ),
            OpenApiParameter(
                name='color5',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Fifth color in hex format',
                default='#ffffff'
            ),
            OpenApiParameter(
                name='color6',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Sixth color in hex format',
                default='#ffffff'
            ),
            OpenApiParameter(
                name='random',
                type=bool,
                location=OpenApiParameter.QUERY,
                description='Set to true to generate random gradient colors',
                default=False
            )
        ],
        responses={200: GradientSerializer},
        description='Generate a CSS linear gradient based on provided colors and direction, or random gradient colors if requested.'
    )
    def get(self, request):
        form = GradientForm(request.GET or None)
        direction = 'to top'
        colors = get_gradient_colors()

        if form.is_valid():
            direction = form.cleaned_data['direction']

            if form.cleaned_data['random'] :
                form = GradientForm(initial={f'color{i + 1}' :colors[i] for i in range(6)})
            else:
                colors = [form.cleaned_data[f'color{i + 1}'] for i in range(6)]

        gradient = f'linear-gradient({direction}, {", ".join(colors)})'
        css_code = f'background: {gradient};'

        context = {
            'form': form,
            'gradient': gradient,
            'css_code': css_code
        }

        serializer = GradientSerializer(data=data)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)