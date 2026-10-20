// Notes: the Note editor of a card or a Paper note, and All Notes, the dialog with every record of the Paper, its
// search, and its arrangements. margin.js holds the cards, and app.js opens the dialog. As in margin.js, the top level
// only defines functions and adds listeners.
import {node} from './render.js';
import {api, paperAPI, stored, store as keep, state} from './app.js';
import {goPassage, renderMath, selected, detail, openPaper} from './reader.js';
import {COLOURS, marks, paperNote, paperId, lastColour, reset, show, select, schedule, remove, drop, placeAgain, notFound, syncUndo, recordLabel, recolour} from './margin.js';
import {prose, drawActions} from './chat.js';
import {findOffset} from './onetext.js';

// ---- The Note editor ----
// A textarea in the page document, so that the Native shell leaves ⌘⌫ and ⌘Z to it. It shows only during an edit,
// and a saved Note shows as text, so that Find finds its words. It saves at Save, when focus leaves it, and at flush;
// Escape keeps the Note as it was. `mark.note` holds the Note: the margin card's box, or during an edit in All Notes
// the row's box, while `mark.home` keeps the card's box.
export function editNote(mark) {
  mark.editor ||= noteEditor(mark);
  select(mark);
  drawNote(mark);
  mark.editor.querySelector('textarea').focus({preventScroll: true});
}
function noteEditor(mark) {
  const box = node('div', undefined, 'lx-editor'), field = node('textarea'), error = node('p', '', 'lx-error'), save = node('button', 'Save', 'btn-quiet');
  field.value = mark.record.note || ''; field.rows = 4; field.setAttribute('aria-label', 'Note');
  error.id = `lx-note-error-${mark.id}`; error.setAttribute('role', 'alert'); field.setAttribute('aria-describedby', error.id);
  error.hidden = true; save.type = 'button';
  save.onclick = () => saveNote(mark);
  field.onkeydown = event => {
    if (event.key !== 'Escape') return;
    // The margin and an open dialog also close on Escape.
    event.preventDefault(); event.stopPropagation();
    closeNote(mark);
  };
  // Focus that goes to the Save button stays in the editor. In All Notes the editor stays open after the save, because
  // a shorter row would move the button that the reader clicks.
  box.addEventListener('focusout', event => { if (mark.editor === box && !box.contains(event.relatedTarget)) saveNote(mark, !('home' in mark)); });
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
// A record that the server does not have (a new Paper note, or a Highlight whose add failed) goes. An edit in All Notes
// ends in its row, and the card gets its box again. Focus in the editor goes back to the card, or to the row's Edit
// Note, or to Add Paper Note when a new Paper note goes. An edit that another edit ends changes only its row.
function closeNote(mark) {
  const had = mark.note?.contains(document.activeElement), row = mark.note?.closest('.an-row');
  const edit = row?.querySelector(`[data-key="${mark.id} edit"]`);
  mark.editor = null;
  if ('home' in mark) { if (!mark.unsaved) drawNote(mark); mark.note = mark.home; delete mark.home; }
  if (mark.unsaved) { row?.remove(); drop(mark); }
  // A Highlight that gets its first Note in All Notes has no card yet, and the layout builds it.
  else { drawNote(mark); schedule(); }
  if (edit) edit.textContent = mark.record.note ? 'Edit Note' : 'Add Note';
  if (!had) return;
  (mark.unsaved ? view?.dialog.querySelector('.an-add') : edit || mark.element)?.focus({preventScroll: true});
  drawAllNotes();
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
  else box.replaceChildren(...mark.record.note ? [node('p', mark.record.note, 'lx-note-text')] : []);
  if (mark.element) { drawActions(mark); schedule(); }
}

// ---- All Notes ----
// Every stored record of the Paper, so it is the one Chat history of the Paper, with search and four arrangements. The
// Paper notes come first, except in Groups. The margin always shows reading order. `view` is the open dialog:
// {dialog, list, search, arrange, status, arrangement, parts, renaming}, where `renaming` is the name field of a group.
const ARRANGEMENTS = {position: 'Position', colour: 'Colour', date: 'Date', groups: 'Groups'};
let view = null;
const groups = () => detail?.groups || [];
export function showAllNotes() {
  // The cards are another Paper's until the margin mounts for this one, as on a PDF.
  if (selected !== paperId) reset();
  const dialog = node('dialog', undefined, 'all-notes'), head = node('div', undefined, 'dialog-heading'), title = node('h2', 'All Notes');
  const buttons = node('div', undefined, 'an-buttons'), add = node('button', 'Add Paper Note', 'btn-quiet an-add'), done = node('button', 'Done', 'btn-quiet');
  const tools = node('div', undefined, 'an-tools'), search = node('input'), arrange = node('div', undefined, 'segs');
  const status = node('p'), list = node('div'), saved = `localxiv-arrangement-${paperId}`;
  title.id = 'all-notes-title'; dialog.setAttribute('aria-labelledby', title.id);
  add.type = 'button'; add.onclick = () => addPaperNote(null);
  done.type = 'button'; done.onclick = () => dialog.close();
  search.type = 'search'; search.placeholder = 'Search'; search.setAttribute('aria-label', 'Search the Notes'); search.oninput = () => drawAllNotes();
  arrange.setAttribute('role', 'group'); arrange.setAttribute('aria-label', 'Arrange');
  status.setAttribute('role', 'status');
  view = {dialog, list, search, arrange, status, arrangement: Object.hasOwn(ARRANGEMENTS, stored(saved)) ? stored(saved) : 'position', renaming: null};
  for (const [value, label] of Object.entries(ARRANGEMENTS)) {
    const button = node('button', label);
    button.type = 'button'; button.dataset.value = value;
    button.onclick = () => { view.arrangement = value; keep(saved, value); drawAllNotes(); };
    arrange.append(button);
  }
  buttons.append(add, done); head.append(title, buttons); tools.append(search, arrange);
  dialog.append(head, tools, status, list);
  // ⌘Z in the dialog restores a record that it deleted, in every view, so the Native shell's Undo follows the dialog.
  dialog.onclose = () => {
    view = null; dialog.remove(); syncUndo();
    // An edit that is open in a row goes back to its card and saves.
    for (const mark of marks.values()) if ('home' in mark) { mark.note = mark.home; delete mark.home; drawNote(mark); saveNote(mark); }
  };
  drawAllNotes();
  document.body.append(dialog); dialog.showModal(); syncUndo();
}
const say = (text, failed = false) => { if (view) Object.assign(view.status, {textContent: text, className: failed ? 'lx-error' : 'help'}); };

// Draws the list again, with `message` as the status. Focus in the list stays on the same control, or goes to the
// `fallback` control, or to Add Paper Note. An open editor or name field moves to its new row with its focus.
export function drawAllNotes(fallback = '', message = '') {
  if (!view) return;
  const {list, search, arrange, arrangement} = view, active = document.activeElement, was = list.contains(active);
  const {selectionStart, selectionEnd} = active || {};
  say(message);
  for (const button of arrange.children) button.setAttribute('aria-pressed', String(button.dataset.value === arrangement));
  const query = search.value.trim().toLowerCase();
  // A new Paper note shows while the reader writes it.
  const all = [...marks.values()].filter(mark => !mark.draft && (!mark.unsaved || 'home' in mark));
  const shown = mark => 'home' in mark || words(mark).includes(query);
  view.parts = arranged(all, arrangement);
  list.replaceChildren(node('p', all.length ? 'Every Highlight, Note, and Question card of this Paper.'
    : 'This Paper has no Highlights or Notes. Select text in the Paper, then choose a colour, Note, or Ask. Or add a Paper note.', 'help'));
  if (arrangement === 'groups') list.append(button('New Group', 'new-group', newGroup));
  for (const part of view.parts) {
    const items = part.items.filter(shown);
    if (!items.length && (query || part.group === null)) continue;
    const box = node('div', undefined, 'an-part');
    if (part.group !== undefined) { box.setAttribute('role', 'group'); box.setAttribute('aria-label', part.group?.name || 'In no group'); box.append(heading(part)); }
    items.forEach((mark, at) => box.append(row(mark, part, items, at)));
    list.append(box);
  }
  if (query && !list.querySelector('.an-row')) list.append(node('p', 'No Highlight or Note has these words.', 'help'));
  if (!was) return;
  if (active.isConnected) { active.focus({preventScroll: true}); if (selectionStart != null) active.setSelectionRange(selectionStart, selectionEnd); return; }
  const find = key => key && list.querySelector(`[data-key="${key}"]:not(:disabled)`);
  (find(active.dataset.key) || find(fallback) || view.dialog.querySelector('.an-add')).focus({preventScroll: true});
}
// The text that search looks in: the quote, the Note, and each question and answer.
const words = ({record}) => [record.quote, record.note, ...record.turns.flatMap(turn => [turn.question, turn.answer.text || ''])].join('\n').toLowerCase();
// Where a record's words start: the index of its passage, then the start of its words in the passage. A record outside
// a passage, and words that its passage does not have, come last.
function position(record) {
  const passages = detail?.paper?.passages || [], index = passages.findIndex(item => item.id === record.passage);
  const start = index < 0 ? -1 : record.whole ? 0 : findOffset(passages[index].text, record.match || record.head || record.quote, record.prefix, record.suffix);
  return [index < 0 ? Infinity : index, start < 0 ? Infinity : start];
}
const compare = (a, b) => { const at = a.findIndex((value, i) => value !== b[i]); return at < 0 ? 0 : a[at] < b[at] ? -1 : 1; };
// The records in parts: one part, or in Groups each group in order and then the records in no group. Date is oldest
// first. Inside a group, `order` comes first; a record with no order comes after, in reading order.
function arranged(all, arrangement) {
  const key = ({record}) => {
    const first = paperNote(record) ? 0 : 1, date = record.created_at ?? Infinity;
    if (arrangement === 'date') return [first, date];
    if (arrangement === 'colour') return [first, Object.keys(COLOURS).indexOf(record.colour), ...position(record), date];
    if (arrangement === 'groups') return [record.order ?? Infinity, first, ...position(record), date];
    return [first, ...position(record), date];
  };
  const keys = new Map(all.map(mark => [mark, key(mark)])), sorted = all.sort((a, b) => compare(keys.get(a), keys.get(b)));
  if (arrangement !== 'groups') return [{items: sorted}];
  const known = new Set(groups().map(group => group.id));
  return [...groups().map(group => ({group, items: sorted.filter(mark => mark.record.group === group.id)})),
    {group: null, items: sorted.filter(mark => !known.has(mark.record.group))}];
}
// A button that keeps its focus when the list draws again.
function button(label, key, action, className = 'btn-quiet') {
  const element = node('button', label, className);
  element.type = 'button'; element.dataset.key = key; element.onclick = action;
  return element;
}
// A row: the colour name, the section, and the quote (a button that opens the card), Not found, the Note, each question
// and answer, the buttons, and the colour picker. In Groups also the group picker, Move Up, and Move Down.
function row(mark, part, items, at) {
  const {record} = mark, {dialog} = view, item = node('section', undefined, 'an-row'), box = node('div'), actions = node('div', undefined, 'an-actions');
  const section = detail?.paper?.passages?.find(passage => passage.id === record.passage)?.section || record.section;
  const where = [COLOURS[record.colour], paperNote(record) ? 'Paper note' : section, record.kept && record.turns.length ? 'Kept as a Note' : ''].filter(Boolean).join(' · ');
  const lost = notFound(mark);
  item.dataset.id = mark.id; item.style.setProperty('--c', `var(--${record.colour})`);
  // The row names its buttons for a screen reader.
  item.setAttribute('role', 'group'); item.setAttribute('aria-label', paperNote(record) ? `${COLOURS[record.colour]} Paper note` : recordLabel(record));
  if (paperNote(record)) item.append(node('p', where, 'an-where'));
  else {
    const go = button('', `${mark.id} go`, () => { dialog.close(); show(mark); }, 'an-go');
    go.append(node('span', where, 'an-where'), node('span', record.whole ? 'Question about the Paper' : `“${record.quote}”`, 'an-quote'));
    item.append(go);
  }
  if (lost) item.append(node('p', 'Not found in this version', 'an-lost'));
  if ('home' in mark) { mark.note = box; drawNote(mark); }
  else if (record.note) box.append(node('p', record.note, 'lx-note-text'));
  item.append(box);
  for (const turn of record.turns) {
    item.append(node('p', turn.question, 'lx-q'));
    if (turn.answer.text) {
      const text = node('div', undefined, 'prose lx-answer');
      // A preview would open under the modal dialog, so an earlier-version citation opens its card instead.
      prose(text, turn.answer.text, turn.answer.cites || [], renderMath, href => { dialog.close(); goPassage(href); },
        () => { dialog.close(); show(mark); });
      item.append(text);
    }
    if (turn.answer.stopped) item.append(node('p', 'Stopped.', 'lx-meta'));
    if (turn.answer.error) item.append(node('p', turn.answer.error, 'lx-error'));
  }
  actions.append(button(record.note ? 'Edit Note' : 'Add Note', `${mark.id} edit`, () => editHere(mark)));
  // The card at a mark opens only at a click on its words, so the colour picker here is how a keyboard changes a colour.
  if (!mark.unsaved) {
    const colour = node('select');
    colour.dataset.key = `${mark.id} colour`; colour.setAttribute('aria-label', 'Colour');
    colour.append(...Object.entries(COLOURS).map(([value, name]) => new Option(name, value)));
    colour.value = record.colour;
    colour.onchange = async () => {
      await recolour(mark, colour.value);
      drawAllNotes('', mark.record.colour === colour.value ? '' : 'LocalXiv did not change the colour. Try again.');
    };
    actions.append(colour);
  }
  // Place Again waits in the Paper view for the next selection.
  if (lost) actions.append(button('Place Again', `${mark.id} place`, () => { dialog.close(); show(mark); placeAgain(mark); }));
  actions.append(button('Delete', `${mark.id} delete`, () => deleteRow(mark, item)));
  if (part.group !== undefined && !mark.unsaved) {
    const picker = node('select'), up = button('Move Up', `${mark.id} up`, () => step(mark, part, items[at - 1], 0, `${mark.id} down`));
    const down = button('Move Down', `${mark.id} down`, () => step(mark, part, items[at + 1], 1, `${mark.id} up`));
    picker.dataset.key = `${mark.id} group`; picker.setAttribute('aria-label', 'Group');
    picker.append(new Option('In no group', ''), ...groups().map(group => new Option(group.name, group.id)));
    picker.value = part.group?.id || '';
    picker.onchange = () => regroup(mark, picker.value || null);
    up.disabled = at === 0; down.disabled = at === items.length - 1;
    actions.append(picker, up, down);
  }
  item.append(actions);
  return item;
}
// An edit in All Notes: the row's box holds the editor until the edit ends (closeNote). An edit in another row ends.
function editHere(mark) {
  for (const other of marks.values()) if (other !== mark && 'home' in other) saveNote(other);
  if (!('home' in mark)) mark.home = mark.note;
  mark.editor ||= noteEditor(mark);
  drawAllNotes();
  mark.editor.querySelector('textarea').focus({preventScroll: true});
}
// A new Paper note, at the end of `group` when it has one, is stored at its first Save with text.
function addPaperNote(group) {
  const id = crypto.randomUUID().replaceAll('-', ''), orders = [...marks.values()].filter(mark => group && mark.record.group === group).map(mark => mark.record.order ?? -1);
  const mark = {id, unsaved: true, record: {id, colour: lastColour, kept: true, whole: false, passage: null, href: null, quote: '', note: '', turns: [],
    group, order: group ? Math.max(-1, ...orders) + 1 : null}};
  marks.set(id, mark);
  editHere(mark);
}
// Delete pushes the same undo entry as Delete in the margin, so ⌘Z brings the record back. Focus goes to the next row.
async function deleteRow(mark, item) {
  const rows = [...view.list.querySelectorAll('.an-row')], at = rows.indexOf(item), next = rows[at + 1] || rows[at - 1];
  await remove(mark);
  if (marks.has(mark.id)) return say('LocalXiv did not delete it. Try again.', true);
  drawAllNotes(next ? `${next.dataset.id} edit` : '', 'Deleted. Press ⌘Z to undo.');
}

// ---- Note groups ----
// Each change is one update or one groups call. A record moves in its group by `order`; the group numbers its records
// again. A new group, a move, and a rename send the whole ordered list of groups.
async function change(updates, fallback) {
  try {
    const {highlights} = await api(`${paperAPI(paperId)}/highlights/update`, {updates});
    for (const {id, group, order} of highlights) { const mark = marks.get(id); if (mark) mark.record = {...mark.record, group, order}; }
  } catch (error) { say(error.message, true); return false; }
  drawAllNotes(fallback);
  return true;
}
// Puts the record before (0) or after (1) the shown record next to it. The search can hide records between them.
function step(mark, part, neighbour, after, fallback) {
  const list = part.items.filter(item => item !== mark);
  list.splice(list.indexOf(neighbour) + after, 0, mark);
  change(list.flatMap((item, order) => item.unsaved || item.record.order === order ? [] : [{id: item.id, order}]), fallback);
}
// The record goes to the end of `group` (null: no group).
function regroup(mark, group) {
  const items = view.parts.find(part => (part.group?.id ?? null) === group).items.filter(item => item !== mark && !item.unsaved);
  change([...items.flatMap((item, order) => item.record.order === order ? [] : [{id: item.id, order}]), {id: mark.id, group, order: items.length}]);
}
// The groups calls run one at a time, and each edits the list that the server sent last, so that a rename that a
// blur saves and a click that follows it both stay.
let groupsCall = Promise.resolve(true);
function saveGroups(edit, fallback) {
  return groupsCall = groupsCall.then(async () => {
    try { ({groups: detail.groups} = await api(`${paperAPI(paperId)}/groups`, {groups: edit(groups())})); }
    catch (error) { say(error.message, true); return false; }
    drawAllNotes(fallback);
    return true;
  });
}
// The ID is new and unique, and the reader names the group at once.
async function newGroup() {
  const group = {id: crypto.randomUUID().replaceAll('-', ''), name: `Group ${groups().length + 1}`};
  if (await saveGroups(list => [...list, group])) rename(group);
}
// The records of a deleted group go to no group, in reading order: one update, then one groups call.
async function deleteGroup(group, fallback) {
  const ids = [...marks.values()].filter(mark => mark.record.group === group.id && !mark.unsaved).map(mark => mark.id);
  if (ids.length && !await change(ids.map(id => ({id, group: null, order: null})))) return;
  saveGroups(list => list.filter(each => each.id !== group.id), fallback);
}
const move = (id, by) => list => {
  const at = list.findIndex(each => each.id === id), copy = [...list];
  if (copy[at + by]) [copy[at], copy[at + by]] = [copy[at + by], copy[at]];
  return copy;
};
// A group's heading: its name, or the field that renames it, and its buttons. "In no group" has only its name.
function heading({group}) {
  const box = node('div', undefined, 'an-group');
  if (!group) { box.append(node('h3', 'In no group')); return box; }
  const all = groups(), at = all.indexOf(group), near = all[at + 1] || all[at - 1];
  box.append(view.renaming?.dataset.key === `${group.id} name` ? view.renaming : node('h3', group.name));
  const up = button('Move Up', `${group.id} up`, () => saveGroups(move(group.id, -1), `${group.id} down`));
  const down = button('Move Down', `${group.id} down`, () => saveGroups(move(group.id, 1), `${group.id} up`));
  up.disabled = at === 0; down.disabled = at === all.length - 1;
  box.append(button('Rename', `${group.id} rename`, () => rename(group)), up, down,
    button('Add Written Note', `${group.id} write`, () => addPaperNote(group.id)),
    button('Delete Group', `${group.id} delete`, () => deleteGroup(group, near ? `${near.id} rename` : 'new-group')));
  return box;
}
// The name field: Return or a blur saves a name of 1 to 80 characters, and Escape keeps the name as it was. The field
// stays when the list draws again.
function rename(group) {
  if (!view) return;
  const field = node('input');
  field.value = group.name; field.maxLength = 80; field.dataset.key = `${group.id} name`; field.setAttribute('aria-label', 'Group name');
  const end = save => {
    if (view?.renaming !== field) return;
    view.renaming = null;
    const name = field.value.trim(), changed = save && name && name !== group.name, focused = document.activeElement === field;
    // The heading changes in its place, so that a click that ends the edit reaches its button.
    field.replaceWith(node('h3', changed ? name : group.name));
    if (focused) view.list.querySelector(`[data-key="${group.id} rename"]`)?.focus({preventScroll: true});
    if (changed) saveGroups(list => list.map(each => each.id === group.id ? {...each, name} : each));
  };
  field.onkeydown = event => {
    if (event.key === 'Enter') { event.preventDefault(); end(true); }
    // The dialog also closes on Escape.
    else if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); end(false); }
  };
  // A field that the list moves to its new heading also loses focus.
  field.onblur = () => { if (field.isConnected) end(true); };
  view.renaming = field;
  drawAllNotes();
  field.focus({preventScroll: true}); field.select();
}

