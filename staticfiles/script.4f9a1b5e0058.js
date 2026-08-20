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

// Mobile: tap anywhere = random colors, two-finger tap = random saved palettes
let touchStartTime = 0;

document.addEventListener('touchstart', (event) => {
    touchStartTime = Date.now();

    const tag = event.target.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || tag === 'A' || tag === 'BUTTON') return;

    if (event.touches.length === 2) {
        event.preventDefault();
        if (randomSavedBtn) randomSavedBtn.click();
    }
}, { passive: false });

document.addEventListener('touchend', (event) => {
    const tag = event.target.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || tag === 'A' || tag === 'BUTTON') return;

    // ignore long presses / accidental drags — treat only quick taps as trigger
    const duration = Date.now() - touchStartTime;
    if (duration > 300) return;

    // ignore if this was part of a multi-touch gesture (handled in touchstart)
    if (event.changedTouches.length > 1 || event.touches.length > 0) return;

    if (randomColorBtn) randomColorBtn.click();
}, { passive: true });

document.getElementById('copy').addEventListener('click', () => {
    const cssCode = document.getElementById('css-code-area');
    cssCode.style.display = 'block';
    cssCode.select();
    document.execCommand('copy');
    cssCode.style.display = 'none';
    // alert('CSS code copied to clipboard!');
});