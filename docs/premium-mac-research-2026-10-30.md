# Premium Mac app research, 2026-10-30

This reference lists 54 principles for a premium Mac app that [the UI rule book](ui-rule-book-2026-10-21.md) does not state. Each principle has a check that you can do in a screenshot, a native chrome dump, or the code, and the sources that support it. [The UI polish audit of 2026-10-30](ui-polish-audit-2026-10-30.md) used them.

## How the research ran

Five research lanes searched the web with Exa: Liquid Glass on macOS 26 and 27, the seam between web content and a native shell, premium reading and annotation apps, the design philosophies of acclaimed Mac apps, and smoothness in a WKWebView app. A synthesizer removed each principle that the rule book already states, checked doubtful sources again, and merged the duplicates. It kept 54 principles and dropped 19.

A "must" principle is one that a user notices in the first five minutes. A "should" principle is one that a careful user notices. "Refines" names the rule book rule that the principle makes more exact.

Some checks name Swift lines from 2026-10-30. Line numbers change, so search for the code that the check describes.

## Liquid Glass and the native chrome

### N-GLASS-1 (must)

Make every bounce area and the band under the toolbar show the colour of the visible reading surface, in each reading theme. Do not change window chrome per reading theme. Do not let the app document root rubber-band. [From LG-2. Merges R-SEAM-4, PERF-11]

**Check.** Shell.swift:128 and SettingsWindow.swift:23 set underPageBackgroundColor = .clear, and nothing updates it later. Shell.swift:252-253 change window.backgroundColor and toggle titlebarAppearsTransparent for Sepia, so the chrome changes with the reading theme (an R-COL-1 conflict). In Light, Sepia, and Dark, screenshot Home, Library, and a Paper at scroll 0, scrolled, and rubber-banded past the top and bottom. A strip whose colour differs from --paper, or a web toolbar or pill that moves with the bounce, is a finding. WebKit extends a page colour into the toolbar band only from a fixed or sticky element that spans nearly the full viewport width at the inset edge (WebKit 294820@main). List such elements with top of 5 px or less. On macOS 27, WebKit fills the leading inset area under the sidebar with a system background at scroll origin (WebKit PR 67372), so test that strip on both OS versions. Compare getComputedStyle of html and body on each page: the Settings page sets html to --paper and body.panel to --popover, which is a mismatch. Grep the app document for an html overscroll-behavior rule (appearance.js sets contain only in Split view).

**Premium version.** The web layer sends the current --paper value to the Native shell on load and on every theme or view change, and Swift sets underPageBackgroundColor to it. The toolbar and window background are the same in all reading themes. html and body use the same surface colour on each page. The app document root has overscroll-behavior-y: none when it is not the content scroller, so fixed chrome never bounces. Documents that scroll keep the vertical bounce, and the iframe root contains its own bounce. The x axis is left alone.

**Refines.** R-COL-2 (adds the update on every theme change, the overscroll strip, and the full-width fixed-element rule for the toolbar band). R-TYP-18 (adds the document root). R-COL-1 (the per-theme window background and titlebar toggles break 'chrome follows the system')

**Sources.** <https://developer.apple.com/documentation/webkit/wkwebview/underpagebackgroundcolor>, <https://bugs.webkit.org/show_bug.cgi?id=301756>, <https://github.com/WebKit/WebKit/pull/45266>, <https://github.com/WebKit/WebKit/pull/67372>, <https://github.com/WebKit/WebKit/commit/0573d0ea9ff46d1b86e0ea9b960370b061672786>

### N-GLASS-2 (must)

Let sidebar symbols take the system accent colour. Do not grey out unselected rows. [From LG-5]

**Check.** Sidebar.swift:155 and :210 set contentTintColor to .secondaryLabelColor on unselected rows. Set System Settings > Appearance > Accent colour to Purple and screenshot the Library sidebar on macOS 26 and macOS 27. Unselected symbols that stay grey are a finding.

**Premium version.** The RowView and cell tint overrides are gone. Symbols use the default source-list tint, which shows the reader's accent colour. A fixed colour appears only where the colour carries meaning, such as a failed-job warning. The selection style comes from the system on each OS version (macOS 27 adds a semibold selected label).

**Refines.** R-SHELL-7: overrides the 'default or monochrome' clause in its check. The June 2026 HIG says people expect all sidebar icons to show the accent colour they choose, so a monochrome or grey tint fails.

**Sources.** <https://developer.apple.com/design/human-interface-guidelines/sidebars.md>, <https://wwdc.ai/2026/289>, <https://www.macrumors.com/roundup/macos-27/>, <https://www.theverge.com/tech/943695/apple-wwdc-2026-macos-27-macbook-mac-announcement-features>

### N-GLASS-3 (must)

At rest, keep content clear of the toolbar and sidebar glass. Content goes under the glass only when the reader scrolls it there. [From LG-11]

**Check.** Screenshot Home, Library, Notes, and the Paper, Overview, Blog, and Split views at scroll 0, at launch, and after each view switch. Any text, figure, or card under the toolbar or sidebar glass is a finding. A restored scroll position that puts the first line under the glass when the reader was not scrolled there is a finding.

**Premium version.** The first line of each view starts below the toolbar band with the .page top margin. Restored scroll positions put content under the glass only when the reader was already scrolled there.

**Sources.** <https://developer.apple.com/videos/play/wwdc2025/219/>, <https://developer.apple.com/videos/play/wwdc2025/310/>

### N-GLASS-4 (should)

Read the window corner geometry at runtime and pass it to the web layer. Do not hard-code a corner radius or a corner inset. On macOS 26 the radius depends on the window style (a toolbar window has a larger radius than a titlebar-only window). macOS 27 gives all windows one smaller radius. [From LG-1]

