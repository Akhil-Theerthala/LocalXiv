# LocalXiv UI rule book

This book is for the auditors of the LocalXiv user interface. LocalXiv is a native macOS 26 app for reading arXiv papers and keeping a local library. AppKit draws the Native shell. WebKit draws the content in a WKWebView. The goal is a calm, premium, Apple-native feel for researchers who read for hours.

The book merges 180 rules. A skeptic checked each one against its source. Each rule below has an id, a strength, the rule, a check, a threshold, its sources, and the input rules that it merges. Where two sources disagree, the rule names the conflict and states the winner for LocalXiv.

## How to audit

1. Read every rule in your group.
2. Run the check of every rule. A rule is done when you record pass, fail, or "needs native run" for it.
3. For each fail, record the rule id, the file and line or the screenshot, and the value that you measured against the threshold.
4. Where a rule names a conflict, audit against the winner that the rule states.
5. Record a rule that only a native run can check under "needs native run". The list at the end names these rules.

Strength:

- **must**: The release needs this. A fail is a high-priority finding.
- **should**: Follow it. A fail is a finding, unless the code or a doc records a reason.
- **consider**: An improvement. Report a fail as a suggestion.

## Words in this book

- **Native shell**: The AppKit window: the sidebar, the toolbar, the menus, the Settings window, and alerts.
- **Web layer**: The web app in the WKWebView.
- **Chrome**: The parts of the app around the reading content: the Native shell, Home, Library, the Notes page, dialogs, job toasts, menus, and popovers outside the reader.
- **Reading surfaces**: The Paper, the Blog, the Overview, Split view panes, margin cards, Reference previews, and the Chat panel.
- **Reading theme**: Light, Sepia, or Dark, from Reading preferences. Automatic follows the system appearance.
- **Floating layer**: An element that sits over other content: a popover, a menu, a Reference preview, a job toast.
- **In-flow element**: An element in the page flow: a Library row, a note card, a Chat message, paper text.
- **px and pt**: In the WKWebView at 100% page zoom, 1 CSS px equals 1 pt. This mapping is this book's assumption, not a source statement.

Other terms (Paper, Highlight, Note, Question card, All Notes, Not found, Reading position, Reading state, Reference preview, Split view) have the meanings in `CONTEXT.md`.

## Conflict index

Each row names a conflict and the rule that decides it. The reason is in the rule.

| Conflict | Input rules | Winner for LocalXiv | Decided in |
|---|---|---|---|
| System appearance against the reading theme | MACOS-HIG-09, READING-26, A11Y-18 against READING-27, READING-28 | Chrome follows the system. The reading theme applies to reading surfaces only. Default is Automatic. | R-COL-1 |
| WCAG 2 ratio against APCA on dark pairs | A11Y-01 against A11Y-02, A11Y-03 | Both apply. WCAG 2 is the floor. APCA is the target. | R-COL-5 |
| Scope of the system accent | A11Y-16 against MACOS-HIG-10, MACOS-HIG-22 | The HIG scope | R-COL-8 |
| Blur in the content layer | MACOS-HIG-14 check against its source and A11Y-24 | Standard blur on floating layers is allowed | R-VIS-3 |
| Reduce Transparency for web surfaces | MACOS-HIG-15 against A11Y-23 | A Swift bridge | R-VIS-4 |
| Hit target floor | MACOS-HIG-26, A11Y-09 against A11Y-08 | 24 px in the web layer | R-VIS-1 |
| Dialog animation length | INTERACTION-CRAFT-01 against INTERACTION-CRAFT-03 | 300 ms cap | R-MOT-1 |
| Menu open motion | INTERACTION-CRAFT-05 against INTERACTION-CRAFT-10 | No motion for menus | R-MOT-4 |
| Margin card motion | MACOS-HIG-30 against INTERACTION-CRAFT-07 | Brief fade on open, interruptible move on reflow | R-MOT-7 |
| Press feedback | INTERACTION-CRAFT-09 against MACOS-HIG-28, INTERACTION-CRAFT-14 | AppKit-style darken. Scale only on bezel-less icons. | R-MOT-9 |
| Slides under Reduce Motion | INTERACTION-CRAFT-19 against MACOS-HIG-24, A11Y-22 | Fade instead of slide | R-MOT-10 |
| Pointing-hand cursor | MACOS-HIG-28 against INTERACTION-CRAFT-15 | Hand on every link | R-SHELL-12 |
| Redefining a standard shortcut | MACOS-HIG-27 against INTERACTION-CRAFT-23 | Allowed with a recorded reason | R-KEY-1 |
| Window title length | MACOS-HIG-04 against long paper titles | Truncated paper title | R-SHELL-3 |
| Sidebar depth | MACOS-HIG-10 against the Paper outline in the sidebar | Two levels. The fix is the user's decision. | R-SHELL-7 |
| Native Settings window against a web Settings dialog | MACOS-HIG-07, INTERACTION-CRAFT-17 against the app | The native window | R-SHELL-6 |
| Cancel button label | MACOS-HIG-11 against ANNOTATION-AI-26 | "Cancel" | R-SHELL-10 |
| Short alert title against naming the paper | MACOS-HIG-11, STATES-FEEDBACK-15 against STATES-FEEDBACK-14 | Truncated title plus informative text | R-SHELL-10 |
| Default button of Remove paper | STATES-FEEDBACK-16 against ANNOTATION-AI-26 | No default button | R-SHELL-11 |
| Undo against confirmation for Remove paper | MACOS-HIG-29 against ANNOTATION-AI-25, STATES-FEEDBACK-13 | Confirmation. Undo is "consider". | R-DLG-1 |
| Note editor from the selection toolbar | MACOS-HIG-13 against ANNOTATION-AI-03 | The editor replaces the toolbar | R-DLG-3 |
| Remove a Highlight that has a Note | ANNOTATION-AI-04 against MACOS-HIG-12, ANNOTATION-AI-25 | Two menu items, no alert | R-ANN-2 |
| Line length band | READING-TYPOGRAPHY-01 against READING-TYPOGRAPHY-02, READING-TYPOGRAPHY-06 | Layered bands | R-TYP-1 |
| Line and paragraph spacing | READING-TYPOGRAPHY-05, READING-TYPOGRAPHY-07 against READING-TYPOGRAPHY-06 | Default step against loosest step | R-TYP-3 |
| Reading text size against UI text size | READING-TYPOGRAPHY-03 against MACOS-HIG-18 | Scoped by text type | R-TYP-2 |
| Toast lifetime | STATES-FEEDBACK-10, INTERACTION-CRAFT-27 against MACOS-HIG-25, A11Y-30, STATES-FEEDBACK-08, STATES-FEEDBACK-09, ANNOTATION-AI-27 | Three toast classes | R-STATE-6 |
| Spinner show delay | INTERACTION-CRAFT-25 against STATES-FEEDBACK-02 | Delay by expected duration | R-STATE-2 |
| Spinner labels | STATES-FEEDBACK-06 against ANNOTATION-AI-15, STATES-FEEDBACK-04 | Label the job, not the spinner | R-STATE-4 |
| Disabled buttons while busy | STATES-FEEDBACK-29 against ANNOTATION-AI-12 and its own source | `aria-busy` and a guard | R-STATE-15 |
| Chat log announcements | ANNOTATION-AI-23 against ANNOTATION-AI-24 | `aria-busy` while an answer streams | R-STATE-8 |

---

## 1. Motion and feedback

### R-MOT-1 Keep animations short

