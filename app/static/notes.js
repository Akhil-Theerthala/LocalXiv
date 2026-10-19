// All Notes: the dialog with every Question card of the Paper. margin.js holds the cards, and app.js opens the
// dialog. As in margin.js, the top level only defines functions and adds listeners.
import {node} from './render.js';
import {goPassage, renderMath, selected, detail} from './reader.js';
import {marks, hasCard, paperId, reset, show} from './margin.js';
import {prose} from './chat.js';

// Every Question card of the Paper in reading order: the one Chat history of the Paper. A card opens at its words.
const order = card => {
  const index = detail?.paper?.passages?.findIndex(item => item.id === card.record.passage) ?? -1;
  return [index < 0 ? Infinity : index, card.record.created_at || 0];
};
export function showAllNotes() {
  // The cards are another Paper's until the margin mounts for this one, as on a PDF.
  if (selected !== paperId) reset();
  const dialog = node('dialog', undefined, 'all-notes'), head = node('div', undefined, 'dialog-heading'), title = node('h2', 'All Notes');
  const done = node('button', 'Done', 'btn-quiet');
  title.id = 'all-notes-title'; dialog.setAttribute('aria-labelledby', title.id);
  done.type = 'button'; done.onclick = () => dialog.close();
  head.append(title, done);
  dialog.append(head);
  const list = [...marks.values()].filter(card => !card.draft && hasCard(card)).sort((a, b) => {
    const [x, y] = [order(a), order(b)];
    return x[0] - y[0] || x[1] - y[1];
  });
  dialog.append(node('p', list.length ? 'Every Question card of this Paper, in reading order.' : 'This Paper has no Question cards. Select text in the Paper, then choose Ask.', 'help'));
  for (const card of list) {
    const row = node('section', undefined, 'an-row'), go = node('button', undefined, 'an-go');
    const section = detail?.paper?.passages?.find(item => item.id === card.record.passage)?.section || '';
    go.type = 'button';
    go.append(node('span', [section, card.record.kept ? 'Kept as a Note' : ''].filter(Boolean).join(' · '), 'an-where'),
      node('span', card.record.whole ? 'Question about the Paper' : `“${card.record.quote}”`, 'an-quote'));
    go.onclick = () => { dialog.close(); show(card); };
    row.append(go);
    for (const turn of card.record.turns) {
      row.append(node('p', turn.question, 'lx-q'));
      if (turn.answer.text) {
        const text = node('div', undefined, 'prose lx-answer');
        // A preview would open under the modal dialog, so an earlier-version citation opens its card instead.
        prose(text, turn.answer.text, turn.answer.cites || [], renderMath, href => { dialog.close(); goPassage(href); },
          () => { dialog.close(); show(card); });
        row.append(text);
      }
      if (turn.answer.stopped) row.append(node('p', 'Stopped.', 'lx-meta'));
      if (turn.answer.error) row.append(node('p', turn.answer.error, 'lx-error'));
    }
    dialog.append(row);
  }
  dialog.onclose = () => dialog.remove();
  document.body.append(dialog); dialog.showModal();
}
