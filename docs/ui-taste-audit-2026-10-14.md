# UI taste audit of the redesign

Audited on 2026-10-14 at branch `ui-redesign` (`e6378c5`), with the `design-taste-frontend` skill. This is a report only. No code changed.

## Scope and method

The skill is written for landing pages and portfolios. Its Section 13 puts product UI and native apps out of scope, except for the rules that still apply. So the audit used this design read: a native macOS reading app (product UI) for researchers, with an Apple-native, calm, typographic language, on AppKit and Apple Human Interface Guidelines conventions. The dials are `DESIGN_VARIANCE 3`, `MOTION_INTENSITY 3`, and `VISUAL_DENSITY 5`.

The audit applied these rules: no em dash, the middle-dot ration, theme lock, colour lock, shape lock, contrast for buttons, forms, and text, empty, loading, and error states, motivated motion and reduced motion, no pure black, icon discipline, z-index restraint, and the copy self-audit. It skipped the hero, bento, logo wall, marquee, image, and stack rules, because they do not apply to an app.

One agent captured 147 screenshots: every web screen in Light, Sepia, and Dark in WebKit, and the native window with the native harness. Five auditors each took one lens: visual system, copy, accessibility, states and motion, and native conventions. For each lens, a skeptic tried to refute every finding against the code and the screenshots. Of 95 findings, 88 survived (60 confirmed, 28 plausible) and 7 were refuted. The skeptics lowered every "high" finding, so no finding is high. Each item below gives its audit IDs. The screenshots and the full findings are in the session scratch folder (`scratchpad/audit/`, with `INDEX.md` and `joined.json`). macOS can delete that folder, so the file and line references are the durable evidence.

## What already passes

- The accent is one green hue at 43 to 46% saturation in every theme. White on the accent fill is 5.2:1 or more.
- No pure black anywhere. Dark paper is `#1e1e1e`. The Light paper `#ffffff` is accepted for a reading surface, because the ink `#1d1d1f` keeps it at 16.8:1.
- Body text, secondary text, helper text, error text, links, citation markers, and accent and destructive buttons all pass 4.5:1 in all three themes.
- The app's own copy has no em dash. Every metadata line except one (copy-01) has at most one middle dot. The only dot in a row is the semantic New marker.
- Light, Sepia, and Dark lock the whole browser page. Light, Dark, and Match System lock the whole native window.
- Cards appear only where they mean hierarchy. Lists use hairlines.
- Keyframes animate only `transform` and `opacity`. Every animation stops under reduced motion. Motion is feedback or state change only.
- The z-index values follow a system.
- Labels sit above fields. No button label wraps at 1280 px.
- The native toolbar zones, window title, menu case, ellipses, shortcuts, source-list headers and counts, find bar, Remove Paper alert, and narrow-window behaviour follow the HIG.

## Medium findings, by area

### Colour: two accents in one window

1. **The native window shows blue and green together.** (V1, NC-01, NC-02, NC-03.) AppKit tints every sidebar icon, the back chevron, the selected Aa controls, and the Settings pane selection with the system accent, which is blue on a default Mac (`Sidebar.swift:130-133`, `ReadingPopover.swift:89`). The page beside them uses green for the New dot, Go, Save, and checkboxes. The web chrome uses three looks for "selected": a grey pill with a green icon for sidebar rows (`app.css:125-127`), a green tint for the current Contents row (`app.css:140-141`), and a fixed blue `#0063e1` for Library rows, menus, and Suggestions (`app.css:9`). In the native window, the Reading-state glyph is also mirrored: the sidebar fills the left half (`circle.lefthalf.filled`), and the row icon fills the right half (`index.html:9`).
   **Tweak (choose one):** (a) Selection and selected controls use the system accent, and green marks only links, progress, the unread dot, and primary buttons. Set sidebar icons to `.secondaryLabelColor`, and give web sidebar rows and outline rows the `.prow.is-selected` treatment. (b) Lock every app control to green. Tint each control in Swift with one dynamic colour (`#2f7a55`, `#5cc28e`), because the build has no `actool` for an asset-catalog accent colour. The spec today says (a). For both options, flip the web Reading glyph to fill the left half.

