// A classic script in <head>: it runs before the body parses, so the first frame has the reader's theme and width.
// app.js applies the full Reading preferences later, from the server settings.
try {
  const theme = JSON.parse(localStorage.getItem('localxiv-reading'))?.theme;
  document.documentElement.dataset.theme = ['light', 'sepia', 'dark'].includes(theme) ? theme
    : matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
} catch {}
// Below a 1000 px window the sidebar is an overlay, as in the Native shell. A media query cannot say this, because
// WebKit leaves a classic scroll bar out of its width, so a 1000 px window would match (max-width: 999px).
{
  const narrow = () => document.documentElement.classList.toggle('narrow', innerWidth < 1000);
  narrow();
  addEventListener('resize', narrow);
}
