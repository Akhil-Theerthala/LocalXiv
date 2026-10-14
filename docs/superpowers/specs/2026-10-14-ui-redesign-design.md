# UI redesign: a native Mac reading app for papers

Date: 2026-10-14. Branch `ui-redesign`. Domain nouns are `CONTEXT.md`'s, including the new terms that this change adds: **Reading state**, **Reading position**, **Reference preview**, **Split view**, **Chrome state**, and **Native shell**.

The user decided four things on 2026-10-14 from three prototypes and a question round:

- The **Native** visual direction: a first-party macOS look with SF Pro, neutral greys, and a green accent.
- A **Native shell**: AppKit draws the window structure (sidebar, toolbar, menus, and a Settings window), and the WKWebView draws content.
- The **core** scope listed under "What a reader gets". Highlights, notes, Collections, and Tags are later work.
- Four specific changes: `allow-scripts` in the paper frame, Blog citations on screen, no phone-width layouts, and Home stays.

The evidence comes from eight research lanes, a synthesis, and a gap check, all kept with the session's scratch files. The prototypes are in the same place, with screenshots rendered in WebKit.

## What a reader gets

1. **The paper stays in front.** A Paper, its Overview, or its Blog shows in a reading column of about 68 characters per line. The Overview and the Blog say which model made them and when. Every Blog claim shows its source passage on hover.
2. **No jump costs the reader their place.** In the Paper, hovering a citation, figure, table, equation, section, or footnote link shows a **Reference preview**. Clicking the link goes there, and **Back** (`⌘[`) returns to the same paragraph. On a window at least 1200 px wide, a Blog citation or an Overview card opens the Paper in a **Split view** beside the explanation.
3. **The Library knows what the reader read.** Each Paper has a **Reading state** (New, Reading, or Read) and a **Reading position** (view, chapter, and passage). Home and the Library show Continue reading. A Paper reopens where the reader stopped, also after the service restarts.
4. **It is a Mac app.** A native sidebar, a native toolbar, full menus with shortcuts, a Settings window on `⌘,`, and no controls fixed to the bottom of the window.

## Why these changes

| Change | Evidence |
| --- | --- |
| Reference previews with Back | Six of eight lanes. More than 63% of about 36,000 arXiv survey users rated reference links important. A Zotero request for hover previews ran from 2021 to 2026. |
| Reading state and Reading position | Five lanes. Zotero users have asked for read status since 2012. Paperpile users asked for a last-read sort from 2016 to 2025. |
| A 34 em measure, 18 px, and line height 1.55 | Today the column is 880 px, about 110 characters at 16 px, with line height 1.85. Research supports 60 to 75 characters and 1.4 to 1.6. |
| Passage citations and provenance | Generative answers were fully supported in about half their sentences. Linked source views raised correct answers on wrong summaries from 12.5% to 70%. |
| Split view | Linked side-by-side views had lower mental demand than separate tabs (Papeos: 4.50 against 5.31). |
| Native structure and full menus | The Mac design lane. AppKit split items and toolbars follow each macOS release, and macOS 27 already changed the sidebar and toolbar geometry of macOS 26. |

Two facts from this session also shape the design:

- **Paper-frame handlers.** In WebKit, the app's handlers on elements inside the paper frame never run while the frame's sandbox lacks `allow-scripts`. A test with native mouse events recorded `events: []`. So "click a figure to enlarge" in the Paper view is broken in the Mac app today, and it works only in Chromium. With `allow-scripts` in the iframe `sandbox` attribute and in the paper CSP's `sandbox` directive, the handlers run, and `default-src 'none'` still blocks paper scripts, inline scripts, and inline event attributes (`pwned: [null, null]`). After this change, the CSP is the one control that stops paper scripts.
- **Preferences reset.** A release starts its server on port 0 (`launch.command`), so the origin changes when the service restarts. `localStorage` is per origin, so the theme, font, size, and last Paper reset after a restart today.

## Window structure

