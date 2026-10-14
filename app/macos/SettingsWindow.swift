import Cocoa
import WebKit

// The Settings window: a preference toolbar of panes over the web app's settings view, /?panel=settings&pane=<pane>.
// The web view shares the default website data store, so the session token reaches it.
final class SettingsWindow: NSObject, NSToolbarDelegate, NSWindowDelegate {
    static let panes: [(id: String, label: String, symbol: String)] = [
        ("general", "General", "gearshape"), ("reading", "Reading", "textformat.size"), ("ai", "AI", "sparkles"),
        ("kindle", "Kindle", "paperplane"), ("search", "Search", "magnifyingglass"), ("help", "Help", "questionmark.circle")]
    let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 680, height: 560), styleMask: [.titled, .closable, .resizable], backing: .buffered, defer: false)
    let webView: WKWebView
    private var ready = false
    private var closing = false
    private var pane = UserDefaults.standard.string(forKey: "SettingsPane") ?? "general" {
        didSet { UserDefaults.standard.set(pane, forKey: "SettingsPane") }
    }

    init(app: PapersApp) {
        let configuration = WKWebViewConfiguration()
        configuration.userContentController.add(app, name: "shell")
        webView = WKWebView(frame: .zero, configuration: configuration)
        super.init()
        webView.navigationDelegate = app; webView.uiDelegate = app
        let toolbar = NSToolbar(identifier: "settings")
        toolbar.delegate = self
        window.toolbar = toolbar
        window.delegate = self
        window.toolbarStyle = .preference
        window.contentView = webView
        window.minSize = NSSize(width: 560, height: 420)
        window.isReleasedWhenClosed = false
        window.center()
        window.setFrameAutosaveName("Settings")
    }

    // An open window keeps its unsaved edits; a closed one loads the saved settings again, on the last pane or on the pane
    // that the page asks for. The window has no minimize button, so open means visible.
    func show(origin: URL, token: String, pane requested: String? = nil) {
        select(requested ?? pane)
        if window.isVisible {
            if requested != nil { deliver() }
        } else {
            var url = URLComponents(url: origin, resolvingAgainstBaseURL: false)!
            url.path = "/"
            url.queryItems = [URLQueryItem(name: "panel", value: "settings"), URLQueryItem(name: "pane", value: pane)]
            url.fragment = "token=" + token
            ready = false
            webView.load(URLRequest(url: url.url!))
        }
        window.makeKeyAndOrderFront(nil)
    }

    // The close button and Command-W save unsaved edits first. When the server rejects them, the page shows the
    // error and the window stays open.
    func windowShouldClose(_ sender: NSWindow) -> Bool {
        guard ready else { return true }
        if closing { return false }
        closing = true
        webView.callAsyncJavaScript("return await window.localxiv.command({name: 'close-settings'})", in: nil, in: .page) { result in
            self.closing = false
            if case .success(let closed) = result, closed as? Bool == false { return }
            self.window.close()
        }
        return false
    }

    func received(_ body: [String: Any]) {
        guard body["type"] as? String == "ready" else { return }
        ready = true
        deliver()
    }

    private func select(_ id: String) {
        pane = Self.panes.contains { $0.id == id } ? id : "general"
        window.toolbar?.selectedItemIdentifier = NSToolbarItem.Identifier(pane)
        window.title = Self.panes.first { $0.id == pane }?.label ?? "Settings"
    }

    // A pane chosen before the page is ready reaches it with 'ready'.
    private func deliver() {
        if ready, let script = commandScript(["name": "settings", "pane": pane]) { webView.evaluateJavaScript(script) }
    }

    @objc func choose(_ sender: NSToolbarItem) {
        select(sender.itemIdentifier.rawValue)
        deliver()
    }

    func toolbarDefaultItemIdentifiers(_ toolbar: NSToolbar) -> [NSToolbarItem.Identifier] { Self.panes.map { NSToolbarItem.Identifier($0.id) } }
    func toolbarAllowedItemIdentifiers(_ toolbar: NSToolbar) -> [NSToolbarItem.Identifier] { toolbarDefaultItemIdentifiers(toolbar) }
    func toolbarSelectableItemIdentifiers(_ toolbar: NSToolbar) -> [NSToolbarItem.Identifier] { toolbarDefaultItemIdentifiers(toolbar) }

    func toolbar(_ toolbar: NSToolbar, itemForItemIdentifier identifier: NSToolbarItem.Identifier, willBeInsertedIntoToolbar flag: Bool) -> NSToolbarItem? {
        guard let pane = Self.panes.first(where: { $0.id == identifier.rawValue }) else { return nil }
        let item = NSToolbarItem(itemIdentifier: identifier)
        item.label = pane.label
        item.image = NSImage(systemSymbolName: pane.symbol, accessibilityDescription: pane.label)
        item.target = self; item.action = #selector(choose(_:))
        return item
    }
}

extension PapersApp {
    @objc func openSettings(_ sender: Any?) { showSettings(pane: nil) }

    func showSettings(pane: String?) {
        guard let origin, let token else { return }
        if settings == nil { settings = SettingsWindow(app: self) }
        applyTheme()
        settings?.show(origin: origin, token: token, pane: pane)
    }
}
