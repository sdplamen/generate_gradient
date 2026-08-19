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

document.getElementById('copy').addEventListener('click', () => {
    const cssCode = document.getElementById('css-code-area');
    cssCode.style.display = 'block';
    cssCode.select();
    document.execCommand('copy');
    cssCode.style.display = 'none';
    // alert('CSS code copied to clipboard!');
});

document.addEventListener('keydown', (event) => {
    if (event.code !== 'Space') return;

    // Don't hijack spacebar if the user is typing in an input/textarea,
    // or if focus is already on another button (avoid double-triggering)
    const tag = document.activeElement.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

    event.preventDefault(); // stop page scroll

    // Default spacebar action = Random Colors
    document.getElementById('random-color-btn').click();
  });