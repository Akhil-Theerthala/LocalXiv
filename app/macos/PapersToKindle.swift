import Cocoa
import UniformTypeIdentifiers
import WebKit
#if canImport(Sparkle)
import Sparkle
#endif

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
    var serviceArguments: [String] = []
    var token: String?
    var downloads: [ObjectIdentifier: (URL, URL)] = [:]
    var chrome = ChromeState()
    var pageReady = false
    var queued: [[String: Any]] = []
    let sidebar = SidebarController()
    let toolbar = ToolbarController()
    var findBar: FindBar!
    let launch = LaunchView()
    var wasWide = true
    var settings: SettingsWindow?
#if canImport(Sparkle)
    var updaterController: SPUStandardUpdaterController?
    var installingUpdate = false
    var updateShutdownStarted = false
#endif

    func applicationDidFinishLaunching(_ notification: Notification) {
#if canImport(Sparkle)
        updaterController = SPUStandardUpdaterController(startingUpdater: true, updaterDelegate: self, userDriverDelegate: nil)
#endif
        NSWindow.allowsAutomaticWindowTabbing = false
        NSApp.mainMenu = makeMainMenu()
        makeWindow()
        syncReduceTransparency()
        NSWorkspace.shared.notificationCenter.addObserver(forName: NSWorkspace.accessibilityDisplayOptionsDidChangeNotification, object: nil, queue: .main) { [weak self] _ in
            self?.syncReduceTransparency()
        }
        chrome.prefs.theme = UserDefaults.standard.string(forKey: "ReadingTheme") ?? chrome.prefs.theme
        applyTheme()
        window.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true)
#if LOCALXIV_AUTOMATION
        startAutomation(atLaunch: true)
