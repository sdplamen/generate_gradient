const randomColorBtn = document.getElementById('random-color-btn');
const randomSavedBtn = document.getElementById('random-saved-btn');

document.addEventListener('keydown', (event) => {
    if (event.code !== 'Space') return;

    const tag = document.activeElement.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

    event.preventDefault();

    if (event.shiftKey) {
        if (randomSavedBtn) randomSavedBtn.click();
    } else {
        if (randomColorBtn) randomColorBtn.click();
    }
});

// Mobile: long press = random colors, two-finger long press = random saved palettes
const LONG_PRESS_MS = 500;
const MOVE_TOLERANCE = 10; // px — cancel if finger drifts more than this

let pressTimer = null;
let touchStartX = 0;
let touchStartY = 0;
let longPressFired = false;

function isInteractiveTarget(target) {
    const tag = target.tagName;
    return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || tag === 'A' || tag === 'BUTTON';
}

document.addEventListener('touchstart', (event) => {
    // A second finger restarts the timer as a two-finger press, so only one action fires
    clearTimeout(pressTimer);
    pressTimer = null;
    if (isInteractiveTarget(event.target)) return;

    longPressFired = false;
    const touch = event.touches[0];
    touchStartX = touch.clientX;
    touchStartY = touch.clientY;

    const isTwoFinger = event.touches.length === 2;

    pressTimer = setTimeout(() => {
        longPressFired = true;
        if (isTwoFinger) {
            if (randomSavedBtn) randomSavedBtn.click();
        } else {
            if (randomColorBtn) randomColorBtn.click();
        }
        // optional: haptic-ish feedback via a quick CSS class toggle could go here
    }, LONG_PRESS_MS);
}, { passive: true });

document.addEventListener('touchmove', (event) => {
    if (!pressTimer) return;
    const touch = event.touches[0];
    const dx = Math.abs(touch.clientX - touchStartX);
    const dy = Math.abs(touch.clientY - touchStartY);

    if (dx > MOVE_TOLERANCE || dy > MOVE_TOLERANCE) {
        clearTimeout(pressTimer);
        pressTimer = null;
    }
}, { passive: true });

// Lifting the finger before LONG_PRESS_MS makes it a normal tap, not a long press
function cancelLongPress() {
    clearTimeout(pressTimer);
    pressTimer = null;
}

document.addEventListener('touchend', cancelLongPress, { passive: true });
document.addEventListener('touchcancel', cancelLongPress, { passive: true });

// The gradient as it is set on the page now: colours (color1 first), type, angle and colour interpolation,
// including changes not yet applied
function currentGradient() {
    const colors = [...document.querySelectorAll('.color-input-form input[type="color"]')].map(input => input.value);
    const typeInput = document.querySelector('.type-picker input[name="type"]:checked');
    const angleInput = document.getElementById('angle-input');
    const interpolationInput = document.querySelector('.interpolation-picker input[name="interpolation"]:checked');
    return {
        colors,
        type: typeInput ? typeInput.value : 'linear',
        angle: angleInput ? Number(angleInput.value) : 0,
        interpolation: interpolationInput ? interpolationInput.value : 'srgb',
    };
}

// CSS Color 4 interpolation, as INTERPOLATIONS in colors.py: sRGB is the classic blend and adds nothing to the CSS
const INTERPOLATIONS = {
    srgb: '',
    oklab: 'in oklab',
    oklch: 'in oklch',
    'hsl-longer': 'in hsl longer hue',
};

// Same CSS as build_gradient in colors.py: radial spreads from the centre, conic closes the circle on its first colour
function gradientCss({ colors, type, angle, interpolation }) {
    const stops = colors.join(', ');
    const space = INTERPOLATIONS[interpolation] ? ` ${INTERPOLATIONS[interpolation]}` : '';
    if (type === 'radial') return `radial-gradient(circle${space}, ${stops})`;
    if (type === 'conic') return `conic-gradient(from ${angle}deg${space}, ${stops}, ${colors[0]})`;
    return `linear-gradient(${angle}deg${space}, ${stops})`;
}

