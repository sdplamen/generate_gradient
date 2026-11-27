import colorsys
import math
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

GRADIENT_TYPES = ('linear', 'radial', 'conic')
DEFAULT_TYPE = 'linear'
# The web page's angle slider runs from 0 to 360 degrees; 0 points up, like DIRECTION
MAX_ANGLE = 360
DEFAULT_ANGLE = 0

# CSS Color 4 colour interpolation: how the browser blends between the stops. 'srgb' is the classic blend and
# adds nothing to the CSS; the others add an "in <space>" clause after the direction
INTERPOLATIONS = {
    'srgb': '',
    'oklab': 'in oklab',
    'oklch': 'in oklch',
    'hsl-longer': 'in hsl longer hue',
}
INTERPOLATION_LABELS = {'srgb': 'sRGB', 'oklab': 'OKLab', 'oklch': 'OKLCH', 'hsl-longer': 'HSL longer hue'}
DEFAULT_INTERPOLATION = 'srgb'

# Easing curves: with anything but linear, each pair of colours gets EASING_STEPS - 1 extra stops, evenly spaced,
# whose colours follow the curve, so the blend eases in and out of each colour instead of changing at a steady rate
def _cubic_bezier(x1, y1, x2, y2):
    """A CSS cubic-bezier() timing function: progress 0–1 in, eased progress out."""
    def ease(t):
        if t <= 0 or t >= 1:
            return t
        low, high = 0.0, 1.0
        for _ in range(40):  # bisection on x(s) = t, which rises steadily for these control points
            s = (low + high) / 2
            if 3 * (1 - s) ** 2 * s * x1 + 3 * (1 - s) * s ** 2 * x2 + s ** 3 < t:
                low = s
            else:
                high = s
        s = (low + high) / 2
        return 3 * (1 - s) ** 2 * s * y1 + 3 * (1 - s) * s ** 2 * y2 + s ** 3
    return ease


EASINGS = {
    'linear': lambda t: t,
    'ease-in-out': _cubic_bezier(0.42, 0, 0.58, 1),  # the same curve as CSS ease-in-out
    'smoothstep': lambda t: t * t * (3 - 2 * t),
}
EASING_LABELS = {'linear': 'Linear', 'ease-in-out': 'Ease-In-Out', 'smoothstep': 'Smoothstep'}
DEFAULT_EASING = 'linear'
EASING_STEPS = 7

# SVG can only blend in sRGB, so other spaces are drawn with this many stops between each pair of colours
SVG_STEPS = 16
# Below this chroma (OKLCH) or saturation (HSL) a colour is grey and its hue does not count
POWERLESS_HUE = 1e-4

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


def _percent(offset):
    return f'{offset * 100:.2f}'.rstrip('0').rstrip('.') + '%'


def build_gradient(colors, direction=DIRECTION, gradient_type=DEFAULT_TYPE, interpolation=DEFAULT_INTERPOLATION,
                   easing=DEFAULT_EASING):
    """The CSS gradient and its `background:` declaration.

    `direction` is one returned by parse_direction. Radial gradients ignore it (they spread out from the centre);
    conic ones start at its angle and end on the first colour again, so the sweep has no hard seam.
    `interpolation` is one of INTERPOLATIONS; anything but sRGB adds its "in <space>" clause.
    `easing` is one of EASINGS; anything but linear adds eased stops between the colours, each with its position.
    """
    space = INTERPOLATIONS.get(interpolation, '')
    if easing in EASINGS and easing != DEFAULT_EASING:
        # Conic gradients close the circle, so the way back to the first colour is eased too
        ring = colors + [colors[0]] if gradient_type == 'conic' else colors
        stops = ', '.join(f'{color} {_percent(offset)}' for offset, color in eased_stops(ring, interpolation, easing))
        if interpolation == 'hsl-longer':
            # The long way round is already in the stops; between neighbouring stops "longer hue" would
            # loop the whole wheel again, so the browser takes the short way from one to the next
            space = 'in hsl'
    else:
        stops = ', '.join(colors + [colors[0]] if gradient_type == 'conic' else colors)
    space = f' {space}' if space else ''
    if gradient_type == 'radial':
        gradient = f'radial-gradient(circle{space}, {stops})'
    elif gradient_type == 'conic':
        gradient = f'conic-gradient(from {direction_angle(direction)}deg{space}, {stops})'
    else:
        gradient = f'linear-gradient({direction}{space}, {stops})'
    return gradient, f'background: {gradient};'


# Colour spaces for drawing CSS Color 4 interpolation where only sRGB blending exists (SVG).
# OKLab matrices from Björn Ottosson, https://bottosson.github.io/posts/oklab/

def _to_linear(channel):
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def _from_linear(channel):
    return 12.92 * channel if channel <= 0.0031308 else 1.055 * channel ** (1 / 2.4) - 0.055