#endif
        let resources = Bundle.main.resourceURL
        let bundledApp = resources?.appendingPathComponent("app", isDirectory: true)
        let runtime: String
        let data: String
        if let bundledApp = bundledApp, FileManager.default.fileExists(atPath: bundledApp.appendingPathComponent("launch.command").path) {
            runtime = bundledApp.path
            data = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/LocalXiv/library").path
            guard let identity = try? String(contentsOf: bundledApp.appendingPathComponent("release-id.txt"), encoding: .utf8),
                  !identity.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                launchFailed("LocalXiv could not start", "The LocalXiv runtime is incomplete. Reinstall LocalXiv.", retry: false); return
            }
            expectedRuntimeID = identity.trimmingCharacters(in: .whitespacesAndNewlines) + "|" + bundledApp.resolvingSymlinksInPath().path
        } else if let installedRuntime = Bundle.main.object(forInfoDictionaryKey: "PapersRuntimePath") as? String,
                  let installedData = Bundle.main.object(forInfoDictionaryKey: "PapersDataPath") as? String {
            runtime = installedRuntime; data = installedData
        } else {
            launchFailed("LocalXiv could not start", "The app installation is incomplete. Reinstall LocalXiv.", retry: false); return
        }
        dataDirectory = URL(fileURLWithPath: data, isDirectory: true)
        let logDirectory = expectedRuntimeID == nil ? dataDirectory! : dataDirectory.deletingLastPathComponent()
        startupLog = logDirectory.appendingPathComponent(expectedRuntimeID == nil ? "server.log" : "startup.log")
        serviceArguments = [runtime + "/launch.command", "--serve", "--data-dir", data]
        startService()
    }

    // Starts the background service, also again after a launch failure, and waits up to 30 s for it to answer.
    // When the service cannot start, its log stays empty, so the alert gives the system's cause.
    func startService() {
        if service?.isRunning == true { service?.terminate() }
        launch.start()
        do {
            try FileManager.default.createDirectory(at: startupLog.deletingLastPathComponent(), withIntermediateDirectories: true)
            if !FileManager.default.fileExists(atPath: startupLog.path) { FileManager.default.createFile(atPath: startupLog.path, contents: nil) }
            let handle = try FileHandle(forWritingTo: startupLog); handle.seekToEndOfFile()
            let process = Process(); process.executableURL = URL(fileURLWithPath: "/bin/bash")
            process.arguments = serviceArguments
            process.standardOutput = handle; process.standardError = handle
            try process.run(); service = process
            try? handle.close()
            deadline = Date().addingTimeInterval(30)
            timer = Timer.scheduledTimer(withTimeInterval: 0.25, repeats: true) { [weak self] _ in self?.checkService() }
            checkService()
        } catch { launchFailed("The background service could not start", error.localizedDescription) }
    }

    // The window has nothing to show without the background service, so the alert offers Try Again, Show Log, and
    // Quit. An incomplete installation offers only Quit, because nothing changes until LocalXiv is installed again.
    func launchFailed(_ title: String, _ detail: String, retry: Bool = true) {
        timer?.invalidate()
        launch.fail(title)
        let alert = NSAlert(); alert.messageText = title; alert.informativeText = detail
        if retry { ["Try Again", "Show Log"].forEach { alert.addButton(withTitle: $0) } }
        alert.addButton(withTitle: "Quit")
        alert.beginSheetModal(for: window) { response in
            switch retry ? response : .cancel {
            case .alertFirstButtonReturn: self.startService()
            case .alertSecondButtonReturn:
                NSWorkspace.shared.activateFileViewerSelecting([self.startupLog])
                DispatchQueue.main.async { self.launchFailed(title, detail) }
            default: NSApp.terminate(nil)
            }
        }
    }

    func checkService() {
        if Date() > deadline { launchFailed("The background service did not start", "It did not answer within 30 seconds. Its log can show the cause."); return }
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
                    self.launchFailed("An older background service is running", "Wait for its jobs to finish, then restart your Mac and open LocalXiv again. Your library is unchanged.")
                    return
                }
                self.origin = base; self.token = token
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
              message.name == "shell", let body = message.body as? [String: Any] else { return }
        if let settings, message.webView === settings.webView { settings.received(body) } else { shell(body) }
    }

    // A new page registers its command handlers again, so commands wait for its 'ready'.
    func webView(_ webView: WKWebView, didCommit navigation: WKNavigation!) {
        if webView === self.webView { pageReady = false }
    }

    // The page shows itself with 'ready'. A page that fails before then still shows after 3 s.
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        guard webView === self.webView, let url = webView.url, localURL(url) else { return }
        DispatchQueue.main.asyncAfter(deadline: .now() + 3) { self.showPage() }
#if LOCALXIV_AUTOMATION
        startAutomation()