// SVG only blends in sRGB, so other spaces are drawn with extra stops sampled in that space (gradient_stops in colors.py)
const ColorSpaces = (() => {
    const SVG_STEPS = 16;
    const POWERLESS_HUE = 1e-4;
    const HUE_INDEX = { oklch: 2, 'hsl-longer': 0 };

    const toRgb = hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255);
    const toHex = rgb => '#' + rgb.map(c => Math.round(Math.min(Math.max(c, 0), 1) * 255).toString(16).padStart(2, '0')).join('');
    const toLinear = c => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
    const fromLinear = c => (c <= 0.0031308 ? 12.92 * c : 1.055 * Math.sign(c) * Math.abs(c) ** (1 / 2.4) - 0.055);

    // OKLab matrices from Björn Ottosson, https://bottosson.github.io/posts/oklab/
    function toOklab(hex) {
        const [r, g, b] = toRgb(hex).map(toLinear);
        const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
        const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
        const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
        return [
            0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
        ];
    }

    function fromOklab([L, a, b]) {
        const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
        const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
        const s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3;
        return toHex([
            4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
        ].map(fromLinear));
    }

    // [hue in degrees or null for greys, saturation, lightness]
    function toHsl(hex) {
        const [r, g, b] = toRgb(hex);
        const max = Math.max(r, g, b);
        const min = Math.min(r, g, b);
        const l = (max + min) / 2;
        const d = max - min;
        if (d === 0) return [null, 0, l];
        const s = l <= 0.5 ? d / (max + min) : d / (2 - max - min);
        let h;
        if (max === r) h = ((g - b) / d) % 6;
        else if (max === g) h = (b - r) / d + 2;
        else h = (r - g) / d + 4;
        return [s > POWERLESS_HUE ? ((h * 60) + 360) % 360 : null, s, l];
    }

    function fromHsl([h, s, l]) {
        const hue = ((h % 360) + 360) % 360;
        const k = n => (n + hue / 30) % 12;
        const a = s * Math.min(l, 1 - l);
        const f = n => l - a * Math.max(-1, Math.min(k(n) - 3, 9 - k(n), 1));
        return toHex([f(0), f(8), f(4)]);
    }

    function toSpace(hex, space) {
        if (space === 'hsl-longer') return toHsl(hex);
        const [L, a, b] = toOklab(hex);
        if (space !== 'oklch') return [L, a, b];
        const c = Math.hypot(a, b);
        return [L, c, c > POWERLESS_HUE ? ((Math.atan2(b, a) * 180 / Math.PI) + 360) % 360 : null];
    }

    function fromSpace(values, space) {
        if (space === 'hsl-longer') return fromHsl(values);
        if (space !== 'oklch') return fromOklab(values);
        const [L, c, h] = values;
        const radians = h * Math.PI / 180;
        return fromOklab([L, c * Math.cos(radians), c * Math.sin(radians)]);
    }

    // CSS Color 4 hue fix-up; a grey's hue is missing, so it takes the other colour's hue
    function huePair(start, end, longer) {
        if (start === null || end === null) {
            const hue = (start === null ? end : start) || 0;
            return [hue, hue];
        }
        const delta = end - start;
        if (longer) {
            if (delta > 0 && delta < 180) start += 360;
            else if (delta > -180 && delta <= 0) end += 360;
        } else if (delta > 180) start += 360;
        else if (delta < -180) end += 360;
        return [start, end];
    }

    function mix(start, end, t, space) {
        const a = toSpace(start, space);
        const b = toSpace(end, space);
        if (space in HUE_INDEX) {
            const i = HUE_INDEX[space];
            [a[i], b[i]] = huePair(a[i], b[i], space === 'hsl-longer');
        }
        return fromSpace(a.map((value, i) => value + (b[i] - value) * t), space);
    }

    // [offset 0–1, colour] pairs that draw the gradient with plain sRGB blending
    function stops(colors, space) {
        const last = colors.length - 1;
        if (!INTERPOLATIONS[space]) return colors.map((color, i) => [i / last, color]);
        const result = [];
        for (let i = 0; i < last; i++) {
            for (let k = 0; k < SVG_STEPS; k++) {
                result.push([(i + k / SVG_STEPS) / last, mix(colors[i], colors[i + 1], k / SVG_STEPS, space)]);
            }
        }
        result.push([1, colors[last]]);
        return result;
    }

    return { stops };
})();

