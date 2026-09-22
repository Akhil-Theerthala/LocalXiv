# Front-end deepening design

Date: 2026-09-22. Source: the architecture review of the browser front end, read through the `better-ui`, `better-colors`, `better-layout` and `better-typography` lenses. The user accepted all five candidates on 2026-09-22.

The vocabulary is the `codebase-design` skill's: a **module** has one **interface** and an **implementation**; a module is **deep** when much behaviour sits behind a small interface; a **seam** is where an interface lives; an **adapter** satisfies an interface at a seam; depth gives callers **leverage** and maintainers **locality**. Domain nouns are `CONTEXT.md`'s.

## The front end today

`app/static/` is five files with no build step: `index.html` (126 lines), `app.css` (532 lines), `reader-layout.css` (80 lines), `app.js` (1,019 lines, one classic script), and `math-config.js`. `app/server.py:396` serves them from a fixed map. The macOS release copies the whole `app` directory, so a new static file needs only a map entry.

One front-end test exists, `tests/test_job_notices.js`. It cannot load `app.js`, because the file wires about sixty handlers at load, so it slices function bodies out of the source text by string index.

## 1. Appearance module (Strong)

**Friction.** One theme or reading preference crosses four seams. The palette lives as tokens in `app.css:3-4`; `styleReader` in `app.js:761-772` restates it as hex literals inside a template of about forty `!important` rules injected into the Paper's reader iframe; `reader-layout.css:40,43` and `app.css:94,97` pin the figure frames to cream with no dark rule; `papers/document.py:26` carries the EPUB stylesheet. The iframe template also re-derives the 850px breakpoint to choose its canvas colour.

**Design.** `app.css :root` stays the one source of the palette. A new module, `app/static/appearance.js`, owns the mapping from Reading preferences to values: it validates stored preferences, resolves the theme, returns the root custom properties, and returns the reader stylesheet from resolved values. It touches no DOM. Two adapters apply it: the page root writes the custom properties, and the reader iframe adapter reads the computed tokens and the computed background of the document pane, then injects the stylesheet. The figure frames reference the tokens, so they follow the theme.

**Not in scope.** The EPUB stylesheet in `papers/document.py` stays a light-only adapter: it holds no colour, and Kindle applies its own typography. The loading page in `app/macos/PapersToKindle.swift:98` keeps its one hex value, because Swift cannot read `app.css`.

## 2. Stylesheet scale tier (Worth exploring)

**Friction.** Radius, shadow, motion and type sizes exist only as raw numbers: 21 distinct radii, 9 one-off tinted shadows beside one token, three near-identical easing curves, 25 font sizes. The file grew by appending, so later blocks contradict earlier ones (`.icon-button:hover` lifts at line 266 and is cancelled at 525; the library card is restyled five times; dialogs animate under two keyframes). Six selector groups match nothing in `index.html` or `app.js`: `.chapter-bar`, `.export`, `#appearance-dialog`, `.empty`, `.privacy`, `.figure-downloads`. The 850px breakpoint is opened nine times across the two files.

**Design.** A token tier at the top of `app.css` becomes the interface every rule references: type sizes, the radii that already repeat, one scrim per role, shadow roles, one easing and three durations. Tokens are introduced by exact value match, so no pixel moves except where the design says so (shadow roles). Dead groups and contradictions are deleted. A node test fails on any hex literal outside a custom-property declaration in either stylesheet or anywhere in the scripts, and on any dead selector. Breakpoint blocks are merged only after a script proves that no same-selector property collision changes the cascade.

**Left raw.** Spacing, letter-spacing and line-height stay as numbers. Tokenising them changes hundreds of declarations for no behaviour the app can test.

## 3. View module (Worth exploring)

**Friction.** The reading layout (home, library or workspace; Overview, Blog or Paper tab; focus; with or without contents; mobile) is an implicit state spread over hidden flags on six elements, four body classes, one data attribute and the mobile nav's `aria-current`, written by five functions: `openPaper`, `goHome`, `showLibrary`, `renderContents`, and the focus toggles.

**Design.** `app/static/view.js` owns one view value and derives every flag from it. The five writers become callers that name a destination. The module takes the document it writes into, so a stub document tests every page.

## 4. Renderers behind a seam (Worth exploring)

**Friction.** Every renderer reads the page's document directly and `app.js` wires handlers at load, so the only test slices source text. `renderProse` also decides the 600px picture breakpoint that the stylesheet declares separately.

**Design.** `app/static/render.js` holds the renderers: job notices, prose, library, recommendations and contents. Each accepts the element it draws into and an object of the actions it may trigger, and it creates nodes through the document it is given. `app.js` keeps the state and wiring and calls the renderers. `tests/test_job_notices.js` imports the module instead of slicing the source.

## 5. Figure palette as an adapter (Speculative)

**Friction.** The Figure library carries its own ramp as constants in `papers/figures/layout.py:22-27`, plus literal fills in `render.py`, and every Figure render is light-only. The in-app frame therefore stays cream in dark mode.

**Design.** `papers/figures/palette.py` defines a `Palette` and two values, `LIGHT` (byte-identical to today's constants) and `DARK`. `compose` and the drawers take a palette. `Figure.build` composes the dark variant from the same layout and writes it as a real SVG beside the light assets, with no second WebKit pass. The app swaps a figure's source with the theme and falls back to the light source for figures saved before the key existed.

**Not in scope.** The figure font stays Arial: the editable SVG export opens on machines without the app's fonts. Aligning the figure hues with the app tokens is a design change the user has not seen; it becomes a one-line edit in `palette.py` after this plan.
