import Cocoa
import WebKit

// The Chrome state that the web app posts (docs/superpowers/specs/2026-10-14-ui-redesign-design.md).
// A missing or mistyped field takes its default, so a page that is ahead of or behind this shell still draws.
struct ChromeState: Codable, Equatable {
    var mode = "home", title = "LocalXiv", subtitle = ""
    var canBack = false, canForward = false
    var sidebar = Sidebar()
    var views: Views? = nil
    var actions: [String: [Action]] = [:]
    var prefs = Prefs()
    var activity: Activity? = nil
    var search = Search()
    // A text field in the page has the focus, and the page can restore a removed Question card (Edit › Undo, which
    // names the action that removed it).
    var editing = false, canUndo = false, undoName = ""
    // A modal web dialog is open, and the page drops the commands of the sidebar, the toolbar, and the page menu items.
    var modal = false

    struct Sidebar: Codable, Equatable {
        var selected: String? = nil
        var counts: [String: Int] = [:]
        var recent: [Recent] = []
        var reader: Reader? = nil
    }
    struct Recent: Codable, Equatable { var id = "", title = "", current = false }
    // `link` is the Paper's arXiv link, or empty when the Paper has no arXiv ID.
    struct Reader: Codable, Equatable { var back = "Library", title = "", byline = "", link = "", outline: [Entry] = [] }
    struct Entry: Codable, Equatable { var id = "", label = "", number = "", level = 1, current = false }
    struct Views: Codable, Equatable { var current = "paper", overview = "off", blog = "off", paper = "ready" }
    struct Action: Codable, Equatable { var id = "", label = "", enabled = false, role: String? = nil, separatorBefore = false }
    struct Prefs: Codable, Equatable { var theme = "system", font = "new-york", size = 16, margins = "normal", spacing = "normal" }
    struct Activity: Codable, Equatable { var label = "", progress: Double? = nil, count = 1, failed = false }
    struct Search: Codable, Equatable { var query = "" }

    var allActions: [Action] { (actions["share"] ?? []) + (actions["more"] ?? []) }
}

extension KeyedDecodingContainer {
    subscript<T: Decodable>(key: Key, or fallback: T) -> T { (try? decodeIfPresent(T.self, forKey: key)) ?? fallback }
}

// The types are Codable, not only Decodable, because the synthesized Encodable supplies the CodingKeys used here.
extension ChromeState {
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self); self.init()
        mode = c[.mode, or: mode]; title = c[.title, or: title]; subtitle = c[.subtitle, or: subtitle]
        canBack = c[.canBack, or: canBack]; canForward = c[.canForward, or: canForward]
        sidebar = c[.sidebar, or: sidebar]; views = c[.views, or: views]; actions = c[.actions, or: actions]
        prefs = c[.prefs, or: prefs]; activity = c[.activity, or: activity]; search = c[.search, or: search]
        editing = c[.editing, or: editing]; canUndo = c[.canUndo, or: canUndo]; undoName = c[.undoName, or: undoName]
        modal = c[.modal, or: modal]
    }
}
extension ChromeState.Sidebar {
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self); self.init()
        selected = c[.selected, or: selected]; counts = c[.counts, or: counts]; recent = c[.recent, or: recent]; reader = c[.reader, or: reader]
    }
}
extension ChromeState.Recent {
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self); self.init()
        id = c[.id, or: id]; title = c[.title, or: title]; current = c[.current, or: current]
    }
}
extension ChromeState.Reader {
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self); self.init()
        back = c[.back, or: back]; title = c[.title, or: title]; byline = c[.byline, or: byline]; link = c[.link, or: link]; outline = c[.outline, or: outline]
    }
}
extension ChromeState.Entry {
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self); self.init()
        id = c[.id, or: id]; label = c[.label, or: label]; number = c[.number, or: number]; level = c[.level, or: level]; current = c[.current, or: current]
    }
}
extension ChromeState.Views {
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self); self.init()
        current = c[.current, or: current]; overview = c[.overview, or: overview]; blog = c[.blog, or: blog]; paper = c[.paper, or: paper]
    }
}
extension ChromeState.Action {
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self); self.init()
        id = c[.id, or: id]; label = c[.label, or: label]; enabled = c[.enabled, or: enabled]; role = c[.role, or: role]; separatorBefore = c[.separatorBefore, or: separatorBefore]
    }
}
extension ChromeState.Prefs {
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self); self.init()
        theme = c[.theme, or: theme]; font = c[.font, or: font]; size = c[.size, or: size]; margins = c[.margins, or: margins]; spacing = c[.spacing, or: spacing]
    }
}
extension ChromeState.Activity {
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self); self.init()
        label = c[.label, or: label]; progress = c[.progress, or: progress]; count = c[.count, or: count]; failed = c[.failed, or: failed]
    }
}
extension ChromeState.Search {
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self); self.init()
        query = c[.query, or: query]
    }
}

