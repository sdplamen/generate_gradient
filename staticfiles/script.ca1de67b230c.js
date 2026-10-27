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

    const tag = document.activeElement.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

    event.preventDefault();

    if (event.shiftKey) {
      document.getElementById('random-saved-btn').click();
    } else {
      document.getElementById('random-color-btn').click();
    }
  });