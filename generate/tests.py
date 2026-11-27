from unittest import mock

from django.contrib.auth.models import User
from django.core.cache import caches
from django.test import TestCase
from django.urls import reverse

from generate.colors import (
    DEFAULT_COLORS, HEX_COLOR_RE, MAX_COLORS, MIN_COLORS, _distance, _harmonious_colors, build_gradient,
    gradient_stops, mix_colors, normalize_colors, parse_direction, random_colors, resize_colors,
)
from generate.forms import GradientForm, style_from_query
from generate.models import ColorPalette
from generate.throttles import PaletteCreateThrottle

NUM_COLORS = MAX_COLORS

BLUES = ['#000011', '#000022', '#000033', '#000044', '#000055', '#000066']
REDS = ['#110000', '#220000', '#330000', '#440000', '#550000', '#660000']


def color_data(colors):
    return GradientForm.initial_for(colors)


class ColorsTests(TestCase):
    def test_random_colors_are_valid_hex(self):
        for _ in range(200):
            colors = random_colors()
            self.assertEqual(len(colors), DEFAULT_COLORS)
            self.assertTrue(all(HEX_COLOR_RE.match(color) for color in colors), colors)

    def test_random_colors_keep_locked_slots(self):
        for _ in range(50):
            colors = random_colors(NUM_COLORS, locked={0: '#123456', 3: '#abcdef'})
            self.assertEqual((colors[0], colors[3]), ('#123456', '#abcdef'))
            self.assertEqual(len(colors), NUM_COLORS)

    def test_unlocked_colors_blend_into_locked_ones(self):
        clashing = ['#00ff00'] * NUM_COLORS
        smooth = ['#ee0000', '#dd0000', '#cc0000', '#bb0000', '#aa0000', '#990000']
        with mock.patch('generate.colors._curated_colors', side_effect=[clashing, smooth] * 20), \
                mock.patch('generate.colors.random.random', return_value=0), \
                mock.patch('generate.colors.LOCK_SHORTLIST', 1):
            colors = random_colors(NUM_COLORS, locked={0: '#ff0000'})
        self.assertEqual(colors, ['#ff0000'] + smooth[1:])

    def test_harmonious_sweep_passes_close_to_the_anchor(self):
        for _ in range(50):
            colors = _harmonious_colors(NUM_COLORS, anchor=(2, '#1f6acd'))
            self.assertLess(_distance(colors[2], '#1f6acd'), 60, colors)

    def test_resize_blends_short_lists_and_samples_long_ones(self):
        self.assertEqual(resize_colors(['#000000', '#ffffff'], 3), ['#000000', '#808080', '#ffffff'])
        self.assertEqual(resize_colors(['#000001', '#000002', '#000003', '#000004', '#000005'], 3),
                         ['#000001', '#000003', '#000005'])

    def test_normalize_drops_invalid_values_and_fits_length(self):
        self.assertEqual(normalize_colors(['#FF0000', 'pink', '#0000ff']), ['#ff0000', '#0000ff'])
        self.assertEqual(normalize_colors(['#111111']), ['#111111'] * MIN_COLORS)
        self.assertEqual(len(normalize_colors(BLUES + REDS)), MAX_COLORS)
        self.assertEqual(normalize_colors(['#000000', '#ffffff'], 3), ['#000000', '#808080', '#ffffff'])

    def test_random_colors_any_count(self):
        for size in range(MIN_COLORS, MAX_COLORS + 1):
            self.assertEqual(len(random_colors(size)), size)
            self.assertEqual(len(random_colors(size, locked={0: '#123456'})), size)


