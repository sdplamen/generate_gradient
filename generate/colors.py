import colorsys
import random
import re

from generate.palettes import AVAILABLE_PALETTES

# How many colours a gradient can have; most gradients people use have 2–3 stops, so new ones start with 3
MIN_COLORS = 2
MAX_COLORS = 6
DEFAULT_COLORS = 3
DIRECTION = 'to top'
HEX_COLOR_RE = re.compile(r'^#[0-9a-fA-F]{6}$')

# CSS gradient directions the API accepts, with their angle (CSS: 0deg points up, angles go clockwise);
# any whole angle from -360deg to 360deg is accepted too
DIRECTION_ANGLES = {
    'to top': 0, 'to top right': 45, 'to right': 90, 'to bottom right': 135,
    'to bottom': 180, 'to bottom left': 225, 'to left': 270, 'to top left': 315,
}
DIRECTIONS = tuple(DIRECTION_ANGLES)
ANGLE_RE = re.compile(r'^(-?\d{1,3})deg$')

# Share of random gradients taken from the curated palettes; the rest are generated on the colour wheel
CURATED_SHARE = 0.7


def _to_hex(r, g, b):
    return f'#{r:02x}{g:02x}{b:02x}'


def _to_rgb(color):
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def clamp_count(count):
    return min(max(count, MIN_COLORS), MAX_COLORS)


def resize_colors(colors, size=DEFAULT_COLORS):
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


def _harmonious_colors(size, anchor=None):
    """Sweep a slice of the colour wheel while moving from dark to light, so neighbouring colours always match.

    `anchor` is an optional (slot index, colour) pair: the sweep is shifted so that slot gets close to that colour.
    """
    hue = random.random()
    hue_spread = random.uniform(0.08, 0.35) * random.choice((1, -1))
    saturation = random.uniform(0.45, 0.85)
    lightness = [random.uniform(0.25, 0.45), random.uniform(0.6, 0.8)]
    if random.random() < 0.5:
        lightness.reverse()

    if anchor:
        index, color = anchor
        t = index / (size - 1)
        anchor_hue, anchor_lightness, anchor_saturation = colorsys.rgb_to_hls(*(c / 255 for c in _to_rgb(color)))
        hue = anchor_hue - hue_spread * t
        saturation = min(anchor_saturation, 0.9)
        shift = anchor_lightness - (lightness[0] + (lightness[1] - lightness[0]) * t)
        lightness = [min(max(value + shift, 0.03), 0.97) for value in lightness]

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


def _distance(color_a, color_b):
    """Rough perceptual distance between two colours ("redmean" weighted RGB)."""
    (r1, g1, b1), (r2, g2, b2) = _to_rgb(color_a), _to_rgb(color_b)
    mean_red = (r1 + r2) / 2
    return ((2 + mean_red / 256) * (r1 - r2) ** 2 + 4 * (g1 - g2) ** 2 + (2 + (255 - mean_red) / 256) * (b1 - b2) ** 2) ** 0.5


def _lock_fit(colors, locked):
    """How badly the locked colours clash with their neighbours (lower is better)."""
    return sum(
        _distance(colors[i], colors[i + 1])
        for i in range(len(colors) - 1)
        if i in locked or i + 1 in locked
    )


def _random_candidate(size, locked):
    if random.random() < CURATED_SHARE:
        colors = _curated_colors(size)
    else:
        colors = _harmonious_colors(size, anchor=random.choice(list(locked.items())))
    for index, color in locked.items():
        colors[index] = color
    return colors


# With locked colours, try this many random palettes and pick one of the few that fit the locks best
LOCK_CANDIDATES = 40
LOCK_SHORTLIST = 5


def random_colors(size=DEFAULT_COLORS, locked=None):
    """Random colours; `locked` maps slot index (0-based) to a colour that stays in that slot.

    The other slots are chosen to blend into the locked colours: several random palettes are tried
    (curated ones, and colour-wheel sweeps that pass through a locked colour) and one of the smoothest fits
    is picked, so pressing Space again still gives something new.
    """
    locked = {index: color for index, color in (locked or {}).items() if 0 <= index < size}
    if not locked:
        return _curated_colors(size) if random.random() < CURATED_SHARE else _harmonious_colors(size)
    if len(locked) == size:
        return [locked[i] for i in range(size)]

    candidates = sorted(
        {tuple(_random_candidate(size, locked)) for _ in range(LOCK_CANDIDATES)},
        key=lambda colors: _lock_fit(colors, locked),
    )
    return list(random.choice(candidates[:LOCK_SHORTLIST]))


def normalize_colors(colors, size=None):
    """Make stored colours safe to display: drop invalid values and fit the rest to `size` colours
    (by default their own count, kept between MIN_COLORS and MAX_COLORS)."""
    valid = [color.lower() for color in colors or [] if isinstance(color, str) and HEX_COLOR_RE.match(color)]
    size = clamp_count(size or len(valid) or DEFAULT_COLORS)
    if not valid:
        return random_colors(size)
    return resize_colors(valid, size)


def parse_direction(value):
    """A CSS gradient direction in its canonical form ('to top right', '45deg'), or None if it is not one we accept.

    Case and extra spaces are ignored, and corner keywords may come in either order ('to right top').
    """
    words = value.lower().split()
    if len(words) == 1:
        match = ANGLE_RE.match(words[0])
        if match and -360 <= int(match.group(1)) <= 360:
            return f'{int(match.group(1))}deg'
        return None
    if len(words) not in (2, 3) or words[0] != 'to':
        return None
    sides = words[1:]
    if len(sides) == 2 and sides[0] in ('left', 'right'):
        sides.reverse()
    direction = ' '.join(['to', *sides])
    return direction if direction in DIRECTION_ANGLES else None


def direction_angle(direction):
    """The angle in degrees of a direction returned by parse_direction."""
    if direction in DIRECTION_ANGLES:
        return DIRECTION_ANGLES[direction]
    return int(direction.removesuffix('deg'))


def build_gradient(colors, direction=DIRECTION):
    gradient = f'linear-gradient({direction}, {", ".join(colors)})'
    return gradient, f'background: {gradient};'
