"""Renderers for ?format=css and ?format=svg (also picked by an Accept: text/css or image/svg+xml header).

Error responses (400, 403, 429, ...) have no gradient to draw, so they are sent as JSON whatever the format.
"""
import json
import math
from xml.sax.saxutils import quoteattr

from rest_framework.renderers import BaseRenderer

from generate.colors import DEFAULT_EASING, DEFAULT_INTERPOLATION, direction_angle, gradient_stops

SVG_SIZE = 400


def _error_as_json(data, renderer_context):
    response = (renderer_context or {}).get('response')
    if response is None or response.status_code < 400:
        return None
    response['Content-Type'] = 'application/json'
    return json.dumps(data).encode()


class CSSRenderer(BaseRenderer):
    media_type = 'text/css'
    format = 'css'
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        error = _error_as_json(data, renderer_context)
        if error is not None:
            return error
        return f'{data["css_code"]}\n'.encode()


class SVGRenderer(BaseRenderer):
    """A square SVG image of a linear or radial gradient, drawn the way CSS draws it in a square box.

    SVG has no conic gradients; the view turns those away before they get here.
    """

    media_type = 'image/svg+xml'
    format = 'svg'
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        error = _error_as_json(data, renderer_context)
        if error is not None:
            return error

        if data['type'] == 'radial':
            # CSS "circle" reaches the farthest corner: half the diagonal of the square
            element = 'radialGradient'
            attributes = f'cx="0.5" cy="0.5" r="{round(math.sqrt(0.5), 4)}"'
        else:
            # CSS runs the gradient line through the centre, long enough that the corners get the first and last colour
            angle = math.radians(direction_angle(data['direction']))
            dx, dy = math.sin(angle), -math.cos(angle)
            half = (abs(dx) + abs(dy)) / 2
            x1, y1, x2, y2 = (round(value, 4) for value in (0.5 - dx * half, 0.5 - dy * half, 0.5 + dx * half, 0.5 + dy * half))
            element = 'linearGradient'
            attributes = f'x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"'

        # SVG blends in sRGB only and linearly, so other spaces and easings are drawn with extra stops sampled from them
        stops = '\n'.join(
            f'    <stop offset="{round(offset, 4)}" stop-color={quoteattr(color)}/>'
            for offset, color in gradient_stops(
                data['colors'], data.get('interpolation', DEFAULT_INTERPOLATION), data.get('easing', DEFAULT_EASING),
            )
        )
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_SIZE}" height="{SVG_SIZE}" '
            f'viewBox="0 0 {SVG_SIZE} {SVG_SIZE}">\n'
            f'  <{element} id="gradient" {attributes}>\n{stops}\n  </{element}>\n'
            f'  <rect width="100%" height="100%" fill="url(#gradient)"/>\n'
            f'</svg>\n'
        ).encode()