const round = value => Math.round(value * 100) / 100;

// Copy Code: copies the gradient as code, in the format picked next to the button
const EXPORT_FORMATS = {
    css: gradient => `background: ${gradientCss(gradient)};`,

    // Arbitrary-value class: works in Tailwind v3 and v4, with any number of colours
    tailwind: gradient => `bg-[${gradientCss(gradient).replace(/, /g, ',').replace(/ /g, '_')}]`,

    // SVG has no conic gradients, so this format is switched off for them
    svg: ({ colors, type, angle, interpolation }) => {
        const width = 800;
        const height = 600;
        const cx = width / 2;
        const cy = height / 2;
        const stops = ColorSpaces.stops(colors, interpolation).map(([offset, color]) =>
            `      <stop offset="${round(offset * 100)}%" stop-color="${color}"/>`
        ).join('\n');

        let open;
        let close;
        if (type === 'radial') {
            // CSS "circle" reaches the farthest corner
            open = `<radialGradient id="gradient" gradientUnits="userSpaceOnUse" cx="${cx}" cy="${cy}" r="${round(Math.hypot(cx, cy))}">`;
            close = '</radialGradient>';
        } else {
            // CSS runs the line through the centre, just long enough for the corners to get the end colours
            const radians = angle * Math.PI / 180;
            const dx = Math.sin(radians);
            const dy = -Math.cos(radians);
            const half = (Math.abs(width * dx) + Math.abs(height * dy)) / 2;
            open = `<linearGradient id="gradient" gradientUnits="userSpaceOnUse" ` +
                `x1="${round(cx - dx * half)}" y1="${round(cy - dy * half)}" x2="${round(cx + dx * half)}" y2="${round(cy + dy * half)}">`;
            close = '</linearGradient>';
        }
        return [
            `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`,
            '  <defs>',
            `    ${open}`,
            stops,
            `    ${close}`,
            '  </defs>',
            '  <rect width="100%" height="100%" fill="url(#gradient)"/>',
            '</svg>',
        ].join('\n');
    },

    json: ({ colors, type, angle, interpolation }) =>
        JSON.stringify(type === 'radial' ? { type, interpolation, colors } : { type, angle, interpolation, colors }, null, 2),

    hex: ({ colors }) => colors.join(', '),
};

