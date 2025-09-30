from django.contrib.auth.models import User
from django.db import models

# Create your models here.
class ColorPalette(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='palettes')
    colors = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # return f"Palette from {self.created_at.strftime('%Y-%m-%d %H:%M')}"
        color_preview = ', '.join(self.colors) if isinstance(self.colors, list) else '...'
        return f"Palette {self.id} | Colors: {color_preview[:50]}"

    @property
    def name(self):
        return self.__str__()