// ---- The Notes page: every Highlight, Note, and Question card of the library, by Paper ----
// The page reads the backup route, which also lists the records of Papers that left the library. Those stay out, as
// the sidebar count leaves them out. Editing stays in the Paper: a row opens the Paper at the card.
const TAG = /#[\p{L}\p{N}_-]+/gu;
const tags = record => record.note.match(TAG) || [];
const page = {records: [], query: '', off: new Set(), on: new Set()};
export async function drawNotesPage() {
  const status = document.getElementById('notes-status');
  status.textContent = 'Loading…';
  try { page.records = (await api('/files/library/notes.json')).highlights; }
  catch (error) { status.textContent = error.message; return; }
  drawNotesList();
}
// A redraw makes new buttons, so the focus moves to the new button with the same label.
function drawToggles(box, keys, label, pressed, toggle) {
  const focused = box.contains(document.activeElement) ? document.activeElement.textContent : null;
  box.replaceChildren(...keys.map(key => {
    const button = node('button', label(key));
    button.type = 'button'; button.setAttribute('aria-pressed', String(pressed(key))); button.onclick = () => toggle(key);
    return button;
  }));
  if (focused !== null) [...box.children].find(button => button.textContent === focused)?.focus();
}
// Inside a Paper: a Paper note first, then reading order (the passage IDs are positions), then the oldest first.
const pageKey = record => [paperNote(record) ? 0 : 1, record.passage || '\uffff', record.created_at ?? Infinity];
function drawNotesList() {
  const $ = id => document.getElementById(id), {records, off, on} = page, query = page.query.trim().toLowerCase();
  const titles = new Map(state.papers.map(paper => [paper.id, paper.title || paper.id]));
  const known = [...new Set(records.flatMap(tags))].sort();
  for (const tag of on) if (!known.includes(tag)) on.delete(tag);
  drawToggles($('notes-colours'), Object.keys(COLOURS), key => COLOURS[key], key => !off.has(key), key => { off.has(key) ? off.delete(key) : off.add(key); drawNotesList(); });
  drawToggles($('notes-tags'), known, tag => tag, tag => on.has(tag), tag => { on.has(tag) ? on.delete(tag) : on.add(tag); drawNotesList(); });
  $('notes-tags').hidden = !known.length;
  const shown = record => !off.has(record.colour) && [...on].every(tag => tags(record).includes(tag))
    && (!query || [record.quote, record.note, titles.get(record.paper), ...record.turns.flatMap(turn => [turn.question, turn.answer.text || ''])].join('\n').toLowerCase().includes(query));
  const list = $('notes-list');
  let count = 0;
  list.replaceChildren();
  for (const paper of state.papers) {
    const rows = records.filter(record => record.paper === paper.id && shown(record)).sort((a, b) => compare(pageKey(a), pageKey(b)));
    if (!rows.length) continue;
    count += rows.length;
    const box = node('div', undefined, 'an-part'), head = node('div', undefined, 'an-paper'), open = node('button', 'Open', 'btn-quiet');
    box.setAttribute('role', 'group'); box.setAttribute('aria-label', titles.get(paper.id));
    open.type = 'button'; open.onclick = () => openPaper(paper.id);
    head.append(node('h2', titles.get(paper.id)), open);
    box.append(head, ...rows.map(record => pageRow(record, paper.id)));
    list.append(box);
  }
  $('notes-status').textContent = !records.some(record => titles.has(record.paper)) ? 'No Notes yet. Select words in a Paper and choose a colour.'
    : count ? '' : query ? 'No Highlight or Note has these words.' : 'No Highlight or Note has this colour and these tags.';
}
// A row: the colour name and the section, the quote (a button that opens the Paper at the card), Not found, the Note,
// and the first line of each question.
function pageRow(record, paper) {
  const item = node('section', undefined, 'an-row'), go = node('button', undefined, 'an-go');
  const where = [COLOURS[record.colour], paperNote(record) ? 'Paper note' : record.section].filter(Boolean).join(' · ');
  item.style.setProperty('--c', `var(--${record.colour})`);
  item.setAttribute('role', 'group'); item.setAttribute('aria-label', paperNote(record) ? `${COLOURS[record.colour]} Paper note` : recordLabel(record));
  go.type = 'button'; go.dataset.id = record.id; go.onclick = () => openRecord(paper, record);
  go.append(node('span', where, 'an-where'));
  if (!paperNote(record)) go.append(node('span', record.whole ? 'Question about the Paper' : `“${record.quote}”`, 'an-quote'));
  item.append(go);
  if (record.found === 'not-found') item.append(node('p', 'Not found in this version', 'an-lost'));
  if (record.note) item.append(node('p', record.note, 'lx-note-text'));
  for (const turn of record.turns) item.append(node('p', turn.question.split('\n')[0], 'lx-q'));
  return item;
}
// Opens the Paper, then its card at the record's words, as a click on a marker does. A Paper note has no card, so All
// Notes opens.
async function openRecord(paper, record) {
  await openPaper(paper);
  if (selected !== paper) return;
  if (selected !== paperId) reset();
  const card = marks.get(record.id);
  if (!card) return;
  if (paperNote(record)) showAllNotes(); else show(card);
}
document.getElementById('notes-search').oninput = event => { page.query = event.target.value; drawNotesList(); };