document.addEventListener('DOMContentLoaded', () => {
    const copyBtn = document.getElementById('copy');
    const cssCodeArea = document.getElementById('css-code-area');
    const formatSelect = document.getElementById('export-format');
    if (!copyBtn || !cssCodeArea) return;

    const FORMAT_KEY = 'exportFormat';
    const originalText = copyBtn.textContent;
    const svgOption = formatSelect && formatSelect.querySelector('option[value="svg"]');
    let preferredFormat = formatSelect ? formatSelect.value : 'css';

    // Remember the picked format for next time (only a convenience, so storage errors are ignored)
    if (formatSelect) {
        try {
            const saved = localStorage.getItem(FORMAT_KEY);
            if (saved && EXPORT_FORMATS[saved]) preferredFormat = formatSelect.value = saved;
        } catch (err) { /* storage unavailable */ }
    }

    function currentCode() {
        const format = formatSelect && EXPORT_FORMATS[formatSelect.value] ? formatSelect.value : 'css';
        return EXPORT_FORMATS[format](currentGradient());
    }

    function refreshCodeArea() {
        // SVG can't draw a conic gradient: offer CSS meanwhile, and go back to SVG when the type allows it again
        if (svgOption) {
            const conic = currentGradient().type === 'conic';
            svgOption.disabled = conic;
            svgOption.textContent = conic ? 'SVG (no conic)' : 'SVG';
            formatSelect.value = conic && preferredFormat === 'svg' ? 'css' : preferredFormat;
        }
        cssCodeArea.value = currentCode();
    }

    refreshCodeArea();
    document.addEventListener('gradientchange', refreshCodeArea);
    if (formatSelect) {
        formatSelect.addEventListener('change', () => {
            preferredFormat = formatSelect.value;
            try { localStorage.setItem(FORMAT_KEY, formatSelect.value); } catch (err) { /* storage unavailable */ }
            refreshCodeArea();
        });
    }

    function showCopied(text) {
        copyBtn.textContent = text;
        setTimeout(() => {
            copyBtn.textContent = originalText;
        }, 1500);
    }

    copyBtn.addEventListener('click', async () => {
        const code = currentCode();
        const label = formatSelect ? formatSelect.selectedOptions[0].textContent : 'CSS';

        try {
            await navigator.clipboard.writeText(code);
            showCopied(`Copied ${label}!`);
        } catch (err) {
            // Fallback for browsers or non-HTTPS pages without the Clipboard API
            const temp = document.createElement('textarea');
            temp.value = code;
            temp.style.position = 'fixed';
            temp.style.opacity = '0';
            document.body.appendChild(temp);
            temp.select();
            const ok = document.execCommand('copy');
            document.body.removeChild(temp);
            showCopied(ok ? `Copied ${label}!` : 'Copy failed');
        }
    });
});

// Keep each hex label readable: dark text on light colors, light text on dark ones
document.addEventListener('DOMContentLoaded', () => {
    const LIGHT_TEXT = '#f3f2f2';
    const DARK_TEXT = '#1a1a1a';

    // WCAG relative luminance of a "#rrggbb" color
    function luminance(hex) {
        const channels = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255);
        const [r, g, b] = channels.map(c => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    }

    // Pick whichever text color gives the higher contrast ratio
    function readableTextColor(hex) {
        const bg = luminance(hex);
        const contrastWithLight = (luminance(LIGHT_TEXT) + 0.05) / (bg + 0.05);
        const contrastWithDark = (bg + 0.05) / (luminance(DARK_TEXT) + 0.05);
        return contrastWithDark > contrastWithLight ? DARK_TEXT : LIGHT_TEXT;
    }

    document.querySelectorAll('.color-swatch').forEach(swatch => {
        const input = swatch.closest('.color-field').querySelector('input[type="color"]');
        const label = swatch.querySelector('.color-value-text');
        if (!input || !label) return;

        const lockBtn = swatch.querySelector('.lock-toggle');

        function updateLabel() {
            label.textContent = input.value;
            label.style.color = readableTextColor(input.value);
            if (lockBtn) lockBtn.style.color = label.style.color;
        }

        updateLabel();
        input.addEventListener('input', updateLabel);
    });
});

// Briefly show "Saved!" on the Save Palette button after a successful save
document.addEventListener('DOMContentLoaded', () => {
    const saveBtn = document.getElementById('save-palette-btn');
    if (!saveBtn || !saveBtn.dataset.saved) return;

    const originalText = saveBtn.textContent;
    saveBtn.textContent = 'Saved!';
    setTimeout(() => {
        saveBtn.textContent = originalText;
    }, 1500);
});

