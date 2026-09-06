import Cocoa
import WebKit

final class WindowDragView: NSView {
    var regions: [NSRect] = []
    override var isFlipped: Bool { true }
    override func hitTest(_ point: NSPoint) -> NSView? {
        let local = convert(point, from: superview)
        return regions.contains(where: { $0.contains(local) }) ? self : nil
    }
    override func mouseDown(with event: NSEvent) {
        if event.clickCount == 2 { window?.zoom(nil) }
        else { window?.performDrag(with: event) }
    }
}

// The native window and browser workflow share the same loopback service/library.
final class PapersApp: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKUIDelegate, WKDownloadDelegate, WKScriptMessageHandler {
    var window: NSWindow!
    var webView: WKWebView!
    var service: Process?
    var timer: Timer?
    var checking = false
    var deadline = Date()
    var origin: URL?
    var dataDirectory: URL!
    var expectedRuntimeID: String?
    var startupLog: URL!
    var downloads: [ObjectIdentifier: (URL, URL)] = [:]
    let dragView = WindowDragView()

    func applicationDidFinishLaunching(_ notification: Notification) {
        let menu = NSMenu()
        let appItem = NSMenuItem(); menu.addItem(appItem)
        let appMenu = NSMenu(); appItem.submenu = appMenu
        appMenu.addItem(withTitle: "Quit LocalXiv", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        let editItem = NSMenuItem(); menu.addItem(editItem)
        let editMenu = NSMenu(title: "Edit"); editItem.submenu = editMenu
        for (title, action, key) in [("Undo", "undo:", "z"), ("Cut", "cut:", "x"), ("Copy", "copy:", "c"), ("Paste", "paste:", "v"), ("Select All", "selectAll:", "a")] {
            editMenu.addItem(withTitle: title, action: Selector(action), keyEquivalent: key)
        }
        NSApp.mainMenu = menu
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1180, height: 820), styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView], backing: .buffered, defer: false)
        window.title = "LocalXiv"
        window.titleVisibility = .hidden
        window.titlebarAppearsTransparent = true
        window.isMovableByWindowBackground = true
        window.backgroundColor = .windowBackgroundColor
        window.minSize = NSSize(width: 700, height: 500)
        window.setFrameAutosaveName("PaperLibrary")
        window.isReleasedWhenClosed = false
        let configuration = WKWebViewConfiguration()
        configuration.userContentController.add(self, name: "windowDragRegions")
        configuration.userContentController.addUserScript(WKUserScript(
            source: """
            document.addEventListener('DOMContentLoaded',function(){
              document.documentElement.classList.add('native-window');
              const header = document.querySelector('.app-header'); if (!header) return;
              function update() {
                const regions = [];
                if (!document.querySelector('dialog[open]')) {
                  const h = header.getBoundingClientRect(), brand = (header.querySelector('.header-start') || header.querySelector('.brand')).getBoundingClientRect(), actions = header.querySelector('.header-actions').getBoundingClientRect();
                  if (actions.left > brand.right + 8) regions.push({x:brand.right+4,y:h.top,width:actions.left-brand.right-8,height:h.height});
                  regions.push({x:94,y:h.top,width:Math.max(0,h.width-94),height:7});
                }
                window.webkit.messageHandlers.windowDragRegions.postMessage(regions);
              }
              new ResizeObserver(update).observe(header);
              new MutationObserver(update).observe(document.body,{subtree:true,attributes:true,attributeFilter:['open','hidden','class']});
              window.addEventListener('resize',update); update();
            });
            """,
            injectionTime: .atDocumentStart, forMainFrameOnly: true))
        webView = WKWebView(frame: window.contentView!.bounds, configuration: configuration)
        if #available(macOS 12.0, *) { webView.underPageBackgroundColor = .clear }
        webView.autoresizingMask = [.width, .height]
        webView.navigationDelegate = self; webView.uiDelegate = self
        let content = NSView(frame: webView.frame)
        content.addSubview(webView)
        dragView.frame = content.bounds; dragView.autoresizingMask = [.width, .height]
        content.addSubview(dragView)
        window.contentView = content
        window.center(); window.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true)
        webView.loadHTMLString("<body style='font:16px -apple-system;padding:70px 40px;background:#f5f1e8'>Opening your paper library…</body>", baseURL: nil)
        let resources = Bundle.main.resourceURL
        let bundledApp = resources?.appendingPathComponent("app", isDirectory: true)
        let runtime: String
        let data: String
        if let bundledApp = bundledApp, FileManager.default.fileExists(atPath: bundledApp.appendingPathComponent("launch.command").path) {
            runtime = bundledApp.path
            data = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/LocalXiv/library").path
            guard let identity = try? String(contentsOf: bundledApp.appendingPathComponent("release-id.txt"), encoding: .utf8),
                  !identity.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                fail("The LocalXiv runtime is incomplete. Reinstall LocalXiv."); return
            }
            expectedRuntimeID = identity.trimmingCharacters(in: .whitespacesAndNewlines) + "|" + bundledApp.resolvingSymlinksInPath().path
        } else if let installedRuntime = Bundle.main.object(forInfoDictionaryKey: "PapersRuntimePath") as? String,
                  let installedData = Bundle.main.object(forInfoDictionaryKey: "PapersDataPath") as? String {
            runtime = installedRuntime; data = installedData
        } else {
            fail("The app installation is incomplete. Reinstall LocalXiv."); return
        }
        dataDirectory = URL(fileURLWithPath: data, isDirectory: true)
        do {
            // Leave library creation to Python so it can migrate an existing library first.
            let logDirectory = expectedRuntimeID == nil ? dataDirectory! : dataDirectory.deletingLastPathComponent()
            try FileManager.default.createDirectory(at: logDirectory, withIntermediateDirectories: true)
            let log = logDirectory.appendingPathComponent(expectedRuntimeID == nil ? "server.log" : "startup.log")
            startupLog = log
            if !FileManager.default.fileExists(atPath: log.path) { FileManager.default.createFile(atPath: log.path, contents: nil) }
            let handle = try FileHandle(forWritingTo: log); handle.seekToEndOfFile()
            let process = Process(); process.executableURL = URL(fileURLWithPath: "/bin/bash")
            process.arguments = [runtime + "/launch.command", "--serve", "--data-dir", data]
            process.standardOutput = handle; process.standardError = handle
            try process.run(); service = process
            try? handle.close()
            deadline = Date().addingTimeInterval(30)
            timer = Timer.scheduledTimer(withTimeInterval: 0.25, repeats: true) { [weak self] _ in self?.checkService() }
            checkService()
        } catch { fail("Could not start the local library: " + error.localizedDescription) }
    }

    func checkService() {
        if Date() > deadline { timer?.invalidate(); fail("The local library did not start. Check " + startupLog.path + "."); return }
        guard !checking,
              let data = try? Data(contentsOf: dataDirectory.appendingPathComponent("session.json")),
              let session = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let port = session["port"] as? Int, (1...65535).contains(port),
              let token = session["token"] as? String,
              let base = URL(string: "http://127.0.0.1:\(port)") else { return }
        checking = true
        var request = URLRequest(url: base.appendingPathComponent("api/health")); request.timeoutInterval = 2
        request.setValue("Bearer " + token, forHTTPHeaderField: "Authorization")
        URLSession.shared.dataTask(with: request) { data, response, _ in
            let json = data.flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: Any] }
            DispatchQueue.main.async {
                self.checking = false
                guard (response as? HTTPURLResponse)?.statusCode == 200, json?["application"] as? String == "papers-to-kindle" else { return }
                self.timer?.invalidate()
                if let expected = self.expectedRuntimeID, json?["runtime_id"] as? String != expected {
                    self.fail("An older LocalXiv background service is still running. Wait for its jobs to finish, then restart your Mac and open LocalXiv again. Your library is unchanged.")
                    return
                }
                self.origin = base
                var url = URLComponents(url: base, resolvingAgainstBaseURL: false)!
                url.path = "/"; url.fragment = "token=" + token
                self.webView.load(URLRequest(url: url.url!))
            }
        }.resume()
    }

    func localURL(_ url: URL) -> Bool {
        guard let origin = origin else { return false }
        return url.scheme == origin.scheme && url.host == origin.host && url.port == origin.port
    }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.frameInfo.isMainFrame, let url = message.frameInfo.request.url, localURL(url),
              let regions = message.body as? [[String: Double]] else { return }
        dragView.regions = regions.compactMap { region in
            guard let x = region["x"], let y = region["y"], let width = region["width"], let height = region["height"],
                  x >= 0, y >= 0, width >= 0, height >= 0, y + height <= 80 else { return nil }
            return NSRect(x: x, y: y, width: width, height: height)
        }
    }

    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = action.request.url else { decisionHandler(.cancel); return }
        if url.absoluteString == "about:blank" { decisionHandler(.allow); return }
        if localURL(url) { decisionHandler(action.shouldPerformDownload ? .download : .allow); return }
        // Only explicit external links leave the app. Paper content cannot navigate it remotely.
        if action.navigationType == .linkActivated, ["https", "http", "mailto"].contains(url.scheme ?? "") { NSWorkspace.shared.open(url) }
        decisionHandler(.cancel)
    }

    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration, for action: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        if let url = action.request.url, localURL(url) { webView.load(action.request) }
        return nil
    }

    func webView(_ webView: WKWebView, decidePolicyFor response: WKNavigationResponse, decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void) {
        decisionHandler(response.canShowMIMEType ? .allow : .download)
    }
    func webView(_ webView: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) { download.delegate = self }
    func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) { download.delegate = self }

    func download(_ download: WKDownload, decideDestinationUsing response: URLResponse, suggestedFilename: String, completionHandler: @escaping (URL?) -> Void) {
        let panel = NSSavePanel(); panel.nameFieldStringValue = URL(fileURLWithPath: suggestedFilename).lastPathComponent
        panel.beginSheetModal(for: window) { result in
            guard result == .OK, let destination = panel.url else { completionHandler(nil); return }
            // WebKit needs a nonexistent destination. Keep an existing book intact until download succeeds.
            let temporary = destination.deletingLastPathComponent().appendingPathComponent(".papers-download-" + UUID().uuidString)
            self.downloads[ObjectIdentifier(download)] = (temporary, destination)
            completionHandler(temporary)
        }
    }
    func downloadDidFinish(_ download: WKDownload) {
        guard let (temporary, destination) = downloads.removeValue(forKey: ObjectIdentifier(download)) else { return }
        do {
            if FileManager.default.fileExists(atPath: destination.path) {
                _ = try FileManager.default.replaceItemAt(destination, withItemAt: temporary)
            } else { try FileManager.default.moveItem(at: temporary, to: destination) }
        } catch { fail("The download could not be saved: " + error.localizedDescription) }
    }
    func download(_ download: WKDownload, didFailWithError error: Error, resumeData: Data?) {
        if let (temporary, _) = downloads.removeValue(forKey: ObjectIdentifier(download)) { try? FileManager.default.removeItem(at: temporary) }
        fail("The download failed: " + error.localizedDescription)
    }
    func fail(_ message: String) {
        let alert = NSAlert(); alert.messageText = "LocalXiv"; alert.informativeText = message
        alert.beginSheetModal(for: window)
    }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        window.makeKeyAndOrderFront(nil); return true
    }
    func applicationWillTerminate(_ notification: Notification) { timer?.invalidate() }
}

let app = NSApplication.shared
let delegate = PapersApp()
app.setActivationPolicy(.regular)
app.delegate = delegate
app.run()