```
+-------------------------------------------------------------------------------------+
| (o o o) [▤] [‹ ›]  Title — subtitle        [Overview|Blog|Paper] [Aa] [⇪] […] [Search] |  NSToolbar
+------------------+------------------------------------------------------------------+
| NSOutlineView    | WKWebView                                                        |
| (sidebar item)   |   Home, Library, search results, or the reader                   |
|                  |                                                                  |
| Library mode:    |   Reader: header (arXiv ID and month, title, authors, links)     |
|   Home           |           reading column; figures and tables up to 1.5x measure  |
|   LIBRARY        |           Split view: explanation | Paper                        |
|    All Papers  9 |                                                                  |
|    New         3 |                                                                  |
|    Reading     3 |                                                                  |
|    Read        1 |                                                                  |
|   RECENT         |                                                                  |
|    5 Papers      |                                                                  |
|   ─────────────  |                                                                  |
|   Activity line  |                                                                  |
| Reader mode:     |                                                                  |
|   ‹ Library      |                                                                  |
|   title, byline  |                                                                  |
|   CONTENTS       |                                                                  |
|    outline       |                                                                  |
+------------------+------------------------------------------------------------------+
```

- `NSSplitViewController` holds a sidebar item (`NSSplitViewItem(sidebarWithViewController:)`, full height, 200 to 320 pt, collapsible) and a content item that holds the WKWebView. Below a 1000 pt window, the sidebar collapses on its own; the toggle shows it again.
- The toolbar uses the unified style with a sidebar tracking separator. The window title and subtitle come from the Chrome state.
- AppKit drags the window, so `WindowDragView`, the `windowDragRegions` script and handler, and the page's drag-region CSS go away.
- The executable stays `PapersToKindle`. The Swift code may split into several files in `app/macos/`. `install-app.sh` and `build-release.py` then compile every `app/macos/*.swift` file, and `docs/development.md` names the main file. The development build targets macOS 26.0, as the release does.

## Chrome state and commands

The web app owns all state. It computes one **Chrome state** object and gives it to one of two renderers:

- In the **Native shell**, it posts the object to the `shell` script-message handler, and Swift draws the sidebar, toolbar, title, and menus from it.
- In a **browser** (`app.server --open`, the browser pane, and the WebKit screenshot tool), the web app draws its own sidebar and toolbar from the same object, in the same visual style.

The web app detects the shell from `window.webkit.messageHandlers.shell`. Every action, from a native control, a menu, a web control, or a key, goes through one command dispatcher in the web app.

### Messages from the web app to Swift

```js
{type: 'ready'}                       // sent once, after the page initializes
{type: 'state', state: ChromeState}   // sent on change, at most once per animation frame
{type: 'settings', pane}              // asks Swift to open the Settings window at a pane
```

```js
ChromeState = {
  mode: 'home' | 'library' | 'search' | 'reader',
  title: string,                      // window title: 'Home', 'Library', the Paper's short title
  subtitle: string,                   // for example '3 Model Architecture' or '9 Papers'
  canBack: boolean, canForward: boolean,
  sidebar: {
    selected: 'home' | 'all' | 'new' | 'reading' | 'read' | null,
    counts: {all: number, new: number, reading: number, read: number},
    recent: [{id: string, title: string, current: boolean}],   // at most 5
    reader: null | {
      back: 'Library' | 'Results' | 'Home',                  // where the leave command goes
      title: string, byline: string,                         // 'Vaswani et al. · Jun 2017'
      outline: [{id: string, label: string, number: string, level: 1 | 2 | 3, current: boolean}]
    }
  },
  views: null | {                                            // null outside the reader
    current: 'overview' | 'blog' | 'paper',
    overview: ViewState, blog: ViewState, paper: 'ready'
  },
  actions: {share: [Action], more: [Action]},
  prefs: {theme: 'system' | 'light' | 'sepia' | 'dark', font: string, size: number,
          margins: 'narrow' | 'normal' | 'wide', spacing: 'compact' | 'normal' | 'relaxed'},
  activity: null | {label: string, progress: number | null, count: number, failed?: boolean},
  search: {query: string}
}
ViewState = 'ready' | 'working' | 'empty' | 'off'
// ready: saved content exists, with or without an AI connection
// working: a job is making it; empty: none saved and AI is connected; off: none saved and no AI connection
Action = {id: string, label: string, enabled: boolean, role?: 'destructive', separatorBefore?: boolean}
```

The web app sends the outline's `current` flag at most once per animation frame while the reader scrolls.

### Commands from Swift to the web app

Swift calls `window.localxiv.command(command)` with `evaluateJavaScript`, and only after `ready`.