// Lock colours: locked slots keep their colour when randomizing (Random Colors button, Space, long press)
document.addEventListener('DOMContentLoaded', () => {
    const lockInput = document.getElementById('lock-input');
    const lockButtons = document.querySelectorAll('.lock-toggle');
    if (!lockInput || !lockButtons.length) return;

    function lockedSlots() {
        return [...lockButtons]
            .filter(btn => btn.getAttribute('aria-pressed') === 'true')
            .map(btn => btn.dataset.slot);
    }

    function colorInput(slot) {
        return document.querySelector(`.color-input-form input[name="color${slot}"]`);
    }

    // Keep the lock in the form and the address bar, so Update Gradient and reloads remember it
    function syncLockState() {
        const slots = lockedSlots();
        lockInput.value = slots.join(',');
        lockInput.disabled = slots.length === 0;

        const url = new URL(window.location.href);
        if (slots.length) {
            url.searchParams.set('lock', slots.join(','));
            slots.forEach(slot => url.searchParams.set(`color${slot}`, colorInput(slot).value));
        } else {
            url.searchParams.delete('lock');
        }
        history.replaceState(null, '', url);
    }

    lockButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const locked = btn.getAttribute('aria-pressed') === 'true';
            btn.setAttribute('aria-pressed', String(!locked));
            syncLockState();
            btn.blur(); // so Space randomizes instead of toggling the lock again
        });
    });

    // A colour picked after locking should be the one that stays
    document.querySelectorAll('.color-input-form input[type="color"]').forEach(input => {
        input.addEventListener('change', () => {
            if (lockedSlots().length) syncLockState();
        });
    });

    lockInput.disabled = lockedSlots().length === 0;

    // Send the locked slots and their colours with the Random Colors request
    const randomForm = document.getElementById('random-color-form');
    if (!randomForm) return;

    randomForm.addEventListener('submit', () => {
        randomForm.querySelectorAll('.lock-field').forEach(el => el.remove());
        const slots = lockedSlots();
        if (!slots.length) return;

        const fields = { lock: slots.join(',') };
        slots.forEach(slot => { fields[`color${slot}`] = colorInput(slot).value; });

        Object.entries(fields).forEach(([name, value]) => {
            const hidden = document.createElement('input');
            hidden.type = 'hidden';
            hidden.className = 'lock-field';
            hidden.name = name;
            hidden.value = value;
            randomForm.appendChild(hidden);
        });
    });
});

// Colour count picker: picking 2–6 reloads with the current colours blended or sampled to that many
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.count-picker input[name="count"]').forEach(radio => {
        radio.addEventListener('change', () => {
            radio.form.requestSubmit();
        });
    });
});

// Gradient type and angle: the preview, code and links follow the controls as they change, without a reload
document.addEventListener('DOMContentLoaded', () => {
    const box = document.querySelector('.gradient-box');
    const angleInput = document.getElementById('angle-input');
    if (!box || !angleInput) return;

    const angleControl = document.querySelector('.angle-control');
    const angleLabel = document.getElementById('angle-label');
    const angleValue = document.getElementById('angle-value');

    // Same as style_params in forms.py: defaults are left out of URLs
    function setStyleParams(params, { type, angle, interpolation }) {
        if (type === 'linear') params.delete('type'); else params.set('type', type);
        if (angle === 0) params.delete('angle'); else params.set('angle', String(angle));
        if (interpolation === 'srgb') params.delete('interpolation'); else params.set('interpolation', interpolation);
    }

    function update() {
        const gradient = currentGradient();
        box.style.background = gradientCss(gradient);

        angleValue.textContent = `${gradient.angle}°`;
        angleLabel.textContent = gradient.type === 'conic' ? 'Gradient Start Angle:' : 'Gradient Angle:';
        angleControl.hidden = gradient.type === 'radial';

        // Random Colors, Random Saved Palettes and Save Palette send the style along
        document.querySelectorAll('.style-field').forEach(field => {
            field.value = String(gradient[field.name]);
        });
        // Saved palette and page links keep it too
        document.querySelectorAll('a.keeps-style').forEach(link => {
            const url = new URL(link.href);
            setStyleParams(url.searchParams, gradient);
            link.href = url.href;
        });
        // And so does a reload
        const url = new URL(window.location.href);
        setStyleParams(url.searchParams, gradient);
        history.replaceState(null, '', url);

        document.dispatchEvent(new CustomEvent('gradientchange'));
    }

    angleInput.addEventListener('input', update);
    document.querySelectorAll('.type-picker input[name="type"], .interpolation-picker input[name="interpolation"]').forEach(radio => {
        radio.addEventListener('change', update);
    });
    document.querySelectorAll('.color-input-form input[type="color"]').forEach(input => {
        input.addEventListener('input', update);
    });
});
