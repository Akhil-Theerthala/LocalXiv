// Notes: the Note editor of a card or a Paper note, and All Notes, the dialog with every Note and Question card of the
// Paper. margin.js holds the cards, and app.js opens the dialog. As in margin.js, the top level only defines functions
// and adds listeners.
import {node} from './render.js';
import {api, paperAPI} from './app.js';
import {goPassage, renderMath, selected, detail} from './reader.js';
import {marks, hasCard, paperNote, paperId, lastColour, reset, show, select, schedule, remove, drop} from './margin.js';
import {prose, drawActions} from './chat.js';

// ---- The Note editor ----
// A textarea in the page document, so that the Native shell leaves ⌘⌫ and ⌘Z to it. It shows only during an edit,
// and a saved Note shows as text, so that Find finds its words. It saves at Save, when focus leaves it, and at flush;
// Escape keeps the Note as it was. `mark.note` holds the Note: in the margin card, or in All Notes for a Paper note.
export function editNote(mark) {
  mark.editor ||= noteEditor(mark);
  if (!paperNote(mark.record)) select(mark);
  drawNote(mark);
  mark.editor.querySelector('textarea').focus({preventScroll: true});
}
function noteEditor(mark) {
  const box = node('div', undefined, 'lx-editor'), field = node('textarea'), error = node('p', '', 'lx-error'), save = node('button', 'Save', 'btn-quiet');
  field.value = mark.record.note || ''; field.rows = 4; field.setAttribute('aria-label', 'Note');
  error.hidden = true; save.type = 'button';
  save.onclick = () => saveNote(mark);
  field.onkeydown = event => {
    if (event.key !== 'Escape') return;
    // The margin and an open dialog also close on Escape.
    event.preventDefault(); event.stopPropagation();
    closeNote(mark);
  };
  // Focus that goes to the Save button stays in the editor.
  box.addEventListener('focusout', event => { if (mark.editor === box && !box.contains(event.relatedTarget)) saveNote(mark); });
  box.append(field, error, save);
  return box;
}
// One save at a time: a blur and a flush can come together, and a new Paper note must be stored once. The Paper is
// the one at the call, because a Paper change saves the open editors first (margin.js reset).
function saveNote(mark, close = true) {
  const paper = paperId;
  return mark.saving = (mark.saving || Promise.resolve()).catch(() => {}).then(() => store(mark, close, paper));
}
// The server takes a Note of at most 10,000 characters, so a longer Note stays in the editor. At flush (`close`
// false) the editor stays open.
async function store(mark, close, paper) {
  const box = mark.editor, field = box?.querySelector('textarea'), error = box?.querySelector('.lx-error');
  if (!box) return;
  const text = field.value.trim(), length = [...text].length;
  const fail = message => { error.textContent = message; error.hidden = !message; };
  if (length > 10000) return fail(`A Note can have at most 10,000 characters. This Note has ${length.toLocaleString('en-US')}.`);
  fail('');
  if (!text && paperNote(mark.record)) return close && dropPaperNote(mark);
  if (text !== mark.record.note) {
    try {
      // A new Highlight takes its Note after the server stores it.
      if (mark.adding) await mark.adding;
      if (mark.unsaved) ({highlight: mark.record} = await api(`${paperAPI(paper)}/highlights/add`, {highlight: {...mark.record, note: text}}));
      else mark.record = {...mark.record, note: (await api(`${paperAPI(paper)}/highlights/update`, {updates: [{id: mark.id, note: text}]})).highlights[0].note};
      mark.unsaved = false;
    } catch (failure) { return fail(failure.message); }
  }
  // Text typed during the save keeps the editor open.
  if (close && mark.editor === box && field.value.trim() === text) closeNote(mark);
}
// Saves each open Note editor and keeps it open. The Native shell waits for this before it quits (reader.js).
export function flushNotes() { return Promise.all([...marks.values()].filter(mark => mark.editor).map(mark => saveNote(mark, false))); }
// A record that the server does not have (a new Paper note, or a Highlight whose add failed) goes. Focus in the
// editor goes back to the card, or to the Edit button of a Paper note, or to Add Paper Note when a new Paper note goes.
function closeNote(mark) {
  const had = mark.note?.contains(document.activeElement), add = mark.note?.closest('dialog')?.querySelector('.an-add');
  mark.editor = null;
  if (mark.unsaved) { mark.note.closest('.an-row')?.remove(); drop(mark); }
  else drawNote(mark);
  if (had) (mark.unsaved ? add : mark.element || mark.note.querySelector('button'))?.focus({preventScroll: true});
}
// A Paper note with no text goes: a new one was never stored, and Delete keeps a stored one for ⌘Z.
async function dropPaperNote(mark) {
  if (!mark.unsaved) await remove(mark);
  if (mark.unsaved || !marks.has(mark.id)) { mark.unsaved = true; closeNote(mark); }
}
export function drawNote(mark) {
  const box = mark.note;
  if (!box) return;
  if (mark.editor) { if (box.firstChild !== mark.editor) box.replaceChildren(mark.editor); }
  else {
    const parts = mark.record.note ? [node('p', mark.record.note, 'lx-note-text')] : [];
    // A Paper note has no card, so its Edit button is beside its text.
    if (paperNote(mark.record)) {
      const edit = node('button', 'Edit', 'btn-quiet');
      edit.type = 'button'; edit.setAttribute('aria-label', 'Edit the Paper note'); edit.onclick = () => editNote(mark);
      parts.push(edit);
    }
    box.replaceChildren(...parts);
  }
  if (mark.element) { drawActions(mark); schedule(); }
}

