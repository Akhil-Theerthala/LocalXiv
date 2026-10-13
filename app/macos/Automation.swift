#if LOCALXIV_AUTOMATION
import Cocoa
import WebKit

// Test builds only. Runs the JSON step list named by LOCALXIV_AUTOMATION; tools/native_shot.py lists the steps.
extension PapersApp {
    static var automationStarted = false

    func startAutomation() {
        guard !Self.automationStarted, let path = ProcessInfo.processInfo.environment["LOCALXIV_AUTOMATION"] else { return }
        Self.automationStarted = true
        let file = URL(fileURLWithPath: path)
        guard let data = try? Data(contentsOf: file),
              let steps = try? JSONSerialization.jsonObject(with: data) as? [[String: Any]] else { automationFail("Cannot read the steps in \(path).") }
        runSteps(steps[...], folder: file.deletingLastPathComponent())
    }

    func runSteps(_ steps: ArraySlice<[String: Any]>, folder: URL) {
        guard let step = steps.first else { return }
        automationLog("step \(String(decoding: (try? JSONSerialization.data(withJSONObject: step)) ?? Data(), as: UTF8.self))")
        let next = { self.runSteps(steps.dropFirst(), folder: folder) }
        // AppKit and WebKit redraw after a change returns, so the next step waits for that redraw.
        let settle = { DispatchQueue.main.asyncAfter(deadline: .now() + 0.5, execute: next) }
        if let source = step["js"] as? String {
            webView.evaluateJavaScript(source) { result, error in
                self.automationLog(error.map { "js error: \($0)" } ?? "js result: \(result ?? "undefined")")
                next()
            }
        } else if let command = step["command"], let json = try? JSONSerialization.data(withJSONObject: command, options: .fragmentsAllowed) {
            webView.evaluateJavaScript("if (window.localxiv) { window.localxiv.command(\(String(decoding: json, as: UTF8.self))); true } else false") { result, error in
                if result as? Bool != true { self.automationLog("command not sent: \(error.map { "\($0)" } ?? "no window.localxiv")") }
                settle()
            }
        } else if let state = step["state"] {
            shell(["type": "state", "state": state])
            settle()
        } else if let identifier = step["toolbar"] as? String {
            guard let item = window.toolbar?.items.first(where: { $0.itemIdentifier.rawValue == identifier }), let action = item.action
            else { automationFail("No toolbar item \(identifier) with an action.") }
            NSApp.sendAction(action, to: item.target, from: item)
            settle()
        } else if let path = step["menu"] as? String {
            let titles = path.split(separator: "/").map(String.init)
            var menu = NSApp.mainMenu
            for title in titles.dropLast() { menu = menu?.items.first(where: { $0.submenu?.title == title })?.submenu }
            guard let menu, let index = menu.items.firstIndex(where: { $0.title == titles.last }) else { automationFail("No menu item \(path).") }
            menu.performActionForItem(at: index)
            settle()
        } else if let seconds = step["wait"] as? Double {
            DispatchQueue.main.asyncAfter(deadline: .now() + seconds, execute: next)
        } else if let size = step["size"] as? [Double], size.count == 2 {
            window.setContentSize(NSSize(width: size[0], height: size[1]))
            settle()
        } else if let name = step["appearance"] as? String, ["light", "dark"].contains(name) {
            NSApp.appearance = NSAppearance(named: name == "dark" ? .darkAqua : .aqua)
            settle()
        } else if let name = step["snapshot"] as? String {
            snapshot(to: folder.appendingPathComponent(name), then: next)
        } else if step["quit"] != nil {
            NSApp.terminate(nil)
        } else {
            automationFail("Unknown step.")
        }
    }

    // cacheDisplay draws the title bar, toolbar, and sidebar but leaves WebKit's layer empty, so the page is drawn in from takeSnapshot.
    // Backdrop layers and scroll-edge pockets blur what is behind them, which an offscreen drawing does not have, so they paint
    // the sidebar opaque white; they are hidden while drawing. The selected segment of a toolbar group still draws without its label.
    func snapshot(to file: URL, then next: @escaping () -> Void) {
        webView.takeSnapshot(with: nil) { image, error in
            guard let image else { self.automationFail("No web view snapshot: \(error.map { "\($0)" } ?? "unknown error").") }
            let frameView = self.window.contentView!.superview!
            let size = frameView.bounds.size
            let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: Int(size.width) * 2, pixelsHigh: Int(size.height) * 2,
                                          bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                                          colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
            bitmap.size = size
            func views(_ view: NSView) -> [NSView] { [view] + view.subviews.flatMap(views) }
            let backdrops = views(frameView).filter { view in
                !view.isHidden && (view.layer.map { "\(type(of: $0))" } == "CABackdropLayer" || "\(type(of: view))" == "NSScrollPocket")
            }
            backdrops.forEach { $0.isHidden = true }
            frameView.displayIfNeeded()
            frameView.cacheDisplay(in: frameView.bounds, to: bitmap)
            backdrops.forEach { $0.isHidden = false }
            var rect = self.webView.convert(self.webView.bounds, to: frameView)
            if frameView.isFlipped { rect.origin.y = size.height - rect.maxY }
            NSGraphicsContext.saveGraphicsState()
            NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)
            image.draw(in: rect)
            NSGraphicsContext.restoreGraphicsState()
            do { try bitmap.representation(using: .png, properties: [:])!.write(to: file) }
            catch { self.automationFail("Cannot write \(file.path): \(error.localizedDescription)") }
            self.automationLog("snapshot \(file.path)")
            next()
        }
    }

    func automationLog(_ text: String) {
        FileHandle.standardError.write(Data(("automation: " + text + "\n").utf8))
    }

    func automationFail(_ text: String) -> Never {
        automationLog("error: " + text)
        exit(1)
    }
}
#endif