func commandScript(_ command: [String: Any]) -> String? {
    guard let json = try? JSONSerialization.data(withJSONObject: command) else { return nil }
    return "window.localxiv?.command(\(String(decoding: json, as: UTF8.self)))"
}

// The window: a split view with the sidebar and the web view, under a unified toolbar.
extension PapersApp: NSWindowDelegate {
    func makeWindow() {
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1180, height: 820), styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView], backing: .buffered, defer: false)
        window.title = "LocalXiv"
        window.toolbar = toolbar.toolbar
        window.toolbarStyle = .unified
        window.minSize = NSSize(width: 700, height: 500)
        window.isReleasedWhenClosed = false
        let configuration = WKWebViewConfiguration()
        configuration.userContentController.add(self, name: "shell")
        let page = PageView(frame: .zero, configuration: configuration)
        page.addItems = { [unowned self] in self.addSelectionItems(to: $0) }
        webView = page
        webView.identifier = NSUserInterfaceItemIdentifier("page")
        webView.underPageBackgroundColor = .clear
        // A web view with no page paints white, and the toolbar and sidebar glass would show it, so it stays clear until the page is ready.
        webView.alphaValue = 0
        webView.navigationDelegate = self; webView.uiDelegate = self
        findBar = FindBar(webView: webView)
        // The web view fills the window under the toolbar and the sidebar, so their glass shows the page. The page's layout
        // viewport and the launch state keep to the safe area beside and below them.
        let content = NSViewController()
        content.view = ContentView(webView: webView)
        let safe = content.view.safeAreaLayoutGuide
        for view in [webView!, launch] {
            content.view.addSubview(view)
            view.translatesAutoresizingMaskIntoConstraints = false
        }
        NSLayoutConstraint.activate([
            webView.topAnchor.constraint(equalTo: content.view.topAnchor), webView.bottomAnchor.constraint(equalTo: content.view.bottomAnchor),
            webView.leadingAnchor.constraint(equalTo: content.view.leadingAnchor), webView.trailingAnchor.constraint(equalTo: content.view.trailingAnchor),
            launch.topAnchor.constraint(equalTo: safe.topAnchor), launch.bottomAnchor.constraint(equalTo: safe.bottomAnchor),
            launch.leadingAnchor.constraint(equalTo: safe.leadingAnchor), launch.trailingAnchor.constraint(equalTo: safe.trailingAnchor)])
        let split = NSSplitViewController()
        let side = NSSplitViewItem(sidebarWithViewController: sidebar)
        side.minimumThickness = 200; side.maximumThickness = 320
        // The Activity line is a bottom accessory of the sidebar, so the outline scrolls under it.
        let activityAccessory = NSSplitViewItemAccessoryViewController()
        activityAccessory.view = sidebar.activity
        // The line has its own edge insets, so the standard content insets would double them.
        activityAccessory.automaticallyAppliesContentInsets = false
        activityAccessory.isHidden = true
        sidebar.activity.accessory = activityAccessory
        side.addBottomAlignedAccessoryViewController(activityAccessory)
        split.addSplitViewItem(side)
        // The sidebar overlays the content item, so the content spans the window and its safe area starts beside the sidebar.
        // At the 700 pt minimum window, the 200 pt sidebar leaves the page its 500 pt.
        let main = NSSplitViewItem(viewController: content)
        main.automaticallyAdjustsSafeAreaInsets = true
        main.minimumThickness = 500
        // The find bar is an accessory of the content item, under the toolbar and beside the sidebar. The system draws
        // the edge between it and the page, and the content's safe area starts below it.
        let findAccessory = NSSplitViewItemAccessoryViewController()
        findAccessory.view = findBar
        // The bar has its own edge insets, so the standard content insets would double them.
        findAccessory.automaticallyAppliesContentInsets = false
        findAccessory.isHidden = true
        findBar.accessory = findAccessory
        main.addTopAlignedAccessoryViewController(findAccessory)
        split.addSplitViewItem(main)
        split.splitView.autosaveName = "Sidebar"
        window.contentViewController = split
        // The web view starts at the window's top left, where the key view order would give it the first focus; the sidebar takes it.
        window.initialFirstResponder = sidebar.outline
        // Tab out of the page's last stop goes to the sidebar, which shows its accent selection, and back into the page.
        // With no next key view, the web view keeps the focus with no element focused, and no control shows it.
        webView.nextKeyView = sidebar.outline
        sidebar.outline.nextKeyView = webView
        window.delegate = self
        // A content view controller resizes the window to its view, so the size and the saved frame come after it.
        // The window opens centred until it has a saved frame.
        window.setContentSize(NSSize(width: 1180, height: 820))
        window.center()
        window.setFrameAutosaveName("PaperLibrary")
        // The sidebar opens at 250 pt, so most outline entries fit, until the reader drags it to a width of their own.
        // The split view sets its position only after its first layout, so it lays out now, before the window shows.
        if UserDefaults.standard.object(forKey: "NSSplitView Subview Frames Sidebar") == nil {
            split.view.layoutSubtreeIfNeeded()
            split.splitView.setPosition(250, ofDividerAt: 0)
        }
        sidebar.send = { [unowned self] in self.send($0) }
        sidebar.sendClick = { [unowned self] in self.send($0, then: $1) }
        toolbar.send = { [unowned self] in self.send($0) }
        toolbar.page = webView
        // The window opens on the last Home state, so the sidebar and the title show before the page is ready.
        // The page always opens on Home, and its first state replaces this one.
        var initial = ChromeState(); initial.title = "Home"; initial.sidebar.selected = "home"
        if let data = UserDefaults.standard.data(forKey: "LastChromeState"), let cached = try? JSONDecoder().decode(ChromeState.self, from: data) { initial = cached }
        sidebar.apply(initial); toolbar.apply(initial); window.title = initial.title
    }

    // Messages from the main page: {type: 'ready'} once its command handlers exist, then {type: 'state', state},
    // {type: 'settings', pane} to open the Settings window on a pane, and {type: 'menu', x, y, items} to show a context menu.
    func shell(_ body: [String: Any]) {
        switch body["type"] as? String {
        case "ready":
            pageReady = true
            showPage()
            // A page that loads while LocalXiv is inactive gets the class too, before a queued command can show a toast.
            syncActive(NSApp.isActive)
            queued.forEach(deliver)
            queued.removeAll()
        case "state":
            guard let value = body["state"], JSONSerialization.isValidJSONObject(value),
                  let data = try? JSONSerialization.data(withJSONObject: value),
                  let state = try? JSONDecoder().decode(ChromeState.self, from: data) else { return }
            apply(state)
        case "settings":
            showSettings(pane: body["pane"] as? String)
        case "menu":
            showMenu(body["items"] as? [[String: Any]] ?? [], x: body["x"] as? Double, y: body["y"] as? Double)
        default: break
        }
    }

    func apply(_ state: ChromeState) {
        updatePaperMenu(state)
        chrome = state
        window.title = state.title
        window.subtitle = state.subtitle
        sidebar.apply(state)
        toolbar.apply(state)
        if state.mode != "reader" { findBar.close() }
        applyTheme()
        // Only a Home state goes to the cache, because the page opens a Paper at launch only when it resumes reading.
        var cached = ChromeState(); cached.title = "Home"; cached.prefs = state.prefs
        cached.sidebar.selected = "home"; cached.sidebar.counts = state.sidebar.counts
        cached.sidebar.recent = state.sidebar.recent.map { var row = $0; row.current = false; return row }
        if let data = try? JSONEncoder().encode(cached), UserDefaults.standard.data(forKey: "LastChromeState") != data {
            UserDefaults.standard.set(data, forKey: "LastChromeState")
        }
    }

    func showPage() {
        launch.removeFromSuperview()
        webView.alphaValue = 1
    }

    // WebKit does not know prefers-reduced-transparency, so both pages read Reduce Transparency from a class on html.
    func syncReduceTransparency() {
        let on = NSWorkspace.shared.accessibilityDisplayShouldReduceTransparency
        let script = WKUserScript(source: "document.documentElement.classList.toggle('reduce-transparency', \(on))", injectionTime: .atDocumentStart, forMainFrameOnly: true)
        for webView in [webView, settings?.webView].compactMap(\.self) {
            webView.configuration.userContentController.removeAllUserScripts()
            webView.configuration.userContentController.addUserScript(script)
            webView.evaluateJavaScript(script.source)
        }
    }

    // The Reading theme sets each window's appearance, so the sidebar, toolbar, and popovers match the page.
    // Match System leaves the windows to the app's appearance, which follows macOS. Sepia also warms the main and
    // Settings window backgrounds, so the launch state and the Settings toolbar band meet the page without a cool edge.
    // The main window's toolbar and sidebar glass have the page under them, so they need no Sepia colour of their own.
    // The next launch applies the theme kept here before its window shows.
    func applyTheme() {
        let theme = chrome.prefs.theme, sepia = theme == "sepia"
        if UserDefaults.standard.string(forKey: "ReadingTheme") != theme { UserDefaults.standard.set(theme, forKey: "ReadingTheme") }
        let appearance = ["dark": NSAppearance.Name.darkAqua, "light": .aqua, "sepia": .aqua][theme].flatMap(NSAppearance.init(named:))
        for window in NSApp.windows where window.appearance?.name != appearance?.name { window.appearance = appearance }
        let background = sepia ? NSColor(hex: 0xf8f2e6) : .windowBackgroundColor
        // A title bar draws its own band unless it is transparent, and after an appearance change the main window's band
        // can keep its light colour over the Sepia background, so in Sepia both bands show the window background.
        for window in [window, settings?.window].compactMap(\.self) {
            if window.backgroundColor != background { window.backgroundColor = background }
            if window.titlebarAppearsTransparent != sepia { window.titlebarAppearsTransparent = sepia }
        }
    }

    // Below 1000 pt the sidebar collapses on its own, once when the window gets narrow, so the toggle can show it again.
    // A collapse from canCollapseFromWindowResize comes only from a live resize, and its content minimum would hold the window at 800 pt.
    // When the window gets wide again, a sidebar that collapsed on its own comes back.
    // shortcut: a sidebar that the reader showed and hid again while the window was narrow also comes back; a
    // toggleSidebar override in an NSSplitViewController subclass can clear autoCollapsed if that matters.
    func windowDidResize(_ notification: Notification) {
        let wide = window.frame.width >= 1000
        let side = (window.contentViewController as? NSSplitViewController)?.splitViewItems.first
        if wasWide && !wide, side?.isCollapsed == false {
            side?.isCollapsed = true; autoCollapsed = true
        } else if !wasWide && wide, autoCollapsed {
            if side?.isCollapsed == true { side?.isCollapsed = false }
            autoCollapsed = false
        }
        wasWide = wide
    }

    func send(_ command: [String: Any]) {
        if pageReady { deliver(command) } else { queued.append(command) }
    }

    // A command with a callback once the page has run it. The page posts a state that it set before then ahead of the
    // reply. A page that is not ready queues the command and calls back at once.
    func send(_ command: [String: Any], then done: @escaping () -> Void) {
        guard pageReady else { send(command); return done() }
        webView.callAsyncJavaScript("await window.localxiv?.command(command)", arguments: ["command": command], in: nil, in: .page) { _ in done() }
    }

    private func deliver(_ command: [String: Any]) {
        if let script = commandScript(command) { webView.evaluateJavaScript(script) }
    }
}

