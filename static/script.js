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

// The gradient as it is set on the page now: colours (color1 first), type and angle, including changes not yet applied
function currentGradient() {
    const colors = [...document.querySelectorAll('.color-input-form input[type="color"]')].map(input => input.value);
    const typeInput = document.querySelector('.type-picker input[name="type"]:checked');
    const angleInput = document.getElementById('angle-input');
    return {
        colors,
        type: typeInput ? typeInput.value : 'linear',
        angle: angleInput ? Number(angleInput.value) : 0,
    };
}

// Same CSS as build_gradient in colors.py: radial spreads from the centre, conic closes the circle on its first colour
function gradientCss({ colors, type, angle }) {
    const stops = colors.join(', ');
    if (type === 'radial') return `radial-gradient(circle, ${stops})`;
    if (type === 'conic') return `conic-gradient(from ${angle}deg, ${stops}, ${colors[0]})`;
    return `linear-gradient(${angle}deg, ${stops})`;
}

const round = value => Math.round(value * 100) / 100;

// Copy Code: copies the gradient as code, in the format picked next to the button
const EXPORT_FORMATS = {
    css: gradient => `background: ${gradientCss(gradient)};`,

    // Arbitrary-value class: works in Tailwind v3 and v4, with any number of colours
    tailwind: gradient => `bg-[${gradientCss(gradient).replace(/, /g, ',').replace(/ /g, '_')}]`,

    // SVG has no conic gradients, so this format is switched off for them
    svg: ({ colors, type, angle }) => {
        const width = 800;
        const height = 600;
        const cx = width / 2;
        const cy = height / 2;
        const stops = colors.map((color, i) =>
            `      <stop offset="${Math.round((i / (colors.length - 1)) * 100)}%" stop-color="${color}"/>`
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

    json: ({ colors, type, angle }) =>
        JSON.stringify(type === 'radial' ? { type, colors } : { type, angle, colors }, null, 2),

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
    function setStyleParams(params, { type, angle }) {
        if (type === 'linear') params.delete('type'); else params.set('type', type);
        if (angle === 0) params.delete('angle'); else params.set('angle', String(angle));
    }

    function update() {
        const gradient = currentGradient();
        box.style.background = gradientCss(gradient);

        angleValue.textContent = `${gradient.angle}°`;
        angleLabel.textContent = gradient.type === 'conic' ? 'Gradient Start Angle:' : 'Gradient Angle:';
        angleControl.hidden = gradient.type === 'radial';

        // Random Colors, Random Saved Palettes and Save Palette send the style along
        document.querySelectorAll('.style-field').forEach(field => {
            field.value = field.name === 'type' ? gradient.type : String(gradient.angle);
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
    document.querySelectorAll('.type-picker input[name="type"]').forEach(radio => {
        radio.addEventListener('change', update);
    });
    document.querySelectorAll('.color-input-form input[type="color"]').forEach(input => {
        input.addEventListener('input', update);
    });
});