#endif
    }

    // After a page crash, the main page loads again: it signs in with its stored token and shows itself with 'ready'.
    // The Settings window closes, and its next opening loads the settings again.
    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        if webView === self.webView { pageReady = false; webView.alphaValue = 0; webView.reload() } else { settings?.window.close() }
    }

    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = action.request.url else { decisionHandler(.cancel); return }
        if url.absoluteString == "about:blank" { decisionHandler(.allow); return }
        if localURL(url) { decisionHandler(action.shouldPerformDownload ? .download : .allow); return }
        // Only explicit external links leave the app. Paper content cannot navigate it remotely.
        if action.navigationType == .linkActivated, ["https", "http", "mailto"].contains(url.scheme ?? "") { NSWorkspace.shared.open(url) }
        decisionHandler(.cancel)
    }

    // No page opens a new window in the app, so the app page never navigates away. A local PDF, such as the original
    // that the PDF link and Open PDF ask for, opens in the reader's PDF app.
    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration, for action: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        if let url = action.request.url, localURL(url), url.pathExtension.lowercased() == "pdf" { openPDF(url, from: webView.window) }
        return nil
    }

    // A file input of the app page, such as Restore Notes…, asks for a file with an open panel. WebKit does not give the
    // input's accept list, and the one file input takes a JSON backup.
    func webView(_ webView: WKWebView, runOpenPanelWith parameters: WKOpenPanelParameters, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping ([URL]?) -> Void) {
        guard frame.isMainFrame, let url = frame.request.url, localURL(url) else { completionHandler(nil); return }
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = parameters.allowsMultipleSelection
        panel.canChooseDirectories = parameters.allowsDirectories
        panel.allowedContentTypes = [.json]
        panel.beginSheetModal(for: webView.window ?? window) { result in completionHandler(result == .OK ? panel.urls : nil) }
    }

    // The URL carries the session token, so a plain request fetches the file. /files/<paper>/original.pdf becomes <paper>.pdf.
    func openPDF(_ url: URL, from source: NSWindow?) {
        let file = FileManager.default.temporaryDirectory.appendingPathComponent(url.deletingLastPathComponent().lastPathComponent + ".pdf")
        URLSession.shared.downloadTask(with: url) { location, response, error in
            // The downloaded file is gone after this closure returns, so it moves now, off the main thread.
            let moved = Result {
                guard let location, (response as? HTTPURLResponse)?.statusCode == 200 else { throw error ?? URLError(.badServerResponse) }
                try? FileManager.default.removeItem(at: file)
                try FileManager.default.moveItem(at: location, to: file)
            }
            DispatchQueue.main.async {
                if case .failure = moved { self.fail("The PDF could not be opened", "LocalXiv could not get the PDF from its library. Try again, or choose Open on arXiv.", in: source) }
                else { NSWorkspace.shared.open(file) }
            }
        }.resume()
    }

    func webView(_ webView: WKWebView, decidePolicyFor response: WKNavigationResponse, decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void) {
        decisionHandler(response.canShowMIMEType ? .allow : .download)
    }
    func webView(_ webView: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) { download.delegate = self }
    func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) { download.delegate = self }

    func download(_ download: WKDownload, decideDestinationUsing response: URLResponse, suggestedFilename: String, completionHandler: @escaping (URL?) -> Void) {
        let panel = NSSavePanel(); panel.nameFieldStringValue = URL(fileURLWithPath: suggestedFilename).lastPathComponent
        panel.beginSheetModal(for: download.webView?.window ?? window) { result in
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
        } catch { fail("The download could not be saved", error.localizedDescription + " Choose another folder, then try again.", in: download.webView?.window) }
    }
    func download(_ download: WKDownload, didFailWithError error: Error, resumeData: Data?) {
        if let (temporary, _) = downloads.removeValue(forKey: ObjectIdentifier(download)) { try? FileManager.default.removeItem(at: temporary) }
        // A cancelled download, such as Cancel in the save panel, shows no alert.
        if (error as? URLError)?.code == .cancelled { return }
        fail("The download failed", "LocalXiv could not save the file. Try again, or choose another folder.", in: download.webView?.window)
    }
    // The title states the problem, and the detail gives the cause or the next step. An alert that only informs stops
    // the reader, so the main page says it in a toast. Before the page is ready, and in the Settings window, an alert does.
    func fail(_ title: String, _ detail: String, in target: NSWindow? = nil) {
        let target = target.flatMap { $0.isVisible ? $0 : nil } ?? window!
        if pageReady && target === window { send(["name": "notice", "text": title + ". " + detail]); return }
        let alert = NSAlert(); alert.messageText = title; alert.informativeText = detail
        alert.beginSheetModal(for: target)
    }
    // WebKit reports the page hidden when the window is hidden or covered, but not when LocalXiv is inactive. The page's
    // toasts hold their timers in both cases, so it gets an `inactive` class on html and an 'appactive' event.
    func applicationDidBecomeActive(_ notification: Notification) { syncActive(true) }
    func applicationDidResignActive(_ notification: Notification) { syncActive(false) }
    func syncActive(_ active: Bool) {
        webView?.evaluateJavaScript("document.documentElement.classList.toggle('inactive', \(!active)); document.dispatchEvent(new Event('appactive'))")
    }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        window.makeKeyAndOrderFront(nil); return true
    }
    // localxiv://import?url=<link or ID>, from the bookmarklet in the README, adds the Paper as a pasted link does.
    // The service checks the link, so another host gets the usual error. localxiv://open?paper=<id>&passage=<id>,
    // from the Markdown export of the Notes, opens the Paper at the passage. A URL that starts LocalXiv can come
    // before its window exists, and send() keeps the command until the page is ready.
    func application(_ application: NSApplication, open urls: [URL]) {
        window?.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true)
        for url in urls {
            let query = { (name: String) in URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems?.first(where: { $0.name == name })?.value }
            if url.host == "import", let link = query("url") {
                send(["name": "search", "query": link, "submit": true, "link": true])
            } else if url.host == "open", let id = query("paper") {
                send(["name": "open", "id": id, "passage": query("passage") ?? ""])
            }
        }
    }
    func applicationWillTerminate(_ notification: Notification) { timer?.invalidate() }

    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