class GradientFormTests(TestCase):
    def test_accepts_hex_and_lowercases(self):
        form = GradientForm(color_data(['#AABBCC'] * NUM_COLORS))
        self.assertTrue(form.is_valid())
        self.assertEqual(form.colors, ['#aabbcc'] * NUM_COLORS)

    def test_rejects_non_hex_values(self):
        for bad in ['red;', 'pink', '#00000000', '#12345g', '']:
            form = GradientForm(color_data([bad] + BLUES[1:]))
            self.assertFalse(form.is_valid(), bad)

    def test_field_count_follows_the_data(self):
        self.assertEqual(GradientForm(color_data(BLUES[:2])).color_names, ['color1', 'color2'])
        self.assertEqual(len(GradientForm(initial=color_data(BLUES[:4])).color_names), 4)
        self.assertEqual(len(GradientForm().color_names), DEFAULT_COLORS)
        self.assertFalse(GradientForm({'color1': '#000000'}).is_valid())


class GradientPageTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', password='pass12345')
        self.other = User.objects.create_user('other', password='pass12345')

    def test_each_visit_gets_new_random_colors(self):
        with mock.patch('generate.mixins.random_colors', side_effect=[BLUES, REDS]):
            first = self.client.get(reverse('generate_gradient'))
            second = self.client.get(reverse('generate_gradient'))
        self.assertContains(first, BLUES[0])
        self.assertContains(second, REDS[0])

    def test_valid_query_colors_are_shown(self):
        response = self.client.get(reverse('generate_gradient'), color_data(BLUES))
        self.assertContains(response, f'linear-gradient(0deg, {", ".join(BLUES)})')

    def test_first_visit_gets_default_count(self):
        response = self.client.get(reverse('generate_gradient'))
        self.assertEqual(len(response.context['colors']), DEFAULT_COLORS)
        self.assertRegex(response.content.decode(), rf'value="{DEFAULT_COLORS}" checked')

    def test_query_with_fewer_colors_keeps_them(self):
        response = self.client.get(reverse('generate_gradient'), color_data(BLUES[:2]))
        self.assertEqual(response.context['colors'], BLUES[:2])

    def test_count_resizes_the_given_colors(self):
        query = {**color_data(['#000000', '#ffffff']), 'count': '3'}
        response = self.client.get(reverse('generate_gradient'), query)
        self.assertEqual(response.context['colors'], ['#000000', '#808080', '#ffffff'])
        query = {**color_data(BLUES), 'count': '2'}
        self.assertEqual(self.client.get(reverse('generate_gradient'), query).context['colors'], [BLUES[0], BLUES[-1]])

    def test_random_uses_the_count(self):
        for count in range(MIN_COLORS, MAX_COLORS + 1):
            response = self.client.get(reverse('generate_gradient'), {'random': 'true', 'count': str(count)})
            self.assertEqual(len(response.context['colors']), count)

    def test_out_of_range_count_is_ignored(self):
        for count in ['1', '7', 'x', '']:
            response = self.client.get(reverse('generate_gradient'), {**color_data(BLUES[:4]), 'count': count})
            self.assertEqual(response.context['colors'], BLUES[:4])

    def test_locks_outside_the_new_count_are_dropped(self):
        query = {**color_data(BLUES), 'count': '2', 'lock': '1,3'}
        response = self.client.get(reverse('generate_gradient'), query)
        self.assertEqual(response.context['locked_slots'], [1])

    def test_invalid_query_colors_are_ignored(self):
        response = self.client.get(reverse('generate_gradient'), color_data(['red;'] * NUM_COLORS))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'red;')

    def test_random_keeps_locked_colors_and_marks_them_locked(self):
        query = {'random': 'true', 'lock': '1,3', 'color1': '#123456', 'color3': '#ABCDEF'}
        with mock.patch('generate.colors._curated_colors', return_value=list(BLUES)), \
                mock.patch('generate.colors.random.random', return_value=0):
            response = self.client.get(reverse('generate_gradient'), query)
        expected = ['#123456', BLUES[1], '#abcdef'] + BLUES[3:]
        self.assertEqual(response.context['colors'], expected)
        self.assertEqual(response.context['locked_slots'], [1, 3])
        html = response.content.decode()
        self.assertRegex(html, r'data-slot="1"\s+aria-pressed="true"')
        self.assertRegex(html, r'data-slot="2"\s+aria-pressed="false"')

    def test_invalid_locks_are_ignored(self):
        query = {'random': 'true', 'lock': '0,2,9,x', 'color2': 'red;'}
        response = self.client.get(reverse('generate_gradient'), query)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['locked_slots'], [])
        self.assertNotContains(response, 'red;')

    def test_saving_requires_login(self):
        response = self.client.post(reverse('generate_gradient'), color_data(BLUES))
        self.assertRedirects(response, reverse('login'), fetch_redirect_response=False)
        self.assertFalse(ColorPalette.objects.exists())

    def test_save_valid_palette(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('generate_gradient'), color_data(BLUES))
        palette = ColorPalette.objects.get()
        self.assertEqual((palette.user, palette.colors), (self.owner, BLUES))
        self.assertNotIn('csrfmiddlewaretoken', response.url)

    def test_save_invalid_palette_does_not_crash(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('generate_gradient'), color_data(['#00000000'] + BLUES[1:]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Palette not saved')
        self.assertFalse(ColorPalette.objects.exists())

    def test_saved_palette_with_fewer_colors_is_shown(self):
        palette = ColorPalette.objects.create(user=self.owner, colors=['#111111', '#222222'])
        response = self.client.get(reverse('get_palette', args=[palette.id]))
        self.assertContains(response, 'linear-gradient(0deg, #111111, #222222)')

    def test_save_palette_with_three_colors(self):
        self.client.force_login(self.owner)
        self.client.post(reverse('generate_gradient'), color_data(BLUES[:3]))
        self.assertEqual(ColorPalette.objects.get().colors, BLUES[:3])

    def test_owner_can_edit_palette(self):
        palette = ColorPalette.objects.create(user=self.owner, colors=BLUES)
        self.client.force_login(self.owner)
        self.client.post(reverse('edit-palette', args=[palette.id]), color_data(REDS))
        palette.refresh_from_db()
        self.assertEqual(palette.colors, REDS)

    def test_other_users_cannot_edit_or_delete(self):
        palette = ColorPalette.objects.create(user=self.owner, colors=BLUES)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(reverse('edit-palette', args=[palette.id]), color_data(REDS)).status_code, 404)
        self.assertEqual(self.client.post(reverse('delete-palette', args=[palette.id])).status_code, 404)
        self.assertTrue(ColorPalette.objects.filter(id=palette.id).exists())

    def test_saved_palettes_are_numbered_from_one_oldest_first(self):
        first = ColorPalette.objects.create(user=self.owner, colors=BLUES)
        gone = ColorPalette.objects.create(user=self.owner, colors=REDS)
        last = ColorPalette.objects.create(user=self.owner, colors=REDS)
        gone.delete()
        response = self.client.get(reverse('generate_gradient'))
        self.assertEqual(list(response.context['saved_palettes']), [first, last])
        self.assertContains(response, 'Palette 1</span>')
        self.assertContains(response, 'Palette 2</span>')
        self.assertNotContains(response, f'Palette {last.id}</span>')
        self.assertEqual(last.number, 2)

    def test_save_palette_with_name(self):
        self.client.force_login(self.owner)
        self.client.post(reverse('generate_gradient'), {**color_data(BLUES[:3]), 'name': '  Ocean  '})
        self.assertEqual(ColorPalette.objects.get().name, 'Ocean')

    def test_save_palette_with_too_long_name_is_rejected(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('generate_gradient'), {**color_data(BLUES[:3]), 'name': 'x' * 41}, follow=True)
        self.assertContains(response, 'Palette not saved')
        self.assertFalse(ColorPalette.objects.exists())

    def test_named_palette_shows_its_name_others_their_number(self):
        ColorPalette.objects.create(user=self.owner, colors=BLUES, name='Ocean <b>')
        ColorPalette.objects.create(user=self.owner, colors=REDS)
        response = self.client.get(reverse('generate_gradient'))
        self.assertContains(response, 'Ocean &lt;b&gt;</span>')
        self.assertContains(response, 'Palette 2</span>')
        self.assertNotContains(response, 'Palette 1</span>')

    def test_owner_can_rename_palette(self):
        palette = ColorPalette.objects.create(user=self.owner, colors=BLUES, name='Old')
        self.client.force_login(self.owner)
        response = self.client.get(reverse('edit-palette', args=[palette.id]))
        self.assertContains(response, 'value="Old"')
        self.client.post(reverse('edit-palette', args=[palette.id]), {**color_data(REDS), 'name': 'New'})
        palette.refresh_from_db()
        self.assertEqual((palette.name, palette.colors), ('New', REDS))
        self.client.post(reverse('edit-palette', args=[palette.id]), color_data(REDS))
        palette.refresh_from_db()
        self.assertEqual(palette.name, '')

    def test_edit_page_renders_one_color_field_per_color(self):
        palette = ColorPalette.objects.create(user=self.owner, colors=BLUES[:3])
        self.client.force_login(self.owner)
        response = self.client.get(reverse('edit-palette', args=[palette.id]))
        self.assertContains(response, 'type="color"', count=3)
        self.assertContains(response, 'Palette 1 | Colors')


class GradientStyleTests(TestCase):
    """Gradient type (linear, radial, conic) and angle on the web page."""

    def setUp(self):
        self.owner = User.objects.create_user('owner', password='pass12345')

    def test_build_gradient_for_each_type(self):
        colors = ['#000000', '#ffffff']
        self.assertEqual(build_gradient(colors, '45deg')[0], 'linear-gradient(45deg, #000000, #ffffff)')
        self.assertEqual(build_gradient(colors, '45deg', 'radial')[0], 'radial-gradient(circle, #000000, #ffffff)')
        self.assertEqual(build_gradient(colors, '45deg', 'conic')[0],
                         'conic-gradient(from 45deg, #000000, #ffffff, #000000)')
        self.assertEqual(build_gradient(colors, 'to right', 'conic')[0],
                         'conic-gradient(from 90deg, #000000, #ffffff, #000000)')

    def test_style_from_query_falls_back_to_defaults(self):
        self.assertEqual(style_from_query({'type': 'conic', 'angle': '360', 'interpolation': 'oklch'}),
                         ('conic', 360, 'oklch'))
        for query in [{}, {'type': 'diamond', 'angle': '361'}, {'type': 'Radial', 'angle': '-5'}, {'angle': '4.5'},
                      {'interpolation': 'OKLCH'}, {'interpolation': 'hsl'}]:
            self.assertEqual(style_from_query(query), ('linear', 0, 'srgb'), query)

    def test_page_uses_type_and_angle(self):
        query = {**color_data(BLUES[:2]), 'type': 'conic', 'angle': '90'}
        response = self.client.get(reverse('generate_gradient'), query)
        self.assertContains(response, f'conic-gradient(from 90deg, {BLUES[0]}, {BLUES[1]}, {BLUES[0]})')
        html = response.content.decode()
        self.assertRegex(html, r'name="type" value="conic" checked')
        self.assertRegex(html, r'id="angle-input" name="angle"[^>]*value="90"')
        self.assertIn('Gradient Start Angle:', html)

        response = self.client.get(reverse('generate_gradient'), {**color_data(BLUES[:2]), 'angle': '135'})
        self.assertContains(response, f'linear-gradient(135deg, {BLUES[0]}, {BLUES[1]})')

    def test_radial_hides_the_angle_but_keeps_it(self):
        response = self.client.get(reverse('generate_gradient'), {**color_data(BLUES[:2]), 'type': 'radial', 'angle': '30'})
        self.assertContains(response, f'radial-gradient(circle, {BLUES[0]}, {BLUES[1]})')
        self.assertContains(response, '<div class="angle-control" hidden>')
        self.assertRegex(response.content.decode(), r'id="angle-input" name="angle"[^>]*value="30"')

    def test_links_and_nav_forms_keep_the_style(self):
        palette = ColorPalette.objects.create(user=self.owner, colors=BLUES)
        self.client.force_login(self.owner)
        response = self.client.get(reverse('generate_gradient'), {'type': 'radial', 'angle': '30'})
        self.assertContains(response, f'href="{reverse("get_palette", args=[palette.id])}?type=radial&amp;angle=30"')
        # Random Colors, Random Saved Palettes and Save Palette
        self.assertContains(response, 'class="style-field" name="type" value="radial"', count=3)
        self.assertContains(response, 'class="style-field" name="angle" value="30"', count=3)

    def test_default_style_adds_nothing_to_links(self):
        palette = ColorPalette.objects.create(user=self.owner, colors=BLUES)
        response = self.client.get(reverse('generate_gradient'))
        self.assertContains(response, f'href="{reverse("get_palette", args=[palette.id])}"')

    def test_saving_keeps_the_style(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('generate_gradient'), {**color_data(BLUES[:2]), 'type': 'conic', 'angle': '45'})
        self.assertIn('type=conic&angle=45', response.url)
        self.assertEqual(ColorPalette.objects.get().colors, BLUES[:2])

    def test_random_saved_palette_keeps_the_style(self):
        palette = ColorPalette.objects.create(user=self.owner, colors=BLUES)
        response = self.client.get(reverse('get_saved_palette'), {'type': 'radial', 'angle': '0'})
        self.assertRedirects(response, f'{reverse("get_palette", args=[palette.id])}?type=radial',
                             fetch_redirect_response=False)
        response = self.client.get(reverse('get_saved_palette'))
        self.assertRedirects(response, reverse('get_palette', args=[palette.id]), fetch_redirect_response=False)


class InterpolationTests(TestCase):
    """CSS Color 4 colour interpolation: in oklab, in oklch, in hsl longer hue."""

    def test_build_gradient_adds_the_space_after_the_direction(self):
        colors = ['#ff0000', '#0000ff']
        self.assertEqual(build_gradient(colors, '45deg', 'linear', 'oklch')[0],
                         'linear-gradient(45deg in oklch, #ff0000, #0000ff)')
        self.assertEqual(build_gradient(colors, 'to right', 'linear', 'oklab')[0],
                         'linear-gradient(to right in oklab, #ff0000, #0000ff)')
        self.assertEqual(build_gradient(colors, '0deg', 'radial', 'hsl-longer')[0],
                         'radial-gradient(circle in hsl longer hue, #ff0000, #0000ff)')
        self.assertEqual(build_gradient(colors, '90deg', 'conic', 'oklch')[0],
                         'conic-gradient(from 90deg in oklch, #ff0000, #0000ff, #ff0000)')
        self.assertEqual(build_gradient(colors, '45deg', 'linear', 'srgb')[0],
                         'linear-gradient(45deg, #ff0000, #0000ff)')

    def test_mix_colors_in_each_space(self):
        self.assertEqual(mix_colors('#ff0000', '#0000ff', 0.5), '#800080')
        self.assertEqual(mix_colors('#ffffff', '#000000', 0.5, 'oklab'), '#636363')
        # Red to blue the long way round: through yellow, green and cyan
        self.assertEqual([mix_colors('#ff0000', '#0000ff', t, 'hsl-longer') for t in (0.25, 0.5, 0.75)],
                         ['#ffff00', '#00ff00', '#00ffff'])
        for space in ('oklab', 'oklch', 'hsl-longer'):
            self.assertEqual(mix_colors('#123456', '#abcdef', 0, space), '#123456', space)
            self.assertEqual(mix_colors('#123456', '#abcdef', 1, space), '#abcdef', space)

    def test_grey_takes_the_other_hue_in_oklch(self):
        # Grey has no hue, so the blend keeps red's hue instead of swinging through another colour
        middle = mix_colors('#808080', '#ff0000', 0.5, 'oklch')
        r, g, b = (int(middle[i:i + 2], 16) for i in (1, 3, 5))
        self.assertGreater(r, g + 50)
        self.assertGreater(r, b + 50)

    def test_gradient_stops(self):
        self.assertEqual(gradient_stops(['#000000', '#ffffff']), [(0.0, '#000000'), (1.0, '#ffffff')])
        stops = gradient_stops(['#ff0000', '#00ff00', '#0000ff'], 'oklch', steps=4)
        self.assertEqual(len(stops), 9)
        self.assertEqual(stops[0], (0.0, '#ff0000'))
        self.assertEqual(stops[4], (0.5, '#00ff00'))
        self.assertEqual(stops[-1], (1.0, '#0000ff'))

    def test_page_uses_and_keeps_the_interpolation(self):
        owner = User.objects.create_user('owner', password='pass12345')
        palette = ColorPalette.objects.create(user=owner, colors=BLUES)
        self.client.force_login(owner)
        response = self.client.get(reverse('generate_gradient'), {**color_data(BLUES[:2]), 'interpolation': 'oklch'})
        self.assertContains(response, f'linear-gradient(0deg in oklch, {BLUES[0]}, {BLUES[1]})')
        self.assertContains(response, 'name="interpolation" value="oklch" checked')
        self.assertContains(response, f'href="{reverse("get_palette", args=[palette.id])}?interpolation=oklch"')
        self.assertContains(response, 'class="style-field" name="interpolation" value="oklch"', count=3)

        response = self.client.post(reverse('generate_gradient'), {**color_data(BLUES[:2]), 'interpolation': 'hsl-longer'})
        self.assertIn('interpolation=hsl-longer', response.url)

    def test_api_interpolation(self):
        query = {**color_data(['#ff0000', '#0000ff']), 'direction': 'to right'}
        data = self.client.get(reverse('api_gradient'), query).json()
        self.assertEqual((data['interpolation'], data['gradient']), ('srgb', 'linear-gradient(to right, #ff0000, #0000ff)'))
        data = self.client.get(reverse('api_gradient'), {**query, 'interpolation': 'hsl-longer'}).json()
        self.assertEqual(data['gradient'], 'linear-gradient(to right in hsl longer hue, #ff0000, #0000ff)')
        css = self.client.get(reverse('api_gradient'), {**query, 'interpolation': 'oklab', 'format': 'css'})
        self.assertEqual(css.content.decode(), 'background: linear-gradient(to right in oklab, #ff0000, #0000ff);\n')

        svg = self.client.get(reverse('api_gradient'), {**query, 'interpolation': 'hsl-longer', 'format': 'svg'})
        svg = svg.content.decode()
        self.assertEqual(svg.count('<stop '), 17)
        self.assertIn('<stop offset="0.5" stop-color="#00ff00"/>', svg)

        response = self.client.get(reverse('api_gradient'), {'interpolation': 'lab'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('interpolation', response.json())


class DirectionTests(TestCase):
    def test_parse_direction_accepts_keywords_and_angles(self):
        self.assertEqual(parse_direction('to right'), 'to right')
        self.assertEqual(parse_direction('  To   RIGHT  top '), 'to top right')
        self.assertEqual(parse_direction('45deg'), '45deg')
        self.assertEqual(parse_direction('-090deg'), '-90deg')

    def test_parse_direction_rejects_everything_else(self):
        for bad in ['', 'right', 'to', 'to middle', 'to top bottom', 'to left right', 'to top right left',
                    '361deg', '45', '4.5deg', '45deg; color: red', 'to right)']:
            self.assertIsNone(parse_direction(bad), bad)


class GradientAPITests(TestCase):
    def setUp(self):
        caches['throttle'].clear()

    def test_get_returns_gradient(self):
        response = self.client.get(reverse('api_gradient'), color_data(BLUES))
        self.assertEqual(response.json()['colors'], BLUES)
        self.assertEqual(response.json()['direction'], 'to top')

    def test_get_no_longer_lists_saved_palettes(self):
        ColorPalette.objects.create(user=User.objects.create_user('api', password='pass12345'), colors=BLUES)
        self.assertNotIn('saved_palettes', self.client.get(reverse('api_gradient')).json())

    def test_direction_is_used_in_the_gradient(self):
        data = self.client.get(reverse('api_gradient'), {**color_data(BLUES[:2]), 'direction': 'to right top'}).json()
        self.assertEqual(data['direction'], 'to top right')
        self.assertEqual(data['css_code'], f'background: linear-gradient(to top right, {BLUES[0]}, {BLUES[1]});')
        data = self.client.get(reverse('api_gradient'), {'direction': '135deg'}).json()
        self.assertTrue(data['gradient'].startswith('linear-gradient(135deg, '))

    def test_invalid_direction_or_count_is_rejected(self):
        for query in [{'direction': 'sideways'}, {'direction': 'to right); x: y'}, {'count': '1'}, {'count': '7'},
                      {'count': 'x'}]:
            response = self.client.get(reverse('api_gradient'), query)
            self.assertEqual(response.status_code, 400, query)
            self.assertIn(next(iter(query)), response.json())

    def test_count_sets_the_number_of_colors(self):
        for count in range(MIN_COLORS, MAX_COLORS + 1):
            self.assertEqual(len(self.client.get(reverse('api_gradient'), {'count': count}).json()['colors']), count)
        query = {**color_data(['#000000', '#ffffff']), 'count': '3'}
        self.assertEqual(self.client.get(reverse('api_gradient'), query).json()['colors'],
                         ['#000000', '#808080', '#ffffff'])

    def test_css_format(self):
        response = self.client.get(reverse('api_gradient'), {**color_data(BLUES[:2]), 'format': 'css'})
        self.assertEqual(response['Content-Type'], 'text/css; charset=utf-8')
        self.assertEqual(response.content.decode(), f'background: linear-gradient(to top, {BLUES[0]}, {BLUES[1]});\n')
        response = self.client.get(reverse('api_gradient'), color_data(BLUES[:2]), HTTP_ACCEPT='text/css')
        self.assertEqual(response['Content-Type'], 'text/css; charset=utf-8')

    def test_svg_format(self):
        query = {**color_data(['#000000', '#808080', '#ffffff']), 'direction': 'to right', 'format': 'svg'}
        response = self.client.get(reverse('api_gradient'), query)
        self.assertEqual(response['Content-Type'], 'image/svg+xml; charset=utf-8')
        svg = response.content.decode()
        self.assertIn('x1="0.0" y1="0.5" x2="1.0" y2="0.5"', svg)
        self.assertIn('<stop offset="0.5" stop-color="#808080"/>', svg)
        corner = self.client.get(reverse('api_gradient'), {'direction': '45deg', 'format': 'svg'}).content.decode()
        self.assertIn('x1="0.0" y1="1.0" x2="1.0" y2="0.0"', corner)

    def test_errors_are_json_in_any_format(self):
        response = self.client.get(reverse('api_gradient'), {'direction': 'nope', 'format': 'css'})
        self.assertEqual((response.status_code, response['Content-Type']), (400, 'application/json'))
        self.assertIn('direction', response.json())

    def test_type_parameter(self):
        query = color_data(BLUES[:2])
        data = self.client.get(reverse('api_gradient'), query).json()
        self.assertEqual(data['type'], 'linear')
        data = self.client.get(reverse('api_gradient'), {**query, 'type': 'radial'}).json()
        self.assertEqual((data['type'], data['gradient']), ('radial', f'radial-gradient(circle, {BLUES[0]}, {BLUES[1]})'))
        data = self.client.get(reverse('api_gradient'), {**query, 'type': 'conic', 'direction': 'to bottom'}).json()
        self.assertEqual(data['gradient'], f'conic-gradient(from 180deg, {BLUES[0]}, {BLUES[1]}, {BLUES[0]})')
        response = self.client.get(reverse('api_gradient'), {**query, 'type': 'conic', 'format': 'css'})
        self.assertEqual(response.content.decode(),
                         f'background: conic-gradient(from 0deg, {BLUES[0]}, {BLUES[1]}, {BLUES[0]});\n')

    def test_invalid_type_is_rejected(self):
        response = self.client.get(reverse('api_gradient'), {'type': 'diamond'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('type', response.json())

    def test_svg_for_radial_and_not_for_conic(self):
        svg = self.client.get(reverse('api_gradient'), {'type': 'radial', 'format': 'svg'}).content.decode()
        self.assertIn('<radialGradient id="gradient" cx="0.5" cy="0.5" r="0.7071">', svg)
        self.assertIn('</radialGradient>', svg)
        response = self.client.get(reverse('api_gradient'), {'type': 'conic', 'format': 'svg'})
        self.assertEqual((response.status_code, response['Content-Type']), (400, 'application/json'))
        self.assertIn('type', response.json())

    def test_unknown_format_is_not_found(self):
        self.assertEqual(self.client.get(reverse('api_gradient'), {'format': 'png'}).status_code, 404)

    def test_post_requires_login_and_valid_colors(self):
        self.assertEqual(self.client.post(reverse('api_gradient'), color_data(BLUES)).status_code, 403)
        self.client.force_login(User.objects.create_user('api', password='pass12345'))
        self.assertEqual(self.client.post(reverse('api_gradient'), color_data(['pink'] * NUM_COLORS)).status_code, 400)
        self.assertEqual(self.client.post(reverse('api_gradient'), color_data(BLUES)).status_code, 201)

    def test_post_is_throttled_per_user(self):
        first = User.objects.create_user('api', password='pass12345')
        with mock.patch.dict(PaletteCreateThrottle.THROTTLE_RATES, {'palette_create': '2/hour'}):
            self.client.force_login(first)
            statuses = [self.client.post(reverse('api_gradient'), color_data(BLUES)).status_code for _ in range(3)]
            self.assertEqual(statuses, [201, 201, 429])
            self.assertEqual(ColorPalette.objects.count(), 2)
            self.assertEqual(self.client.get(reverse('api_gradient')).status_code, 200)

            self.client.force_login(User.objects.create_user('second', password='pass12345'))
            self.assertEqual(self.client.post(reverse('api_gradient'), color_data(BLUES)).status_code, 201)


class PaletteAPITests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', password='pass12345')
        self.other = User.objects.create_user('other', password='pass12345')

    def test_post_saves_name_and_palettes_lists_it(self):
        caches['throttle'].clear()
        self.client.force_login(self.owner)
        self.client.post(reverse('api_gradient'), {**color_data(BLUES), 'name': 'Night'})
        response = self.client.get(reverse('api_palettes'))
        self.assertEqual(response.status_code, 200)
        [palette] = response.json()['results']
        self.assertEqual((palette['name'], palette['colors']), ('Night', BLUES))
        self.assertEqual(set(palette), {'id', 'name', 'colors', 'created_at'})

    def test_list_is_public_and_paginated_oldest_first(self):
        palettes = [ColorPalette.objects.create(user=self.owner, colors=BLUES) for _ in range(25)]
        data = self.client.get(reverse('api_palettes')).json()
        self.assertEqual(data['count'], 25)
        self.assertEqual([p['id'] for p in data['results']], [p.id for p in palettes[:20]])
        self.assertIsNotNone(data['next'])
        second = self.client.get(reverse('api_palettes'), {'page': 2}).json()
        self.assertEqual([p['id'] for p in second['results']], [p.id for p in palettes[20:]])
        self.assertIsNone(second['next'])
        small = self.client.get(reverse('api_palettes'), {'page_size': 5}).json()
        self.assertEqual(len(small['results']), 5)
        self.assertEqual(len(self.client.get(reverse('api_palettes'), {'page_size': 1000}).json()['results']), 25)

    def test_mine_lists_only_own_palettes(self):
        ColorPalette.objects.create(user=self.other, colors=REDS)
        own = ColorPalette.objects.create(user=self.owner, colors=BLUES)
        self.assertEqual(self.client.get(reverse('api_palettes'), {'mine': 'true'}).status_code, 403)
        self.client.force_login(self.owner)
        results = self.client.get(reverse('api_palettes'), {'mine': 'true'}).json()['results']
        self.assertEqual([p['id'] for p in results], [own.id])

    def test_schema_builds(self):
        response = self.client.get(reverse('schema'))
        self.assertEqual(response.status_code, 200)
        schema = response.content.decode()
        self.assertIn('/api/palettes/', schema)
        self.assertIn('direction', schema)
