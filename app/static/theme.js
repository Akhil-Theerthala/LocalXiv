// A classic script in <head>: it runs before the body parses, so the first frame has the reader's theme.
// app.js applies the full Reading preferences later, from the server settings.
try {
  const theme = JSON.parse(localStorage.getItem('localxiv-reading'))?.theme;
  document.documentElement.dataset.theme = ['light', 'sepia', 'dark'].includes(theme) ? theme
    : matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
} catch {}