### Contrast and forms

2. **Placeholders and the off view segment are too light.** (V2, CF-02.) `--label-3` carries text that the reader must read. Placeholders are 3.42:1 on the Home bar and 3.72:1 on fields in Light (`app.css:80`, `:186`). The enabled off segment of the view switch is 3.6 to 4.1:1 (`app.css:349`).
   **Tweak:** point `input::placeholder` and `.seg>button.is-off` at `--label-2` (4.87:1 or more on every surface), and keep `--label-3` for non-text marks.
3. **The focus ring fails 3:1 in Light and Sepia.** (CF-01.) The 55% accent ring is 2.2:1 (`app.css:8`, `:21`, `:51`). Dark passes.
   **Tweak:** raise the alpha to .85 in Light and Sepia, or use the solid accent at 2 px.
4. **Fields almost vanish on dialogs.** (CF-04.) Fields are paper on near-paper with a .5 px edge at 10 to 13% alpha (`app.css:79`). Pop-ups show no edge at all, because an inset box-shadow does not draw on `select`. The `--field` token is defined but never used.
   **Tweak:** draw a 1 px `border` from a new `--field-edge` token. About 45% alpha gives 3:1.
5. **Accent text on the accent tint is 4.44:1 in Light.** (CF-03.) This affects the "In library" chip and the current outline number. **Tweak:** lower the tint to 8%, or use a darker text green.
6. **The page ignores Increase Contrast.** (CF-06, plausible.) AppKit darkens its borders, and the page keeps its hairlines. **Tweak:** add a `prefers-contrast: more` block with stronger separators, field edges, a solid focus ring, and `--label-3` set to `--label-2`.

### Keyboard paths

7. **Component details need a mouse.** (CF-10.) Overview cards take focus, but their details show only in the SVG `<title>` tooltip (`render.js:345-357`). **Tweak:** on focus, show the same summary in a preview anchored to the card, and change the note to "Hover or focus a card for its details."
8. **Reference preview actions cannot be reached with the keyboard.** (CF-11.) Tab leaves the link, and the preview closes (`reader.js:368-371`, `:457-462`). **Tweak:** Down Arrow moves focus into the preview, the preview stays open while it has focus, and Escape returns focus to the link.

### Settings and Setup

9. **Settings has three save models.** (copy-05, NC-11, V13.) The web dialog's Close also saves (`app.js:624-627`), so "Close" hides that it saves. The native Settings window asks for Save on four panes, applies changes at once on Reading, and saves again when it closes. On Reading and Help, the footer is an empty band with a rule (`app.js:541`, `app.css:493`).
   **Tweak:** in the native window, save each field when the reader commits it, show server errors under the field, keep the save in `windowShouldClose` as a safety net, and hide the footer. In the web dialog, show one "Done" button that saves and closes.
10. **Setup can be skipped by accident.** (copy-06, CF-15.) Close and Skip Setup do the same thing, and Close gets the first focus, so Return skips setup on the first launch (`app.js:695-696`). **Tweak:** remove the heading Close button, and give the first focus to Provider.
11. **The API key placeholder is false when no key exists.** (copy-11, CF-09.) "Leave blank to keep your saved key" is fixed text (`index.html:127`, `:149`). **Tweak:** use "Paste your API key" when no key is saved, and put the "leave blank" sentence only in the status line.

### Native shell

