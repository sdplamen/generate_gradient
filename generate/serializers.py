from rest_framework import serializers
from generate.colors import MAX_COLORS, MIN_COLORS

class GradientSerializer(serializers.Serializer):
    direction = serializers.CharField(max_length=20)
    colors = serializers.ListField(child=serializers.CharField(max_length=7), min_length=MIN_COLORS, max_length=MAX_COLORS)
    gradient = serializers.CharField()
    css_code = serializers.CharField()