**Check.** Grep Swift for edgeInsets(for: or layoutGuide(for: .safeArea(cornerAdaptation: (no matches today). Grep CSS for fixed px insets and radii on elements that touch window edges in the Native shell: .split #paper (18 px radius, 12 px from the bottom, 16 px from the trailing edge), #notifications (top 12 px, right 16 px), the Chat composer, and Settings buttons near the bottom corners. Screenshot the bottom corners of the main window and the Settings window on macOS 26 and macOS 27. A corner that looks pinched or flared, or content that the corner clips, is a finding.

**Premium version.** ContentView.layout() reads the layout region with corner adaptation, subtracts safeAreaInsets, and sends the corner size to CSS as --window-corner, the same way it sends the Reduce Transparency class. A web element near a corner uses at least var(--window-corner) as its inset and max(minimum, var(--window-corner) - inset) as its radius. Native views near a corner use the corner-adapted layout guide on macOS 26 and cornerConfiguration with .containerConcentric(minimum) on macOS 27.

**Refines.** R-SHELL-8 (adds the runtime read, the CSS bridge, and the per-OS radius). R-VIS-2 (concentric radius against the window corner)

**Sources.** <https://developer.apple.com/videos/play/wwdc2025/310/>, <https://wwdc.ai/2026/289>, <https://www.macrumors.com/roundup/macos-27/>

### N-GLASS-5 (should)

Use the automatic scroll edge effect style. Change it only after a legibility test fails, and record the reason. [From LG-3]

**Check.** Grep Swift for preferredScrollEdgeEffectStyle. It is absent or .automatic. A forced .hard or .soft needs a recorded reason. Open the find bar over scrolled Paper text and screenshot the edge under it on macOS 26 and macOS 27. Grep CSS for mask-image or gradient fades at the top of scroll containers where no floating UI sits.

**Premium version.** The toolbar, the find bar accessory, and the sidebar all use the system effect at the automatic style. On macOS 27 the automatic style becomes hard where free-floating text (the window title) is above content, with no app code. The edge looks the same in the Paper, Overview, and Blog views and in both Split view panes. The web layer adds no fade.

**Refines.** R-SHELL-9: corrects its 'use the hard style for pinned headers and text controls'. The June 2026 HIG says to prefer the automatic style, and macOS 27 resolves it to hard by itself where needed.

**Sources.** <https://developer.apple.com/design/human-interface-guidelines/scroll-views.md>, <https://developer.apple.com/videos/play/wwdc2026/289/>, <https://developer.apple.com/videos/play/wwdc2025/310/>

### N-GLASS-6 (should)

Put content that is pinned to the bottom of the sidebar in a bottom-aligned split item accessory, not in a stack under the scroll view. [From LG-4]

**Check.** Sidebar.swift:48 puts ActivityButton in an NSStackView under the outline scroll view. Grep for addBottomAlignedAccessoryViewController (absent). Show a long Paper outline with a running job, scroll the outline, and screenshot the boundary between the outline and the Activity line and the bottom-leading sidebar corner. A hard cut-off edge is a finding.

**Premium version.** An NSSplitViewItemAccessoryViewController holds the Activity line, added with addBottomAlignedAccessoryViewController, and its isHidden follows the job state. The outline scrolls under it with the system scroll edge effect, and the accessory insets the sidebar safe area and stays clear of the corner. A failed-job warning also shows somewhere other than the sidebar bottom.

**Refines.** R-SHELL-7 (adds the container for bottom sidebar content)

**Sources.** <https://developer.apple.com/videos/play/wwdc2025/310/>, <https://developer.apple.com/documentation/appkit/nssplitviewitemaccessoryviewcontroller>, <https://developer.apple.com/design/human-interface-guidelines/sidebars.md>

### N-GLASS-7 (should)

Give the window subtitle information that the chrome does not already show: in reading views, the current section and, if wanted, the time left in it. [From LG-6. Merges READ-3]

**Check.** reader.js sets subtitle to VIEW_LABELS[activeTab] in the Overview and Blog views, which repeats the selected segment. app.js sets the Library subtitle to the selected filter, which the selected sidebar row already shows. Screenshot each view and compare the subtitle with the selected segment, the selected sidebar row, and the web header. In the Paper, check that the subtitle is correct on the first frame after the Reading position is restored, not only after the first scroll.

**Premium version.** The subtitle is empty, or it shows new information: the current section in the Paper, Overview, and Blog views, optionally with a progress value such as '6 min left in section'. The pace comes from the reader's own steady reading and stays on this Mac. A View > Reading Progress submenu chooses Time Left in Section, Percent, or None. The title area does not change height between views.

**Refines.** R-SHELL-3 (adds subtitle content). R-TYP-17 (adds where progress shows)

**Sources.** <https://developer.apple.com/videos/play/wwdc2026/289/>, <https://docs.readwise.io/changelog>, <https://www.glencoelibrary.org/wp-content/uploads/2023/02/Kindle_Paperwhite_Users_Guide.pdf>

### N-GLASS-8 (should)

Give menu items SF Symbol icons sparingly: only on key actions with a clear standard symbol, and for all items in a separator group or none of them. [From LG-7]

**Check.** Grep Toolbar.swift menu(), Menus.swift showMenu, and the main menu builder for NSMenuItem.image (none today). After adding icons, check each separator group: all items in the group have an icon, or none do. Screenshot the More menu and a Paper context menu.

**Premium version.** The More menu, the Share submenu, and page context menus have standard symbols (Share, Copy, Search) on their key actions, in one aligned column, with uniform groups. No icon appears where no clear symbol exists. This matches macOS 27, which uses fewer menu icons than macOS 26.

**Refines.** R-SHELL-5 (adds the icon rule)

**Sources.** <https://developer.apple.com/design/human-interface-guidelines/menus.md>, <https://9to5mac.com/2026/06/09/macos-27-golden-gate-includes-these-changes-that-tahoe-critics-will-appreciate/>

### N-GLASS-9 (must)

In the Native shell, open every menu as an NSMenu, also the menus that a web button opens. [From LG-8]

**Check.** shell.js openMenu sends only pointer-anchored menus to Swift (native && !(at instanceof Element)). A menu anchored to a button still draws the web .menu (12 px radius, backdrop-filter). In the Native shell, click each control with aria-haspopup=menu and screenshot. A web-drawn menu is a finding.

**Premium version.** A button-anchored menu sends the button rect to Swift. Swift adds the obscured insets, as showMenu already does, and calls NSMenu.popUp(positioning:at:in:) under the button. The web .menu is used only in browser mode.

**Refines.** R-MOT-4 (it says NSMenu for the More menu and context menus 'where possible'. This closes the gap for button-anchored web menus)

**Sources.** <https://developer.apple.com/videos/play/wwdc2025/310/>, <https://developer.apple.com/design/human-interface-guidelines/menus.md>, <https://www.raycast.com/blog/a-technical-deep-dive-into-the-new-raycast>

### N-GLASS-10 (should)

In the Aa popover, anchor the text size slider fill at the default size, keep secondary controls quiet with tint prominence, and let Auto Layout size the controls. [From LG-9]

**Check.** ReadingPopover.swift: the size slider (15 to 36 pt) has no neutralValue and no tintProminence. Grep Swift for heightAnchor.constraint(equalToConstant:) on controls and for prefersCompactControlSizeMetrics. Screenshot the popover at the default size, a smaller size, and a larger size.

**Premium version.** size.neutralValue equals the Actual Size value, so the fill grows from that point in either direction and shows the distance from the default. Actual Size is dimmed at the default size. Controls use Auto Layout heights. prefersCompactControlSizeMetrics is used only if the popover becomes too tall, and then on the whole popover.

**Refines.** R-DLG-5 (the reset control and the slider show the default together)

**Sources.** <https://developer.apple.com/videos/play/wwdc2025/310/>

### N-GLASS-11 (should)

Treat a trailing panel that adds to the current view as an inspector, or make it flush with the trailing edge. Do not float a shadowed card beside the sidebar. [From LG-12]

**Check.** In the Blog view with the Question card open (.blog-chat, 320 px trailing column) and in the Split view (.split #paper, sticky card with an 18 px radius and a shadow), screenshot the window. Count the floating surfaces. Grep Swift for NSSplitViewItem(inspectorWithViewController:) and .toggleInspector. A trailing web panel with a shadow or a radius that does not touch the window edge is a finding.

**Premium version.** Consider an inspector split item for the Question card, with a .toggleInspector toolbar item and the inspector tracking separator, so the toolbar divides over it and its edge effect matches the content pane. If the panel stays in the web layer, it is flush with the trailing edge, with no shadow, and its top margin matches the main column. On macOS 27 the sidebar is edge to edge, so a floating trailing card looks even more out of place.

**Refines.** R-VIS-7 (shadows only on floating layers. A docked panel is not one)

**Sources.** <https://developer.apple.com/videos/play/wwdc2025/310/>, <https://www.macrumors.com/roundup/macos-27/>

## The web and native seam

### N-SEAM-1 (must)

Remove the browser items from the WebKit context menu, and keep the system text services. [From R-SEAM-1]

**Check.** In PageView.willOpenMenu (Shell.swift), log each NSMenuItem.identifier after super. Right-click the page background, a citation, the PDF link, and a figure image in the Paper, Overview, and Blog. Each of these is a finding: WKMenuItemIdentifierReload, GoBack, GoForward, OpenLink, OpenLinkInNewWindow, DownloadLinkedFile, OpenImageInNewWindow, DownloadImage, OpenFrameInNewWindow, OpenMediaInNewWindow, DownloadMedia, and InspectElement in a Release build. The identifiers are undocumented but stable across releases.

**Premium version.** The context menu shows only items that work in a reader app: Look Up, Translate, Copy, Share, Speech, Services, and the LocalXiv items. On a link, 'Open Link' becomes 'Open in Browser' and 'Copy Link' copies the public arXiv URL. On a figure, Copy Image stays and LocalXiv adds 'Save Figure…' in place of Download Image. No menu shows Reload, Back, Forward, or 'in New Window'.

**Refines.** R-SHELL-12 and R-ANN-2 (they add items to context menus. This removes WebKit's browser items)

**Sources.** <https://icab.de/blog/2022/06/12/customize-the-contextual-menu-of-wkwebview-on-macos/>, <https://www.raycast.com/blog/a-technical-deep-dive-into-the-new-raycast>

### N-SEAM-2 (must)

Keep the reader's text selection when focus moves to a native control and back. [From R-SEAM-10]

**Check.** WKWebView clears the DOM selection when it resigns first responder (WebKit bug 253958. Mail has the same problem). Select a sentence in the Paper, then: press Command-F and Esc. Click the toolbar search field and press Esc. Open and close the Aa popover. Click a sidebar row and click back. Each case where the selection is gone is a finding.

**Premium version.** The page saves the selection Range on selectionchange. While native has focus, it draws that range with the CSS Custom Highlight API in --selection-inactive, as NSTextView draws an inactive selection. When the shell calls makeFirstResponder(webView), it sends a command and the page restores the Range. Highlight, Add Note, and Ask still apply to the sentence after any native round trip.

**Sources.** <https://bugs.webkit.org/show_bug.cgi?id=253958>

### N-SEAM-3 (must)

Drive web selection and accent states from the key-window state, as an NSTableView does: accent fill when the list has focus in the key window, grey otherwise. [From R-SEAM-8. Merges LG-10]

**Check.** app.css gives selected web rows a grey fill at all times (.prow.is-selected, .toc-row.is-current, .sb-row[aria-current=page], .an-go.is-selected, Settings pane buttons all use --selection-inactive). Click the Library list and use the arrow keys: the selected row stays grey. PapersToKindle.swift toggles html.inactive only from applicationDidBecomeActive and applicationDidResignActive, so opening Settings (Command-comma) leaves the main page emphasized while the toolbar and sidebar recede. shell.js:53 listens to DOM blur, which also fires when focus moves into the Paper iframe. :window-inactive works only on ::selection and scrollbars (WebKit bug 38927).

**Premium version.** The shell sends windowDidBecomeKey and windowDidResignKey for the main window, and the page sets data-window-active on html. A selected row in a focused list in the key window gets the accent fill (N-SEAM-4) and white text. Otherwise it gets the grey fill. In a non-key window, accent-filled web controls (primary button, checked toggle, selected segment) change to grey. The web layer changes state in the same frame as the native sidebar and toolbar. Toast timers keep their own app-active signal (R-STATE-6).

**Refines.** R-COL-8 (where the accent goes. This adds the focused and non-key-window states)

**Sources.** <https://developer.apple.com/design/human-interface-guidelines/windows.md>, <https://developer.apple.com/videos/play/wwdc2025/219/>, <https://bugs.webkit.org/show_bug.cgi?id=38927>, <https://css-tricks.com/window-inactive-styling/>

### N-SEAM-4 (should)

Pass the system accent colour from the Native shell. Do not trust the CSS AccentColor keyword. [From R-SEAM-9]

**Check.** app.css:68 sets --control-accent: AccentColor. A WebKit engineer states that AccentColor intentionally returns a fixed colour to protect against fingerprinting (WebKit standards-positions issue 136). Set the accent to Graphite, then Pink, and read getComputedStyle(document.documentElement).getPropertyValue('--control-accent') and look at focus rings and selected segments. A value that does not change is a finding. ReadingPopover.swift:92 is the only controlAccentColor use in Swift.

**Premium version.** The shell reads NSColor.controlAccentColor in the window's effective appearance and sends it to the page as --control-accent on load, on NSSystemColorsDidChangeNotification, and on each appearance change. Focus rings, emphasized selection, accent-color on form controls, and the primary button change live with the native sidebar symbols.

**Refines.** R-COL-8 (it allows 'a CSS system colour keyword'. For the accent, WebKit makes that route fail)

**Sources.** <https://github.com/WebKit/standards-positions/issues/136>, <https://github.com/w3c/csswg-drafts/issues/7347>

### N-SEAM-5 (should)

Keep local URLs and the session token inside the app, and turn off Force Click link previews. [From R-SEAM-2]

**Check.** reader.js sets #reader-pdf href to fileURL('original.pdf'), and fileURL (app.js:62-67) adds ?token=<session token> to an http://127.0.0.1 URL. downloadLink does the same. Right-click the PDF link, choose Copy Link, and paste: a 127.0.0.1 URL with token= is a finding. Drag the link into Notes: the same. Grep Swift for allowsLinkPreview (no match). Apple documents the macOS default as true, and a click in the preview opens Safari.

**Premium version.** No user gesture puts a local URL or the token on the pasteboard or in another app. The main and Settings WKWebViews set allowsLinkPreview = false. Force Click on a word still gives Look Up. Links that carry the token are buttons that call the shell, or links with -webkit-user-drag: none, and Copy Link copies the arXiv URL.

**Refines.** R-ANN-11 (covers what goes to the server. This covers what leaves through the pasteboard and drag)

**Sources.** <https://developer.apple.com/documentation/webkit/wkwebview/allowslinkpreview.md>, <https://icab.de/blog/2022/06/12/customize-the-contextual-menu-of-wkwebview-on-macos/>

### N-SEAM-6 (should)

Accept a drop or refuse it visibly. Do not let controls drag as links. [From R-SEAM-3]

**Check.** Drag an arxiv.org link from Safari, a .pdf from Finder, and the text '2401.01234' onto the Library and the Paper. Today the drop becomes a navigation that decidePolicyFor cancels, while the cursor shows the green copy badge and nothing happens. That is a finding. No app JS has a dragover or drop handler. Drag each <a> that looks like a button ('.links a', toast action links, Save links): a URL ghost image is a finding. Grep CSS for -webkit-user-drag (no match).

**Premium version.** A dropped arXiv URL, arXiv ID, or PDF starts Add Paper with the same job toast as the Add command. Other drops set dataTransfer.dropEffect = 'none' in a capture-phase dragover handler, so the cursor shows no badge. Controls styled as links set -webkit-user-drag: none. Content drags stay: a figure drags out as an image, and a Library row drags its arXiv URL.

**Sources.** <https://gist.github.com/madrobby/8dc43c58114466d6a894>, <https://github.com/refactoringhq/tolaria/pull/229>

### N-SEAM-7 (should)

Keep WebKit's native overlay scrollbars, and give each app-document surface that follows the reading theme its own color-scheme. [From R-SEAM-5]

**Check.** Grep CSS for ::-webkit-scrollbar: none today (pass. Keep it so). The reader iframe already sets color-scheme per theme (appearance.js:59). In the app document, app.css sets color-scheme only on :root and :root[data-theme=dark]. Set the system to Dark and the reading theme to Light or Sepia, and the reverse. Screenshot the margin, Chat, and Settings while they scroll. A light knob on a light surface or a dark knob on a dark surface is a finding. Also check the caret and form controls on each surface.

**Premium version.** Scrollbars are the system overlay scrollers and follow System Settings > Show scroll bars. Each app-document surface that sets its own reading-theme background also sets a matching color-scheme (light for Light and Sepia, dark for Dark). Where a tint is needed, scrollbar-color is the only styling.

**Refines.** R-COL-1 (adds scrollbars, caret, and controls on a surface whose theme differs from the system)

**Sources.** <https://webkit.org/blog/363/styling-scrollbars/>, <https://webkit.org/blog/17640/webkit-features-for-safari-26-2/>

### N-SEAM-8 (should)

Make web chrome text render like the AppKit text next to it, and prove it by a pixel test: get tracking from the font's trak table, not from hand letter-spacing, and pick the smoothing value that matches native stem weight. [From R-SEAM-6. Merges R-SEAM-7]

**Check.** WebKit applies the SF trak table only under text-rendering: optimizeLegibility (WebKit PR 10354). app.css has no text-rendering and 24 hand letter-spacing values on UI text. app.css:81 sets -webkit-font-smoothing: antialiased on body, which reports say makes text thinner than native. No WebKit source confirms this, so measure it. Put a 13 px web label and a 13 pt NSTextField with the same 20-character string side by side at 400% zoom, in Light and Dark. An advance-width difference over 1 px, or visibly thinner stems on 'l' and 'i', is a finding.

**Premium version.** In order: 1) set text-rendering: optimizeLegibility on system-ui chrome text only (sidebar-style rows, controls, dialogs, toasts, card chrome), not on Paper body text. 2) remove the hand letter-spacing on that text. 3) set the smoothing value that passes the stem test once on body, with no per-component overrides. 4) repeat the pixel test. Removing letter-spacing without step 1 makes text worse.

**Refines.** R-TYP-4 (sets size and weight only. This adds tracking and rendered stem weight)

**Sources.** <https://github.com/WebKit/WebKit/pull/10354>, <https://bugs.webkit.org/show_bug.cgi?id=252592>, <https://developer.apple.com/videos/play/wwdc2020/10175/>, <https://skip.house/blog/macos-font-rendering>

### N-SEAM-9 (should)

Move keyboard focus across the native and web seam in both directions and in visual order, also when the shell adds or removes views. Let arrow keys in the toolbar search field move through the web Suggestions. [From R-SEAM-11. Merges MAC-KEYLOOP-1]

**Check.** Grep app/macos for autorecalculatesKeyViewLoop (no match), though the find bar and reader-only toolbar items change at run time. Turn on Keyboard navigation. Tab past the last web control: focus goes to the next native key view. Shift-Tab from the sidebar into the page: focus lands on the last web control. Click a native control, then the page: the last focused DOM element gets focus again. Open the find bar and Tab through the window. In the toolbar search field, press Down Arrow with Suggestions showing: Toolbar.swift control(_:textView:doCommandBy:) handles only insertNewline: and cancelOperation:, so moveDown: and moveUp: do nothing. That is a finding.

**Premium version.** The main and Settings windows set autorecalculatesKeyViewLoop = true. The Tab loop crosses the seam in visual order both ways, with no skipped or trapped control. In the search field, Down and Up Arrow move a highlight through Suggestions while the caret stays in the field. Return opens the highlighted item. Esc closes Suggestions, then clears the field, then returns focus to the page.

**Refines.** R-KEY-3 (covers Tab inside the web layer only)

**Sources.** <https://wwdc.ai/2026/289>, <https://bugs.webkit.org/show_bug.cgi?id=161448>, <https://trac.webkit.org/changeset/262051/webkit>

### N-SEAM-10 (should)

Send Select All to the part that has focus. [From R-SEAM-12]

**Check.** Press Command-A on Home, the Library, Notes, and Chat with no field focused. Text highlighted across headers, rows, and chrome is a finding (user-select: none hides it on chrome, but Select All still selects the whole document). Press Command-A in the Paper: a selection that runs into margin cards or the web toolbar is a finding.

**Premium version.** selectAll: acts like AppKit. In a focused list it selects all rows. In the Paper it selects Paper text only. In a field it selects the field text. Where nothing can be selected, it does nothing and validateMenuItem disables the item.

**Refines.** R-KEY-1 (keeps the shortcut. This sets its scope)

**Sources.** <https://kilianvalkhof.com/talks/cross-platform-electron/>

### N-SEAM-11 (should)

Show plain-label tooltips with the system title tooltip, not a DOM tooltip. [From R-SEAM-13]

**Check.** Grep the web layer for custom tooltip elements as opposed to the title attribute. Hover icon controls at the right window edge, under the toolbar, and beside the sidebar. A DOM tooltip that the window edge clips or the sidebar glass covers is a finding.

**Premium version.** Icon controls with a plain label use title, so AppKit draws and times the tooltip and it can cross the window edge. A rich floating layer that must cross the edge is a native window requested through the bridge, as Raycast does (R-DLG-3 already covers popovers).

**Refines.** R-MOT-11: conflicts with its 'title is out of scope'. This rule wins for plain-label icon tooltips. R-MOT-11 timing then applies only to rich custom tooltips that remain.

**Sources.** <https://www.raycast.com/blog/a-technical-deep-dive-into-the-new-raycast>

### N-SEAM-12 (should)

Recover from a WebContent process crash in place. [From R-SEAM-14]

**Check.** Open a Paper in the Blog view, scroll to 60%, open Settings, and kill LocalXiv's com.apple.WebKit.WebContent process in Activity Monitor. webViewWebContentProcessDidTerminate (PapersToKindle.swift) reloads the main page at alpha 0 and closes Settings. Settings closing, a return to Home, a changed scroll position or view, or a blank frame is a finding.

**Premium version.** After a crash, the window shows the same Paper, view, scroll position, and open panel within about 1 s, with no blank frame. Settings reloads in place on the same pane. The retry budget is one reload per 30 s. After a second crash, the window shows an inline error with a Reload button.

**Refines.** R-COL-2 and R-TYP-16 (add crash recovery to no-blank-frame and Reading position restore)

**Sources.** <https://github.com/WebKit/WebKit/pull/500>, <https://danielcosenza.com/posts/mac-wkwebview-navigation-process-lifecycle/>

### N-SEAM-13 (should)

Use WebKit's native-appearance form controls in the web layer before drawing custom ones. [From R-SEAM-15]

**Check.** Grep CSS for appearance: none and -webkit-appearance: none on input and select. app.css:597-599 redraws input[type=range] with a custom thumb. List each custom checkbox, toggle, select, and slider in Settings, Setup, and dialogs. Turn on Increase Contrast and make the window non-key. A custom control that does not change with these, or does not follow the accent, is a finding.

**Premium version.** Checkboxes, radios, switches (<input type=checkbox switch>), selects, and sliders keep appearance: auto, and accent-color takes the shell accent (N-SEAM-4). A <select> opens a real NSMenu. A control is redrawn only when no native one exists, and then it copies every state.

**Refines.** R-SHELL-12 (asks web controls to behave like AppKit. This says to use WebKit's AppKit-drawn controls first)

**Sources.** <https://webkit.org/blog/17640/webkit-features-for-safari-26-2/>, <https://webkit.org/blog/17541/webkit-features-for-safari-26-1/>

### N-SEAM-14 (should)

Keep WKWebView browser gestures off and Web Inspector out of Release builds. Route pinch to the reading size only. [From R-SEAM-16]

**Check.** Grep Swift for allowsMagnification, allowsBackForwardNavigationGestures, and isInspectable (none today, so defaults apply). In a Release build, two-finger swipe and pinch do not scale or navigate the page, and the context menu has no Inspect Element. isInspectable = true appears only under #if DEBUG.

**Premium version.** A pinch never scales the whole UI. Where pinch has a meaning, it changes the reading size through the app setting (GestureEvent in the Paper), so the toolbar, margin, and chrome keep their size. A swipe never moves to a blank history entry.

**Refines.** R-TYP-5 (text enlargement goes through the reading size or pageZoom, not magnification)

**Sources.** <https://developer.apple.com/documentation/webkit/wkwebview/allowsmagnification>, <https://developer.apple.com/documentation/webkit/wkwebview>

## Reading and annotation

### N-READ-1 (should)

Let the toolbar auto-hide in full screen while a reading view is open, with no reflow when it shows or hides. [From READ-1]

**Check.** Shell.swift has no window(_:willUseFullScreenPresentationOptions:). Open a Paper and press Control-Command-F: the toolbar and its glass band stay over the text. After adding the option, move the pointer to the top to show the toolbar and record: page text must not move. WebKit sets the top obscured inset to zero while the full-screen toolbar is hidden (WebKit commit 5c93ade), so a layout that follows safeAreaInsets can reflow.

**Premium version.** While the Paper, Overview, or Blog is open, the delegate returns [.fullScreen, .autoHideMenuBar, .autoHideDock, .autoHideToolbar]. On Home and the Library it returns the proposed options. The toolbar shows over the page without a reflow. Apple Books and PDF Expert hide reading chrome in full screen.

**Sources.** <https://devstreaming-cdn.apple.com/videos/wwdc/2015/22160ycymy0qg/221/221_improving_the_full_screen_window_experience.pdf>, <https://developer.apple.com/documentation/appkit/nsapplication/presentationoptions-swift.struct/autohidetoolbar>, <https://github.com/WebKit/WebKit/commit/5c93ade672f8cebd902fc2e07d4656f7a4db0d00>, <https://support.apple.com/guide/books/read-books-ibks5f526382/mac>

### N-READ-2 (should)

Keep the display awake while the reader actively reads. [From READ-2]

**Check.** Grep app/macos for beginActivity, idleDisplaySleepDisabled, or IOPMAssertion (none). Set display sleep to 2 minutes and read one section without input: the screen dims.

**Premium version.** While a reading view is in the key window and the reader scrolled, clicked, or pressed a key in the last 10 minutes, hold ProcessInfo.beginActivity(options: .idleDisplaySleepDisabled, reason: 'Reading a Paper'). End it after 10 minutes with no input, and when the window resigns key, is minimised, or the app hides. Settings > Reading has a toggle. Apple Books has 'Extend by 10 minutes while reading'.

**Sources.** <https://support.apple.com/guide/books/change-books-settings-ibksa12a5a23/mac>, <https://support.readdle.com/pdfexpert/en_US/reading-pdfs/reading-mode>

### N-READ-3 (should)

Fill the Library Reading mark by the furthest-read fraction. [From READ-4]

**Check.** render.js libraryRow draws icon('progress', 'i ring') as one static glyph for every Paper in the Reading state. Two Papers at 10% and 90% look the same.

**Premium version.** The ring stroke fills to the furthest-read fraction (stroke-dasharray on the SVG circle). The row aria-label and tooltip say 'Reading, 40%' in tabular numerals. Kindle shows percent read on each cover. Reeder fills a circle for an episode in progress.

**Refines.** R-COL-7 and R-TYP-17 (the Reading mark also shows how far)

**Sources.** <https://docs.readwise.io/reader/docs/faqs>, <https://www.macstories.net/reviews/reeder-a-new-approach-to-following-feeds/>

### N-READ-4 (should)

After a long jump in the Paper, show a way back in the corner of the page. [From READ-5]

**Check.** In the Paper, click an outline entry or follow a citation to the bibliography. Look at the bottom corners of the reading pane: only Go > Back (Command-[) returns, and nothing on the page shows the way back.

**Premium version.** After a jump of more than one screen, a small chip in the bottom leading corner says, for example, 'Back to 3.2 Attention'. A click or Command-[ returns to the passage and flashes it. The chip leaves when the reader returns or reads at the new place for some seconds. Its inset follows --window-corner (N-GLASS-4). Apple Books on Mac shows a Go Back control after a multipage jump.

**Refines.** R-TYP-16 and R-TYP-17 (a jump leaves the Reading position alone. This adds a visible return control)

**Sources.** <https://support.apple.com/guide/books/read-books-ibks5f526382/mac>, <https://github.com/ahrm/sioyek-documentation/blob/main/docs/source/usage.rst>

### N-READ-5 (should)

Let one key apply each Highlight colour from the selection toolbar. [From READ-7]

**Check.** selection.js bar.onkeydown handles only Escape, Left Arrow, and Right Arrow. Select text with Shift-Arrow and try to choose Question without the pointer.

**Premium version.** While the selection toolbar is open, keys 1 to 4 apply Key point, Question, Use in my work, and Disagree, and N opens the Note editor. Each swatch tooltip shows its key, for example 'Question (2)'.

**Refines.** R-ANN-1 (adds a keyboard path for the colour choice)

**Sources.** <https://blog.readwise.io/p/f8c0f71c-fe5f-4025-af57-f9f65c53fed7/>, <https://github.com/ahrm/sioyek-documentation/blob/main/docs/source/usage.rst>

### N-READ-6 (should)

Show the keyboard shortcut in the tooltip of each web control that has one, and build menu keys and tooltip text from one table. [From READ-8. Merges MAC-TIP-1]

**Check.** Margin card actions, selection toolbar swatches, and the Chat send control have titles with no shortcut. grep 'kbd' in app/static: 0 matches. Help has no list of reading shortcuts.

**Premium version.** A web control with a shortcut shows the action and then the key, for example 'Add Note (N)' or 'Highlight (⌃⌘H)'. One table builds both the NSMenuItem keyEquivalent and the tooltip text, so they cannot disagree. Help > Keyboard Shortcuts lists the reading keys. Native toolbar items may keep plain labels, because their menu items show the keys. A control with no shortcut shows only its name.

**Sources.** <https://docs.readwise.io/reader/docs/faqs/navigation>, <https://www.raycast.com/blog/a-fresh-look-and-feel>

### N-READ-7 (should)

Mark a Highlight that has a Note in the text itself. [From READ-10]

**Check.** appearance.js paints ::highlight(lx-<colour>) with a fill only. At a narrow width, where margin cards collapse, a Highlight with a Note and one without look the same.

**Premium version.** A second highlight name (for example lx-noted) covers ranges whose Highlight has a Note, with a text-decoration such as a dotted underline in the Highlight colour, so the cue works in every theme without the margin. Highlights for Mac draws a bubble icon next to annotations with a comment.

**Refines.** R-ANN-5 (adds an in-text cue that does not depend on the margin)

**Sources.** <https://highlightsapp.net/changelog/mac/>

### N-READ-8 (should)

Open Reference previews from cross-references that have no link. [From READ-11]

**Check.** reader.js opens previews only for a[href]. Hover plain 'Figure 2', 'Table 3', 'Eq. (4)', or 'Section 5' in a Paper whose converter left no link: nothing opens.

**Premium version.** After a chapter loads, unlinked labels that match a figure, table, equation, or section in the same Paper become preview triggers with the same hover timing, keyboard focus, and Escape behaviour as linked ones. Sioyek and Zotero 7 preview unlinked references.

**Refines.** R-ANN-7 and R-TYP-13 (extend previews to unlinked cross-references)

**Sources.** <https://sioyek.info/>, <https://www.zotero.org/blog/zotero-7/>

### N-READ-9 (should)

Show generated words and Paper words apart in each span, and keep the mark on copies. [From READ-13]

**Check.** Screenshot a Blog section and a Chat answer that quote the Paper: a verbatim quote must differ from generated prose by more than a label. When a Chat answer becomes a Note (margin.js), the Note keeps no mark that its words are generated.

**Premium version.** Each verbatim Paper quote in the Blog and Chat uses one quote style: the Paper reading font, a left rule, and its citation chip. A Note made from a Chat answer keeps a small 'Generated' mark that clears when the reader rewrites the text. iA Writer Authorship marks AI text until the writer types over it.

**Refines.** R-ANN-10 (labels each span and each copy, not only each surface)

**Sources.** <https://ia.net/writer/support/editor/authorship>, <https://ia.net/topics/see-what-ai-wrote>

### N-READ-10 (should)

Add the Apple Books section keys to the Go menu. [From READ-15]

**Check.** The Go menu in Menus.swift has only Back, Forward, Home, and Library. In the Paper, try to go to the next section or the start of this section from the keyboard.

**Premium version.** Go has Next Section (Option-Right Arrow), Previous Section (Option-Left Arrow), Beginning of Section (Option-Up Arrow), and End of Section (Option-Down Arrow), the same keys Apple Books on Mac uses for chapters. They act only when no text field has focus, so Option-Arrow word moves in fields stay. Each jump flashes the heading.

**Refines.** R-KEY-1 (adds the Apple Books chapter keys)

**Sources.** <https://support.apple.com/guide/books/keyboard-shortcuts-and-gestures-ibk0a716cf4-9a70-485b-9835-72e3c7ed6c29/mac>

### N-READ-11 (should)

Ship the sample Paper with annotations that teach by example. [From READ-17]

**Check.** app/sample/attention/sample.json has only the keys paper and generations. Open the sample Paper: the margin is empty.

**Premium version.** The sample Paper opens with one Highlight in each of the four colours (so the names show in the cards), one Note, one Question card with an answer, and one margin line such as 'Select any sentence to add your own Highlight.' The reader can remove them, and Undo brings them back. Readwise puts a teaching document in every new Library.

**Refines.** R-DLG-9 and R-STATE-12 (first-run Paper shows annotation by example)

**Sources.** <https://blog.readwise.io/p/bf87944f-b0fe-4f08-a461-f75ab8aded6a/>, <https://docs.readwise.io/reader/docs/faqs>

## Craft of acclaimed Mac apps

### N-CRAFT-1 (must)

Make the app icon in the macOS 26 layered format. Supply square, unmasked layers, and let the system draw the shape, edge, highlights, and shadow. [From MAC-ICON-1]

**Check.** app/assets/icon.svg draws its own rounded-square path with a grey #d5cdbf stroke. build-icon.sh makes only AppIcon.icns. build-release.py and install-app.sh set CFBundleIconFile, not CFBundleIconName. No .icon file exists. Put the Dock in Dark, Clear, and Tinted icon styles: a grey frame around the icon or a flat icon with no glass is a finding.

**Premium version.** An AppIcon.icon from Icon Composer: a full-bleed paper-colour background, the three sheets as foreground layers in at most 4 groups, no drawn border, no pre-masked corners, no drawn shadow, lines thick enough for 16 px. Dark and Mono appearances are in the same file. The build compiles it with actool into Assets.car and sets CFBundleIconName. AppIcon.icns stays as the fallback.

**Sources.** <https://developer.apple.com/design/human-interface-guidelines/app-icons>, <https://developer.apple.com/documentation/xcode/creating-your-app-icon-using-icon-composer>, <https://culturedcode.com/things/blog/2025/09/things-for-os-26/>

### N-CRAFT-2 (should)

Open LocalXiv where the reader quit it: the page, the open Paper, its view, the sidebar selection, and full screen. Restore UI state only, not Library data. [From MAC-RESTORE-1]

**Check.** app.js:1141 runs nav.push({page: 'home'}) at every start. Grep app/macos for isRestorable, restorationClass, encodeRestorableState, invalidateRestorableState, applicationSupportsSecureRestorableState (0 matches). Open a Paper in the Blog, quit, relaunch: Home opens.

**Premium version.** The main window sets identifier, isRestorable = true, and a restorationClass. The app delegate returns true from applicationSupportsSecureRestorableState. Each Chrome state change calls invalidateRestorableState(). encodeRestorableState writes only the nav entry (page, filter, Paper id, view). restoreState queues an open command for the web app, which then restores the Reading position. No Home frame shows first. The restoreWindow completion handler is always called.

**Refines.** R-TYP-16 (adds app-level restore across quit and restart)

**Sources.** <https://developer.apple.com/videos/play/wwdc2026/289/>, <https://wwdc.ai/2026/289>, <https://developer.apple.com/documentation/appkit/restoring-your-app-s-state-with-appkit>

### N-CRAFT-3 (should)

Let an information or error alert never block a quit or an overnight restart. [From MAC-QUIT-1]

**Check.** PapersToKindle.swift has beginSheetModal calls for information and error alerts (lines 108, 258, 367). None sets preventsApplicationTerminationWhenModal = false. Show an update or launch-failure alert, then choose Restart from the Apple menu: LocalXiv must not stop it.

**Premium version.** Each alert or sheet that does not guard unsaved work sets alert.window.preventsApplicationTerminationWhenModal = false. The 1.5 s flush in applicationShouldTerminate stays the only delay at quit.

**Sources.** <https://developer.apple.com/videos/play/wwdc2026/289/>, <https://wwdc.ai/2026/289>

### N-CRAFT-4 (should)

Make About LocalXiv a complete, correct panel. [From MAC-ABOUT-1]

**Check.** Menus.swift calls orderFrontStandardAboutPanel with no options. build-release.py sets NSHumanReadableCopyright to a licence line, not a copyright. install-app.sh sets no CFBundleShortVersionString. No Credits file exists. Open About in Light and Dark.

**Premium version.** NSHumanReadableCopyright is '© 2026 Akhil Theerthala'. Both builds set CFBundleShortVersionString and CFBundleVersion, so the panel shows 'Version 0.1.2 (N)'. The credits attributed string uses labelColor, secondaryLabelColor, and linkColor, and links the AGPL licence, the third-party notices, and the project. It reads correctly in both appearances.

**Refines.** R-SHELL-4

**Sources.** <https://developer.apple.com/documentation/appkit/nsapplication/orderfrontstandardaboutpanel(options:)>, <https://stackoverflow.com/questions/53671360/macos-dark-mode-and-nsaboutpaneloptioncredits>

### N-CRAFT-5 (should)

Let the reader start a search by typing. On Home, the Library, and Notes, a letter key with no modifier opens the toolbar search with that letter in it. [From MAC-KEY-TRAVEL-1]

**Check.** app.js:351 handles only ArrowDown, ArrowUp, Home, and End in the Library list. Focus a Library row and type 'atten': nothing happens.

**Premium version.** A document keydown handler on Home, the Library, and Notes takes a printable key with no Command or Control modifier when no field has focus and sends it to the shell, which calls beginSearchInteraction() on the NSSearchToolbarItem and inserts the key. Suggestions show on the first key. Esc returns focus to the row. In the Paper, letter keys keep their reader meanings. Things calls this Type Travel.

**Sources.** <https://culturedcode.com/things/features/>, <https://culturedcode.com/things/support/articles/2803584/>

### N-CRAFT-6 (should)

Show what Return will do before the reader presses it. When the search text names exactly one arXiv paper, the first Suggestions row says whether Return adds it or opens it. [From MAC-PREVIEW-1]

**Check.** The field placeholder is 'Search or paste a link'. Paste https://arxiv.org/abs/1706.03762 and do not press Return: no row says that Return adds this Paper, or that it is already in the Library.

**Premium version.** When the text parses as an arXiv ID or link, the first row shows the parsed ID and the title when known, and says 'Add to Library' or 'In Library, Open'. Return does exactly that. Other text shows normal search results.

**Sources.** <https://startupproject.org/blog/stay-inspired-not-on-auto-pilot-an-interview-with-fantasticals-founder/>

### N-CRAFT-7 (should)

Play a trackpad haptic only when a dragged value snaps into place, with the Alignment pattern. [From MAC-HAPTIC-1]

**Check.** Grep for NSHapticFeedbackManager (0 matches). The figure canvas (app.js figureFitUnit) snaps to Fit. On a Force Touch trackpad, drag figure zoom past Fit and 100%: no tap.

**Premium version.** The figure canvas sends a bridge message when zoom crosses Fit or 100% or a pan reaches an edge, and the shell calls NSHapticFeedbackManager.defaultPerformer.perform(.alignment, performanceTime: .drawCompleted). The text size NSSlider keeps its system behaviour. No haptic for clicks, completed jobs, or events the reader did not start.

**Sources.** <https://developer.apple.com/design/human-interface-guidelines/playing-haptics>, <https://developer.apple.com/documentation/appkit/nshapticfeedbackmanager>

### N-CRAFT-8 (should)

Give sibling controls one height and one feedback duration, and do not let a growing field move the content above it. [From MAC-SAME-1]

**Check.** Measure the heights of adjacent web buttons (Try Again beside other quiet buttons, the margin card action row): a difference of 1 px or more is a finding. List the transition values on :hover and :active rules of sibling controls: a sibling with none or a different duration is a finding. Type a second line in the Chat composer and a Note field: the panel above must not jump.

**Premium version.** One control-height token and one feedback-duration token on :root, used by every button class. The Chat composer grows upward within a fixed frame and keeps the answer list in place.

**Refines.** R-MOT-1 and R-VIS-6 (add a height token and one duration per control family)

**Sources.** <https://linear.app/now/quality-wednesdays>, <https://www.linear.app/now/how-we-redesigned-the-linear-ui>

## Smoothness and speed

### N-PERF-1 (must)

Show the window, sidebar, and toolbar at once at launch from cached Chrome state, keep heavy scripts off the first-frame path, and reveal the web view only after WebKit has drawn a complete frame. Measure launch against a budget. [From MAC-LAUNCH-1. Merges PERF-14, PERF-5]

**Check.** Shell.swift LaunchView.init shows the spinner and 'Opening your library…' at t = 0. The sidebar gets rows only from the first Chrome state, which needs the Python service. index.html loads pele.global.js (about 730 KB) and rough.js as parser-blocking <script> tags in <head>, though only figure views need them. app.js calls chrome.ready() right after show() and openPaper(), and shell.js posts {type:'ready'} at once, so Swift sets alphaValue = 1 before any frame is drawn (an R-COL-2 violation). Measure with os_signpost marks at main, window visible, service answer, and 'ready', median of 5 warm launches. Record launch frame by frame in Dark and Sepia.

**Premium version.** The shell keeps the last Chrome state (sidebar rows, counts, title) in UserDefaults and draws the chrome from it in the first frame, as it already does for the reading theme. The spinner shows only after about 1 s with no 'ready'. pele.global.js and rough.js have defer or load when the first figure view opens. The page posts 'ready' after the next paint (rAF then setTimeout 0, with the existing timer fallback). Target: chrome visible in about 400 ms, and the first visible web frame is complete.

**Refines.** R-STATE-2 (adds the cached-chrome first frame and a launch budget). R-COL-2 (the 'ready' post site is where its check fails)

**Sources.** <https://www.raycast.com/blog/a-technical-deep-dive-into-the-new-raycast>, <https://developer.apple.com/videos/play/wwdc2019/423/>, <https://blog.persistent.info/2016/02/avoiding-incremental-rendering-in.html>

### N-PERF-2 (should)

Do not read layout in a scroll handler. A scroll event stores the offset and schedules one frame. That frame does all reads first and all writes after. Track position with IntersectionObserver. [From PERF-1. Merges the spy() part of PERF-9]

**Check.** margin.js scrolled() (line 134-146) writes card.element.style.top and then calls margin.getBoundingClientRect() in the scroll event (read after write, forced layout), and line.draw() calls getClientRects() and getBoundingClientRect() and writes SVG attributes in the event. reader.js spy() reads getBoundingClientRect() of every heading. Record a Web Inspector Timeline while scrolling a Paper with an open margin card for 3 s: each Forced Layout with a margin.js initiator is a finding, and frames over 8.3 ms at 120 Hz are findings.

**Premium version.** The scroll handler only calls the existing schedule(). The rAF callback reads the card box, margin box, frame box, and range rects, then writes style.top, the offer top, and the path. A card that follows the view uses position: sticky where possible. Heading tracking uses IntersectionObserver. A scroll recording shows 0 forced layouts.

**Sources.** <https://web.dev/articles/avoid-large-complex-layouts-and-layout-thrashing>, <https://webkit.org/web-inspector/timelines-tab/>

### N-PERF-3 (should)

Drive web motion with compositor-accelerated transform and opacity only, never a rAF loop, because WebKit updates non-accelerated animations and rAF at about 60 Hz while Core Animation runs accelerated ones at the display rate. [From PERF-2]

**Check.** List every transition, @keyframes, element.animate(), and rAF animation loop. An animated property other than transform, opacity, or filter (stroke-dashoffset, background-color, box-shadow, width, top, an SVG attribute), or a rAF loop that writes style each frame, runs at no more than 60 Hz. Check that web motion beside native motion (sidebar collapse, NSPopover, window resize) is accelerated, in the Web Inspector Layers tab.

**Premium version.** Motion uses CSS transitions or WAAPI on transform and opacity, so it runs at 120 Hz and survives a busy main thread. will-change is absent by default and added only on one element where a recording shows a late layer. The app does not flip WebKit's private 60 fps feature flag (Raycast does, through feature-flag SPI. That is a deliberate power and SPI tradeoff, not a default).

**Refines.** R-MOT-8 (adds the WKWebView 60 Hz reason and the rAF-loop ban)

**Sources.** <https://webkit.github.io/explainers/animation-frame-rate/>, <https://bugs.webkit.org/show_bug.cgi?id=294338>, <https://www.raycast.com/blog/a-technical-deep-dive-into-the-new-raycast>, <https://emilkowal.ski/ui/great-animations>

### N-PERF-4 (should)

An idle page draws no frames. Do not loop a paint-only animation forever on a full-viewport layer. [From PERF-3]

**Check.** app.css:538 gives .lx-line path animation: lx-march .7s linear infinite on stroke-dashoffset, and .lx-line is position: fixed. inset: 0. Open a margin card, do not touch input, and turn on paint flashing: a region that stays flashing, or a non-flat WebContent CPU timeline, is a finding.

**Premium version.** The dotted line marches for a short finite time (for example 2 iterations) and then stays still, or the SVG is sized to the path bounding box and moves by a transform on a <g>. With a card open and no input, paint flashing shows nothing and CPU is flat.

**Refines.** R-MOT-7 (its keyframe exemption covers spinners and progress bars, not a decorative loop that repaints the viewport). R-MOT-10

**Sources.** <https://webkit.github.io/explainers/animation-frame-rate/>, <https://motion.dev/magazine/web-animation-performance-tier-list>, <https://webkit.org/web-inspector/timelines-tab/>

### N-PERF-5 (should)

Load the bundled figure font before the first Figure render, so each figure draws once. [From PERF-4. Merges MAC-FONT-1]

**Check.** index.html has no <link rel=preload> for /static/Excalifont.woff2. App.css declares it with font-display: swap. reader.js:878-879 draws a figure and draws it again when Excalifont loads. Quit, relaunch, and open an Overview or Blog with figures: a recording that shows labels change shape or boxes resize, or two Pele renders per figure, is a finding.

**Premium version.** index.html preloads /static/Excalifont.woff2 with as=font, type=font/woff2, and crossorigin. Boot starts document.fonts.load('16px Excalifont'). The local font uses font-display: block. The figure code waits on that one promise with a short timeout (about 100-300 ms) and draws once.

**Refines.** R-STATE-16 (it says load reading fonts locally or preload them. This adds the figure font, the block value, and the second-draw check)

**Sources.** <https://web.dev/articles/font-best-practices>, <https://web.dev/articles/preload-optional-fonts>

### N-PERF-6 (should)

Keep the web view drawing and its layout stable during native window and sidebar animations. [From PERF-6. Merges MAC-ZOOM-1]

**Check.** Choose Window > Zoom, double-click the toolbar, press Control-Command-F, and press Control-Command-S on a Paper and on an Overview with figures. Record at 60 fps or more. A frame where the page stays at the old size, shows a blank strip, or jumps at the end is a finding. ContentView.layout() sets webView.obscuredContentInsets = safeAreaInsets on each layout pass, and pele.global.js redraws a figure from a ResizeObserver. In a Timeline recording, more than one figure render per collapse, or a reading line that rewraps, is a finding.

**Premium version.** WebKit suspends drawing during setFrame(animate: true). Where the shell animates a window frame, it overrides setFrame and runs the change as implicit Core Animation in an NSAnimationContext group (allowsImplicitAnimation = true), as Raycast does, so the WKWebView keeps drawing. The reading column has a fixed measure, so a wider viewport moves the column and no line rewraps. Figures keep their SVG during the motion and redraw once when the width is stable (viewDidEndLiveResize, or about 100 ms with no change).

**Refines.** R-SHELL-13 (adds the Zoom, full-screen, and sidebar animations, the implicit-animation fix, and a per-frame layout and figure-render count)

**Sources.** <https://www.raycast.com/blog/a-technical-deep-dive-into-the-new-raycast>, <https://web.dev/articles/avoid-large-complex-layouts-and-layout-thrashing>, <https://webkit.org/web-inspector/timelines-tab/>

### N-PERF-7 (should)

When web motion runs at the same time as a native animation, use the native duration and the Core Animation default curve, which equals CSS ease. [From PERF-7]

**Check.** Find each place where web motion runs during a native animation, for example SettingsWindow.swift fit() animates setFrame while the web pane changes. Record the pane switch and the sidebar toggle: the web part ends in the same frame as the native part. In Swift, a custom sidebar duration set only through NSAnimationContext has no effect on NSSplitViewItem.isCollapsed.

**Premium version.** Web motion in step with AppKit motion uses cubic-bezier(0.25,0.1,0.25,1) and the native duration (NSWindow.animationResizeTime(_:) for frames. The system sidebar duration left at default). Web-only motion keeps the R-MOT-2 ease-out token. Under Reduce Motion both halves change at once.

**Refines.** R-MOT-2 (adds an exception for web motion in step with AppKit motion)

**Sources.** <https://developer.apple.com/documentation/quartzcore/camediatimingfunctionname/default>, <https://developer.apple.com/documentation/appkit/nsanimationcontext/duration>, <https://stackoverflow.com/questions/55570683/nssplitviewitem-iscollapsed-ignores-animation-durations>

### N-PERF-8 (should)

Keep the passage on screen still when content above it changes height, with one owner per scroller: JavaScript or CSS scroll anchoring, never both. [From PERF-8. Merges READ-14]

**Check.** reader.js holds the position by hand (held, heldY, resizeReader() calls scrollTo after iframe height changes). grep overflow-anchor finds nothing. WebKit 26 (macOS 26) has no scroll anchoring. Safari 27 (macOS 27) has it on, so both can correct one jump. On macOS 26 and 27, scroll to mid-chapter, then change content above (late images, Aa text size, a margin card above, a Blog section finishing above, a Library import adding a row): the first visible line moving by more than one line, or moving twice, is a finding.

**Premium version.** Where JavaScript holds the position (the Paper root scroller), CSS sets overflow-anchor: none so the result is the same on WebKit 26 and 27. Elsewhere, before an insert above the viewport, the page stores the first visible passage and its offset and restores them in the same frame. In Chat, overflow-anchor stays auto on WebKit 27 with the JS fallback on 26. In the Library, a finished import does not move the row under the pointer.

**Refines.** R-STATE-16, R-TYP-16, and R-ANN-14 (add the WebKit 26/27 split and single ownership of anchoring)

**Sources.** <https://caniuse.com/css-overflow-anchor>, <https://github.com/WebKit/WebKit/pull/58575>, <https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Scroll_anchoring/Overview>, <https://reeder.app/help/>

### N-PERF-9 (should)

Keep the work per frame of a streaming Chat answer constant as the answer grows. [From PERF-12]

**Check.** chat.js drawPending() coalesces tokens into one rAF, but each frame calls prose() on the full answer text, so frame cost grows with length. Ask for a long answer (over 1,500 words, with math): frame time that grows over the stream, or frames over 8.3 ms near the end, is a finding.

**Premium version.** Finished blocks render once and are kept. Each frame renders only the last open block. Math renders when its block closes. Frame time near the end equals the start, under 8.3 ms.

**Refines.** R-ANN-14 (adds a frame-cost budget for the stream)

**Sources.** <https://web.dev/articles/avoid-large-complex-layouts-and-layout-thrashing>, <https://webkit.org/web-inspector/timelines-tab/>

### N-PERF-10 (should)

Choose the loading form by the scope of the wait: a layout-matched skeleton only for a full view that takes 1-10 s, a small inline indicator for one module, and progress for a process. Never show an empty frame skeleton. [From PERF-13]

**Check.** For each loading state (Paper open from network, Overview and Blog first render, Paper search, figure regeneration), note the form and scope. A spinner over a full-view load, a skeleton for import or export, or a skeleton with only a header and an empty body is a finding. Compare a skeleton screenshot with the loaded view: blocks sit at the same positions.

**Premium version.** An uncached Paper that takes over 1 s shows a skeleton of the reading column (title block, author line, paragraph bars at the measure width). One slow figure shows a small indicator in its reserved box. Generation and import use R-STATE-3 progress. A load under 1 s shows nothing.

**Refines.** R-STATE-2 (sets timing. This adds the form by scope and bans empty frame skeletons)

**Sources.** <https://www.nngroup.com/articles/skeleton-screens/>