| Command | Meaning |
| --- | --- |
| `{name: 'go', to: 'home' \| 'all' \| 'new' \| 'reading' \| 'read'}` | Show Home or a Library view. |
| `{name: 'open', id}` | Open a Paper at its Reading position. |
| `{name: 'view', view}` | Show the Overview, Blog, or Paper. |
| `{name: 'outline', id}` | Scroll to an outline entry. |
| `{name: 'back'}`, `{name: 'forward'}` | Move in the history, which also holds jumps inside a Paper. |
| `{name: 'leave'}` | Leave the reader for the page the Paper was opened from. The sidebar's back row sends it. |
| `{name: 'search', query, submit}` | Run Library search and Paper search as the reader types; `submit` is Return. |
| `{name: 'prefs', patch}` | Change Reading preferences. |
| `{name: 'text-size', step}` | `1`, `-1`, or `0` for reset. |
| `{name: 'action', id}` | Run a Share or More action. |
| `{name: 'add'}` | Focus search to add a Paper. |
| `{name: 'activity'}` | Show the job list. |
| `{name: 'settings', pane}` | Settings window only: show a pane. |

### Keys

Native menu key equivalents take `⌘1`, `⌘2`, `⌘3`, `⌘[`, `⌘]`, `⌃⌘S`, `⌘+`, `⌘-`, `⌘0`, `⌘N`, `⌘F`, and `⌘,` before the page sees them, and send the matching command. In a browser, the web app's key map sends the same commands. The key map is off in the Native shell, so no key runs twice. Keys that no menu holds (arrow keys and Return in lists, Escape) stay in the web app in both modes. Keys pressed while focus is in the paper frame reach the same handlers.

### Menus

| Menu | Items |
| --- | --- |
| LocalXiv | About, Settings… `⌘,`, Check for Updates…, Quit |
| File | Add Paper… `⌘N`, Export ▸ (EPUB, PDF, PNG, Editable SVG), Send to Kindle…, Close Window `⌘W` |
| Edit | Undo, Redo, Cut, Copy, Paste, Select All, Find… `⌘F` (in the reader, a native find bar searches the open view with `WKWebView.find`; outside the reader it focuses search) |
| View | Overview `⌘1`, Blog `⌘2`, Paper `⌘3`, Show or Hide Sidebar `⌃⌘S`, Bigger `⌘+`, Smaller `⌘-`, Actual Size `⌘0`, Theme ▸, Enter Full Screen `⌃⌘F` |
| Go | Back `⌘[`, Forward `⌘]`, Home `⇧⌘H`, Library `⇧⌘L` |
| Window | Minimize `⌘M`, Zoom |
| Help | LocalXiv Help (the project README on GitHub) |

Swift enables each item from the latest Chrome state. Only the Chrome state moves a native selection after a click: a click sends its command and keeps the old selection until a new state arrives, because the page drops page commands while a dialog is open. An arrow key in the sidebar moves the selection and sends the new row's command. When the page drops a command, it posts its Chrome state again, so the shell corrects the selection.

In the Native shell, the PDF link and Open PDF open the original PDF in Preview, so the app page never navigates away. In a browser they open a new tab.

### Toolbar

| Mode | Items, leading to trailing |
| --- | --- |
| Home, Library, search | Sidebar toggle, back and forward, title, flexible space, Search |
| Reader | Sidebar toggle, back and forward, title, flexible space, view switch (Overview, Blog, Paper), Aa, More, Search |

- The view switch is an `NSToolbarItemGroup` with one selection. Every segment stays enabled. A view that is `off` explains inside the view how to connect a provider, or why the Paper cannot have one.
- **Aa** opens an `NSPopover` with theme swatches, a font menu, a size slider, margins, and line spacing. Each change sends `prefs`.
- **More** is a menu toolbar item built from `actions`: the Paper actions, then a **Share** submenu with the export and Kindle actions. Add Paper is not a toolbar item; File › Add Paper… (`⌘N`), the search, and Home's field add a Paper.
- **Search** is a magnifier button that expands into a search field when clicked, on `⌘F` outside the reader, or on `⌘K`, and folds back when it loses focus with no text. Typing sends `search`, and Return sends `search` with `submit`.

### Settings window

`⌘,` opens a separate window with a preference-style toolbar of panes: General, Reading, AI, Kindle, Search, and Help. The window holds a second WKWebView that loads `/?panel=settings&pane=<pane>#token=…`. It shares the default website data store, so the session token reaches it. In the Settings window, a change is saved when the reader commits it (a checkbox or pop-up change, or leaving a text field), as Mac settings windows do, and a server error shows under its field. The window has no Save button. In a browser, the same settings view opens as a dialog with its own pane list and one **Done** button that saves and closes. The main window picks up saved settings through its existing poll.

### First run