12. **The sidebar opens at its 200 pt minimum, and it forgets a width.** (NC-06, V9.) Most outline entries and Recent titles are cut. **Tweak:** open at about 250 pt and set the split view's `autosaveName`.
13. **A long Paper title is cut with no ellipsis.** (NC-07.) Setting `wraps = true` drops the tail ellipsis (`Sidebar.swift:142-143`). **Tweak:** set `truncatesLastVisibleLine = true`.
14. **Some actions live only in toolbar menus.** (NC-09.) Mark as Read, Open PDF, Open on arXiv, Regenerate, Remove, Copy arXiv Link, and Copy BibTeX have no menu bar item. **Tweak:** add a Paper menu built from `chrome.actions`. Remove from Library… gets `⌘⌫`.
15. **Sepia mixes warm and cool greys.** (NC-13, V3.) Sepia maps to Aqua, so a white toolbar band and a cool sidebar meet the warm page with a hard edge (`Shell.swift:186`). The browser paints the same state warm. **Tweak:** set each window's `backgroundColor` to the Sepia paper and check it with the harness, or apply the Apple Books rule in both renderers (Sepia changes the page only).
16. **The launch page and the launch failure need work.** (S01, S02, copy-23.) "Opening your paper library…" is in `GrayText`, at 1.8:1, and uses the macOS appearance, so a fixed Reading theme flips at each launch (`PapersToKindle.swift:43`). Every alert has the title "LocalXiv" and only OK (`PapersToKindle.swift:194`). **Tweak:** draw the launch state in AppKit with a progress indicator. Keep the last Reading theme in UserDefaults and apply it before the window shows. Give alerts a title that states the problem, plus Try Again, Show Log, and Quit.

### Reader

17. **Titles stop leading at large text sizes.** (V5.) Titles are fixed px, and headings scale with the reading size. At 26 px, a Blog section heading (30.4 px) is larger than the Blog title (28 px), and the paper's chapter heading (32.5 px) is larger than the Paper title (32 px). **Tweak:** `.blog-title{font-size:max(28px,1.5em)}` and `.doc-head h1{font-size:max(32px,1.7em)}`.
18. **The jump highlight runs backwards.** (S03.) The tint fades in over 1.4 s and then disappears in one frame (`appearance.js:68`, `reader.js:282`). **Tweak:** start at full tint and fade out with a keyframe animation.
19. **Generated text brings em dashes.** (copy-04, NC-17, copy-25.) Blog bodies and headings, which the sidebar outline repeats, contain em dashes. The bundled sample Blog has two. The combined EPUB names its Blog section "Title — Blog" (`papers/exports.py:185`). **Tweak:** add a Section check that rejects U+2014, edit the sample text, and change the EPUB section name.

### Search and jobs

20. **A refined search shows old results under the new query.** (S04.) The heading changes at once, and the old arXiv rows stay with no "Searching…" (`app.js:418`, `:426`). **Tweak:** dim the old rows and show "Searching…" until the new response arrives.
21. **Job toasts cover content, and errors land in the wrong place.** (S06, S07, S08, S09, copy-15.) Toasts at the top right cover Resume, Sort, and Open buttons. Failed toasts never expire. In the reader, one job shows three times, with two Retry buttons. Import toasts name no paper (`render.js:31-32`). Errors from the Send to Kindle sheet appear behind its modal scrim (`app.js:41-42`). An error notice looks like a success notice (`app.js:67-74`).
    **Tweak:** do not toast a job that the current view already shows. Move lasting failures to the sidebar Activity line. Name imports by arXiv ID. Show sheet errors inside the sheet. Give error notices the red edge.

## Low findings, by area

### Copy

- The provenance line has two middle dots (copy-01). Put the model on one line, and the date and length on the next.
- The Blog length options use an en dash for a range (copy-03, `index.html:135`). Use a hyphen.
- The Setup title "A little setup. Just once." is cute (copy-07). Use "Connection Setup".
- The Remove dialog uses a straight apostrophe in "paper's" (copy-08, `index.html:87`).
- "Paper" and "paper" mix in sentences, for example "9 Papers" over "No new papers" (copy-09). This needs your decision, because **Paper** is a `CONTEXT.md` term.
- "Match system" in the web and "Match System" in the native shell (copy-10, NC-14). Use "Match System" everywhere.
- The Kindle address has three names: "Send-to-Kindle email", "Kindle email", and "Kindle address" (copy-12).
- Several help lines have unclear referents or undefined words: the reasoning help, "valid papers", and "Large articles" (copy-14).
- Two buttons use sentence case: "Go to reference" and "Enlarge figure" (copy-16).
- "Model" and "Model name" for one field, and the web toolbar placeholder "Search" against the native "Search or paste a link" (copy-17, NC-14).
- The native Aa tooltip says "Reading" (copy-18). Use "Reading Preferences".
- The Library column header "Explained" does not say which icon is which (copy-21).
- `README.md:87` still says "Settings → AI connection" (copy-22). The pane is "AI".
- Server warnings speak as "We" (copy-24, `papers/convert.py:65`, `papers/pdf.py:7`).
- "Mark as Unread" makes the Paper New and deletes its Reading position, and the label does not say so (copy-20, plausible).