// ---- All Notes ----
// The Paper notes, then every Note and Question card of the Paper in reading order: the one Chat history of the
// Paper. A card opens at its words.
const order = card => {
  const index = detail?.paper?.passages?.findIndex(item => item.id === card.record.passage) ?? -1;
  return [index < 0 ? Infinity : index, card.record.created_at || 0];
};
export function showAllNotes() {
  // The cards are another Paper's until the margin mounts for this one, as on a PDF.
  if (selected !== paperId) reset();
  const dialog = node('dialog', undefined, 'all-notes'), head = node('div', undefined, 'dialog-heading'), title = node('h2', 'All Notes');
  const buttons = node('div', undefined, 'an-buttons'), add = node('button', 'Add Paper Note', 'btn-quiet an-add'), done = node('button', 'Done', 'btn-quiet');
  const papers = node('div');
  title.id = 'all-notes-title'; dialog.setAttribute('aria-labelledby', title.id);
  add.type = 'button'; add.onclick = () => addPaperNote(papers);
  done.type = 'button'; done.onclick = () => dialog.close();
  buttons.append(add, done);
  head.append(title, buttons);
  dialog.append(head);
  const notes = [...marks.values()].filter(mark => paperNote(mark.record) && !mark.unsaved);
  const list = [...marks.values()].filter(card => !card.draft && !paperNote(card.record) && hasCard(card)).sort((a, b) => {
    const [x, y] = [order(a), order(b)];
    return x[0] - y[0] || x[1] - y[1];
  });
  dialog.append(node('p', list.length || notes.length ? 'Every Note and Question card of this Paper. The Paper notes come first, then the rest in reading order.'
    : 'This Paper has no Notes. Select text in the Paper, then choose Note or Ask. Or add a Paper note.', 'help'), papers);
  for (const mark of notes) papers.append(paperNoteRow(mark));
  for (const card of list) {
    const row = node('section', undefined, 'an-row'), go = node('button', undefined, 'an-go');
    const section = detail?.paper?.passages?.find(item => item.id === card.record.passage)?.section || '';
    go.type = 'button';
    go.append(node('span', [section, card.record.kept ? 'Kept as a Note' : ''].filter(Boolean).join(' · '), 'an-where'),
      node('span', card.record.whole ? 'Question about the Paper' : `“${card.record.quote}”`, 'an-quote'));
    go.onclick = () => { dialog.close(); show(card); };
    row.append(go);
    if (card.record.note) row.append(node('p', card.record.note, 'lx-note-text'));
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
function paperNoteRow(mark) {
  const row = node('section', undefined, 'an-row');
  mark.note = node('div');
  row.append(node('span', 'Paper note', 'an-where'), mark.note);
  drawNote(mark);
  return row;
}
// A new Paper note is stored at its first Save with text.
function addPaperNote(box) {
  const id = crypto.randomUUID().replaceAll('-', '');
  const mark = {id, unsaved: true, record: {id, colour: lastColour, kept: true, whole: false, passage: null, href: null, quote: '', note: '', turns: []}};
  marks.set(id, mark);
  box.append(paperNoteRow(mark));
  editNote(mark);
}