def _to_oklab(color):
    r, g, b = (_to_linear(c / 255) for c in _to_rgb(color))
    l = math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m = math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s = math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    return (
        0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
        1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
        0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
    )


def _from_oklab(lightness, a, b):
    l = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (lightness - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def _round(value):
    """Round halves up, like JavaScript's Math.round, so the page's exports match the API."""
    return math.floor(value + 0.5)


def _from_unit_rgb(r, g, b):
    """#rrggbb from 0–1 channels, clipping colours outside sRGB."""
    return _to_hex(*(_round(min(max(c, 0), 1) * 255) for c in (r, g, b)))


def _to_space(color, interpolation):
    """The colour's components in the interpolation space; a hue is None when it does not count (greys)."""
    if interpolation == 'hsl-longer':
        hue, lightness, saturation = colorsys.rgb_to_hls(*(c / 255 for c in _to_rgb(color)))
        return [hue * 360 if saturation > POWERLESS_HUE else None, saturation, lightness]
    lightness, a, b = _to_oklab(color)
    if interpolation == 'oklch':
        chroma = math.hypot(a, b)
        return [lightness, chroma, math.degrees(math.atan2(b, a)) % 360 if chroma > POWERLESS_HUE else None]
    return [lightness, a, b]


def _from_space(values, interpolation):
    if interpolation == 'hsl-longer':
        hue, saturation, lightness = values
        # The CSS Color 4 hsl-to-rgb formula, the same as the page's script, so both round the same way
        hue %= 360
        a = saturation * min(lightness, 1 - lightness)

        def channel(n):
            k = (n + hue / 30) % 12
            return lightness - a * max(-1, min(k - 3, 9 - k, 1))
        return _from_unit_rgb(channel(0), channel(8), channel(4))
    if interpolation == 'oklch':
        lightness, chroma, hue = values
        values = [lightness, chroma * math.cos(math.radians(hue)), chroma * math.sin(math.radians(hue))]
    return _from_unit_rgb(*(_from_linear(c) for c in _from_oklab(*values)))


def _hue_pair(start, end, longer):
    """Start and end hue fixed up the way CSS Color 4 does for "shorter hue" or "longer hue".

    A grey's hue is missing, so it takes the other colour's hue and the blend does not turn the wheel.
    """
    if start is None or end is None:
        hue = end if start is None else start
        return (hue or 0,) * 2
    delta = end - start
    if longer:
        if 0 < delta < 180:
            start += 360
        elif -180 < delta <= 0:
            end += 360
    elif delta > 180:
        start += 360
    elif delta < -180:
        end += 360
    return start, end


HUE_INDEX = {'oklch': 2, 'hsl-longer': 0}


def mix_colors(start, end, fraction, interpolation=DEFAULT_INTERPOLATION):
    """The colour `fraction` (0–1) of the way from `start` to `end`, blended the way CSS does in `interpolation`."""
    if interpolation not in HUE_INDEX and interpolation != 'oklab':
        return _to_hex(*(_round(a + (b - a) * fraction) for a, b in zip(_to_rgb(start), _to_rgb(end))))
    a, b = _to_space(start, interpolation), _to_space(end, interpolation)
    if interpolation in HUE_INDEX:
        i = HUE_INDEX[interpolation]
        a[i], b[i] = _hue_pair(a[i], b[i], longer=interpolation == 'hsl-longer')
    return _from_space([x + (y - x) * fraction for x, y in zip(a, b)], interpolation)


def eased_stops(colors, interpolation=DEFAULT_INTERPOLATION, easing=DEFAULT_EASING, steps=EASING_STEPS):
    """(offset 0–1, colour) stops: `steps` evenly spaced ones per pair of colours, plus the last colour.

    Each colour is the easing curve's share of the way between its pair, blended in `interpolation`.
    """
    ease = EASINGS.get(easing, EASINGS[DEFAULT_EASING])
    last = len(colors) - 1
    stops = [
        ((i + k / steps) / last, colors[i] if k == 0 else mix_colors(colors[i], colors[i + 1], ease(k / steps), interpolation))
        for i in range(last) for k in range(steps)
    ]
    return stops + [(1.0, colors[-1])]


def gradient_stops(colors, interpolation=DEFAULT_INTERPOLATION, easing=DEFAULT_EASING, steps=SVG_STEPS):
    """(offset 0–1, colour) stops that draw the gradient with plain sRGB blending (for SVG).

    A linear sRGB blend needs only the colours themselves; other spaces and easings get `steps` stops per pair.
    """
    if not INTERPOLATIONS.get(interpolation) and EASINGS.get(easing, EASINGS[DEFAULT_EASING]) is EASINGS[DEFAULT_EASING]:
        last = len(colors) - 1
        return [(i / last, color) for i, color in enumerate(colors)]
    return eased_stops(colors, interpolation, easing, steps)