The setup dialog still opens on the first launch. The four-step tour goes away, because its targets become native controls. Home shows a short welcome in its place until the reader adds a Paper.

## Visual system

The Native prototype is the reference (`prototypes/native/index.html` with the session's scratch files).

- UI text is SF Pro: 13 px rows and controls, 11 px section labels and captions, 15 to 17 px list titles. Inline SVG icons follow SF Symbols: 1.5 px strokes and round caps.
- Light: paper `#ffffff`, label `#1d1d1f`, secondary label `#6b6b70`, separator `rgba(0,0,0,.09)`, accent `#2f7a55`. Dark: paper `#1e1e1e`, label `#f2f2f4`, secondary `#a2a2a7`, accent `#5cc28e`. Sepia: paper `#f8f2e6`, label `#3a2f22`, accent `#2c6e4c`. Selection, selected segments, the chosen theme swatch, and focus use the system accent. Green marks links, progress, the unread dot, and primary buttons. Sidebar icons are secondary grey until their row is selected.
- In the Native shell, AppKit draws the sidebar material and the toolbar. In a browser, the web sidebar imitates them.

## Reading

- Defaults: 18 px, line height 1.55, and a measure of 34 em (Normal margins). The measure is in em, so a size change keeps the line length.
- **Reading preferences**: theme (Light, Sepia, Dark, or Match System), font (New York through `ui-serif`, Charter, Iowan Old Style, Palatino, or SF Pro), size from 15 to 26 px, margins (Narrow 42 em, Normal 34 em, Wide 28 em of text between them), and line spacing (1.4, 1.55, or 1.7). Margins set the Paper and Blog text; figures and the Overview keep their own width rules.
- The server settings store Reading preferences (`reading_theme`, `reading_font`, `reading_size`, `reading_margins`, `reading_spacing`), so they survive a new port. `localStorage` keeps a copy, so the first paint has the right theme.
- Dark is a dark grey. In Dark and Sepia, paper figures sit on a light card, so their white backgrounds read as figures. Overview and Blog figures use their own dark Figure palette.
- Paragraphs use `text-wrap: pretty` and `hyphens: auto`. Headings use `text-wrap: balance`. Display equations are centred and scroll sideways inside their own box when too wide. Figures, tables, and display equations may run to 1.5 times the measure. Tables use tabular numerals.

## Home

Home keeps its search field as the main control. Under it, Continue reading shows up to three Papers in the Reading state with their last section, and Recently added shows the newest Papers. On a library with no Papers except the included sample, Home shows the welcome that replaces the tour.

## The Library

- Home, the Library, and the results page sit in one centred content column with a maximum width, so a full-screen window keeps them in the middle.

- The Library shows one view at a time from the sidebar: All Papers, New, Reading, or Read. All Papers starts with a Continue reading card for the last Paper.
- A row shows the title, up to three authors as "First Last" with "et al.", the publication month from the arXiv ID (`2511.01689` is Nov 2025), Overview and Blog marks, the Reading state (a dot for New), and the added date. The stored "Last, First" pairs become "First Last" names. An odd number of parts shows the stored text.
- Sort by recently added (the default), recently read, title, or publication date.
- The arrow keys move the selection, and Return opens the Paper. The context menu holds Open, Mark as Read or Mark as Unread, Copy arXiv Link, Copy BibTeX, and Remove from Library.

## Search

The toolbar search field, the Home field, and the results page share one component: Direct import for a link or an arXiv ID, and Paper search with Suggestions for other text (`docs/superpowers/specs/2026-09-29-paper-search-design.md`). Typing shows the results page live: Papers in the library first, then Papers from arXiv with **Add** or **Open**. Return on a link imports it. Escape returns to the page before the search.

## The reader

- The header shows the arXiv ID with its month, the title, the authors, and the links **arXiv** and **PDF**. The sidebar shows the outline of the current view and marks the current section as the reader scrolls.
- **Paper view.** One chapter shows at a time, as today. The outline lists every chapter, and the current chapter expands to its subsections, read from the chapter's headings. The end of a chapter links the previous and the next chapter.
- **Reference preview.** After 250 ms on a citation, cross-reference (`data-reference-type`), footnote, or section link, a popover shows its target: the bibliography entry, the figure with its caption, the table, the equation, or the section's first paragraph. The popover reads the target chapter with `fetch` and `DOMParser`, so it needs no new data. A link that does not resolve shows no popover. A citation preview has **Go to Reference** and **Search** (Paper search with the entry's text). Clicking a link goes to its target and adds a history entry.
- Clicking a paper figure opens the figure dialog.
- **Overview view.** The figure draws on the page with no frame inside a frame, up to the full pane width. Its header says which model made it and when, and how the Component hover works. The outline lists the figure's panels.
- **Blog view.** The header shows the title, the explanation's `contribution` as a lead, and a provenance block: "Generated with <model>" on one line, and "<date> · <n> min read" on the next. The body renders `blog.cited_text`. Each `[pNNNNN]` citation is a small superscript number. Hovering shows the passage's section and text from `blog.evidence`, and clicking opens the Paper at that passage. The Blog ends with the explanation's `limitation`.
- **Split view.** On a window at least 1200 px wide, opening a passage from the Blog or the Overview shows the Paper in a pane beside the explanation. A narrower window switches to the Paper view, and Back returns.
- **Generation states** stay inside the view. A view with no Overview or Blog explains what it is and offers **Generate**. With no AI connection, it says how to connect a provider. While a job runs, the view shows its progress text, and the Paper stays readable. Regenerate is in the More menu, beside the provenance line.
- **Reading state.** Opening a New Paper sets Reading. The reader sets Read from the More menu or the Library. Reaching the end of the last body chapter shows one quiet "Mark as read" prompt.
- **Reading position.** The web app saves the view, the chapter, and the passage ID at the top of the viewport, and in the Blog the section at the top, two seconds after scrolling stops, when the view changes, when the reader leaves, and when the app quits. Opening a Paper restores them. A jump from a preview or a citation does not move the saved position until the reader scrolls there.

