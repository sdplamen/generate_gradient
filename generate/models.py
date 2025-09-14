from django.db import models

# Create your models here.
class ColorPalette(models.Model):
    colors = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Palette from {self.created_at.strftime('%Y-%m-%d %H:%M')}"