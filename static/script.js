document.addEventListener('DOMContentLoaded', () => {
    const paletteLinks = document.querySelectorAll('.saved-palettes ul li a');
    const palettes = [];
    paletteLinks.forEach(link => {
        if (link) {
            const idMatch = link.textContent.match(/#(\d+)/);
            const paletteId = idMatch ? parseInt(idMatch[1], 10) : null;
            const paletteUrl = link.href;
            palettes.push({
                id: paletteId,
                url: paletteUrl
            });
        }
    });

    console.log(palettes);
});

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
