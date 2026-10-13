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
    struct Views: Codable, Equatable {
        var current = "paper", overview = "off", blog = "off", paper = "ready"
        subscript(view: String) -> String { ["overview": overview, "blog": blog, "paper": paper][view] ?? "off" }
    }
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
extension PapersApp {
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
        // The window has a full-size content view for the full-height sidebar; the page starts below the toolbar.
        let content = NSViewController()
        content.view = NSView()
        content.view.addSubview(webView)
        webView.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            webView.topAnchor.constraint(equalTo: content.view.safeAreaLayoutGuide.topAnchor),
            webView.bottomAnchor.constraint(equalTo: content.view.bottomAnchor),
            webView.leadingAnchor.constraint(equalTo: content.view.leadingAnchor),
            webView.trailingAnchor.constraint(equalTo: content.view.trailingAnchor)])
        let split = NSSplitViewController()
        let side = NSSplitViewItem(sidebarWithViewController: sidebar)
        side.minimumThickness = 200; side.maximumThickness = 320
        split.addSplitViewItem(side)
        split.addSplitViewItem(NSSplitViewItem(viewController: content))
        window.contentViewController = split
        // A content view controller resizes the window to its view, so the size and the saved frame come after it.
        window.setContentSize(NSSize(width: 1180, height: 820))
        window.setFrameAutosaveName("PaperLibrary")
        sidebar.send = { [unowned self] in self.send($0) }
        toolbar.send = { [unowned self] in self.send($0) }
    }

    // Messages from the main page: {type: 'ready'} once its command handlers exist, then {type: 'state', state}.
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
        default: break
        }
    }

    func apply(_ state: ChromeState) {
        chrome = state
        window.title = state.title
        window.subtitle = state.subtitle
        sidebar.apply(state)
        toolbar.apply(state)
    }

    func send(_ command: [String: Any]) {
        if pageReady { deliver(command) } else { queued.append(command) }
    }

    private func deliver(_ command: [String: Any]) {
        if let script = commandScript(command) { webView.evaluateJavaScript(script) }
    }
}

