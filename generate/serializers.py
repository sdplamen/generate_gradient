from rest_framework import serializers
from generate.colors import (
    DEFAULT_TYPE, DIRECTION, DIRECTIONS, GRADIENT_TYPES, MAX_COLORS, MIN_COLORS, parse_direction,
)
from generate.models import ColorPalette


class GradientSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=GRADIENT_TYPES)
    direction = serializers.CharField(max_length=20)
    colors = serializers.ListField(child=serializers.CharField(max_length=7), min_length=MIN_COLORS, max_length=MAX_COLORS)
    gradient = serializers.CharField()
    css_code = serializers.CharField()


class GradientQuerySerializer(serializers.Serializer):
    """The query parameters of GET /api/gradient/ that are rejected with a 400 when they are not valid."""

    type = serializers.ChoiceField(
        choices=GRADIENT_TYPES, required=False, default=DEFAULT_TYPE,
        help_text=f'Gradient type. Default: {DEFAULT_TYPE}.',
    )
    direction = serializers.CharField(
        required=False, default=DIRECTION,
        help_text=f'One of {", ".join(DIRECTIONS)}, or an angle such as 45deg (-360deg to 360deg). Default: {DIRECTION}. '
                  'For conic gradients it is the start angle; radial gradients ignore it.',
    )
    count = serializers.IntegerField(
        required=False, min_value=MIN_COLORS, max_value=MAX_COLORS,
        help_text='How many colours the gradient has. The given colours are blended or sampled to that many.',
    )

    def validate_direction(self, value):
        direction = parse_direction(value)
        if direction is None:
            raise serializers.ValidationError(f'Use one of {", ".join(DIRECTIONS)}, or an angle such as 45deg.')
        return direction


class PaletteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ColorPalette
        fields = ['id', 'name', 'colors', 'created_at']
