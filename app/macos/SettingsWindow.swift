import Cocoa
import WebKit

// The Settings window: a preference toolbar of panes over the web app's settings view, /?panel=settings&pane=<pane>.
// The web view shares the default website data store, so the session token reaches it.
final class SettingsWindow: NSObject, NSToolbarDelegate, NSWindowDelegate {
    static let panes: [(id: String, label: String, symbol: String)] = [
        ("general", "General", "gearshape"), ("reading", "Reading", "textformat.size"), ("ai", "AI", "sparkles"),
        ("kindle", "Kindle", "paperplane"), ("search", "Search", "magnifyingglass"), ("help", "Help", "questionmark.circle")]
    let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 680, height: 560), styleMask: [.titled, .closable], backing: .buffered, defer: false)
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
        webView.underPageBackgroundColor = .clear
        super.init()
        webView.navigationDelegate = app; webView.uiDelegate = app
        let toolbar = NSToolbar(identifier: "settings")
        toolbar.delegate = self
        window.toolbar = toolbar
        window.delegate = self
        window.toolbarStyle = .preference
        window.contentView = webView
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
    // error and the window stays open. A page that does not answer within 1.5 s does not keep the window open.
    func windowShouldClose(_ sender: NSWindow) -> Bool {
        guard ready else { return true }
        if closing { return false }
        closing = true
        var answered = false
        let finish = { (close: Bool) in
            if answered { return }
            answered = true
            self.closing = false
            if close { self.window.close() }
        }
        webView.callAsyncJavaScript("return await window.localxiv.command({name: 'close-settings'})", in: nil, in: .page) { result in
            if case .success(let closed) = result, closed as? Bool == false { finish(false) } else { finish(true) }
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { finish(true) }
        return false
    }

    // The page drops the token from its URL, so a later load of the same pane only adds a fragment and keeps the old
    // page, which never sends 'ready' again. A blank page makes the next show() load the saved settings again.
    func windowWillClose(_ notification: Notification) {
        ready = false
        // The next opening shows this page until the settings load, so it takes the Dark or Light background.
        webView.loadHTMLString("<meta name=color-scheme content='light dark'>", baseURL: nil)
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

    // A pane chosen before the page is ready reaches it with 'ready'. The window then fits the pane.
    private func deliver() {
        guard ready, let script = commandScript(["name": "settings", "pane": pane]) else { return }
        webView.evaluateJavaScript(script + ";" + Self.paneHeight) { [weak self] height, _ in
            if let height = height as? Double, height > 0 { self?.fit(CGFloat(height)) }
        }
    }

    // The page fills the window and the pane scrolls inside it, so the height the page needs is the window's height
    // less the pane's box, plus the pane's content. Shrunk to no height for one synchronous read, the pane's scroll
    // height is all of its content, with padding and margins.
    private static let paneHeight = """
        (() => {
          const pane = document.querySelector('.pane:not([hidden])'); if (!pane) return 0;
          const box = pane.clientHeight;
          pane.style.flex = '0 0 0';
          const content = pane.scrollHeight;
          pane.style.flex = '';
          return Math.ceil(innerHeight - box + content);
        })()
        """

    // As in Mac settings windows, the height follows the pane and the title bar stays in place.
    private func fit(_ height: CGFloat) {
        let delta = min(max(height, 120), 720) - webView.frame.height
        guard abs(delta) >= 1 else { return }
        var frame = window.frame
        frame.size.height += delta
        frame.origin.y -= delta
        window.setFrame(frame, display: true, animate: window.isVisible)
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
