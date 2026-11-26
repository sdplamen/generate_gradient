from django.contrib.auth.models import User
from django.db import models

from generate.colors import HEX_COLOR_RE

NAME_MAX_LENGTH = 40


# Create your models here.
class ColorPalette(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='palettes')
    colors = models.JSONField()
    name = models.CharField(max_length=NAME_MAX_LENGTH, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # return f"Palette from {self.created_at.strftime('%Y-%m-%d %H:%M')}"
        color_preview = ', '.join(self.colors) if isinstance(self.colors, list) else '...'
        label = self.name or f"Palette {self.id}"
        return f"{label} | Colors: {color_preview[:50]}"

    @property
    def number(self):
        """Position in the Saved Palettes list (oldest = 1), shown instead of the database id."""
        return ColorPalette.objects.filter(id__lte=self.id).count()

    @property
    def display_name(self):
        """The palette's name, or "Palette N" when it has none."""
        return self.name or f"Palette {self.number}"

    @property
    def preview_gradient(self):
        """Left-to-right CSS gradient of the stored colours, for the strip in the Saved Palettes list.
        Only valid hex colours go into the CSS; one colour becomes a solid strip, none a grey one."""
        colors = self.colors if isinstance(self.colors, list) else []
        valid = [color for color in colors if isinstance(color, str) and HEX_COLOR_RE.match(color)] or ['#808080']
        if len(valid) == 1:
            valid = valid * 2
        return f'linear-gradient(to right, {", ".join(valid)})'