// The content item's view. The page's obscured insets follow the safe area, which changes with the window size, full
// screen, the toolbar, the sidebar, and the find bar, so the page does not scroll a match under the find bar.
final class ContentView: NSView {
    let webView: WKWebView

    init(webView: WKWebView) {
        self.webView = webView
        super.init(frame: .zero)
    }
    required init?(coder: NSCoder) { nil }

    override func layout() {
        super.layout()
        webView.obscuredContentInsets = safeAreaInsets
    }
}

// The page. Its context menu gets the selection commands after WebKit's own items, as in Apple Books.
final class PageView: WKWebView {
    var addItems: (NSMenu) -> Void = { _ in }
    // LocalXiv is not a browser. These items do nothing here, and Reload starts the web app again, so open work is lost.
    private static let browserItems: Set<String> = [
        "WKMenuItemIdentifierOpenFrameInNewWindow", "WKMenuItemIdentifierReload", "WKMenuItemIdentifierGoBack", "WKMenuItemIdentifierGoForward",
        "WKMenuItemIdentifierOpenLinkInNewWindow", "WKMenuItemIdentifierOpenImageInNewWindow", "WKMenuItemIdentifierDownloadImage",
        "WKMenuItemIdentifierDownloadLinkedFile", "WKMenuItemIdentifierOpenMediaInNewWindow", "WKMenuItemIdentifierDownloadMedia"]