## Server changes

- `papers/library.py`: a `reading` table (`paper TEXT PRIMARY KEY, value TEXT`). A record holds `state` (`reading` or `read`; no record means New), `opened_at`, `view`, `chapter`, `anchor`, `section` (the Blog section), and `read_at`. Removing a Paper removes its record.
- `app/server.py`:
  - `POST /api/papers/<id>/reading` merges a partial record and rejects unknown keys and values.
  - `GET /api/state` adds `reading` to each Paper.
  - Settings accept and validate the five Reading preference keys.
  - The static file list serves the new front-end files.
  - The paper CSP adds `allow-scripts` to its `sandbox` directive.

## Native test harness

The session cannot screenshot other apps' windows, so the shell takes its own pictures. A build with `-D LOCALXIV_AUTOMATION` reads a step file named by the `LOCALXIV_AUTOMATION` environment variable. A step runs JavaScript, sends a command, presses a toolbar item, waits, sets the window size or appearance, writes a snapshot, or quits. A snapshot draws the window frame view with `cacheDisplay` and lays the web view's `takeSnapshot` image over it. Production builds do not pass the flag, so they contain none of this code.

A test run installs a scratch bundle with `PAPERS_INSTALL_ROOT` and `PAPERS_APPLICATIONS_DIR`, replaces its executable with the automation build, and uses a copy of a library. The run checks that port 8765 is free first. The app's service survives the app, so every run ends by stopping the scratch service. `install-app.sh` copies `node_modules` as a link when it is one, so the run copies the real tree.

## Not in this change

Highlights and notes, Collections and Tags, an inspector pane, a command palette beyond search, changes to `papers/figures/` or to conversion, and phone-width layouts.

## Done when

The check for each item uses the real artifact: the browser pane for behaviour, the WebKit screenshot tool for web rendering, the native harness for the Native shell, and component tests through the server API.

1. Every flow that works today still works: Direct import, Paper search with Suggestions, the results page, Paper export, Send to Kindle, Overview and Blog generation and regeneration, Settings, setup, Paper removal, job notices with Cancel and Retry, the figure dialog, and the Component hover.
2. A Paper reopens at its view, chapter, and passage after the server restarts on a new port.
3. In WebKit, hovering a citation, a figure link, a table link, and an equation link in the Paper shows a preview. A click, then Back, returns to the same paragraph.
4. The measured default line length is 60 to 75 characters in WebKit.
5. Every Overview and Blog shows its model and date. Every Blog citation shows its passage on hover.
6. The Library shows Reading states, sorts four ways, and filters by state.
7. Native harness snapshots show the sidebar in Library mode and in Reader mode, the toolbar in both modes, the Aa popover, and the Settings window, in light and dark.
8. Light, Sepia, and Dark meet 4.5:1 for body text and 3:1 for UI text.
9. `install-app.sh` and `build-release.py` both compile, with and without Sparkle.