#if canImport(Sparkle)
        if installingUpdate {
            if !updateShutdownStarted {
                updateShutdownStarted = true
                stopServiceForUpdate()
            }
            return .terminateLater
        }
#endif
        // No pagehide or visibilitychange reaches the page at quit, so the page saves its Reading position first.
        // A page that does not answer within 1.5 s does not hold up the quit.
        guard pageReady else { return .terminateNow }
        var replied = false
        let reply = {
            if replied { return }
            replied = true
            NSApp.reply(toApplicationShouldTerminate: true)
        }
        webView.callAsyncJavaScript("await window.localxiv.command({name: 'flush'})", in: nil, in: .page) { _ in reply() }
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5, execute: reply)
        return .terminateLater
    }
}

#if canImport(Sparkle)
extension PapersApp: SPUUpdaterDelegate {
    func updater(_ updater: SPUUpdater, willInstallUpdate item: SUAppcastItem) {
        installingUpdate = true
    }

    func stopServiceForUpdate() {
        guard let base = origin, let runtimeID = expectedRuntimeID,
              let data = try? Data(contentsOf: dataDirectory.appendingPathComponent("session.json")),
              let session = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let token = session["token"] as? String else {
            cancelUpdateShutdown("Could not contact the background service. Reopen LocalXiv and try updating again.")
            return
        }
        var request = URLRequest(url: base.appendingPathComponent("api/update/shutdown"))
        request.httpMethod = "POST"; request.timeoutInterval = 5
        request.setValue("Bearer " + token, forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: ["runtime_id": runtimeID])
        URLSession.shared.dataTask(with: request) { data, response, error in
            let status = (response as? HTTPURLResponse)?.statusCode
            let body = data.flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: Any] }
            DispatchQueue.main.async {
                if status == 200, body?["ready"] as? Bool == true {
                    self.waitForServiceExit(deadline: Date().addingTimeInterval(10))
                } else if status == 409, body?["busy"] as? Bool == true {
                    self.cancelUpdateShutdown("Finish the running and queued jobs, then choose Install and Relaunch again. Your update has been downloaded.")
                } else {
                    self.cancelUpdateShutdown(error?.localizedDescription ?? "The background service could not stop safely. Reopen LocalXiv and try again.")
                }
            }
        }.resume()
    }

    func waitForServiceExit(deadline: Date) {
        if !FileManager.default.fileExists(atPath: dataDirectory.appendingPathComponent("session.json").path) {
            NSApp.reply(toApplicationShouldTerminate: true)
        } else if Date() > deadline {
            cancelUpdateShutdown("The background service has not exited. Reopen LocalXiv before trying the update again.")
        } else {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) { self.waitForServiceExit(deadline: deadline) }
        }
    }

    func cancelUpdateShutdown(_ message: String) {
        installingUpdate = false; updateShutdownStarted = false
        NSApp.reply(toApplicationShouldTerminate: false)
        // An alert, not a toast: the reader chose to install the update and waits for LocalXiv to quit.
        let alert = NSAlert(); alert.messageText = "The update was not installed"; alert.informativeText = message
        alert.beginSheetModal(for: window)
    }
}
#endif

// @main, not top-level code: top-level statements compile only in a single-file build or in main.swift.
@main
enum Main {
    static let delegate = PapersApp()
    static func main() {
        let app = NSApplication.shared
        app.setActivationPolicy(.regular)
        app.delegate = delegate
        app.run()
    }
}