    override func willOpenMenu(_ menu: NSMenu, with event: NSEvent) {
        super.willOpenMenu(menu, with: event)
        for item in menu.items where Self.browserItems.contains(item.identifier?.rawValue ?? "") { menu.removeItem(item) }
        addItems(menu)
        // One separator between two groups: none first, none last, and none after another one. Hidden items do not count.
        // With no items, AppKit shows no menu.
        var previous: NSMenuItem?
        for item in menu.items where !item.isHidden {
            if item.isSeparatorItem, previous?.isSeparatorItem ?? true { menu.removeItem(item) } else { previous = item }
        }
        if let last = menu.items.last(where: { !$0.isHidden }), last.isSeparatorItem { menu.removeItem(last) }
    }
}

// The launch state, until the page is ready: a spinner and one line, or the line that names a launch failure.
// The spinner and the line show only after 0.6 s, so a fast launch shows nothing.
final class LaunchView: NSStackView {
    private let spinner = NSProgressIndicator()
    private let label = NSTextField(labelWithString: "")
    private var attempt = 0

    init() {
        super.init(frame: .zero)
        spinner.style = .spinning
        spinner.controlSize = .small
        label.textColor = .secondaryLabelColor
        label.identifier = NSUserInterfaceItemIdentifier("launch-status")
        setViews([spinner, label], in: .center)
        orientation = .vertical
        spacing = 8
        start()
    }
    required init?(coder: NSCoder) { nil }

