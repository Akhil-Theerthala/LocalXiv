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

    struct Sidebar: Codable, Equatable {
        var selected: String? = nil
        var counts: [String: Int] = [:]
        var recent: [Recent] = []
        var reader: Reader? = nil
    }
    struct Recent: Codable, Equatable { var id = "", title = "", current = false }
    struct Reader: Codable, Equatable { var back = "Library", title = "", byline = "", outline: [Entry] = [] }
    struct Entry: Codable, Equatable { var id = "", label = "", number = "", level = 1, current = false }
    struct Views: Codable, Equatable { var current = "paper", overview = "off", blog = "off", paper = "ready" }
    struct Action: Codable, Equatable { var id = "", label = "", enabled = false, role: String? = nil, separatorBefore = false }
    struct Prefs: Codable, Equatable { var theme = "system", font = "new-york", size = 18, width = "medium", spacing = "normal" }
    struct Activity: Codable, Equatable { var label = "", progress: Double? = nil, count = 1 }
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
        back = c[.back, or: back]; title = c[.title, or: title]; byline = c[.byline, or: byline]; outline = c[.outline, or: outline]
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
        theme = c[.theme, or: theme]; font = c[.font, or: font]; size = c[.size, or: size]; width = c[.width, or: width]; spacing = c[.spacing, or: spacing]
    }
}
extension ChromeState.Activity {
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self); self.init()
        label = c[.label, or: label]; progress = c[.progress, or: progress]; count = c[.count, or: count]
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
        webView = WKWebView(frame: .zero, configuration: configuration)
        webView.underPageBackgroundColor = .clear
        webView.navigationDelegate = self; webView.uiDelegate = self
        findBar = FindBar(webView: webView)
        // The window has a full-size content view for the full-height sidebar; the page starts below the toolbar.
        let column = NSStackView(views: [findBar, webView])
        column.orientation = .vertical
        column.alignment = .width
        column.spacing = 0
        let content = NSViewController()
        content.view = NSView()
        content.view.addSubview(column)
        column.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            column.topAnchor.constraint(equalTo: content.view.safeAreaLayoutGuide.topAnchor),
            column.bottomAnchor.constraint(equalTo: content.view.bottomAnchor),
            column.leadingAnchor.constraint(equalTo: content.view.leadingAnchor),
            column.trailingAnchor.constraint(equalTo: content.view.trailingAnchor)])
        let split = NSSplitViewController()
        let side = NSSplitViewItem(sidebarWithViewController: sidebar)
        side.minimumThickness = 200; side.maximumThickness = 320
        split.addSplitViewItem(side)
        // The page keeps 500 pt, so at the 700 pt minimum the sidebar still shows beside it at 200 pt.
        let main = NSSplitViewItem(viewController: content)
        main.minimumThickness = 500
        split.addSplitViewItem(main)
        split.splitView.autosaveName = "Sidebar"
        window.contentViewController = split
        window.delegate = self
        // A content view controller resizes the window to its view, so the size and the saved frame come after it.
        window.setContentSize(NSSize(width: 1180, height: 820))
        window.setFrameAutosaveName("PaperLibrary")
        // The sidebar opens at 250 pt, so most outline entries fit, until the reader drags it to a width of their own.
        // The split view sets its position only after its first layout.
        if UserDefaults.standard.object(forKey: "NSSplitView Subview Frames Sidebar") == nil {
            DispatchQueue.main.async { split.splitView.setPosition(250, ofDividerAt: 0) }
        }
        sidebar.send = { [unowned self] in self.send($0) }
        toolbar.send = { [unowned self] in self.send($0) }
    }

    // Messages from the main page: {type: 'ready'} once its command handlers exist, then {type: 'state', state},
    // and {type: 'settings', pane} to open the Settings window on a pane.
    func shell(_ body: [String: Any]) {
        switch body["type"] as? String {
        case "ready":
            pageReady = true
            queued.forEach(deliver)
            queued.removeAll()
        case "state":
            guard let value = body["state"], JSONSerialization.isValidJSONObject(value),
                  let data = try? JSONSerialization.data(withJSONObject: value),
                  let state = try? JSONDecoder().decode(ChromeState.self, from: data) else { return }
            apply(state)
        case "settings":
            showSettings(pane: body["pane"] as? String)
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
    }

    // The Reading theme sets each window's appearance, so the sidebar, toolbar, and popovers match the page.
    // Match system leaves the windows to the app's appearance, which follows macOS.
    func applyTheme() {
        let appearance = ["dark": NSAppearance.Name.darkAqua, "light": .aqua, "sepia": .aqua][chrome.prefs.theme].flatMap(NSAppearance.init(named:))
        for window in NSApp.windows where window.appearance?.name != appearance?.name { window.appearance = appearance }
    }

    // Below 1000 pt the sidebar collapses on its own, once when the window gets narrow, so the toggle can show it again.
    // A collapse from canCollapseFromWindowResize comes only from a live resize, and its content minimum would hold the window at 800 pt.
    func windowDidResize(_ notification: Notification) {
        let wide = window.frame.width >= 1000
        if wasWide && !wide { (window.contentViewController as? NSSplitViewController)?.splitViewItems.first?.isCollapsed = true }
        wasWide = wide
    }

    func send(_ command: [String: Any]) {
        if pageReady { deliver(command) } else { queued.append(command) }
    }

    private func deliver(_ command: [String: Any]) {
        if let script = commandScript(command) { webView.evaluateJavaScript(script) }
    }
}

// Find in the open view, over the web view. WKWebView has no find bar of its own.
// Typing finds as it goes, Return finds the next match, Shift-Return the previous one, and Escape closes the bar.
final class FindBar: NSStackView, NSSearchFieldDelegate {
    let field = NSSearchField()
    private let status = NSTextField(labelWithString: "")
    private let webView: WKWebView

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
        // Under the default hugging, the column keeps the bar at its fitting width; the rule needs the full width.
        setHuggingPriority(.defaultLow - 1, for: .horizontal)
        let rule = NSBox()
        rule.boxType = .separator
        rule.translatesAutoresizingMaskIntoConstraints = false
        addSubview(rule)
        NSLayoutConstraint.activate([rule.leadingAnchor.constraint(equalTo: leadingAnchor), rule.trailingAnchor.constraint(equalTo: trailingAnchor),
                                     rule.bottomAnchor.constraint(equalTo: bottomAnchor)])
        isHidden = true
    }
    required init?(coder: NSCoder) { nil }

    func open() {
        isHidden = false
        window?.makeFirstResponder(field)
        field.currentEditor()?.selectAll(nil)
    }

    @objc func close() {
        if field.currentEditor() != nil { window?.makeFirstResponder(webView) }
        isHidden = true
    }

    @objc func findNext() { find(backwards: false) }
    @objc func step(_ sender: NSSegmentedControl) { find(backwards: sender.selectedSegment == 0) }

    func find(backwards: Bool) {
        status.stringValue = ""
        guard !field.stringValue.isEmpty else { return }
        let configuration = WKFindConfiguration()
        configuration.backwards = backwards
        webView.find(field.stringValue, configuration: configuration) { [weak self] result in
            self?.status.stringValue = result.matchFound ? "" : "Not found"
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

