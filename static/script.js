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

document.addEventListener('DOMContentLoaded', () => {
    const copyButton = document.getElementById('copy-button');
    const cssCodeArea = document.getElementById('css-code-area');
    copyButton.addEventListener('click', () => {xtarea
      cssCodeArea.select();
      cssCodeArea.setSelectionRange(0, 99999);
      navigator.clipboard.writeText(cssCodeArea.value)
        .then(() => {
          copyButton.textContent = 'Copied!';
          setTimeout(() => {
            copyButton.textContent = 'Copy Code';
          }, 2000);
        })
        .catch(err => {
          console.error('Failed to copy text: ', err);
          document.execCommand('copy');
        });
    });
  });