    func start() {
        attempt += 1
        let mine = attempt
        label.stringValue = "Opening your library…"
        spinner.isHidden = true; label.isHidden = true
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) { [weak self] in
            guard let self, self.attempt == mine, self.window != nil else { return }
            self.spinner.isHidden = false; self.label.isHidden = false
            self.spinner.startAnimation(nil)
        }
    }

    // A failure shows its line at once, and a late timer of start() does not show the spinner again.
    func fail(_ title: String) {
        attempt += 1
        label.isHidden = false
        label.stringValue = title
        spinner.stopAnimation(nil)
        spinner.isHidden = true
    }
}

// Find in the open view, in a bar under the toolbar. WKWebView has no find bar of its own, and the page finds (reader.js).
// Typing finds as it goes, Return finds the next match, Shift-Return the previous one, and Escape closes the bar.
final class FindBar: NSStackView, NSSearchFieldDelegate {
    let field = NSSearchField()
    private let status = NSTextField(labelWithString: "")
    private let webView: WKWebView
    // Hidden, the accessory folds to no height but keeps the bar in the window.
    weak var accessory: NSSplitViewItemAccessoryViewController?

    init(webView: WKWebView) {
        self.webView = webView
        super.init(frame: .zero)
        field.identifier = NSUserInterfaceItemIdentifier("find")
        field.placeholderString = "Find in this view"
        field.sendsSearchStringImmediately = true
        field.delegate = self
        field.target = self; field.action = #selector(findNext)
        field.widthAnchor.constraint(equalToConstant: 260).isActive = true
        status.textColor = .secondaryLabelColor
        status.identifier = NSUserInterfaceItemIdentifier("find-status")
        let images = ["chevron.left", "chevron.right"].compactMap { NSImage(systemSymbolName: $0, accessibilityDescription: nil) }
        let steps = NSSegmentedControl(images: images, trackingMode: .momentary, target: self, action: #selector(step(_:)))
        steps.identifier = NSUserInterfaceItemIdentifier("find-steps")
        steps.setToolTip("Previous", forSegment: 0); steps.setToolTip("Next", forSegment: 1)
        let done = NSButton(title: "Done", target: self, action: #selector(close))
        done.identifier = NSUserInterfaceItemIdentifier("find-done")
        // At the trailing edge, as in Safari; "Not found" grows to the left, so the field does not move.
        setViews([status, field, steps, done], in: .trailing)
        edgeInsets = NSEdgeInsets(top: 6, left: 12, bottom: 6, right: 12)
        isHidden = true
    }
    required init?(coder: NSCoder) { nil }

    // The bar hides with its accessory, so the folded field leaves the key view loop.
    func open() {
        isHidden = false
        accessory?.isHidden = false
        layoutPage()
        window?.makeFirstResponder(field)
        field.currentEditor()?.selectAll(nil)
    }

    // Done removes the marks of the matches, as in Safari.
    @objc func close() {
        if field.currentEditor() != nil { window?.makeFirstResponder(webView) }
        guard !isHidden else { return }
        clearMarks()
        status.stringValue = ""
        accessory?.isHidden = true
        isHidden = true
        layoutPage()
    }

    // The accessory changes the content's safe area, but that does not lay out the content view again, so its
    // layout() does not copy the new insets into the page's obscured insets.
    private func layoutPage() {
        DispatchQueue.main.async { [weak self] in self?.webView.superview?.needsLayout = true }
    }

    private func clearMarks() {
        if let script = commandScript(["name": "find-clear"]) { webView.evaluateJavaScript(script) }
    }

    @objc func findNext() { find(backwards: false) }
    @objc func step(_ sender: NSSegmentedControl) { find(backwards: sender.selectedSegment == 0) }

    // The page finds in the open view and gives the place of the current match, such as "2 of 9".
    func find(backwards: Bool) {
        status.stringValue = ""
        guard !field.stringValue.isEmpty else { return clearMarks() }
        let text = field.stringValue
        webView.callAsyncJavaScript("return await window.localxiv.command({name: 'find', text, backwards})", arguments: ["text": text, "backwards": backwards],
                                    in: nil, in: .page) { [weak self] result in
            // A reply for a text that is no longer in the field, or after Done, is old.
            guard let self, !self.isHidden, self.field.stringValue == text else { return }
            guard case .success(let value) = result, let found = value as? [String: Any],
                  let index = found["index"] as? Int, let count = found["count"] as? Int, count > 0 else { self.status.stringValue = "Not found"; return }
            self.status.stringValue = "\(index + 1) of \(count)"
        }
    }

    func control(_ control: NSControl, textView: NSTextView, doCommandBy selector: Selector) -> Bool {
        switch selector {
        case #selector(NSResponder.insertNewline(_:)): find(backwards: NSApp.currentEvent?.modifierFlags.contains(.shift) == true)
        case #selector(NSResponder.cancelOperation(_:)): close()
        default: return false
        }
        return true
    }
}

