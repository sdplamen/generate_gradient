import colorsys
import random
import re

from generate.palettes import AVAILABLE_PALETTES

NUM_COLORS = 6
DIRECTION = 'to top'
HEX_COLOR_RE = re.compile(r'^#[0-9a-fA-F]{6}$')

# Share of random gradients taken from the curated palettes; the rest are generated on the colour wheel
CURATED_SHARE = 0.7


def _to_hex(r, g, b):
    return f'#{r:02x}{g:02x}{b:02x}'


def _to_rgb(color):
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def resize_colors(colors, size=NUM_COLORS):
    """Return `size` colours: pick evenly spaced ones from a longer list, blend between neighbours for a shorter one."""
    if len(colors) == size:
        return list(colors)
    if len(colors) == 1:
        return list(colors) * size

    step = (len(colors) - 1) / (size - 1)
    if len(colors) > size:
        return [colors[round(i * step)] for i in range(size)]

    rgb = [_to_rgb(color) for color in colors]
    resized = []
    for i in range(size):
        position = i * step
        low = int(position)
        high = min(low + 1, len(rgb) - 1)
        fraction = position - low
        resized.append(_to_hex(*(round(a + (b - a) * fraction) for a, b in zip(rgb[low], rgb[high]))))
    return resized


def _curated_colors(size):
    colors = [color.lower() for color in random.choice(AVAILABLE_PALETTES).hex_colors]
    if random.random() < 0.5:
        colors.reverse()
    return resize_colors(colors, size)


def _harmonious_colors(size):
    """Sweep a slice of the colour wheel while moving from dark to light, so neighbouring colours always match."""
    hue = random.random()
    hue_spread = random.uniform(0.08, 0.35)
    saturation = random.uniform(0.45, 0.85)
    lightness = [random.uniform(0.25, 0.45), random.uniform(0.6, 0.8)]
    if random.random() < 0.5:
        lightness.reverse()

    colors = []
    for i in range(size):
        t = i / (size - 1)
        r, g, b = colorsys.hls_to_rgb(
            (hue + hue_spread * t) % 1,
            lightness[0] + (lightness[1] - lightness[0]) * t,
            saturation,
        )
        colors.append(_to_hex(round(r * 255), round(g * 255), round(b * 255)))
    return colors


def random_colors(size=NUM_COLORS):
    if random.random() < CURATED_SHARE:
        return _curated_colors(size)
    return _harmonious_colors(size)


def normalize_colors(colors):
    """Make stored colours safe to display: drop invalid values and fit the rest to NUM_COLORS."""
    valid = [color.lower() for color in colors or [] if isinstance(color, str) and HEX_COLOR_RE.match(color)]
    if not valid:
        return random_colors()
    return resize_colors(valid)


def build_gradient(colors, direction=DIRECTION):
    gradient = f'linear-gradient({direction}, {", ".join(colors)})'
    return gradient, f'background: {gradient};'