- **Strength:** should
- **Rule:** Keep every web UI animation at 300 ms or less. Use these bands: press feedback 100-160 ms, toggle and checkbox feedback about 100 ms, tooltips and small popovers 125-200 ms, dropdowns and selects 150-250 ms, dialogs and panels 200-300 ms. Use up to 400 ms only for a movement across the full window. Make each exit shorter than its enter, for example 300 ms in and 200-250 ms out.
- **Check:** Grep CSS and JS for `transition`, `transition-duration`, `animation`, `animation-duration`, and `element.animate({duration})`. List each value with its selector. Flag a value over 300 ms that is not a full-window movement. Flag every value of 500 ms or more. Flag a value outside the band for its element type, for example a Library sort menu at 350 ms. For each enter and exit pair (dialogs, popovers, Reference previews, toasts, the Chat panel, margin cards), flag an exit that is not shorter than its enter.
- **Threshold:** 300 ms or less; 400 ms only for full-window movement; 500 ms or more always fails; exit shorter than enter.
- **Conflict:** The STANDARDS.md table lets dialogs and drawers reach 500 ms. NN/g says 400 ms is very slow and 500 ms feels like a drag. NN/g wins for LocalXiv. The app is a calm tool for long sessions, its dialogs are small, and the general STANDARDS.md cap of 300 ms agrees.
- **Sources:** [Animation Standards Reference (Emil Kowalski)](https://github.com/emilkowalski/skills/blob/main/skills/review-animations/STANDARDS.md); [Executing UX Animations: Duration and Motion Characteristics (NN/g)](https://www.nngroup.com/articles/animation-duration/)
- **Merges:** INTERACTION-CRAFT-01, INTERACTION-CRAFT-03

### R-MOT-2 Use one strong ease-out

- **Strength:** should
- **Rule:** Use ease-out for elements that enter or leave. Use ease-in-out for elements that move on the screen. Use plain `ease` only for hover colour changes. Define one strong ease-out token on `:root`, for example `--ease-out: cubic-bezier(0.23, 1, 0.32, 1)`. Use it for the enter and exit of popovers, job toasts, margin cards, and the Chat panel. Use `linear` only for progress bars and spinners. Keep `ease-in` off UI motion.
- **Check:** Grep `transition` and `animation` declarations for the keyword `ease-in` (not `ease-in-out`). Each match is a finding. Each `linear` outside a progress bar or spinner is a finding. Confirm that popovers, job toasts, margin cards, and the Chat panel use the `:root` token. A bare built-in `ease-out` with no custom token is a minor finding.
- **Threshold:** `cubic-bezier(0.23, 1, 0.32, 1)` as the reference curve.
- **Sources:** [Animation Standards Reference (Emil Kowalski)](https://github.com/emilkowalski/skills/blob/main/skills/review-animations/STANDARDS.md)
- **Merges:** INTERACTION-CRAFT-02

### R-MOT-3 Change frequent and keyboard actions at once

- **Strength:** must
- **Rule:** Change these in the same frame as the input, with no custom animation: Library row selection, the Paper, Overview, and Blog switch, the arrow-key highlight in the Library, Suggestions, the outline, and menus, panel toggles by shortcut, and every change that a keyboard shortcut or arrow key starts. For other repeated actions, keep feedback to a brief fade.
- **Check:** Trace each JS `keydown` handler and each Swift menu key equivalent to the element that it changes. That selector has `transition: none`, or the handler sets a class with no motion. The arrow-key highlight has no `background-color` transition. An NSPopover that a shortcut opens sets `animates = false` (this book's addition; no source states it). In a screen recording, the highlight moves in the same frame as the key press, and the view switch shows no cross-fade or slide.
- **Threshold:** 0 ms for keyboard-initiated changes.
- **Sources:** [Motion (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/motion.json); [You Don't Need Animations (Emil Kowalski)](https://emilkowal.ski/ui/you-dont-need-animations)
- **Merges:** MACOS-HIG-30 (frequent interactions), INTERACTION-CRAFT-04

### R-MOT-4 Open menus with no motion

- **Strength:** should
- **Rule:** Open context menus, the Library sort and filter menus, and the More menu with no open animation. After the reader picks an item, let the item show its selection. Then close the menu with a short opacity fade at most. Use NSMenu for the More menu and for context menus where possible, so the system behaviour applies.
- **Check:** In each web menu, the open state has no `transform` transition and no `opacity` transition. Only the close state can have a short opacity fade. In Swift, the More menu and context menus are NSMenu.
- **Threshold:** 0 ms open.
- **Conflict:** INTERACTION-CRAFT-10 asks to scale menus in from the trigger. INTERACTION-CRAFT-05 wins for menus. macOS menus appear with no motion, and readers open them many times a day. R-MOT-5 still applies to popovers and Reference previews.
- **Sources:** [Invisible Details of Interaction Design (Rauno Freiberg)](https://rauno.me/craft/interaction-design)
- **Merges:** INTERACTION-CRAFT-05

### R-MOT-5 Grow popovers from their trigger

- **Strength:** should
- **Rule:** Scale web popovers and Reference previews in from their trigger. Set `transform-origin` to the side of the trigger. Start from scale 0.9-0.97 with opacity 0. Start from a visible scale, never from `scale(0)`. Keep centred dialogs (Settings, Setup, Send to Kindle, Remove paper) at `transform-origin: center`. A native NSPopover draws its own motion and is out of scope.
- **Check:** For each web popover and tooltip, `transform-origin` is not the default `center`, or JS sets it from the anchored side. The initial scale is 0.9 or more. Each `scale(0)` is a finding. The four dialogs keep `center`.
- **Threshold:** Initial scale 0.9-0.97.
- **Sources:** [Animation Standards Reference (Emil Kowalski)](https://github.com/emilkowalski/skills/blob/main/skills/review-animations/STANDARDS.md)
- **Merges:** INTERACTION-CRAFT-10

### R-MOT-6 Accept input during every animation

- **Strength:** must
- **Rule:** Let the reader act while an animation runs. Accept a click, a key press, and Esc at once, also during the open of a dialog, a popover, or the Chat panel.
- **Check:** Grep JS for handlers that wait on `transitionend`, `animationend`, or `setTimeout` before they accept input. Grep for `pointer-events: none` or `inert` set during a transition, and for `isAnimating` guards that drop events. Each is a finding. Manual test: press Esc or click while a dialog, a popover, or the Chat panel opens. The action takes effect at once.
- **Threshold:** 0 ms input lock.
- **Sources:** [Motion (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/motion.json)
- **Merges:** MACOS-HIG-30 (input lock), INTERACTION-CRAFT-06

### R-MOT-7 Use interruptible transitions for elements that stack

- **Strength:** should
- **Rule:** Use CSS transitions or `@starting-style` for the enter, exit, and reposition of elements that toggle or stack quickly: job toasts, margin cards, Reference previews, and the Chat panel. Keep `@keyframes` for spinners and progress bars. Open a margin card with at most a 150 ms opacity fade. When a card above grows and other cards move, move them with a transform transition of 200 ms or less, ease-in-out.
- **Check:** Grep `@keyframes` and `animation:`. A keyframe animation that does the enter, exit, or reposition of an element that can toggle or stack is a finding. Keyframes for spinners and progress bars pass. Manual test: start three jobs quickly. The older toasts move smoothly to their new positions and do not jump. Add a Highlight above three margin cards. The cards below glide and do not jump.
- **Threshold:** Card open fade 150 ms or less; card reposition 200 ms or less.
- **Conflict:** MACOS-HIG-30 asks for no custom animation when the reader opens a margin card. INTERACTION-CRAFT-07 asks for transitions on margin cards. Both hold for different events. Opening a card is frequent, so it gets only a brief fade, which the HIG allows as brief feedback. Cards that move because another card grew get a short glide, because a jump breaks the reader's place in the margin.
- **Sources:** [Building a toast component (Emil Kowalski)](https://emilkowal.ski/ui/building-a-toast-component); [Motion (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/motion.json)
- **Merges:** INTERACTION-CRAFT-07, MACOS-HIG-30 (margin cards)

### R-MOT-8 Animate transform and opacity

- **Strength:** must
- **Rule:** Animate `transform` and `opacity` first. Avoid transitions on `width`, `height`, `max-height`, `top`, `left`, `margin`, and `padding`. List transition properties by name. Write `transition: all` nowhere. In the Overview SVG, put each animated transform on a `<g>` wrapper with `transform-box: fill-box` and `transform-origin: center`.
- **Check:** Grep for `transition: all`, `transition-property: all`, and transitions on `width`, `height`, `max-height`, `top`, `left`, `margin`, or `padding`. Each is a finding. In the Overview SVG, animated nodes use a `<g>` wrapper with `transform-box: fill-box` and `transform-origin: center`.
- **Threshold:** None.
- **Sources:** [Web Interface Guidelines (Vercel)](https://vercel.com/design/guidelines)
- **Merges:** INTERACTION-CRAFT-08

### R-MOT-9 Show a pressed state

- **Strength:** should
- **Rule:** Give every web button a visible pressed state on `:active`. Match AppKit on bezeled buttons: darken the fill. For bezel-less icon buttons, consider a subtle `scale(0.97)`. Leave list rows and menu items to their selection highlight.
- **Check:** Grep `:active` rules. Each button class and each `[role=button]` has one. A button with no `:active` rule is a finding. A scale value is between 0.95 and 0.98, on a bezel-less icon button only. Its `transform` transition is 100-160 ms ease-out. Under Reduce Motion, the scale changes to a fill change (R-MOT-10).
- **Threshold:** Pressed state within 100 ms; scale 0.97 (range 0.95-0.98); 100-160 ms ease-out.
- **Conflict:** INTERACTION-CRAFT-09 asks for `scale(0.97)` on every button. MACOS-HIG-28 and INTERACTION-CRAFT-14 ask web controls to behave like native controls, and AppKit push buttons darken on press. They do not scale. The native behaviour wins on bezeled buttons, because they sit beside AppKit buttons in the same window. The scale stays an option on bezel-less icons, where a darker glyph is hard to see.
- **Sources:** [7 Practical Animation Tips (Emil Kowalski)](https://emilkowal.ski/ui/7-practical-animation-tips); [Animation Standards Reference (Emil Kowalski)](https://github.com/emilkowalski/skills/blob/main/skills/review-animations/STANDARDS.md) (range and duration); [A Technical Deep Dive Into the New Raycast](https://www.raycast.com/blog/a-technical-deep-dive-into-the-new-raycast); [How to make absolutely any app look like a macOS app (Evil Martians)](https://evilmartians.com/chronicles/how-to-make-absolutely-any-app-look-like-a-macos-app)
- **Merges:** INTERACTION-CRAFT-09

### R-MOT-10 Honour Reduce Motion

- **Strength:** must
- **Rule:** When Reduce Motion is on, replace slide, scale, and depth transitions with opacity fades. Stop animating into and out of blur. Remove parallax, spinning, and multi-axis or multi-speed motion. Remove decorative and repeating animation, including Chat streaming effects. Keep the meaning of a state change with a dissolve, a highlight fade, or a colour shift. Make programmatic scrolls instant.
- **Check:** A `@media (prefers-reduced-motion: reduce)` block covers every transition and animation that uses `transform` translate or scale, `filter: blur`, `backdrop-filter` changes, `top`, `left`, `width`, or `height`, and every `@keyframes` loop. System progress indicators are exempt. Grep `scroll-behavior: smooth`, `scrollIntoView({behavior: 'smooth'})`, and `scrollTo({behavior})`. Each one checks `matchMedia('(prefers-reduced-motion: reduce)')`. Grep scroll listeners that set `transform` or `opacity`. Each one is a finding. In Swift, native animations (sidebar, `NSAnimationContext`) check `NSWorkspace.shared.accessibilityDisplayShouldReduceMotion`.
- **Threshold:** None.
- **Conflict:** Apple's Reduced Motion criteria (INTERACTION-CRAFT-19) do not list simple slides. The HIG Accessibility page says to replace x, y, and z transitions with fades, and WCAG 2.3.3 counts any movement. The HIG wins. It is Apple's own platform rule, and a fade keeps the meaning of a slide.
- **Sources:** [Accessibility (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/accessibility.json); [Reduced Motion evaluation criteria (Apple Developer)](https://developer.apple.com/help/app-store-connect/manage-app-accessibility/reduced-motion-evaluation-criteria/); [Understanding SC 2.3.3: Animation from Interactions (W3C)](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions)
- **Merges:** MACOS-HIG-24, INTERACTION-CRAFT-19, INTERACTION-CRAFT-20, A11Y-VISUAL-SYSTEM-22

### R-MOT-11 Delay the first tooltip only

- **Strength:** should
- **Rule:** Delay the first custom tooltip in a group (toolbar-style web controls, margin card actions, Library row actions). While one tooltip is open, open the next one in the group at once, with no delay and no animation.
- **Check:** Tooltip JS keeps a shared warm state. The first show waits for the delay. A show while warm sets `transition-duration: 0ms`, for example through a `data-instant` attribute. Hover across three adjacent icons: only the first tooltip waits. Native `NSView.toolTip` and the HTML `title` attribute are out of scope, because the system controls them.
- **Threshold:** First tooltip transition about 125 ms; later tooltips 0 ms.
- **Sources:** [7 Practical Animation Tips (Emil Kowalski)](https://emilkowal.ski/ui/7-practical-animation-tips)
- **Merges:** INTERACTION-CRAFT-11

### R-MOT-12 Time hover previews

- **Strength:** should
- **Rule:** Show hover feedback on a citation or footnote trigger within 100 ms. Open the Reference preview after the pointer rests on the trigger for 300-500 ms. Close it only after the pointer is away from both the trigger and the preview for more than 500 ms. R-KEY-8 sets the dismissal and focus behaviour.
- **Check:** In JS, the `pointerenter` timer on citations has an open delay of 300-500 ms. The close timer is 500 ms or more and resets when the pointer enters the preview. The hover style on the trigger has no delay.
- **Threshold:** Feedback 100 ms or less; open after a 300-500 ms rest; close after more than 500 ms away.
- **Sources:** [Timing Guidelines for Exposing Hidden Content (NN/g)](https://www.nngroup.com/articles/timing-exposing-content/)
- **Merges:** INTERACTION-CRAFT-12

---

## 2. Typography and reading

### R-TYP-1 Set a comfortable measure

- **Strength:** must
- **Rule:** At the default text size and Normal margins, set the Paper and Blog column to 45-75 characters per line, ideally about 66. Set the column `max-width` in `em` or `rem`, so the measure stays the same when the reader changes text size. Use `em`, `rem`, or `vw` for every Margins preset, and use `ch` for none of them. Keep every preset at every text-size step at 45-90 characters per line. Keep Normal and Wide at 80 characters or fewer.
- **Check:** Find the `max-width` on the Paper and Blog article container. The unit is `em` or `rem`, not `px` or `%`. Estimate characters per line as `max-width` in em times 2, or count them in a screenshot. Test the extremes: Narrow margins at the largest text size, and Wide margins at the smallest text size. Grep the Margins preset CSS and JS for `ch`.
- **Threshold:** 45-75 at default (66 ideal); 45-90 for every preset and size; 80 or fewer for Normal and Wide; about 0.5 em per character (33em is about 66 characters).
- **Conflict:** Bringhurst gives 45-75, Butterick gives 45-90, and WCAG 1.4.8 asks for a setting of 80 or fewer. All three hold here. The default sits in Bringhurst's band. Only the Narrow preset may reach Butterick's 90. WCAG 1.4.8 asks only for a mechanism, and Normal and Wide supply it.
- **Sources:** [Choose a comfortable measure (Elements of Typographic Style Applied to the Web)](http://webtypography.net/2.1.2); [Responsive web design (Butterick)](https://practicaltypography.com/responsive-web-design.html); [Understanding SC 1.4.8: Visual Presentation (W3C)](https://www.w3.org/WAI/WCAG22/Understanding/visual-presentation)
- **Merges:** READING-TYPOGRAPHY-01, READING-TYPOGRAPHY-02, READING-TYPOGRAPHY-06 (width)

### R-TYP-2 Size reading text for long reading

- **Strength:** should
- **Rule:** Set the default body text of the Paper, the Blog, and Chat answers to 15-25 px.
- **Check:** Read the computed `font-size` of reader paragraphs and Chat answer paragraphs at the default text-size step.
- **Threshold:** 15-25 px.
- **Conflict:** R-TYP-4 sets UI text to 13 pt. The two rules cover different text. This rule covers prose that the reader reads for hours. R-TYP-4 covers labels, rows, and controls. Chat answers are prose, so they follow this rule, also in the narrow panel. Margin card text follows R-TYP-4 and R-ANN-5.
- **Sources:** [Point size (Butterick)](https://practicaltypography.com/point-size.html)
- **Merges:** READING-TYPOGRAPHY-03 (body size)

### R-TYP-3 Set line and paragraph spacing

- **Strength:** should
- **Rule:** Set the default `line-height` of reading body text to a unitless value of 1.2-1.45. Make the loosest Line spacing step 1.5 or more. At the default step, separate paragraphs with 0.5em-1em of space and no first-line indent. At the loosest step, make paragraph spacing at least 1.5 times the line spacing. Give each block that can wrap to three or more lines (note cards, abstracts, Suggestions, Chat answers) a `line-height` of at least the font's `normal`.
- **Check:** The `line-height` on reader paragraphs is a unitless number in the band. A `px` line-height on text that the text-size control changes is a finding. The Line spacing step array has a maximum of 1.5 or more. The reader `p` rule has a margin of 0.5em-1em and `text-indent: 0`, or an indent with a margin of 0. At the loosest step, paragraph spacing is 1.5 times the line spacing or more. Multi-line UI blocks are not tighter than `normal`.
- **Threshold:** Default 1.2-1.45 unitless; loosest step 1.5 or more; paragraph space 50-100% of body size at default; 1.5 times line spacing or more at the loosest step.
- **Conflict:** Butterick sets 120-145% line spacing and 50-100% paragraph space. WCAG 1.4.8 asks for a setting with line spacing of 1.5 or more and paragraph spacing of 1.5 times that. Butterick governs the default step. WCAG governs the loosest step. No step must satisfy both.
- **Sources:** [Line spacing (Butterick)](https://practicaltypography.com/line-spacing.html); [Space between paragraphs (Butterick)](https://practicaltypography.com/space-between-paragraphs.html); [Understanding SC 1.4.8: Visual Presentation (W3C)](https://www.w3.org/WAI/WCAG22/Understanding/visual-presentation); [Typography (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/typography.json)
- **Merges:** READING-TYPOGRAPHY-05, READING-TYPOGRAPHY-06 (spacing), READING-TYPOGRAPHY-07, MACOS-HIG-18 (leading), A11Y-VISUAL-SYSTEM-14 (leading)

### R-TYP-4 Size and weight UI text like macOS

- **Strength:** must
- **Rule:** Set UI text (sidebar, Library rows, metadata, menus, toasts, margin cards, dialogs) to 13 px by default. Show all text at 10 px or more at the default text size. This includes citation superscripts, figure captions, badges, counts, keyboard hints, and Overview SVG labels at the default window width. Use weights from Regular (400) to Bold (700). Give a thin custom weight a larger size; only large display numerals may use a light weight. Keep the typefaces few, and map each family stack to one role: UI, reading, code, or math.
- **Check:** Grep CSS for `font-size` below `10px`, and for `rem` or `em` values that compute below 10 px. Read the computed `font-size` of every text node at the default text size. Chrome body text is 13 px. Grep CSS for `font-weight` 100, 200, 300, or `lighter`. Grep Swift for `NSFont.Weight` `.ultraLight`, `.thin`, or `.light` on text, and for `NSFont` sizes below 10. Count the distinct `font-family` stacks and map each to a role.
- **Threshold:** 13 pt default; 10 pt minimum; weights 400-700.
- **Sources:** [Typography (Apple HIG, JSON)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/typography.json); [Typography (Apple HIG)](https://developer.apple.com/design/human-interface-guidelines/typography)
- **Merges:** MACOS-HIG-18, READING-TYPOGRAPHY-04, A11Y-VISUAL-SYSTEM-10, A11Y-VISUAL-SYSTEM-13, A11Y-VISUAL-SYSTEM-14 (typefaces)

### R-TYP-5 Let readers enlarge text to 200%

- **Strength:** must
- **Rule:** Let the reader enlarge reading text to at least 200% of the default. At every step up to 200%, show no clipped, overlapping, or horizontally scrolling content in the Paper, the Blog, margin cards, the Chat panel, Reference previews, the toolbar title, and dialogs. Show the full text of a truncated UI label on hover or focus. If View > Zoom (Command-plus, Command-minus) does not drive WKWebView `pageZoom`, make the app's own size control also scale Library, Notes, and dialog text.
- **Check:** In the text-size settings, the maximum divided by the default is 2.0 or more. Screenshot the Paper with equations, tables, and margin cards at the maximum. At 200% in a default-size window, `scrollWidth` equals `clientWidth` on the reader. Check what View > Zoom changes.
- **Threshold:** 200%.
- **Sources:** [Accessibility (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/accessibility.json); [Understanding SC 1.4.4: Resize Text (W3C)](https://www.w3.org/WAI/WCAG22/Understanding/resize-text); [Understanding SC 1.4.8: Visual Presentation (W3C)](https://www.w3.org/WAI/WCAG22/Understanding/visual-presentation)
- **Merges:** MACOS-HIG-19, READING-TYPOGRAPHY-06 (resize), A11Y-VISUAL-SYSTEM-11

### R-TYP-6 Survive a text spacing override

- **Strength:** must
- **Rule:** Keep all content and controls intact when the reader sets line height to 1.5, paragraph spacing to 2em, letter spacing to 0.12em, and word spacing to 0.16em. Use `min-height` on text containers. Use a fixed `height` with `overflow: hidden` on none of them.
- **Check:** Inject `* { line-height:1.5 !important; letter-spacing:.12em !important; word-spacing:.16em !important } p { margin-bottom:2em !important }`. Screenshot Home, Library, Paper, Notes, Chat, margin cards, job toasts, Library rows, `#tag` chips, dialog buttons, and menus. Grep for a fixed `height` or `max-height` together with `overflow: hidden` on rows, chips, buttons, cards, and toasts.
- **Threshold:** Line height 1.5, paragraph spacing 2, letter spacing 0.12, word spacing 0.16 times the font size.
- **Sources:** [Understanding SC 1.4.12: Text Spacing (W3C)](https://www.w3.org/WAI/WCAG22/Understanding/text-spacing)
- **Merges:** READING-TYPOGRAPHY-08, A11Y-VISUAL-SYSTEM-12

### R-TYP-7 Align left and hyphenate on purpose

- **Strength:** must (justified text needs hyphenation); should (the rest)
- **Rule:** Left-align reading body text by default (`text-align: start`). If a block is justified, set `hyphens: auto` on the same selector. Set `hyphens: none` on headings, the paper title, sidebar outline rows, and toolbar labels. Consider `hyphens: auto` in narrow columns such as margin cards and Chat answers.
- **Check:** Grep reader CSS for `text-align: justify`. Each match also sets `hyphens: auto`. The default body is `start` or `left`. Grep for `hyphens: auto` that `h1`-`h6`, the title, or the outline inherit. Check whether margin card and Chat answer paragraphs set `hyphens: auto`.
- **Threshold:** None.
- **Sources:** [Justified text (Butterick)](https://practicaltypography.com/justified-text.html); [Hyphenation (Butterick)](https://practicaltypography.com/hyphenation.html)
- **Merges:** READING-TYPOGRAPHY-09, READING-TYPOGRAPHY-10

### R-TYP-8 Wrap lines with `pretty` and `balance`

- **Strength:** should
- **Rule:** Apply `text-wrap: pretty` to paper paragraphs, list items, block quotes, figure captions, and Chat answer paragraphs. Apply `text-wrap: balance` only to short text: `h1`-`h3`, the paper title, card titles, and short captions. Keep `balance` off paragraphs, global selectors, and boxed elements with a border or background, such as buttons, chips, and cards.
- **Check:** Grep for `text-wrap: pretty` and `text-wrap: balance` with their selectors. Screenshot a long section and look for single-word last lines. Time the layout of a very long paragraph.
- **Threshold:** None.
- **Sources:** [Better typography with text-wrap pretty (WebKit)](https://webkit.org/blog/16547/better-typography-with-text-wrap-pretty/); [Improve Text Layout and Legibility (GoogleChrome)](https://github.com/GoogleChrome/modern-web-guidance-src/blob/main/guides/user-experience/improve-text-layout-and-legibility/guide.md)
- **Merges:** READING-TYPOGRAPHY-11, READING-TYPOGRAPHY-12

### R-TYP-9 Keep headings few and quiet

- **Strength:** should
- **Rule:** Style at most three visible heading levels. Two is better. Give `h4`-`h6` from converted papers the `h3` style or a run-in style. Mark headings with bold and a small size step. Keep each heading under twice the body size. Use plain case, upright type, no underline, and left alignment for headings. Give each heading more space above than below, and more than the space between paragraphs.
- **Check:** Count the distinct heading styles in reader CSS. Grep headings for `text-transform: uppercase`, `font-style: italic`, `text-decoration: underline`, and `text-align: center`. Divide each `h1`-`h3` `font-size` by the body `font-size`. For `h1`-`h3`, `margin-top` is greater than `margin-bottom`, and both are greater than the `p` margin.
- **Threshold:** Three levels or fewer; heading size under 2 times body.
- **Sources:** [Headings (Butterick)](https://practicaltypography.com/headings.html); [Point size (Butterick)](https://practicaltypography.com/point-size.html); [Space above and below (Butterick)](https://practicaltypography.com/space-above-and-below.html)
- **Merges:** READING-TYPOGRAPHY-03 (headings), READING-TYPOGRAPHY-14, READING-TYPOGRAPHY-15

### R-TYP-10 Use tabular numerals in tables

- **Strength:** should
- **Rule:** Set tables of numbers and numeric columns (Library dates and counts, sidebar counts) in tabular lining numerals.
- **Check:** Grep CSS for `font-variant-numeric: lining-nums tabular-nums` on paper tables, Library numeric columns, and other columns that the reader scans vertically.
- **Threshold:** None.
- **Sources:** [Designing Tables to be Read, Not Looked At (A List Apart)](https://alistapart.com/article/web-typography-tables/)
- **Merges:** READING-TYPOGRAPHY-17

### R-TYP-11 Use old-style numerals in running text

- **Strength:** consider
- **Rule:** Use old-style numerals in running body text and lining numerals in headings, when the reading font has both.
- **Check:** Grep reader CSS for `font-variant-numeric: oldstyle-nums` on the article body and `lining-nums` on `h1`-`h3`. Check that each selectable font has an `onum` feature. Omit the rule for a font that has none.
- **Threshold:** None.
- **Sources:** [Web Typography: Numerals (A List Apart)](https://alistapart.com/article/web-typography-numerals/)
- **Merges:** READING-TYPOGRAPHY-16

### R-TYP-12 Style tables to be read

- **Strength:** should
- **Rule:** Style paper tables with no outer frame, no zebra stripes, and no fills. Use light rules in one direction only. Left-align text, right-align numbers, and align headers with their data. Keep tables at their natural width.
- **Check:** In the paper table CSS: no `border` on `table`; no `nth-child` or background fills on rows; any rules are lighter and in one direction; numeric `td` and `th` use `text-align: right`; `width` is `auto`, not `100%`; cell padding is small.
- **Threshold:** Example cell padding `0.125em 0.5em 0.25em 0.5em`.
- **Sources:** [Designing Tables to be Read, Not Looked At (A List Apart)](https://alistapart.com/article/web-typography-tables/)
- **Merges:** READING-TYPOGRAPHY-18

### R-TYP-13 Set citation markers as true superscripts

- **Strength:** should
- **Rule:** Set citation and footnote markers as true superscripts that keep the line spacing even. A click or focus on a marker opens the Reference preview anchored to the marker, with no jump to the bibliography.
- **Check:** The `sup` rule uses `font-variant-position: super`, with `vertical-align: baseline` and `font-size: inherit` inside `@supports`. Screenshot a paragraph with markers and compare the line gaps. Click and focus a marker: the preview opens at the marker and the page does not scroll.
- **Threshold:** None.
- **Sources:** [Web Typography: Numerals (A List Apart)](https://alistapart.com/article/web-typography-numerals/)
- **Merges:** READING-TYPOGRAPHY-19

### R-TYP-14 Hang quotation marks

- **Strength:** consider
- **Rule:** For hanging quotes on block quotes and Highlight quote text, use `hanging-punctuation: first last`. The property has limited browser support, so confirm that the WKWebView supports it.
- **Check:** Grep CSS for `hanging-punctuation` on `blockquote` and Highlight quote text. The container has enough inline padding that the hung mark causes no horizontal scroll.
- **Threshold:** None.
- **Sources:** [hanging-punctuation (MDN)](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/hanging-punctuation)
- **Merges:** READING-TYPOGRAPHY-13

### R-TYP-15 Fit figures, tables, and equations

- **Strength:** must
- **Rule:** Keep every figure, table, and display equation inside its container. Scale figures and images proportionally first. As a fallback only, scroll a wide table or equation horizontally inside its own container. Keep the page free of horizontal scroll at every window width. The source does not mention equations. This book adds them because they overflow in the same way.
- **Check:** `img` and `svg` have `max-width: 100%`. Table wrappers and display equation containers (for example `.ltx_equation`) have `overflow-x: auto`. At the minimum window width, on a paper with wide equations, `document.scrollingElement.scrollWidth` equals `clientWidth`.
- **Threshold:** Body text readable at 320-2560 px width with no horizontal page scroll.
- **Sources:** [ARCH 1.0 (Aris)](https://aris.pub/arch/1.0/)
- **Merges:** READING-TYPOGRAPHY-21

### R-TYP-16 Restore the Reading position

- **Strength:** must
- **Rule:** Save each Paper's Reading position: the view, the passage, and in the Blog, the section. Restore it when the Paper opens, after fonts, math, and figures lay out. Restore each view's scroll position on Back and Forward. A jump from a Reference preview or a citation does not move the Reading position until the reader scrolls there.
- **Check:** The reader JS stores a scroll anchor per Paper, debounced on scroll. The restore runs after layout. Test: open a Paper, scroll, close it, reopen it. Test: go from the Paper to the Library, then Back. The scroll offset returns.
- **Threshold:** None.
- **Sources:** [Web Interface Guidelines (Vercel)](https://vercel.com/design/guidelines); [Reader FAQ (Readwise)](https://docs.readwise.io/reader/docs/faqs)
- **Merges:** READING-TYPOGRAPHY-30 (restore), INTERACTION-CRAFT-29 (Back and Forward)

### R-TYP-17 Track reading progress apart from position

- **Strength:** consider
- **Rule:** Track a furthest-read progress for each Paper, apart from the Reading position. Move it forward only on steady reading, not on fast scrolling or skimming. Keep it from moving backward. Show a return-to-position control when the current location differs from the progress.
- **Check:** A furthest-read value only increases. A return control appears when location and progress differ.
- **Threshold:** None.
- **Note:** The input marked this "must". The source is a product FAQ, not a guideline, so this book lowers it.
- **Sources:** [Reader FAQ (Readwise)](https://docs.readwise.io/reader/docs/faqs)
- **Merges:** READING-TYPOGRAPHY-30 (progress)

### R-TYP-18 Contain nested scroll and anchor headings

- **Strength:** should
- **Rule:** Set `overscroll-behavior: contain` on nested scroll areas (the Chat panel, the margin, menus, popovers, dialogs), so their scroll does not move the Paper. Give each heading that the outline links to a `scroll-margin-top` equal to the height of the toolbar and any sticky header.
- **Check:** Grep `overscroll-behavior` on those scroll containers. Grep `scroll-margin-top` on outline targets. Click an outline row: the heading lands fully below the toolbar.
- **Threshold:** None.
- **Sources:** [Web Interface Guidelines (Vercel)](https://vercel.com/design/guidelines)
- **Merges:** INTERACTION-CRAFT-29 (containment and anchors)

---

## 3. Colour, contrast, and themes

### R-COL-1 Follow the system appearance; scope the reading theme

- **Strength:** must
- **Rule:** Make the Native shell and all chrome follow the system appearance (Light, Dark, Auto). Update them live when the appearance changes. Offer no app setting that overrides the chrome appearance. Apply the reading theme (Light, Sepia, Dark) to reading surfaces only. Make Automatic the default reading theme. In Automatic, reading surfaces follow the system appearance. Label the setting in Settings and the Aa popover as a reading setting. When the system is Dark, show every surface dark, except a reading surface that the reader set to Light. When the reading theme is Dark or Sepia, show no light panel inside the reading surfaces.
- **Check:** Grep Swift for `NSApp.appearance =`, `window.appearance =`, and `NSAppearance(named:)` set from the reading theme. Each is a finding. Chrome tokens switch under `@media (prefers-color-scheme: dark)`, or under a value that Swift passes from `effectiveAppearance`. The theme attribute sits on the reading surfaces only. A fresh install starts in Automatic. With a Paper open, change Appearance in System Settings: the shell and the web chrome change with no reload. With the system in Dark, screenshot Home, Library, Notes, Chat, Settings, Setup, Send to Kindle, Remove paper, a job toast, a Reference preview, and the Aa popover. Grep CSS for light literals (`#fff`, `white`, `rgb(255`) outside the theme token blocks.
- **Threshold:** None.
- **Conflict:** The HIG says to avoid an app-specific appearance setting and gives no exception (MACOS-HIG-09, READING-26, A11Y-18). NN/g says the dark option must reach every screen (READING-28). Apple Books offers a page background of Light, Dark, or Automatic (READING-27). For LocalXiv, the chrome follows the system, because AppKit draws the shell and the reader set the system choice on purpose. The reading theme stays, because Sepia has no system equivalent, readers read for hours, and Apple's own reading app keeps a content-only page theme. The Automatic default gives a reader who never opens the setting the system choice on every screen, which satisfies NN/g.
- **Sources:** [Dark Mode (Apple HIG, JSON)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/dark-mode.json); [Dark Mode (Apple HIG)](https://developer.apple.com/design/human-interface-guidelines/dark-mode); [Change a book's appearance in Books on Mac (Apple Support)](https://support.apple.com/guide/books/change-a-books-appearance-ibks8923126d/mac); [Dark Mode vs. Light Mode (NN/g)](https://www.nngroup.com/articles/dark-mode/)
- **Merges:** MACOS-HIG-09, READING-TYPOGRAPHY-26, READING-TYPOGRAPHY-27 (Automatic), READING-TYPOGRAPHY-28, A11Y-VISUAL-SYSTEM-18

### R-COL-2 Show no blank or wrong-theme frame

- **Strength:** must
- **Rule:** Keep the WKWebView hidden until it draws the new view in the current theme. Set the theme attribute in an inline `<head>` script before first paint. Match `underPageBackgroundColor` and the window background to the theme.
- **Check:** In Swift, the WKWebView stays at alpha 0 until first paint (`didFinish` navigation plus a `requestAnimationFrame` or presentation-update callback). An inline `<head>` script sets the theme. Record launch and the Paper, Overview, and Blog switches in Dark and Sepia: no white frame shows.
- **Threshold:** 0 blank frames.
- **Sources:** [A Technical Deep Dive Into the New Raycast](https://www.raycast.com/blog/a-technical-deep-dive-into-the-new-raycast)
- **Merges:** INTERACTION-CRAFT-16

### R-COL-3 Switch themes in one frame

- **Strength:** should
- **Rule:** When the reading theme or the system appearance changes, disable all CSS transitions for that one style change, so every surface changes colour in the same frame.
- **Check:** The JS that applies the theme adds a temporary `* { transition: none !important }` style, sets the theme attribute, forces a style flush with `getComputedStyle`, then removes the temporary style. In a recording of a theme switch, no element fades after the rest.
- **Threshold:** None.
- **Sources:** [Disable transitions on theme toggle (Paco Coursey)](https://paco.me/writing/disable-theme-transitions)
- **Merges:** INTERACTION-CRAFT-18

### R-COL-4 Meet the text contrast floor

- **Strength:** must
- **Rule:** Give every text colour at least 4.5:1 against its surface for text up to 17 pt, and 3:1 for text of 18 pt or more or bold. Meet this in Light, Sepia, and Dark, and with Increase Contrast on. Measure text on a translucent surface against the worst-case backdrop.
- **Check:** For each text token (primary, secondary, tertiary, placeholder, link, green accent text, chip text, toast text) on each surface token (page, sidebar, card, popover, dialog, toast) in each theme, compute the WCAG ratio from the CSS and NSColor values. Do not round. A pair under 4.5:1 for text under 18 px and not bold fails. An `@media (prefers-contrast: more)` block raises the low pairs.
- **Threshold:** 4.5:1 up to 17 pt; 3:1 at 18 pt or bold.
- **Sources:** [Accessibility (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/accessibility.json); [Dark Mode (Apple HIG)](https://developer.apple.com/design/human-interface-guidelines/dark-mode)
- **Merges:** MACOS-HIG-20, READING-TYPOGRAPHY-23 (floor), A11Y-VISUAL-SYSTEM-01

### R-COL-5 Reach the reading contrast targets

- **Strength:** should
- **Rule:** Aim for 7:1 for custom reading colours and small custom-coloured text. Set reading body text (Paper, Blog, Chat answers) to APCA Lc 90 or more against the page, and never below Lc 75. Give small non-body text the Lc that its size needs. Keep placeholder and disabled text at Lc 30 or more and small outline icons at Lc 45 or more. Keep dividers that people must see above Lc 15. Lc 15 serves only non-semantic solid shapes of 5 px or more.
- **Check:** Run an APCA calculator on body text against the page in Light, Sepia, and Dark at the default size. Use the absolute Lc for light text on dark. Lc 75 is valid only at 18 px/400, 16 px/500, or larger. Check Library row metadata, timestamps, sidebar counts, figure captions, and keyboard hints at their sizes. Compute the WCAG ratio of Dark and Sepia body text.
- **Threshold:** Body Lc 90 (minimum Lc 75); non-body 12 px/400 at Lc 90, 15 px/400 at Lc 75; placeholder and disabled Lc 30; small outline icons Lc 45; WCAG target 7:1 for small custom text.
- **Conflict:** WCAG 2 (R-COL-4) and APCA disagree on dark pairs. WCAG 2 overstates contrast for dark colours. Both rules apply. R-COL-4 is the floor that Apple's Accessibility Inspector checks. This rule is the target. A Dark pair must pass both, and a WCAG 2 pass alone does not clear it.
- **Sources:** [APCA in a Nutshell (Myndex)](https://github.com/Myndex/SAPC-APCA/blob/master/documentation/APCA_in_a_Nutshell.md); [Dark Mode (Apple HIG, JSON)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/dark-mode.json); [Dark Mode (Apple HIG)](https://developer.apple.com/design/human-interface-guidelines/dark-mode)
- **Merges:** MACOS-HIG-21 (contrast), READING-TYPOGRAPHY-23 (7:1 target), A11Y-VISUAL-SYSTEM-02, A11Y-VISUAL-SYSTEM-03

### R-COL-6 Give controls and states 3:1

- **Strength:** must
- **Rule:** Give at least 3:1 against adjacent colours to every control boundary that is the only cue, every state indicator, and every meaningful icon or figure line.
- **Check:** Measure from CSS values, not screenshots. Check the Home search field border when the field has no fill, checkbox and switch outlines, the selected segment indicator, Reading state marks, filter chip borders, icon-only toolbar-style and card buttons, and figure lines that carry meaning. Do not round: 2.999:1 fails. Give a 1 px hairline that carries meaning clearly more than 3:1, or make it thicker.
- **Threshold:** 3:1, not rounded.
- **Sources:** [Understanding SC 1.4.11: Non-text Contrast (W3C)](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast)
- **Merges:** A11Y-VISUAL-SYSTEM-04

### R-COL-7 Pair every colour with a shape or a word

- **Strength:** must
- **Rule:** Give every colour-coded state a shape, a symbol, or a text label, and an accessible label. Make the Reading state marks (New, Reading, Read) differ by shape or fill, with a tooltip and an `aria-label`. Show the names of the four Highlight colours (Key point, Question, Use in my work, Disagree) in the card and in the menu. Give success, error, and progress states in job toasts an icon and text. Give errors text. Show text on tag chips and filters. Keep Overview figure categories distinct without hue.
- **Check:** Inspect the Reading state markup for distinct shapes and labels. Inspect Highlight cards, menus, and job toasts for names and symbols. Take a grayscale screenshot: every state stays distinct.
- **Threshold:** None.
- **Sources:** [Accessibility (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/accessibility.json); [Error-Message Guidelines (NN/g)](https://www.nngroup.com/articles/error-message-guidelines/)
- **Merges:** MACOS-HIG-23, A11Y-VISUAL-SYSTEM-15, STATES-FEEDBACK-18 (colour)

### R-COL-8 Give each colour one meaning

- **Strength:** should
- **Rule:** Give each colour one meaning. Use the green only for content emphasis that is not interactive. Use the link colour only for clickable text. If the green and the link colour are close, underline links in text. In AppKit, let the system put the accent where it draws it: sidebar symbols, selection, the one prominent toolbar action, and default buttons. In the web layer, use the accent for selection, focus rings, and the primary button. Get system colours from the system: `NSColor.labelColor`, `.secondaryLabelColor`, `.separatorColor`, and `.controlAccentColor` in Swift, and the value that the Native shell passes, or a CSS system colour keyword, in the web layer. Keep each dynamic system colour in its own role; for example, keep `separatorColor` off text.
- **Check:** Map every use of the green token. All uses share one meaning. Grep for non-interactive labels, tags, headings, and badges in the link colour. Grep for hex values copied from system colours (for example `#007AFF`, `#0A84FF`). Hex and `rgb` literals appear only in theme token blocks (`:root`, `[data-theme]`), and components use `var(--…)`. Swift uses the semantic `NSColor` values for those roles, not RGB literals.
- **Threshold:** None.
- **Conflict:** The A11Y-16 check limits the system accent to selection and focus. HIG Sidebars and HIG Color also put the accent on sidebar symbols and buttons. The HIG wins. AppKit applies the accent in those places by itself, and a shell that fights it looks foreign. The web layer uses the same set and keeps the green for content only.
- **Sources:** [Color (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/color.json); [Sidebars (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/sidebars.json); [Color (Butterick)](https://practicaltypography.com/color.html)
- **Merges:** MACOS-HIG-22 (meaning, system colours), A11Y-VISUAL-SYSTEM-16, READING-TYPOGRAPHY-29

### R-COL-9 Define colours for every theme and for Increase Contrast

- **Strength:** must
- **Rule:** Define every custom colour token for Light, Sepia, and Dark. Define it again under `@media (prefers-contrast: more)` with a much larger difference. Give each custom colour in the Swift asset catalog a High Contrast appearance. Test Dark with Increase Contrast and Reduce Transparency on, one at a time and together.
- **Check:** Each custom colour token has a value per theme and inside a `prefers-contrast: more` block that overrides text, border, separator, focus, and accent tokens. WebKit supports this query. Asset-catalog colours have High Contrast variants.
- **Threshold:** None.
- **Sources:** [Color (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/color.json); [Accessibility (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/accessibility.json)
- **Merges:** MACOS-HIG-20 (Increase Contrast), MACOS-HIG-22 (variants), A11Y-VISUAL-SYSTEM-17

### R-COL-10 Choose soft theme base colours

- **Strength:** should
- **Rule:** In Light, use a slightly off-white page and slightly off-black text. In Dark, use dark grey for the base, near `#121212`. Use off-white text in Dark at three emphasis levels: about 87%, 60%, and 38% white. Keep body text below pure white. Make Dark surfaces lighter as elevation rises: page, then cards, then popovers and menus, then dialogs. Use lighter, less saturated tones for the green and the Highlight colours in Dark than in Light. Keep text greyscale and use colour on purpose.
- **Check:** Light text is not `#000` and the Light page is not `#fff`. Dark text is not `#fff` and the Dark page is not `#000`. OKLCH L rises with elevation in Dark. The Dark green and Highlight tokens have a higher L and a lower C than in Light.
- **Threshold:** Reference Light pair `#fffff8` and `#111111`; Dark base near `#121212`; text 87% / 60% / 38%.
- **Sources:** [Tufte CSS](https://edwardtufte.github.io/tufte-css/); [Material Design: Dark Theme](https://m2.material.io/develop/android/theming/dark); [Design a dark theme with Material and Figma (Google Codelab)](https://codelabs.developers.google.com/codelabs/design-material-darktheme)
- **Merges:** READING-TYPOGRAPHY-24, A11Y-VISUAL-SYSTEM-19, A11Y-VISUAL-SYSTEM-20

### R-COL-11 Dim white images in Dark

- **Strength:** should
- **Rule:** In the Dark reading theme, slightly darken paper figures, Blog images, and raster Overview content that have white backgrounds, for example with `filter: brightness(0.85)` to `brightness(0.9)` or a light figure plate. Figure renders from the Figure library use the dark Figure palette instead of a filter. Keep photos uninverted. This last point is this book's choice; the sources do not state it.
- **Check:** Grep the Dark theme CSS for a filter or plate on `figure img`, Blog images, and Overview raster content. The Overview SVG background in Dark is not white. No `filter: invert` on photos. Screenshot a figure-heavy Paper in Dark: no full-brightness white rectangle.
- **Threshold:** None.
- **Sources:** [Dark Mode (Apple HIG, JSON)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/dark-mode.json); [Dark Mode (Apple HIG)](https://developer.apple.com/design/human-interface-guidelines/dark-mode)
- **Merges:** MACOS-HIG-21 (images), READING-TYPOGRAPHY-22, A11Y-VISUAL-SYSTEM-21

### R-COL-12 Keep Highlights, selection, and search hits readable

- **Strength:** must
- **Rule:** Keep paper text on each Highlight colour at 4.5:1 or more. Keep each Highlight fill at 3:1 or more against the page. Meet both in Light, Sepia, and Dark. Apply the same to `::selection` and to search hits. Set the text colour on highlighted spans in every theme. WebKit picks a contrasting text colour only for its own default highlight.
- **Check:** For each Highlight token in each theme, compute the effective fill after opacity or blend. Compute text on fill and fill against page. The Dark and Sepia selectors override the Highlight background tokens. Highlighted spans set `color` or use `contrast-color()`.
- **Threshold:** Text on Highlight 4.5:1 or more; Highlight against page 3:1 or more.
- **Sources:** [Anatomy of an Accessible eBook Reader for the Web (Scribd)](https://tech.scribd.com/blog/2018/anatomy-ebook-reader.html); [WebKit commit 32caf7b](https://github.com/WebKit/WebKit/commit/32caf7b3a6b7d33bf91842653832615081325b90)
- **Merges:** ANNOTATION-AI-01, ANNOTATION-AI-02

### R-COL-13 Lower the grade of light text in Dark

- **Strength:** consider
- **Rule:** Make light text on dark look as heavy as dark text on light. Lower the font's grade axis in the Dark theme. Keep the weight the same, so lines do not reflow when the theme switches.
- **Check:** Grep the Dark theme CSS for `font-variation-settings` with a negative `"GRAD"` value on a reading font that has a GRAD axis. Switch Light and Dark on one paragraph: the line breaks stay the same. A `font-weight` change between themes that reflows text is a finding.
- **Threshold:** None.
- **Sources:** [Keeping type consistent in changing conditions (Adobe Design)](https://adobe.design/ideas/keeping-type-consistent-in-changing-conditions)
- **Merges:** READING-TYPOGRAPHY-25

---

## 4. Focus and keyboard

### R-KEY-1 Keep the standard shortcuts

- **Strength:** must
- **Rule:** Keep the standard macOS shortcuts with their standard meanings. Command-F finds in the open Paper. Option-Command-F focuses the toolbar search field. Command-G and Shift-Command-G find next and previous. Command-comma opens Settings. Command-W closes. Command-Z undoes. Option-Command-T shows or hides the toolbar. Control-Command-F enters full screen. Let these combinations pass through the web layer to the menu bar. Redefine a standard shortcut only when its standard action makes no sense in LocalXiv, and record the reason in the code.
- **Check:** Compare the `keyEquivalent` values in the menu builder with Apple's standard shortcut table. Grep JS `keydown` listeners for `metaKey` combinations that call `preventDefault` on F, G, W, Z, comma, or period. List every custom key equivalent in Swift and in the JS keydown maps. Each clash without a recorded reason is a finding.
- **Threshold:** None.
- **Conflict:** MACOS-HIG-27 forbids any override. INTERACTION-CRAFT-23 quotes the HIG Keyboards page, which says "in general" and allows a redefinition where the standard action makes no sense. The source wording wins, with a recorded reason for each exception.
- **Sources:** [Keyboards (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/keyboards.json)
- **Merges:** MACOS-HIG-27 (shortcuts), INTERACTION-CRAFT-23 (shortcuts)

### R-KEY-2 Let Esc cancel

- **Strength:** must
- **Rule:** Let Esc close the open popover, menu, Reference preview, or dialog, or cancel the current action. Let Command-period do the same in alerts and dialogs. In AppKit, implement `cancelOperation:`.
- **Check:** Each popover, dialog, menu, and preview has an Escape handler in JS, or `cancelOperation:` in Swift. Press Esc on each one.
- **Threshold:** None.
- **Sources:** [Keyboards (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/keyboards.json); [Alerts (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/alerts.json)
- **Merges:** INTERACTION-CRAFT-23 (Esc), MACOS-HIG-11 (Esc and Command-period)

### R-KEY-3 Support Full Keyboard Access

- **Strength:** must
- **Rule:** With Full Keyboard Access on, let Tab and Shift-Tab reach every web control in visual order.
- **Check:** Turn on Full Keyboard Access. Tab through Home, Library, the Paper, the margin, Chat, Notes, and each dialog. Every control gets focus in visual order.
- **Threshold:** None.
- **Sources:** [Keyboards (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/keyboards.json)
- **Merges:** MACOS-HIG-27 (Full Keyboard Access), INTERACTION-CRAFT-23 (Tab order)

### R-KEY-4 Keep Cocoa text behaviour in web fields

- **Strength:** should
- **Rule:** Let every web text field (Home search, the Note editor, the Chat input, the `#tag` filter) behave like a Cocoa text field. System Emacs-style key bindings, text replacements, and the smart-quote setting work there.
- **Check:** Grep JS `keydown` handlers for `preventDefault` on Control-A, Control-E, Control-K, Control-F, Control-B, Control-N, Control-P, or Option-arrow inside inputs and textareas. Each is a finding. In the app, type a system text replacement in the Note editor and confirm that it expands.
- **Threshold:** None.
- **Sources:** [What Makes an App Feel Right on the Mac? (Coyote Tracks)](https://coyotetracks.org/blog/app-feel-on-mac/)
- **Merges:** MACOS-HIG-08 (text fields)

### R-KEY-5 Show focus rings with `:focus-visible`

- **Strength:** must
- **Rule:** Show focus rings with `:focus-visible`. Use `:focus-within` for grouped controls. Where a rule removes the default outline, draw a replacement: an outline of 2 px or more, or a `box-shadow` ring together with `outline: 2px solid transparent`.
- **Check:** Grep `:focus` rules without `-visible`. Grep `outline: none` and `outline: 0`. Each needs a `:focus-visible` rule that draws a 2 px or wider outline, or a box-shadow ring with a transparent 2 px outline.
- **Threshold:** None.
- **Sources:** [Web Interface Guidelines (Vercel)](https://vercel.com/design/guidelines); [C40: Creating a two-color focus indicator (W3C)](https://www.w3.org/WAI/WCAG22/Techniques/css/C40)
- **Merges:** INTERACTION-CRAFT-21 (rings), A11Y-VISUAL-SYSTEM-05 (outline)

### R-KEY-6 Make focus rings large and clear

- **Strength:** should
- **Rule:** Make each focus indicator at least a 2 CSS px perimeter of the control, or 3 px if inset. Give it at least 3:1 change between its focused and unfocused pixels, in Light, Sepia, and Dark. Where focus can land on varied backgrounds (Overview SVG nodes, highlighted text, figures, coloured cards), use two bands of 2 px or more in colours 9:1 apart. Over images and gradients, check the ring pixel by pixel, because the two-colour guarantee holds only over one solid colour.
- **Check:** `:focus-visible` rules use an `outline-width` of 2 px or more with an `outline-offset` of 0 or more. An inset indicator is 3 px or more. Compute the ring colour against the background in each theme. Sepia has the highest risk. A tinted list row or sidebar item as the indicator passes only if the tinted area meets both the area rule and 3:1. This criterion is Level AAA.
- **Threshold:** 2 px perimeter (3 px inset); 3:1 change; two-colour bands 9:1 apart.
- **Sources:** [Understanding SC 2.4.13: Focus Appearance (W3C)](https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance); [C40: Creating a two-color focus indicator (W3C)](https://www.w3.org/WAI/WCAG22/Techniques/css/C40)
- **Merges:** INTERACTION-CRAFT-22, A11Y-VISUAL-SYSTEM-05 (two colours), A11Y-VISUAL-SYSTEM-06

### R-KEY-7 Keep the focused element in view

- **Strength:** must
- **Rule:** Keep the focused element visible under the toolbar, sticky headers, the Chat composer, open panels, and job toasts. Set `scroll-padding-top` and `scroll-padding-bottom` on each scroll container to the heights of its sticky or fixed layers.
- **Check:** Each scroll container in the web layer sets scroll padding at least as large as its sticky or fixed layers (reader top bar, Library header, Chat composer, toast stack). Tab forward and backward through the Paper, the Library, Notes, margin cards, and Chat while a toast shows. No focused element is fully hidden. Under a dimming or blur overlay, the ring still meets 3:1.
- **Threshold:** Not entirely hidden (Level AA).
- **Sources:** [Understanding SC 2.4.11: Focus Not Obscured (Minimum) (W3C)](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum); [Web Interface Guidelines (Vercel)](https://vercel.com/design/guidelines)
- **Merges:** INTERACTION-CRAFT-21 (obscured), A11Y-VISUAL-SYSTEM-07

### R-KEY-8 Make hover and focus popups dismissible and hoverable

- **Strength:** must
- **Rule:** Let every popup that hover or focus opens (Reference previews, custom tooltips, Component hover) close with Esc without a pointer move. Keep it open while the pointer moves onto it. Keep it until the pointer or focus leaves. Open it on keyboard focus too. R-MOT-12 sets the timing.
- **Check:** In JS, Escape closes the preview while the pointer is still over the trigger. The preview stays open when the pointer moves from the citation into it, with no gap or with a hover bridge. Keyboard focus on a citation opens the same preview. No auto-hide timer runs while the preview is under the pointer.
- **Threshold:** None.
- **Sources:** [Understanding SC 1.4.13: Content on Hover or Focus (W3C)](https://www.w3.org/WAI/WCAG22/Understanding/content-on-hover-or-focus)
- **Merges:** INTERACTION-CRAFT-13

---

## 5. Native shell

### R-SHELL-1 Lay out the toolbar in three groups

- **Strength:** should
- **Rule:** Lay out the NSToolbar in three groups. Put Back, the sidebar toggle, and the title on the leading edge. Put the Paper, Overview, and Blog switch in the centre. Put search, Aa, and More on the trailing edge. Use at most one prominent (tinted) action, on the trailing side. Keep text-labelled buttons in their own capsules, apart from symbol buttons. Use borderless system symbols. Use the standard Back symbol with no "Back" text. Keep custom toolbar backgrounds and tints to a minimum. Let the system make the overflow menu, and lay out items so that nothing overflows at the default window width.
- **Check:** Read the `toolbarDefaultItemIdentifiers` order and the `NSToolbarItemGroup` definitions. Count the visual groups and the prominent items. Grep Swift for `NSImage(systemSymbolName:)` names on toolbar items that end in `.circle` or `.circle.fill`, for a toolbar label or title equal to "Back", for a custom `backgroundColor` or tint on the toolbar or titlebar, and for a hand-made overflow or chevron item. Screenshot at the default window width: no overflow chevron.
- **Threshold:** Three groups or fewer; one prominent action or fewer.
- **Sources:** [Toolbars (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/toolbars.json)
- **Merges:** MACOS-HIG-01, MACOS-HIG-03

### R-SHELL-2 Put every toolbar action in the menu bar

- **Strength:** must
- **Rule:** Give every toolbar action (Back, the view switch, search, Aa reading options, each More menu item) a matching command in the menu bar, because people can hide or customize the toolbar.
- **Check:** For each `NSToolbarItem` action selector, find an `NSMenuItem` with the same selector or responder action in the main menu builder. List each toolbar action with no menu item.
- **Threshold:** None.
- **Sources:** [Toolbars (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/toolbars.json)
- **Merges:** MACOS-HIG-02

### R-SHELL-3 Title the window by place

- **Strength:** should
- **Rule:** Give each window a title that names the current place. Use the view name for Home, Library, and Notes, in 15 characters or fewer. Keep the app name out of the title. In the Paper, Overview, and Blog views, use the paper title and let it truncate at the tail, so every trailing toolbar item stays visible.
- **Check:** Grep Swift for `window.title` and toolbar title assignments. None equals "LocalXiv". Titles for non-Paper views are under 15 characters. With a 150-character paper title, a screenshot at the minimum window width shows the title truncated and every trailing item visible.
- **Threshold:** Under 15 characters for non-Paper views.
- **Conflict:** The HIG asks for titles under 15 characters with no exemption. A paper title cannot meet that and still name the place. LocalXiv keeps the truncated paper title, because it is the only place where the paper's name stays visible while the reader is deep in the text. The HIG limit exists to leave room for controls, and tail truncation keeps that room.
- **Sources:** [Toolbars (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/toolbars.json)
- **Merges:** MACOS-HIG-04

### R-SHELL-4 Build the standard menu bar

- **Strength:** must
- **Rule:** Build the menu bar in the standard order: LocalXiv, File, Edit, View, app menus, Window, Help. Put About LocalXiv first, alone in its group, with no version number in its title. Give Settings… the Command-comma shortcut. Give the View menu state-aware Show Sidebar or Hide Sidebar, Show Toolbar or Hide Toolbar, and Enter Full Screen. Give the Window menu Minimize (Command-M) and Zoom, also with one main window.
- **Check:** Read the NSMenu builder. Confirm the top-level order, a separator after About LocalXiv, the About title, `keyEquivalent ","` on Settings…, the View items, and Minimize and Zoom in the Window menu.
- **Threshold:** About name 16 characters or fewer.
- **Sources:** [The menu bar (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/the-menu-bar.json)
- **Merges:** MACOS-HIG-05

### R-SHELL-5 Write menu items the Mac way

- **Strength:** must
- **Rule:** Dim an unavailable menu item and keep it in the menu. Give each show or hide item a label that names the action it will do now. Add a real ellipsis (U+2026) to items that need more input, such as Settings…, Send to Kindle…, and Export…. Use title-style capitals and leave out articles.
- **Check:** Grep Swift for `isHidden = true` on `NSMenuItem` inside `validateMenuItem` or menu updates. Use `isEnabled = false` instead. Grep menu titles for three ASCII periods. Toggle the sidebar: the View item changes between Show Sidebar and Hide Sidebar.
- **Threshold:** None.
- **Sources:** [Menus (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/menus.json)
- **Merges:** MACOS-HIG-06

### R-SHELL-6 Open Settings in one native window

- **Strength:** must
- **Rule:** Open one native Settings window from Settings… (Command-comma). Give it a pane toolbar that people cannot customize and that always shows the selected pane. Title the window with the pane name. Dim the minimize and zoom buttons. Restore the last-used pane on open. Keep Aa reading options in context, and keep a gear or Settings button out of the main toolbar. Route Command-comma and the Settings menu item to the native window only.
- **Check:** In the Settings `NSWindow` setup: `standardWindowButton(.miniaturizeButton)` and `(.zoomButton)` disabled; `toolbar.allowsUserCustomization == false`; `toolbar.selectedItemIdentifier` set and saved to `UserDefaults`; `window.title` set per pane. Grep the main toolbar for a gear or Settings item. Grep the web code for a Settings dialog that the menu or Command-comma can reach. Each such route is a finding.
- **Threshold:** One Settings surface.
- **Conflict:** The app has a native Settings window and a web Settings dialog. The native window wins. The HIG, Raycast, and Coyote Tracks agree that Mac settings open in a separate window, and two Settings surfaces split one decision across two places.
- **Sources:** [Settings (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/settings.json); [A Technical Deep Dive Into the New Raycast](https://www.raycast.com/blog/a-technical-deep-dive-into-the-new-raycast); [What Makes an App Feel Right on the Mac? (Coyote Tracks)](https://coyotetracks.org/blog/app-feel-on-mac/)
- **Merges:** MACOS-HIG-07, INTERACTION-CRAFT-17 (Settings), MACOS-HIG-08 (Settings window)

### R-SHELL-7 Keep the sidebar shallow and native

- **Strength:** should
- **Rule:** Show at most two levels in the source list: a group label and its items. Give each group a short label. Use SF Symbols that take the system accent colour, with fixed colours only where the colour carries meaning. Keep the sidebar visible by default. Honour the system sidebar icon size. Keep critical actions away from the sidebar bottom. Remove old `NSVisualEffectView` backgrounds from the sidebar split item.
- **Check:** Count the NSOutlineView depth. A group header plus items is two levels. A Paper outline that adds subsections is a third level and a finding. `rowSizeStyle` is `.default`, with no hard-coded `rowHeight`. The symbol tint is default or monochrome. No bottom accessory holds a primary action. The sidebar split item contains no `NSVisualEffectView`.
- **Threshold:** Two levels or fewer.
- **Conflict:** The open Paper's outline is a group whose sections can hold subsections, which makes a third level. The HIG wins for the sidebar, because a deep tree mixes navigation with document structure. Record a third level as a finding. The fix (top-level sections only, or the full outline in its own list) is a product decision for the user.
- **Sources:** [Sidebars (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/sidebars.json); [Build an AppKit app with the new design (WWDC25)](https://developer.apple.com/videos/play/wwdc2025/310/)
- **Merges:** MACOS-HIG-10, A11Y-VISUAL-SYSTEM-25 (sidebar)

### R-SHELL-8 Let the system draw Liquid Glass

- **Strength:** should
- **Rule:** Let the system draw Liquid Glass on the toolbar and the sidebar. Use `NSGlassEffectView` only on bars and the sidebar. Set `isBordered = false` on toolbar items that are not interactive, such as the title and status items. Keep content clear of the larger macOS 26 window corners. Use `NSView.LayoutRegion` corner avoidance, and inset web content at the bottom corners (job toasts, the Chat composer) by at least the window corner radius.
- **Check:** Grep Swift for `NSGlassEffectView` and list where it sits. The toolbar title item and status items set `isBordered = false`. Views near window corners use a corner-avoiding layout region. Screenshot the bottom corners with a toast and the Chat composer: nothing clips.
- **Threshold:** Bottom-corner inset at least the window corner radius.
- **Sources:** [Build an AppKit app with the new design (WWDC25)](https://developer.apple.com/videos/play/wwdc2025/310/); [Materials (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/materials.json)
- **Merges:** A11Y-VISUAL-SYSTEM-25, MACOS-HIG-14 (AppKit)

### R-SHELL-9 Separate the toolbar with the scroll edge effect

- **Strength:** should
- **Rule:** Separate the toolbar from scrolling content with the system scroll edge effect only. Use the hard style for pinned headers and text controls on macOS. Apply one effect per pane. Match the effect heights across Split view panes. Remove hand-made dividers, shadows, and gradients under the toolbar.
- **Check:** Grep web CSS for `border-bottom`, `box-shadow`, or `linear-gradient` on sticky or fixed headers at the top of the WKWebView. Grep Swift for custom separator views under the titlebar. In Split view, a screenshot shows both panes' top edge effects at the same height.
- **Threshold:** One scroll edge effect per pane.
- **Sources:** [Get to know the new design system (WWDC25)](https://developer.apple.com/videos/play/wwdc2025/356/)
- **Merges:** MACOS-HIG-16

### R-SHELL-10 Write alerts that name the situation

- **Strength:** must
- **Rule:** Give each alert a title that names the situation, in two lines or fewer. Use a title other than "Error" or a code. Name the object. For Remove paper, put the paper title in the alert title, truncated to keep two lines, and put the counts of the Highlights, Notes, and Question cards that it removes in the informative text. Ask no bare "Are you sure?". Title the action button with a one-word or two-word verb that names the outcome, for example Remove Paper. Use OK only in an alert that only informs, and use Yes and No nowhere. Title the cancel button exactly "Cancel" and put it on the leading side. Use three buttons or fewer. Use the caution symbol rarely.
- **Check:** For each `NSAlert` and web confirmation, read `messageText`, `informativeText`, the button titles, and the `addButton` order. Search for "Are you sure". No title is "Error" or holds an error code. With a 150-character paper title, the alert title wraps to two lines or fewer.
- **Threshold:** Title two lines or fewer; button titles one or two words; three buttons or fewer.
- **Conflict:** NN/g labels both buttons by outcome, for example Keep Paper (ANNOTATION-AI-26). The HIG asks for "Cancel". The HIG wins for the cancel button, because Mac readers and the Esc and Command-period keys expect it. The action button satisfies both sources, because it names the outcome. Second conflict: STATES-FEEDBACK-14 wants the paper title and counts, and the HIG caps the title at two lines. Both hold: the title carries a truncated paper title, and the informative text carries the counts.
- **Sources:** [Alerts (Apple HIG, JSON)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/alerts.json); [Alerts (Apple HIG)](https://developer.apple.com/design/human-interface-guidelines/alerts.md); [Confirmation Dialogs Can Prevent User Errors (NN/g)](https://www.nngroup.com/articles/confirmation-dialog/)
- **Merges:** MACOS-HIG-11 (text and buttons), STATES-FEEDBACK-14, STATES-FEEDBACK-15, ANNOTATION-AI-26 (naming and labels)

### R-SHELL-11 Set the alert default button

- **Strength:** must
- **Rule:** Keep Cancel from being the default button. Use the destructive style (`hasDestructiveAction = true`) only on a destructive button in an alert that the reader did not start on purpose. For Remove paper, which the reader chooses on purpose, set no default button: clear the Return key equivalent on Remove Paper, so the reader reads the alert and clicks. In web dialogs, put the initial focus on the dialog, not on a button.
- **Check:** In each `NSAlert`, Cancel is not the first-added button and has the Escape key equivalent. Remove Paper has an empty `keyEquivalent` and no destructive style. A destructive style appears only where the reader did not start the action. Web dialogs focus the dialog element on open, and Escape closes them.
- **Threshold:** None.
- **Conflict:** The HIG lets Return confirm a destructive action that the reader chose on purpose (its Empty Trash example). NN/g prefers no default or a safe default. LocalXiv sets no default for Remove paper. The HIG allows this option to make people read, NN/g prefers it, and the action deletes the reader's own Highlights and Notes, which a re-import cannot bring back. Readers remove papers rarely, so one more click costs little. The destructive style stays off, as the HIG asks for an action chosen on purpose.
- **Sources:** [Alerts (Apple HIG, JSON)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/alerts.json); [Alerts (Apple HIG)](https://developer.apple.com/design/human-interface-guidelines/alerts.md); [Confirmation Dialogs Can Prevent User Errors (NN/g)](https://www.nngroup.com/articles/confirmation-dialog/)
- **Merges:** MACOS-HIG-11 (default button), STATES-FEEDBACK-16, ANNOTATION-AI-26 (default)

### R-SHELL-12 Make web controls behave like AppKit controls

- **Strength:** should
- **Rule:** Show the arrow cursor on buttons, toolbar-style controls, list rows, tabs, segmented controls, card actions, and menu items. Show the pointing hand over links: text links in content (including citations and cross-references) and links that open the browser. Show the I-beam over selectable text and text fields. Show a left-right resize cursor over the Split view divider and resizable panel edges. Mark the selected row with the selection highlight, and give rows and bezeled buttons no hover background. Make labels, headers, and button text unselectable. Keep paper text, Note text, Chat answers, and card quotes selectable. Give Library rows, Notes rows, and margin cards a context menu.
- **Check:** Grep `cursor: pointer`: only on links. Grep `cursor: text`: only on content and inputs. Grep `col-resize` or `ew-resize` on the divider and panel edges. A `cursor: default` on paper text is a finding. Grep `:hover` rules that change the background of rows and bezeled buttons. Grep `user-select`: body and content containers are not `none`; buttons, `[role=button]`, card action rows, and headers have `-webkit-user-select: none`; inputs, textareas, and `contenteditable` keep text. Grep JS for `contextmenu` handlers on Library rows, Notes rows, and margin cards. Screenshot tests: a drag across a card header selects nothing; a drag across paper text selects it; a web button shows the arrow.
- **Threshold:** None.
- **Conflict:** Evil Martians (MACOS-HIG-28) allows the pointing hand only on links that open the browser. Apple Support (INTERACTION-CRAFT-15) gives the pointing hand to every link. Apple's description wins. Citations and cross-references are links, and readers expect the hand there. Controls keep the arrow under both rules.
- **Sources:** [How to make absolutely any app look like a macOS app (Evil Martians)](https://evilmartians.com/chronicles/how-to-make-absolutely-any-app-look-like-a-macos-app); [A Technical Deep Dive Into the New Raycast](https://www.raycast.com/blog/a-technical-deep-dive-into-the-new-raycast); [Pointers in macOS (Apple Support)](https://support.apple.com/guide/mac-help/pointers-in-macos-mh35695/mac); [When is it OK to Disable Text Selection? (CSS-Tricks)](https://css-tricks.com/when-is-it-ok-to-disable-text-selection/)
- **Merges:** MACOS-HIG-28, INTERACTION-CRAFT-14, INTERACTION-CRAFT-15, INTERACTION-CRAFT-28

### R-SHELL-13 Resize the window smoothly

- **Strength:** should
- **Rule:** Keep live window resizing smooth, with a stable window origin.
- **Check:** Record the screen while you drag the window edge on the Paper and the Overview. No frame jumps, flicker, or top-edge movement.
- **Threshold:** None.
- **Sources:** [What Happened When I Looked at Two Mac Apps Today (Brent Simmons)](https://inessential.com/2020/05/07/what_happened_when_i_looked_at_two_mac_a.html)
- **Merges:** MACOS-HIG-29 (resize)

---

## 6. Dialogs, forms, and settings

### R-DLG-1 Confirm only what cannot be undone

- **Strength:** must
- **Rule:** Act at once and offer Undo for common actions that can be undone: remove a Highlight, delete a Note, Clear Chat, change a Reading state, edit a tag. Show a confirmation only for an uncommon action that cannot be undone, such as Remove paper. Show no alert at launch and no alert that only informs. Show such problems inline.
- **Check:** List every `NSAlert`, `beginSheetModal`, `dialog.showModal()`, and `confirm()` call site. Each one guards an uncommon destructive action that cannot be undone, and offers an action other than OK. None is on a launch path (`applicationDidFinishLaunching`, the first web render). Remove a Highlight, delete a Note, and Clear Chat: no dialog shows, and Undo is available.
- **Threshold:** None.
- **Conflict:** Brent Simmons (MACOS-HIG-29) asks for a visible Undo after Remove paper. NN/g and the HIG Alerts page ask for a confirmation where no undo exists. LocalXiv keeps the confirmation for Remove paper, because the removal deletes the Paper's files, Highlights, Notes, and Chat, and a re-import brings back only the files. Undo for Remove paper is "consider". If a release adds it, that release removes the alert, because the HIG asks for no alert on actions that can be undone.
- **Sources:** [Alerts (Apple HIG, JSON)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/alerts.json); [Alerts (Apple HIG)](https://developer.apple.com/design/human-interface-guidelines/alerts.md); [Confirmation Dialogs Can Prevent User Errors (NN/g)](https://www.nngroup.com/articles/confirmation-dialog/); [What Happened When I Looked at Two Mac Apps Today (Brent Simmons)](https://inessential.com/2020/05/07/what_happened_when_i_looked_at_two_mac_a.html); [Web Interface Guidelines (Vercel)](https://vercel.com/design/guidelines)
- **Merges:** MACOS-HIG-12, MACOS-HIG-29 (Undo for Remove paper), ANNOTATION-AI-25, STATES-FEEDBACK-12, STATES-FEEDBACK-13, INTERACTION-CRAFT-24 (destructive actions)

### R-DLG-2 Make Undo work and show

- **Strength:** must
- **Rule:** After each action that can be undone, enable Edit > Undo with the action's name, for example "Undo Clear Chat". Let Command-Z restore the item so that the reader sees it come back.
- **Check:** After removing a Highlight, deleting a Note, and Clear Chat, Edit > Undo is enabled, names the action, and Command-Z visibly restores the item.
- **Threshold:** None.
- **Sources:** [What Happened When I Looked at Two Mac Apps Today (Brent Simmons)](https://inessential.com/2020/05/07/what_happened_when_i_looked_at_two_mac_a.html); [Understanding SC 2.2.1: Timing Adjustable (W3C)](https://www.w3.org/WAI/WCAG22/Understanding/timing-adjustable.html)
- **Merges:** MACOS-HIG-29 (Undo), ANNOTATION-AI-27 (Edit menu)

### R-DLG-3 Show one popover at a time

- **Strength:** must
- **Rule:** Show one popover at a time: the selection toolbar, a Reference preview, the Aa popover, the note editor, or a web menu. Close the open popover when another opens, through one shared open state. Replace a popover with the next one instead of opening one from inside another. For example, Add Note replaces the selection toolbar with the note editor. Show nothing over a popover except an alert. Let one click close one popover and open another. Point each popover at its source and keep the source uncovered. Save work when a click outside closes a popover: the note editor saves its draft, and only Cancel discards it. Show warnings outside popovers. Use `NSPopover` with `.transient` behaviour for native popovers. Use a native popover for any popover that must reach past the window edge.
- **Check:** In JS, opening any popover or menu first closes the open one. A Reference preview never opens from inside another popover. Click outside a note editor with typed text: the Note is saved. `NSPopover.behavior` is `.transient`. Grep for warning or error text inside popovers. At the minimum window size, a web popover clipped at the window edge is a finding.
- **Threshold:** One popover visible at a time.
- **Conflict:** The selection toolbar and the note editor are both popovers, and the HIG forbids a popover from a popover. The editor replaces the toolbar, so both rules hold.
- **Sources:** [Popovers (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/popovers.json); [A Technical Deep Dive Into the New Raycast](https://www.raycast.com/blog/a-technical-deep-dive-into-the-new-raycast)
- **Merges:** MACOS-HIG-13, ANNOTATION-AI-30 (one at a time, saving), INTERACTION-CRAFT-17 (native popovers)

### R-DLG-4 Apply settings at once

- **Strength:** must
- **Rule:** Apply each Reading preference (theme, font, text size, Margins, Line spacing) on its change or input event, with no Save or Apply step. Use toggle switches only for settings that apply at once. Put a value that needs a commit (the API key, the Kindle address) in its own group with its own button, and use no toggle switch there.
- **Check:** In Settings and the Aa popover, each preference control applies on `change` or `input`, and the reader updates at once. These groups have no Save or Apply button. The key and address groups are separate and have a command button.
- **Threshold:** None.
- **Sources:** [Toggle-Switch Guidelines (NN/g)](https://www.nngroup.com/articles/toggle-switch-guidelines/); [Popovers (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/popovers.json)
- **Merges:** STATES-FEEDBACK-22, MACOS-HIG-13 (Aa writes on change)

### R-DLG-5 Offer resets in the Aa popover

- **Strength:** should
- **Rule:** In the Aa popover, give a way to reset the text size and a way to reset the reading theme to its default.
- **Check:** Open the Aa popover. Find the reset controls. Grep the popover JS for a reset handler that restores the defaults.
- **Threshold:** None.
- **Sources:** [Change a book's appearance in Books on Mac (Apple Support)](https://support.apple.com/guide/books/change-a-books-appearance-ibks8923126d/mac)
- **Merges:** READING-TYPOGRAPHY-27 (reset)

### R-DLG-6 Label every field outside the field

- **Strength:** must
- **Rule:** Give each input in Settings, Setup, and Send to Kindle a visible label outside the field. Use a placeholder only for an optional example. Show necessary hints as visible text outside the field. The single Home search field is exempt.
- **Check:** Each `<input>` and `<textarea>` has visible label text through `<label for>` or `aria-labelledby`. No field has only a placeholder.
- **Threshold:** None.
- **Sources:** [Placeholders in Form Fields Are Harmful (NN/g)](https://www.nngroup.com/articles/form-design-placeholders/)
- **Merges:** STATES-FEEDBACK-21

### R-DLG-7 Validate after the reader leaves the field

- **Strength:** should
- **Rule:** Show a format error after the reader completes a field and moves on, or on submit. Show a real-time error only when the typed character is already wrong.
- **Check:** Field validation listens on `blur`, `change`, or `submit`, not `focus` or `input`. When a form opens, no field has an error class or message.
- **Threshold:** None.
- **Sources:** [Hostile Patterns in Error Messages (NN/g)](https://www.nngroup.com/articles/hostile-error-messages/)
- **Merges:** STATES-FEEDBACK-19

### R-DLG-8 Label buttons by their action

- **Strength:** should
- **Rule:** Label each button with a few words that say what it does, in title-style capitals. Consider a verb first, for example Import Paper or Send to Kindle. Add an ellipsis (U+2026) when a button opens another window or view, for example Settings… or Send to Kindle…. Keep OK, Submit, Go, and Yes off action buttons. OK is for informational alerts only.
- **Check:** Grep button labels in HTML and Swift. Labels of buttons that open Setup, Settings, Send to Kindle, or Remove paper end with U+2026.
- **Threshold:** None.
- **Sources:** [Buttons (Apple HIG)](https://developer.apple.com/design/human-interface-guidelines/buttons.md); [Alerts (Apple HIG)](https://developer.apple.com/design/human-interface-guidelines/alerts.md)
- **Merges:** STATES-FEEDBACK-30

### R-DLG-9 Keep Setup short and skippable

- **Strength:** should
- **Rule:** Make first-run Setup short and skippable. Ask for the AI provider key and the Kindle address when the reader first uses those features. Keep Setup reachable from the menu bar or Settings after a skip.
- **Check:** The Setup dialog has a skip button. A stored flag keeps it closed after a skip. With no key or address, the app asks when the reader first opens Chat, the Overview, the Blog, or Send to Kindle.
- **Threshold:** None.
- **Sources:** [Onboarding (Apple HIG)](https://developer.apple.com/design/human-interface-guidelines/onboarding.md)
- **Merges:** STATES-FEEDBACK-25

---

## 7. States: empty, loading, error, progress, toasts

### R-STATE-1 Respond within 100 ms

- **Strength:** must
- **Rule:** Show the visible result of a direct action within 100 ms: select a Library row, toggle a filter, open a menu, apply a Highlight colour. Apply the selected or pressed state before any awaited fetch or bridge call. Show edits that will probably succeed at once (add a Highlight, save a Note, change a Reading state, add a tag), and confirm them later. If one fails, roll it back and show an error at its source.
- **Check:** In the Web Inspector Timeline, the time from the input event to the first visual change is 100 ms or less. The DOM update comes before the `await` of the bridge or backend call. The `catch` path reverts the state and shows an error.
- **Threshold:** 0.1 s.
- **Sources:** [Response Times: The 3 Important Limits (NN/g)](https://www.nngroup.com/articles/response-times-3-important-limits/); [Web Interface Guidelines (Vercel)](https://vercel.com/design/guidelines)
- **Merges:** STATES-FEEDBACK-01, INTERACTION-CRAFT-24 (optimistic edits), INTERACTION-CRAFT-26 (0.1 s)

### R-STATE-2 Show loading indicators only when they help

- **Strength:** must (no looped spinner under 1 s); should (the 150-300 ms delay and the minimum display time)
- **Rule:** Show no looped spinner for a task that usually ends in under about 1 s, such as opening a cached Paper or sorting the Library. If such a task passes 1 s, show the indicator then. For tasks that usually take longer (Paper search, Direct import, a Chat answer, generation), show the indicator after a 150-300 ms delay. Keep any indicator on screen for at least 300-500 ms. Keep the original button label while the task runs.
- **Check:** Each place that inserts a spinner or skeleton does it from a `setTimeout` that is cancelled when the task completes. The delay fits the task class. A minimum display time exists. Opening a cached Paper and sorting the Library show no flash.
- **Threshold:** Local tasks: no looped indicator under 1 s. Network and AI tasks: show delay 150-300 ms. Minimum visible 300-500 ms.
- **Conflict:** Vercel delays a spinner by 150-300 ms. NN/g says a looped animation under about 1 s distracts. Both hold if the delay depends on the task. Local tasks rarely pass 1 s, so they show nothing. Network and AI tasks usually pass 1 s, so the reader needs to see early that work started.
- **Sources:** [Progress Indicators Make a Slow System Less Insufferable (NN/g)](https://www.nngroup.com/articles/progress-indicators/); [Web Interface Guidelines (Vercel)](https://vercel.com/design/guidelines)
- **Merges:** STATES-FEEDBACK-02, INTERACTION-CRAFT-25 (timing)

### R-STATE-3 Show progress and Cancel on long jobs

- **Strength:** must
- **Rule:** For work over about 10 s (Direct import, Overview and Blog generation, Paper export, Send to Kindle), show percent done or an "N of M" counter, and a clear Cancel. If percent done is not reliable, show the current step's name and the completed and remaining steps, for example "Writing section 3 of 7". Compute progress from real counters of completed and total work. Keep the indicator moving. If the job stalls, say what is wrong and what the reader can do. For 1-10 s, show a less conspicuous indicator.
- **Check:** Each job type that usually passes 10 s shows a numeric value or an "N of M" counter, and a Cancel that stops the job. Grep progress updates: each value comes from completed and total counters, and no timer moves it toward a cap such as 90%. A timeout or stall branch shows a message with a next step.
- **Threshold:** 0.1 s, 1 s, 10 s.
- **Sources:** [Response Times: The 3 Important Limits (NN/g)](https://www.nngroup.com/articles/response-times-3-important-limits/); [Designing for Long Waits and Interruptions (NN/g)](https://www.nngroup.com/articles/designing-for-waits-and-interruptions/); [Progress indicators (Apple HIG)](https://developer.apple.com/design/human-interface-guidelines/progress-indicators.md)
- **Merges:** INTERACTION-CRAFT-26, STATES-FEEDBACK-03, STATES-FEEDBACK-04, STATES-FEEDBACK-05

### R-STATE-4 Name the task in progress text

- **Strength:** should
- **Rule:** Name the task and its object in progress text, for example "Downloading source for 2401.01234", "Reading section 3", or "Drafting the Blog". Use specific words in place of Loading, Processing, Thinking, and Please wait. End an in-progress label with the ellipsis character, for example Importing…. Put the words in the job toast or beside a progress bar. Leave small spinners without a label.
- **Check:** Grep UI strings for a bare "Loading", "Processing", "Thinking", or "Please wait". Grep in-progress labels for three ASCII periods. Spinner elements carry no text label. Small inline spinners are exempt from naming.
- **Threshold:** None.
- **Conflict:** The HIG says not to label spinners on macOS. The HIG Generative AI page and NN/g ask for text that names the step. Both hold: the job carries the words, and the spinner glyph carries none.
- **Sources:** [Generative AI (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/generative-ai.json); [Progress indicators (Apple HIG)](https://developer.apple.com/design/human-interface-guidelines/progress-indicators.md); [Web Interface Guidelines (Vercel)](https://vercel.com/design/guidelines)
- **Merges:** ANNOTATION-AI-15, STATES-FEEDBACK-06, INTERACTION-CRAFT-25 (labels)

### R-STATE-5 Keep the app usable while jobs run

- **Strength:** must
- **Rule:** Let the reader keep reading while jobs run. Start Overview, Blog, import, and export jobs without a modal or a full-window overlay. Show placeholders as soon as possible, in place of a blank view. Let the reader switch views during generation.
- **Check:** While a job runs, there is no full-window overlay, no modal sheet, and no `pointer-events: none` on `body`. The Paper still scrolls and its text can be selected. Switching views during generation works.
- **Threshold:** None.
- **Sources:** [Loading (Apple HIG)](https://developer.apple.com/design/human-interface-guidelines/loading.md); [Generative AI (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/generative-ai.json)
- **Merges:** STATES-FEEDBACK-07, ANNOTATION-AI-16

### R-STATE-6 Set toast lifetime by class

- **Strength:** must
- **Rule:** Put every toast in one of three classes.
  1. Passive information or success with no action: close after about 4000 ms. Pause the timer while the pointer is on the toast, while it has focus, and while the window is hidden or inactive.
  2. An error, the result of a job over 10 s, or a toast with an action (Open, Retry): keep it until the reader closes it. A long-job completion toast states the result (for example a file name or a figure count) and the elapsed time, and has Open.
  3. An Undo toast: let it close on the class 1 timer only if Edit > Undo (Command-Z) also restores the item. Otherwise keep it until the reader closes it.
- **Check:** Grep JS for `setTimeout` and `animationend` handlers that remove toasts. Error and completion toasts (import, export, Send to Kindle, generation) have no timer. The auto-close constant is about 4000 ms. `pointerenter`, `pointerleave`, `focusin`, `focusout`, and `visibilitychange` pause and resume the timer. If the WKWebView does not report hidden when the app goes inactive, Swift tells the web layer to pause.
- **Threshold:** 4000 ms for class 1 and class 3.
- **Conflict:** Sonner and STATES-FEEDBACK-10 close toasts after 4 s. The HIG asks to minimize views that close on a timer, and NN/g reports a reader who missed an error toast that faded after 5 s. The classes keep both. A timer runs only where a missed toast costs nothing (class 1), or where the same action stays in the Edit menu (class 3). WCAG 2.2.1 allows a timer when the function stays reachable without it.
- **Sources:** [Accessibility (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/accessibility.json); [Building a toast component (Emil Kowalski)](https://emilkowal.ski/ui/building-a-toast-component); [Indicators, Validations, and Notifications (NN/g)](https://www.nngroup.com/articles/indicators-validations-notifications/); [Designing for Long Waits and Interruptions (NN/g)](https://www.nngroup.com/articles/designing-for-waits-and-interruptions/); [Understanding SC 2.2.1: Timing Adjustable (W3C)](https://www.w3.org/WAI/WCAG22/Understanding/timing-adjustable.html)
- **Merges:** MACOS-HIG-25, INTERACTION-CRAFT-27, STATES-FEEDBACK-08, STATES-FEEDBACK-09, STATES-FEEDBACK-10, ANNOTATION-AI-27, A11Y-VISUAL-SYSTEM-30

### R-STATE-7 Confirm only important completions

- **Strength:** should
- **Rule:** Confirm completion only for important tasks: Send to Kindle, Paper export, and import. Save a Highlight, a Note, a tag, or a Reading preference silently. Report only a failure.
- **Check:** List the toast call sites. No toast fires on a successful Highlight, Note, tag, or preference save.
- **Threshold:** None.
- **Sources:** [Feedback (Apple HIG)](https://developer.apple.com/design/human-interface-guidelines/feedback.md)
- **Merges:** STATES-FEEDBACK-28

### R-STATE-8 Announce status through live regions

- **Strength:** must
- **Rule:** Put toasts, job progress text, Library result counts, and "no results" lines inside a `role="status"` container with `aria-atomic="true"` that exists at load. Use `role="alert"` or `aria-live="assertive"` only for urgent, blocking errors. Mark the Chat transcript `role="log"` with an accessible name, also in the initial markup. While an answer streams, set `aria-busy="true"` on the streaming message. Set it to `false` when the stream ends, so the answer is announced once.
- **Check:** The status container and the Chat log are in the static HTML, not created on the first message. The Chat list has `role="log"` and `aria-label` or `aria-labelledby`. The streaming message has `aria-busy="true"` until the stream ends. `role="alert"` appears only on blocking errors.
- **Threshold:** None.
- **Conflict:** `role="log"` is a polite live region, and MDN warns against announcing rapid updates. Streaming tokens into the log would announce each fragment. `aria-busy` on the streaming message holds the announcement until the answer is complete. This resolution is this book's; the sources do not state it.
- **Sources:** [ARIA22: Using role=status (W3C)](https://www.w3.org/WAI/WCAG22/Techniques/aria/ARIA22); [ARIA23: Using role=log (W3C)](https://www.w3.org/WAI/WCAG22/Techniques/aria/ARIA23); [ARIA live regions (MDN)](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Guides/Live_regions)
- **Merges:** STATES-FEEDBACK-11, ANNOTATION-AI-23, ANNOTATION-AI-24

### R-STATE-9 Write errors in plain words

- **Strength:** must
- **Rule:** Say what happened and what to do next, in plain words. Keep raw error text, HTTP codes, and stack text out of the main message. In input-validation errors, use none of these words: forbidden, illegal, you forgot, prohibited, please, sorry, valid, invalid, oops. For a service problem that the reader cannot fix, write a separate message that says what to do next.
- **Check:** Grep user-facing strings, and `catch` blocks that write to the DOM or to an `NSAlert`, for `err.message`, `String(describing: error)`, HTTP codes (for example 406 or 500), and the listed words.
- **Threshold:** None.
- **Sources:** [Error message (GOV.UK Design System)](https://design-system.service.gov.uk/components/error-message/)
- **Merges:** STATES-FEEDBACK-17

### R-STATE-10 Show errors at their source

- **Strength:** must
- **Rule:** Show each error next to the control that caused it, with text and a second cue such as an icon or a highlight. Link it with `aria-describedby`. Keep the reader's input, so the reader can edit it.
- **Check:** The failure branches of search, Note save, Chat send, and Settings save do not call `reset()` or set `value = ''`. The error element is next to its control, `aria-describedby` links it, and it shows text and a second cue.
- **Threshold:** None.
- **Sources:** [Error-Message Guidelines (NN/g)](https://www.nngroup.com/articles/error-message-guidelines/)
- **Merges:** STATES-FEEDBACK-18

### R-STATE-11 Keep red for errors

- **Strength:** should
- **Rule:** Use red and caution symbols only for real errors. Show empty and informational states in neutral colours.
- **Check:** The selectors for no Notes, no Highlights, and no Suggestions use neutral tokens and no `exclamationmark.triangle`. Red and caution tokens appear only in error and destructive selectors.
- **Threshold:** None.
- **Sources:** [Hostile Patterns in Error Messages (NN/g)](https://www.nngroup.com/articles/hostile-error-messages/)
- **Merges:** STATES-FEEDBACK-20

### R-STATE-12 Fill empty states with a next step

- **Strength:** must
- **Rule:** Show an empty state only after loading ends. Give each empty container one line that says what goes there and an action that adds it.
- **Check:** The Library, Notes, margin, Chat, Recent, and outline views show their empty template only when the loading flag is false. Each template has a status line, a line on how items get there, and a button or link, for example Import Paper.
- **Threshold:** None.
- **Sources:** [Designing Empty States in Complex Applications (NN/g)](https://www.nngroup.com/articles/empty-state-interface-design/)
- **Merges:** STATES-FEEDBACK-23

### R-STATE-13 Handle no results

- **Strength:** must
- **Rule:** When Library search or Paper search finds nothing, say that nothing matches the query. Keep the query in the field. Give at least one next step, such as Clear Filters or Search arXiv. Keep the tone plain.
- **Check:** For zero matches, the result area shows a message with the query. The field keeps the query. At least one action exists. The text has no jokes.
- **Threshold:** None.
- **Sources:** [3 Guidelines for Search Engine "No Results" Pages (NN/g)](https://www.nngroup.com/articles/search-no-results-serp/)
- **Merges:** STATES-FEEDBACK-24

### R-STATE-14 Report connection problems inline

- **Strength:** must
- **Rule:** Report a lost connection with an inline label, not an alert. Open the Library and cached Papers as usual. Show the label next to each affected control (Home search, Suggestions, Chat, Direct import), and remove it when the connection returns. Tell "no connection" apart from "service failure". Say what still works. Use the same words for the same problem everywhere.
- **Check:** Simulate no connection. The Library and cached Papers open. Each affected control shows an inline label, and no `NSAlert` or modal opens. There is one message for no connection (`URLError.notConnectedToInternet`, or `navigator.onLine` false) and another for service failure (timeout, or HTTP 5xx from arXiv, Semantic Scholar, or the AI provider). Each place uses the same phrase. The labels go away when the connection returns.
- **Threshold:** None.
- **Sources:** [Alerts (Apple HIG)](https://developer.apple.com/design/human-interface-guidelines/alerts.md); [Offline UX design guidelines (web.dev)](https://web.dev/articles/offline-ux-design-guidelines)
- **Merges:** STATES-FEEDBACK-26, STATES-FEEDBACK-27

### R-STATE-15 Accept one submission per click

- **Strength:** should
- **Rule:** Give feedback at once on slow buttons: Send to Kindle, Direct import, Paper export, Remove. While the request runs, ignore a second click through `aria-busy="true"` and a guard in the handler. Keep the button enabled and readable. Chat Send follows R-ANN-8.
- **Check:** Each of these handlers returns early while its request runs. The button has `aria-busy="true"` during the request and shows feedback next to it. A `disabled` attribute set only to block a second click is a finding.
- **Threshold:** None.
- **Conflict:** The STATES-FEEDBACK-29 check sets `disabled`. Its own GOV.UK page says to avoid disabled buttons, and ANNOTATION-AI-12 keeps Stop clickable. `aria-busy` and a guard give the same protection and keep the button focusable. The input marked this rule "must". GOV.UK makes the second-click guard conditional on research, so this book sets it to "should".
- **Sources:** [Button (GOV.UK Design System)](https://design-system.service.gov.uk/components/button/); [AI UX Patterns: Controls (ShapeofAI)](https://www.shapeof.ai/patterns/controls)
- **Merges:** STATES-FEEDBACK-29

### R-STATE-16 Reserve space for late content

- **Strength:** should
- **Rule:** Reserve space for content that loads late. Give figures and images a width and height, or an `aspect-ratio`. Make skeletons the same size as the final content. Load the reading fonts locally or preload them.
- **Check:** In the Paper, the Blog, and the Overview, each `<img>` and figure `<svg>` has `width` and `height` attributes or a CSS `aspect-ratio`. Skeleton sizes equal the loaded sizes. In a recording of a Paper load, the reading position does not jump.
- **Threshold:** 0 layout shift from images or fonts.
- **Sources:** [Web Interface Guidelines (Vercel)](https://vercel.com/design/guidelines)
- **Merges:** INTERACTION-CRAFT-30

---

## 8. Annotation and Chat

### R-ANN-1 Highlight in one click from a selection

- **Strength:** should
- **Rule:** When the reader selects text, show a small selection toolbar with the four Highlight colours and Copy. App actions such as Add Note, Ask, and Explain may join them. One click on a colour saves the Highlight. Place the toolbar above or below the selection, clear of the selected text. Let Command-C copy the selection and add no Highlight.
- **Check:** The `mouseup` or `selectionchange` handler opens the toolbar with colour buttons. One click saves the Highlight, with no second step. The toolbar rectangle does not overlap the selection rectangle. Select text and press Command-C: no Highlight record appears. If an auto-highlight mode exists, a visible toggle turns it off.
- **Threshold:** One click from selection to a saved Highlight.
- **Sources:** [Zotero PDF Reader](https://www.zotero.org/support/pdf_reader); [Highlights, Tags, and Notes (Readwise)](https://docs.readwise.io/reader/docs/faqs/highlights-tags-notes); [Popovers (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/popovers.json)
- **Merges:** ANNOTATION-AI-03, ANNOTATION-AI-06, ANNOTATION-AI-30 (placement)

### R-ANN-2 Put annotation actions in context menus

- **Strength:** should
- **Rule:** Put the four Highlight colours and Add Note in the context menu of a text selection. Put Change Colour, Edit Note, and Remove in the context menu of a Highlight. For a Highlight with a Note, offer Remove Note and Remove Highlight and Note as two items. Show no confirmation, because both can be undone.
- **Check:** The WKWebView context menu (`willOpenMenu` or a JS `contextmenu` handler) on a selection lists the colours and Add Note. On a Highlight, it lists the colour change, Edit Note, and Remove. On a Highlight with a Note, the two remove items both exist, and neither opens a dialog.
- **Threshold:** None.
- **Conflict:** Apple Books asks in a dialog whether to remove only the Note or both. R-DLG-1 wins, because both outcomes can be undone. The choice moves into the menu.
- **Sources:** [Highlight and add notes in Books on Mac (Apple Support)](https://support.apple.com/guide/books/highlight-book-passages-and-add-notes-ibks3975f128/mac); [Confirmation Dialogs Can Prevent User Errors (NN/g)](https://www.nngroup.com/articles/confirmation-dialog/)
- **Merges:** ANNOTATION-AI-04

### R-ANN-3 Open All Notes with Shift-Command-N

- **Strength:** should
- **Rule:** Open All Notes for the open Paper with Shift-Command-N. A click on an entry scrolls to its passage and flashes it.
- **Check:** A menu item has `keyEquivalent "n"` with `[.command, .shift]`, and no other LocalXiv command uses it (R-KEY-1). Each entry's click handler scrolls to the anchored range and flashes it.
- **Threshold:** Shift-Command-N.
- **Sources:** [Keyboard shortcuts and gestures in Books on Mac (Apple Support)](https://support.apple.com/guide/books/keyboard-shortcuts-and-gestures-ibk0a716cf4-9a70-485b-9835-72e3c7ed6c29/mac)
- **Merges:** ANNOTATION-AI-05

### R-ANN-4 Keep Not found Highlights

- **Strength:** must
- **Rule:** When a Highlight or Note cannot find its words in the Paper, keep it with its quote and its Note. List it in a "Not found" group in the margin and in All Notes, with its quote struck through.
- **Check:** The anchor-resolve failure path keeps the record and shows it. The margin and All Notes show a "Not found" group. The quote has `text-decoration: line-through`.
- **Threshold:** None.
- **Sources:** [What are Unanchored Annotations? (Hypothesis)](https://web.hypothes.is/help/what-are-unanchored-annotations/)
- **Merges:** ANNOTATION-AI-07

### R-ANN-5 Show margin cards beside the text

- **Strength:** should
- **Rule:** Show Highlight, Note, and Question cards in the right margin, visible without a click, when the window is wide. At narrow widths, collapse them to pop-ins anchored to the text. Keep card text no larger than body text and no smaller than 10 pt. R-MOT-7 sets card motion.
- **Check:** The card column is on the right and visible at wide widths. A width or container query switches to pop-ins at narrow widths. Card text size is between 10 px and the body size.
- **Threshold:** Card text 10 pt to body size.
- **Sources:** [Sidenotes In Web Design (Gwern.net)](https://gwern.net/sidenote)
- **Merges:** READING-TYPOGRAPHY-20

### R-ANN-6 Export Highlights and Notes

- **Strength:** should
- **Rule:** Give each Paper two exports of its Highlights and Notes: Copy to Clipboard as plain text, and Download as Markdown. Give a tag view on the Notes page the same two exports, with only the filtered Notes. In each exported entry, include a link back to the passage and a citation of the Paper. These exports differ from a Paper export.
- **Check:** The Paper's More menu and the Notes page have both actions. A tag-filtered export holds only the filtered Notes. Each Markdown entry has a deep link (an app URL with the Paper ID and anchor, or the arXiv URL) and a citation (authors, year, arXiv ID). The link opens the Paper at the passage.
- **Threshold:** None.
- **Sources:** [Exporting (Readwise)](https://docs.readwise.io/reader/docs/faqs/exporting); [Zotero PDF Reader](https://www.zotero.org/support/pdf_reader)
- **Merges:** ANNOTATION-AI-08, ANNOTATION-AI-09

### R-ANN-7 Lead each citation to its passage

- **Strength:** must
- **Rule:** Make each Chat and Blog citation lead to the exact passage. On hover or focus, show a preview with the cited text, not only the section title. R-MOT-12 and R-KEY-8 set its timing and dismissal. On click, scroll the Paper to the passage and flash it. When the app cannot find the passage, show the citation as unavailable, for example a dimmed chip with a tooltip. Keep the page where it is in that case.
- **Check:** The citation preview holds the quoted source text. The click handler scrolls to the passage range and flashes it, not to the top of the section. The resolver has a not-found branch with a visible unavailable state, and no fallback to `scrollTo(0)` or to the section heading.
- **Threshold:** None.
- **Sources:** [AI UX Patterns: Citations (ShapeofAI)](https://www.shapeof.ai/patterns/citations)
- **Merges:** ANNOTATION-AI-10, ANNOTATION-AI-11

### R-ANN-8 Turn Send into Stop

- **Strength:** must
- **Rule:** While an answer streams, change the Send button into a Stop button in the same place. Keep Stop clickable until the stream ends.
- **Check:** The composer has one button that swaps its label, icon, and `aria-label` between Send and Stop by stream state, in the same box. Stop is never disabled during streaming. It cancels the request through `AbortController` or an equivalent.
- **Threshold:** None.
- **Sources:** [AI UX Patterns: Controls (ShapeofAI)](https://www.shapeof.ai/patterns/controls)
- **Merges:** ANNOTATION-AI-12

### R-ANN-9 Put correction controls on each answer

- **Strength:** must
- **Rule:** Give each Chat answer its own action row with Retry, and Edit where the app supports it. Keep earlier answers as versions that the reader can page back to and copy. Say in the Retry label or tooltip that Retry adds a new version. After a Retry or an edit, show a signal that it took effect, such as a version indicator ("2 of 2") or a short "Updated".
- **Check:** Each assistant message has an action row. The Retry handler keeps the earlier answer as a version. No answer is overwritten without notice. After Retry, the message shows a version indicator or status.
- **Threshold:** None.
- **Sources:** [Generative AI (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/generative-ai.json); [AI UX Patterns: Regenerate (ShapeofAI)](https://www.shapeof.ai/patterns/regenerate)
- **Merges:** ANNOTATION-AI-13, ANNOTATION-AI-14

### R-ANN-10 Say what is AI and how reliable it is

- **Strength:** must
- **Rule:** Label Chat answers, the Blog, and the Overview as AI-generated where they appear. Say once on each surface that they can contain errors. In the empty Chat, say that the assistant works from this Paper's text, in hedged words, for example "Answers can be wrong. Check the cited passage." Keep AI copy free of claims of certain correctness.
- **Check:** The Blog and Overview headers and the Chat panel show a visible AI label and a short accuracy note, visible without scrolling. The Chat empty state gives the scope and a line about limits.
- **Threshold:** None.
- **Sources:** [Generative AI (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/generative-ai.json); [Guidelines for Human-AI Interaction (Microsoft, CHI 2019)](https://www.microsoft.com/en-us/research/wp-content/uploads/2019/01/Guidelines-for-Human-AI-Interaction-camera-ready.pdf)
- **Merges:** ANNOTATION-AI-17, ANNOTATION-AI-21

### R-ANN-11 Say what goes to the server

- **Strength:** must
- **Rule:** Before the first AI request, tell the reader that Paper text and questions go to the provider's server. Show what is shared. Say what may be stored off-device or used for training. Naming the provider is this book's addition.
- **Check:** Setup, the Chat empty state, or Settings names the provider and says that Paper text and questions go to it. No AI request is sent before the reader has seen this.
- **Threshold:** None.
- **Sources:** [Generative AI (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/generative-ai.json)
- **Merges:** ANNOTATION-AI-19

### R-ANN-12 Keep the app useful without AI

- **Strength:** must
- **Rule:** Keep Home, the Library, Paper reading, Highlights, and Notes fully working with no AI key. With no key, Chat, the Blog, and the Overview show a setup action that opens Settings or Setup. R-DLG-9 sets when the app asks for the key.
- **Check:** Launch with no API key. The Paper, the Library, and Notes open with no error toasts. Chat, the Blog, and the Overview show a setup action.
- **Threshold:** None.
- **Sources:** [Generative AI (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/generative-ai.json)
- **Merges:** ANNOTATION-AI-18

### R-ANN-13 Offer suggested questions as buttons

- **Strength:** should
- **Rule:** Show suggested questions as buttons that send on click: questions about this Paper in the empty Chat, and follow-up questions after each finished answer. Drop a suggestion that the reader passed over from later turns.
- **Check:** Suggestions are `<button>` elements that send on click. Empty-state suggestions use terms from the open Paper. Follow-up buttons appear only after the stream ends. Shown and ignored suggestions are filtered out of later turns.
- **Threshold:** None.
- **Sources:** [10 Guidelines for Designing Your Site's AI Chatbots (NN/g)](https://www.nngroup.com/articles/ai-chatbots-design-guidelines/)
- **Merges:** ANNOTATION-AI-20

### R-ANN-14 Keep the reader's place while an answer streams

- **Strength:** must
- **Rule:** Keep the scroll position still while an answer streams. When the answer grows taller than the panel, keep the top of the new answer in view. Let the reader's own scrolling win.
- **Check:** The stream handler does not set `scrollTop = scrollHeight` or call `scrollIntoView({block: 'end'})` on each token. The view stays at the start of the new message.
- **Threshold:** None.
- **Sources:** [10 Guidelines for Designing Your Site's AI Chatbots (NN/g)](https://www.nngroup.com/articles/ai-chatbots-design-guidelines/)
- **Merges:** ANNOTATION-AI-22

### R-ANN-15 Explain AI failures in the answer

- **Strength:** must
- **Rule:** Show a Chat failure inside the answer that failed, with Retry. Keep the question text in the user turn or the composer. Name the known limit (Paper text too long, no API key, provider rate limit, Paper not converted) and give the way forward (Retry, open Settings, read the passage). Use plain words (R-STATE-9).
- **Check:** The error appears in the failed message, not only in a global toast, and has a Retry button. Each failure class maps to its own message and next step. "Something went wrong" or "An error occurred" is never the only message. The question stays.
- **Threshold:** None.
- **Sources:** [Error-Message Guidelines (NN/g)](https://www.nngroup.com/articles/error-message-guidelines/); [Errors + Graceful Failure (Google PAIR)](https://pair.withgoogle.com/chapter/errors-failing/)
- **Merges:** ANNOTATION-AI-28, ANNOTATION-AI-29

---

## 9. Icons, spacing, radius, and elevation

### R-VIS-1 Make targets large enough

- **Strength:** must
- **Rule:** Make every pointer target in the web layer at least 24x24 CSS px, and aim for 28x28. A smaller target passes only if a 24 px circle centred on it touches no other target. Links inside sentences are exempt. Leave about 12 px around bezeled buttons. Leave about 24 px around the visible glyph of bezel-less icon buttons, or enlarge their hit area with padding. Size custom native controls at the macOS default of 28x28 pt and at least 20x20 pt.
- **Check:** Run `getBoundingClientRect` on every `button, a, input, select, summary, [role=button], [tabindex]`, except links inside sentences. Common failures: margin card action icons, the toast close button, the dialog close button, `#tag` chips, sort and filter toggles, sidebar disclosure triangles, and clickable Reading state marks. A 24 px square fits inside the target even with rounded corners. Custom `NSButton` and `NSView` frames are 20x20 pt or more.
- **Threshold:** Web 24x24 px minimum, 28x28 px default; native 20x20 pt minimum, 28x28 pt default; about 12 px and 24 px padding.
- **Conflict:** The HIG sets a 20x20 pt floor. WCAG 2.5.8 sets 24x24 CSS px. In the WKWebView, 1 CSS px is 1 pt, so the stricter WCAG floor holds there. AppKit draws its own controls at system sizes, which meet the HIG.
- **Sources:** [Accessibility (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/accessibility.json); [Understanding SC 2.5.8: Target Size (Minimum) (W3C)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum)
- **Merges:** MACOS-HIG-26, A11Y-VISUAL-SYSTEM-08, A11Y-VISUAL-SYSTEM-09

### R-VIS-2 Make nested corners concentric

- **Strength:** should
- **Rule:** Make nested rounded shapes concentric: the inner radius equals the outer radius minus the padding between them. Keep small and medium controls (filter chips, row buttons, toast buttons, compact web controls) as rounded rectangles. Use capsules, with a radius of half the height, only for large standout actions.
- **Check:** For each rounded element inside a rounded parent (cards in the margin, buttons in toasts and dialogs, the field in the search bar, popover content), compare the child `border-radius` with the parent radius minus the inset. Flag `border-radius: 999px` or `50%` on small controls.
- **Threshold:** Inner radius equals outer radius minus padding, within 1 px; capsule radius equals height / 2.
- **Sources:** [Get to know the new design system (WWDC25)](https://developer.apple.com/videos/play/wwdc2025/356/)
- **Merges:** MACOS-HIG-17, A11Y-VISUAL-SYSTEM-26

### R-VIS-3 Use standard materials in the web layer

- **Strength:** must
- **Rule:** Leave Liquid Glass to the system in the navigation layer (R-SHELL-8). In the web layer, imitate no Liquid Glass. Give in-flow elements opaque fills. Floating layers may use a standard blur material (`backdrop-filter`) with a mostly opaque fill, the regular style. Keep one blurred layer per stack: put fills, transparency, or vibrancy on an element that sits on a blurred layer. Use clear, very translucent glass only over media. Over bright content, put a dark dimming layer of about 35% behind its text.
- **Check:** Grep `backdrop-filter` and `-webkit-backdrop-filter`, and list each with its selector. A match on an in-flow element is a finding. An element with a blur inside another element with a blur is a finding. Each floating layer's fill is mostly opaque. A very translucent surface over figures or images has a dimming layer near 35%.
- **Threshold:** About 35% dark dimming for clear glass over bright content.
- **Conflict:** The MACOS-HIG-14 check bans `backdrop-filter` on every content element, including toasts. Its own source and A11Y-24 ban only Liquid Glass in the content layer and recommend standard materials such as blur there. The source wins. A blurred popover over the Paper is a standard material, and an opaque enough fill keeps its text readable.
- **Sources:** [Materials (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/materials.json); [Meet Liquid Glass (WWDC25)](https://developer.apple.com/videos/play/wwdc2025/219/)
- **Merges:** MACOS-HIG-14, MACOS-HIG-15 (glass on glass), A11Y-VISUAL-SYSTEM-24

### R-VIS-4 Bridge Reduce Transparency into the web layer

- **Strength:** should
- **Rule:** Read Reduce Transparency in Swift through `NSWorkspace.shared.accessibilityDisplayShouldReduceTransparency`. Set a class or data attribute on `<html>`, and update it when the display options change. Under that flag, replace `backdrop-filter` and alpha backgrounds with opaque surface tokens. Under `@media (prefers-contrast: more)`, give each translucent surface an opaque fill and a solid border (R-COL-9).
- **Check:** CSS that relies on `prefers-reduced-transparency` alone is a finding, because WebKit never matches it. Swift sets the flag and observes changes. CSS under the flag makes popovers, menus, toasts, Reference previews, and the margin opaque. The `prefers-contrast: more` block adds solid borders.
- **Threshold:** None.
- **Conflict:** The WWDC source says the system glass adapts by itself, so it asks nothing of custom surfaces (MACOS-HIG-15). LocalXiv's web surfaces are not system glass, and WebKit does not support `prefers-reduced-transparency` (A11Y-23). Without a bridge, the web layer ignores the reader's setting. The bridge wins for this app.
- **Sources:** [Web features explorer: prefers-reduced-transparency](https://web-platform-dx.github.io/web-features-explorer/features/prefers-reduced-transparency/); [Meet Liquid Glass (WWDC25)](https://developer.apple.com/videos/play/wwdc2025/219/)
- **Merges:** MACOS-HIG-15 (accessibility settings), A11Y-VISUAL-SYSTEM-23

### R-VIS-5 Match icon weight to text

- **Strength:** should
- **Rule:** Match each icon's weight to the weight of the text next to it. Use outline icons beside text and filled icons for selection. Use one icon family.
- **Check:** Each `NSImage.SymbolConfiguration` uses the weight of the label font next to it. Toolbar and sidebar symbols use outline variants, except in the selected state. Web SVG icons share one `stroke-width` that matches the text weight and one size scale (small, medium, large).
- **Threshold:** None.
- **Sources:** [SF Symbols (Apple HIG)](https://developer.apple.com/tutorials/data/design/human-interface-guidelines/sf-symbols.json)
- **Merges:** A11Y-VISUAL-SYSTEM-27

### R-VIS-6 Take spacing from one scale

- **Strength:** should
- **Rule:** Take every margin, padding, and gap from one spacing scale with an 8 px base and 2, 4, and 6 px small steps. Use the scale through tokens. Use 0-8 px inside compact components, 12-24 px for component padding, and 32 px or more for layout regions.
- **Check:** Collect the px values of `padding`, `margin`, `gap`, and `inset` in CSS, and the layout constants in Swift. Every value is in the set, and CSS writes it as a `var(--space-*)` token.
- **Threshold:** {0, 2, 4, 6, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80}.
- **Sources:** [Spacing (Atlassian Design)](https://atlassian.design/foundations/spacing/)
- **Merges:** A11Y-VISUAL-SYSTEM-28

### R-VIS-7 Keep elevation shallow and few

- **Strength:** consider
- **Rule:** Define a small set of elevation tokens. Give each component type one resting elevation. Keep resting elevations shallow. Use a 1 px border on rows and cards at rest, and use shadows only on floating layers.
- **Check:** Count the distinct `box-shadow` values. Each maps to a named token. All margin cards share one value, all dialogs share one value, and all popovers and menus share one value.
- **Threshold:** None.
- **Sources:** [Elevation (Material Design M2)](https://m2.material.io/guidelines/material-design/elevation-shadows.html)
- **Merges:** A11Y-VISUAL-SYSTEM-29

---

## Rules that need a native run to check

A native run opens the LocalXiv window and takes the front and key focus. Ask the user before a native run. Check the web-only parts of these rules in the browser pane first.

- R-SHELL-1: toolbar groups, the prominent action, and no overflow chevron at the default and the minimum window width.
- R-SHELL-3: paper title truncation with all trailing items visible at the minimum width.
- R-SHELL-4 and R-SHELL-5: menu bar order, dimmed items, and state-aware Show and Hide titles.
- R-SHELL-6: Settings window buttons dimmed, the pane title, and the last pane restored.
- R-SHELL-7: sidebar symbol accent tint, icon size, and outline depth.
- R-SHELL-8: Liquid Glass placement, and window-corner clipping of toasts and the Chat composer.
- R-SHELL-9: scroll edge effect heights across Split view panes.
- R-SHELL-10 and R-SHELL-11: NSAlert layout, button order, no default on Remove Paper, Esc and Command-period.
- R-SHELL-13: live resize stability.
- R-COL-1: live switch of the system appearance while a Paper is open.
- R-COL-2: first-paint flash of the WKWebView at launch and on view switches.
- R-VIS-4 and R-COL-9: rendering under Reduce Transparency and Increase Contrast, alone and together.
- R-MOT-10: native animations under Reduce Motion.
- R-KEY-1 and R-KEY-3: menu key equivalents in the running app, and Full Keyboard Access across the shell and the web layer.
- R-KEY-4: text replacement expansion in web fields.
- R-DLG-2: Edit > Undo names the action and restores the item.
- R-DLG-3: a native popover that reaches past the window edge.
- R-STATE-6: toast timer pause when the app goes inactive.
- R-TYP-5: what View > Zoom changes in the WKWebView.