### Visual system

- 15 different radius values with no documented scale, and a bent hairline under rounded search rows (V4).
- Sepia keeps neutral black shadows and a grey scrim, and about 15 colours bypass the tokens (V6).
- 13 font sizes, including a 12.5 px half step, and two heading ladders (V7).
- The z-index comment leaves out the skip link and the narrow overlay (V12).
- The gap between a view header and its body is 54, 30, or 22 px in the three views (V13).
- Close and zoom controls use text glyphs beside a 1.5 px stroke icon set (V14).
- The filled accent repeats on every search row, so no action stands out (V10). Use a tinted row action.
- The slate-blue wash behind the web sidebar adds a second hue (V11, plausible).

### Native conventions and icons

- The "A PDF has no sections." note is a selectable outline row in the native sidebar (NC-08, `Sidebar.swift:57`).
- Edit has no Find Next, Find Previous, or Use Selection for Find, and Window has no Bring All to Front (NC-10).
- The Settings window can be resized and zoomed, and it keeps one height for every pane (NC-12).
- The web view switch never folds when the window is narrow, so the title is cut first (NC-15).
- Web and native icons differ for the same item: All Papers, More, Aa, and Add Paper (NC-04).
- The gear icon can read as a sun, and the 12 px link arrows look faint (NC-05, plausible). The audit recommends keeping the local sprite and not adding an icon library.
- The Share symbol opens an app menu with no system share services (NC-16, plausible).

### States and motion

- "Search is down" looks like a neutral status and has no Try Again (S05).
- "Adding…" is a faded, disabled button at 1.8:1 that reads as unavailable (S10).
- The welcome text points to the sample paper after it was removed (S12).
- A failed figure has three different looks, and Enlarge stays live (S14).
- The Send to Kindle sheet with no address has no button to Settings (S16).
- The Overview figure loads with no reserved height, so the layout shifts (S17).
- A Paper with no text shows a Generate button that is always disabled (S19).
- The web sidebar slides for 380 ms while the content jumps in one frame (S20).
- Menus scale in over 180 ms, and AppKit menus appear at once (S21).
- A lost connection shows WebKit text such as "Load failed" (S22).
- Empty Library views keep the column header over no rows (S11, plausible).
- A link with a missing target scrolls to the chapter top with no message (S13, plausible).
- The Settings window can flash white in Dark before its page loads (S15, plausible).

### Accessibility

- The reduced-transparency fallback never runs in WebKit, because WebKit does not support that query (CF-07).
- Server errors for a field show in the Settings footer, which can be on another pane (CF-08).
- Selected segments are a slightly darker grey (1.17 to 1.57:1), and the same popover marks the selected font with a raised fill (CF-13).
- Settings opens with focus on a remembered pane button and not on the current pane, and Setup opens with focus on Close (CF-14, plausible).
- Some helper text is not linked to its field with `aria-describedby` (CF-17, plausible).

## Refuted findings

The skeptics refuted these seven:

- **V8:** the light figure card in Sepia is the spec's choice.
- **copy-13:** "Open in Paper" and "Open in Paper View" name different actions correctly.
- **copy-19:** "Results" matches the page's own heading.
- **CF-05:** grey selection with secondary text copies AppKit exactly.
- **CF-12:** the toast close target meets the WCAG spacing exception.
- **CF-16:** the Send to Kindle sheet says how to add an address, and Cancel stays enabled.
- **S18:** "Searching…" is the Mac convention, so search rows need no skeleton.

## Suggested order

1. Item 1 (choose a colour rule), items 2 to 4 (contrast), and items 9 to 11 (Settings and Setup). The reader meets these on every visit.
2. Items 12 to 16 (native shell), items 17 to 19 (reader), and items 20 and 21 (search and jobs).
3. The low findings, area by area.
