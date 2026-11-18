from rest_framework import serializers
from generate.colors import NUM_COLORS

class GradientSerializer(serializers.Serializer):
    direction = serializers.CharField(max_length=20)
    colors = serializers.ListField(child=serializers.CharField(max_length=7), max_length=NUM_COLORS)
    gradient = serializers.CharField()
    css_code = serializers.CharField()
