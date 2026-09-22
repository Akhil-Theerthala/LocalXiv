// One reading layout value. Every hidden flag, body class and aria-current derives from it here and nowhere else.
export const HOME = Object.freeze({page: 'home', tab: 'overview', focused: false, contents: false});

export function applyView(document, view) {
  const $ = id => document.getElementById(id), reading = view.page === 'reading', focused = reading && view.focused;
  $('empty').hidden = view.page !== 'home';
  $('library-page').hidden = view.page !== 'library';
  $('workspace').hidden = !reading;
  $('reading-bar').hidden = !reading;
  $('reader-home').hidden = view.page === 'home';
  $('exit-focus').hidden = !focused;
  $('reading-companion').hidden = !view.contents;
  $('mobile-contents').hidden = !view.contents;
  document.body.classList.toggle('is-library', view.page === 'library');
  document.body.classList.toggle('is-reading', reading);
  document.body.classList.toggle('is-focused', focused);
  $('workspace').classList.toggle('without-contents', !view.contents);
  $('workspace').dataset.view = view.tab;
  for (const [id, page] of [['mobile-home', 'home'], ['mobile-library', 'library']]) {
    if (view.page === page) $(id).setAttribute('aria-current', 'page'); else $(id).removeAttribute('aria-current');
  }
}
