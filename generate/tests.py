from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from generate.colors import (
    DEFAULT_COLORS, HEX_COLOR_RE, MAX_COLORS, MIN_COLORS, _distance, _harmonious_colors, normalize_colors, random_colors, resize_colors,
)
from generate.forms import GradientForm
from generate.models import ColorPalette

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
        self.assertContains(response, f'linear-gradient(to top, {", ".join(BLUES)})')

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
        self.assertContains(response, 'linear-gradient(to top, #111111, #222222)')

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


class GradientAPITests(TestCase):
    def test_get_returns_gradient(self):
        response = self.client.get(reverse('api_gradient'), color_data(BLUES))
        self.assertEqual(response.json()['colors'], BLUES)

    def test_post_requires_login_and_valid_colors(self):
        self.assertEqual(self.client.post(reverse('api_gradient'), color_data(BLUES)).status_code, 403)
        self.client.force_login(User.objects.create_user('api', password='pass12345'))
        self.assertEqual(self.client.post(reverse('api_gradient'), color_data(['pink'] * NUM_COLORS)).status_code, 400)
        self.assertEqual(self.client.post(reverse('api_gradient'), color_data(BLUES)).status_code, 201)

    def test_post_saves_name_and_get_lists_it(self):
        self.client.force_login(User.objects.create_user('api', password='pass12345'))
        self.client.post(reverse('api_gradient'), {**color_data(BLUES), 'name': 'Night'})
        saved = self.client.get(reverse('api_gradient')).json()['saved_palettes']
        self.assertEqual([palette['name'] for palette in saved], ['Night'])
