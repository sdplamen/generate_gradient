from rest_framework import serializers

class GradientSerializer(serializers.Serializer):
    direction = serializers.CharField(max_length=20)
    colors = serializers.ListField(child=serializers.CharField(max_length=7), max_length=6)
    gradient = serializers.CharField()
    css_code = serializers.CharField()