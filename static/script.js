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

// Copy the generated CSS code to the clipboard
document.addEventListener('DOMContentLoaded', () => {
    const copyBtn = document.getElementById('copy');
    const cssCodeArea = document.getElementById('css-code-area');
    if (!copyBtn || !cssCodeArea) return;

    const originalText = copyBtn.textContent;

    function showCopied(text) {
        copyBtn.textContent = text;
        setTimeout(() => {
            copyBtn.textContent = originalText;
        }, 1500);
    }

    copyBtn.addEventListener('click', async () => {
        // Copy only the hex codes, e.g. "#1a2b3c, #4d5e6f"
        const hexCodes = cssCodeArea.value.match(/#[0-9a-fA-F]{3,8}\b/g);
        if (!hexCodes) return;
        const code = hexCodes.join(', ');

        try {
            await navigator.clipboard.writeText(code);
            showCopied('Copied!');
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
            showCopied(ok ? 'Copied!' : 'Copy failed');
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
