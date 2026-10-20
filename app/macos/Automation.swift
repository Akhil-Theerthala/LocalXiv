#if LOCALXIV_AUTOMATION
import Cocoa
import WebKit

// Test builds only. Runs the JSON step list named by LOCALXIV_AUTOMATION; tools/native_shot.py lists the steps.
extension PapersApp {
    static var automationStarted = false
    // The items of the last context menu that a right-click step opened.
    static var openedMenu: [[String: Any]]? = nil

    // Steps start after the first page load, or at launch when the first step is {"launch": true}.
    func startAutomation(atLaunch: Bool = false) {
        guard !Self.automationStarted, let path = ProcessInfo.processInfo.environment["LOCALXIV_AUTOMATION"] else { return }
        let file = URL(fileURLWithPath: path)
        guard let data = try? Data(contentsOf: file),
              let steps = try? JSONSerialization.jsonObject(with: data) as? [[String: Any]] else { automationFail("Cannot read the steps in \(path).") }
        guard (steps.first?["launch"] != nil) == atLaunch else { return }
        Self.automationStarted = true
        runSteps(steps.dropFirst(atLaunch ? 1 : 0), folder: file.deletingLastPathComponent())
    }

    func runSteps(_ steps: ArraySlice<[String: Any]>, folder: URL) {
        guard let step = steps.first else { return }
        automationLog("step \(String(decoding: (try? JSONSerialization.data(withJSONObject: step)) ?? Data(), as: UTF8.self))")
        let next = { self.runSteps(steps.dropFirst(), folder: folder) }
        // AppKit and WebKit redraw after a change returns, so the next step waits for that redraw.
        let settle = { DispatchQueue.main.asyncAfter(deadline: .now() + 0.5, execute: next) }
        let settingsStep = step["window"] as? String == "settings"
        guard !settingsStep || settings != nil else { automationFail("The Settings window is not open.") }
        let target: NSWindow = settingsStep ? settings!.window : window
        // Menus, keys, and first clicks act on the key window, so input steps bring the app to the front.
        // A key or menu step keeps the key window it finds, such as an open Settings window.
        if ["click", "rightclick", "key", "menu", "control"].contains(where: { step[$0] != nil }) && !NSApp.isActive {
            NSApp.activate(ignoringOtherApps: true)
        }
        if (step["click"] != nil || step["rightclick"] != nil || step["control"] != nil || NSApp.keyWindow == nil) && !target.isKeyWindow { target.makeKeyAndOrderFront(nil) }
        if let source = step["js"] as? String {
            (settingsStep ? settings!.webView : webView).evaluateJavaScript(source) { result, error in
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
        } else if let path = step["toolbar"] as? String {
            // "views/1" picks a segment of a group: the subitem's own action, or the group's action with that selection.
            let parts = path.split(separator: "/").map(String.init)
            guard let item = target.toolbar?.items.first(where: { $0.itemIdentifier.rawValue == parts[0] }) else { automationFail("No toolbar item \(path).") }
            var sender: NSToolbarItem = item, enabled = item.isEnabled
            if parts.count == 2, let group = item as? NSToolbarItemGroup, let index = Int(parts[1]), group.subitems.indices.contains(index) {
                let segment = group.subitems[index]
                enabled = segment.isEnabled
                if segment.action != nil { sender = segment } else if enabled { group.selectedIndex = index }
            }
            guard let action = sender.action else { automationFail("The toolbar item \(path) has no action.") }
            if enabled { NSApp.sendAction(action, to: sender.target, from: sender) } else { automationLog("toolbar item \(path) is disabled") }
            settle()
        } else if let path = step["menu"] as? String {
            let titles = path.split(separator: "/").map(String.init)
            var menu = NSApp.mainMenu
            for title in titles.dropLast() { menu = menu?.items.first(where: { $0.submenu?.title == title })?.submenu }
            guard let menu, let index = menu.items.firstIndex(where: { $0.title == titles.last }) else { automationFail("No menu item \(path).") }
            menu.update()
            if menu.items[index].isEnabled { menu.performActionForItem(at: index) } else { automationLog("menu item \(path) is disabled") }
            settle()
        } else if let point = step["click"] as? [Double], point.count == 2 {
            // Window points from the top left, as in a snapshot at half its pixel size.
            click(NSPoint(x: point[0], y: target.frame.height - point[1]), in: target)
            settle()
        } else if let point = step["rightclick"] as? [Double], point.count == 2, let page = webView as? PageView {
            // The context menu tracks the mouse in its own loop. The hook keeps its items for the next dump, and a timer
            // in the common run loop modes closes it.
            let add = page.addItems
            Self.openedMenu = nil
            page.addItems = { menu in
                add(menu)
                page.addItems = add
                Self.openedMenu = menu.items.map { item in
                    item.isSeparatorItem ? ["separator": true]
                        : ["title": item.title, "enabled": item.isEnabled, "identifier": item.identifier?.rawValue ?? ""]
                }
                self.automationLog("context menu autoenables items: \(menu.autoenablesItems)")
                RunLoop.main.add(Timer(timeInterval: 0.5, repeats: false) { _ in menu.cancelTracking() }, forMode: .common)
            }
            click(NSPoint(x: point[0], y: window.frame.height - point[1]), in: window, types: [.rightMouseDown, .rightMouseUp])
            settle()
        } else if let key = step["key"] as? String {
            let named = ["return": ("\r", 36), "escape": ("\u{1b}", 53), "delete": ("\u{7f}", 51), "down": ("\u{F701}", 125), "up": ("\u{F700}", 126),
                         "left": ("\u{F702}", 123), "right": ("\u{F703}", 124), "tab": ("\t", 48)]
            // A focused web view reads the key code as well as the characters, so a character key posts its US-layout code: its index here.
            let layout = Array("asdfhgzxcv\0bqweryt123465=97-80]ou[ip\0lj'k;\\,/nm.")
            let characters = named[key]?.0 ?? key, code = named[key]?.1 ?? (key.count == 1 ? layout.firstIndex(of: Character(key)) : nil)
            let names: [String: NSEvent.ModifierFlags] = ["command": .command, "shift": .shift, "control": .control, "option": .option]
            let flags = NSEvent.ModifierFlags((step["modifiers"] as? [String] ?? []).compactMap { names[$0] })
            for type in [NSEvent.EventType.keyDown, .keyUp] {
                var event = NSEvent.keyEvent(with: type, location: .zero, modifierFlags: flags, timestamp: ProcessInfo.processInfo.systemUptime,
                                             windowNumber: (NSApp.keyWindow ?? window).windowNumber, context: nil, characters: characters,
                                             charactersIgnoringModifiers: characters, isARepeat: false, keyCode: UInt16(code ?? 0))!
                // AppKit matches a key equivalent, such as ⇧⌘A or ⌘⌫, only in an event that the system made from the key code.
                if flags.contains(.command), let code, let cg = CGEvent(keyboardEventSource: nil, virtualKey: CGKeyCode(code), keyDown: type == .keyDown) {
                    cg.flags = CGEventFlags(rawValue: UInt64(flags.rawValue))
                    event = NSEvent(cgEvent: cg)!
                }
                NSApp.postEvent(event, atStart: false)
            }
            settle()
        } else if let name = step["control"] as? String {
            control(name, value: step["value"])
            settle()
        } else if let seconds = step["wait"] as? Double {
            DispatchQueue.main.asyncAfter(deadline: .now() + seconds, execute: next)
        } else if let size = step["size"] as? [Double], size.count == 2 {
            window.setContentSize(NSSize(width: size[0], height: size[1]))
            settle()
        } else if let name = step["appearance"] as? String, ["light", "dark"].contains(name) {
            NSApp.appearance = NSAppearance(named: name == "dark" ? .darkAqua : .aqua)
            settle()
        } else if let name = step["dump"] as? String {
            do { try JSONSerialization.data(withJSONObject: describe(), options: [.prettyPrinted, .sortedKeys]).write(to: folder.appendingPathComponent(name)) }
            catch { automationFail("Cannot write \(name): \(error.localizedDescription)") }
            automationLog("dump \(folder.appendingPathComponent(name).path)")
            next()
        } else if let name = step["snapshot"] as? String {
            snapshot(target, settingsStep ? settings!.webView : webView, to: folder.appendingPathComponent(name), then: next)
        } else if step["quit"] != nil {
            NSApp.terminate(nil)
        } else {
            automationFail("Unknown step.")
        }
    }

    func allViews(_ view: NSView) -> [NSView] { [view] + view.subviews.flatMap(allViews) }

    func click(_ location: NSPoint, in target: NSWindow, types: [NSEvent.EventType] = [.leftMouseDown, .leftMouseUp]) {
        for type in types {
            NSApp.postEvent(NSEvent.mouseEvent(with: type, location: location, modifierFlags: [], timestamp: ProcessInfo.processInfo.systemUptime,
                                               windowNumber: target.windowNumber, context: nil, eventNumber: 0, clickCount: 1, pressure: 1)!, atStart: false)
        }
    }

    // Finds a view by identifier in any window and acts on it as a user would: a row label clicks that sidebar row,
    // text goes into a field through its field editor, and a value sets a control before its action is sent.
    func control(_ name: String, value: Any?) {
        guard let view = NSApp.windows.compactMap(\.contentView?.superview).flatMap(allViews).first(where: { $0.identifier?.rawValue == name })
        else { automationFail("No control \(name).") }
        switch view {
        case let outline as NSOutlineView:
            let row = (0..<outline.numberOfRows).first { row in
                (outline.view(atColumn: 0, row: row, makeIfNecessary: true) as? NSTableCellView)?.textField?.stringValue == value as? String
            }
            guard let row, let window = outline.window else { automationFail("No sidebar row \(value ?? "").") }
            outline.scrollRowToVisible(row)
            let rect = outline.convert(outline.rect(ofRow: row), to: nil)
            click(NSPoint(x: rect.midX, y: rect.midY), in: window)
        case let field as NSTextField:
            field.window?.makeFirstResponder(field)
            field.currentEditor()?.selectAll(nil)
            (field.currentEditor() as? NSTextView)?.insertText(value as? String ?? "", replacementRange: NSRange(location: NSNotFound, length: 0))
        case let control as NSControl:
            if let popup = control as? NSPopUpButton, let value = value as? String {
                popup.selectItem(at: popup.itemArray.firstIndex { $0.representedObject as? String == value || $0.title == value } ?? -1)
            } else if let segments = control as? NSSegmentedControl, let value = value as? Int {
                segments.selectedSegment = value
            } else if let number = value as? Double {
                control.doubleValue = number
            }
            if value == nil, let button = control as? NSButton { button.performClick(nil) }
            else if let action = control.action { NSApp.sendAction(action, to: control.target, from: control) }
        default:
            automationFail("\(name) is not a control.")
        }
    }

    // The native chrome as JSON, so a check can read what the snapshot cannot show.
    func describe() -> [String: Any] {
        func modifiers(_ flags: NSEvent.ModifierFlags) -> String {
            [(NSEvent.ModifierFlags.control, "⌃"), (.option, "⌥"), (.shift, "⇧"), (.command, "⌘")].filter { flags.contains($0.0) }.map(\.1).joined()
        }
        func menu(_ list: NSMenu?) -> [[String: Any]] {
            guard let list else { return [] }
            list.update()
            return list.items.map { item in
                if item.isSeparatorItem { return ["separator": true] }
                var entry: [String: Any] = ["title": item.title, "enabled": item.isEnabled]
                if !item.keyEquivalent.isEmpty { entry["key"] = modifiers(item.keyEquivalentModifierMask) + item.keyEquivalent }
                if item.state == .on { entry["checked"] = true }
                if item.isHidden { entry["hidden"] = true }
                if item.attributedTitle?.attribute(.foregroundColor, at: 0, effectiveRange: nil) as? NSColor == .systemRed { entry["destructive"] = true }
                if item.submenu != nil { entry["items"] = menu(item.submenu) }
                return entry
            }
        }
        func toolbar(_ window: NSWindow?) -> [[String: Any]] {
            (window?.toolbar?.items ?? []).map { item in
                var entry: [String: Any] = ["id": item.itemIdentifier.rawValue, "label": item.label, "hidden": item.isHidden, "enabled": item.isEnabled,
                                            "visible": item.isVisible]
                if item.isNavigational { entry["navigational"] = true }
                if let group = item as? NSToolbarItemGroup {
                    entry["selected"] = group.selectedIndex
                    entry["control"] = "\(type(of: group.view as Any))"
                    entry["segments"] = group.subitems.map { ["label": $0.label, "enabled": $0.isEnabled] }
                }
                if let item = item as? NSMenuToolbarItem { entry["menu"] = menu(item.menu) }
                if let item = item as? NSSearchToolbarItem {
                    entry["text"] = item.searchField.stringValue
                    entry["editing"] = item.searchField.currentEditor() != nil
                    // A folded item shows its magnifier button in place of the field.
                    entry["folded"] = item.searchField.isHiddenOrHasHiddenAncestor
                }
                return entry
            }
        }
        // Window points from the top left, as the click step takes them.
        func place(_ view: NSView) -> [CGFloat] {
            let frame = view.convert(view.bounds, to: nil)
            return [frame.minX, (view.window?.frame.height ?? 0) - frame.maxY, frame.width, frame.height].map { ($0 * 10).rounded() / 10 }
        }
        func edges(_ insets: NSEdgeInsets) -> [String: CGFloat] { ["top": insets.top, "left": insets.left, "bottom": insets.bottom, "right": insets.right] }
        func controls(_ window: NSWindow?) -> [String: Any] {
            guard let frame = window?.contentView?.superview else { return [:] }
            var found: [String: Any] = [:]
            for view in allViews(frame) {
                guard let name = view.identifier?.rawValue, !name.hasPrefix("_"), !name.hasPrefix("NS") else { continue }
                var entry: [String: Any] = ["hidden": view.isHiddenOrHasHiddenAncestor, "frame": place(view)]
                switch view {
                case let outline as NSOutlineView:
                    entry["rows"] = (0..<outline.numberOfRows).map { row -> String in
                        let texts = allViews(outline.view(atColumn: 0, row: row, makeIfNecessary: true) ?? NSView()).compactMap { ($0 as? NSTextField)?.stringValue }
                        return (outline.selectedRow == row ? "> " : "  ") + texts.joined(separator: " | ")
                    }
                case let button as ActivityButton:
                    entry["text"] = [button.label.stringValue, button.count.stringValue]
                    entry["progress"] = button.progress.isIndeterminate ? "indeterminate" : String(button.progress.doubleValue)
                    entry["accessibility"] = [button.cell?.accessibilityRole()?.rawValue ?? "", button.cell?.accessibilityLabel() ?? "",
                                              button.acceptsFirstResponder ? "focusable" : "not focusable"]
                case let popup as NSPopUpButton:
                    entry["selected"] = popup.titleOfSelectedItem ?? ""
                    entry["faces"] = popup.itemArray.map { ($0.attributedTitle?.attribute(.font, at: 0, effectiveRange: nil) as? NSFont)?.fontName ?? "" }
                case let segments as NSSegmentedControl:
                    entry["selected"] = segments.selectedSegment
                case let slider as NSSlider:
                    entry["value"] = slider.doubleValue
                    entry["range"] = [slider.minValue, slider.maxValue]
                case let button as NSButton:
                    entry["on"] = button.state == .on
                case let field as NSTextField:
                    entry["text"] = field.stringValue
                default:
                    break
                }
                found[name] = entry
            }
            return found
        }
        let popover = NSApp.windows.first { $0.isVisible && "\(type(of: $0))".contains("Popover") }
        let context = NSMenu()
        addSelectionItems(to: context)
        var description: [String: Any] = [
            "window": ["title": window.title, "subtitle": window.subtitle, "key": window.isKeyWindow, "size": [window.frame.width, window.frame.height],
                       "firstResponder": window.firstResponder.map { "\(type(of: $0))" } ?? ""],
            "page": ["ready": pageReady, "queued": queued.count, "content": place(webView.superview!), "web": place(webView),
                     "safeArea": edges(webView.superview!.safeAreaInsets), "obscured": edges(webView.obscuredContentInsets),
                     "sidebarCollapsed": (window.contentViewController as? NSSplitViewController)?.splitViewItems.first?.isCollapsed ?? false],
            "chrome": (try? JSONSerialization.jsonObject(with: JSONEncoder().encode(chrome))) ?? [:],
            "toolbar": toolbar(window),
            "controls": controls(window),
            "menus": menu(NSApp.mainMenu),
            // The items that the page's context menu adds after WebKit's items.
            "contextMenu": menu(context),
            "openedContextMenu": Self.openedMenu ?? [],
            "popover": popover.map { ["shown": true, "controls": controls($0)] } ?? ["shown": false],
        ]
        if let sheet = window.attachedSheet?.contentView {
            description["sheet"] = allViews(sheet).compactMap { ($0 as? NSTextField)?.stringValue ?? ($0 as? NSButton)?.title }.filter { !$0.isEmpty }
        }
        if let settings {
            description["settings"] = ["visible": settings.window.isVisible, "title": settings.window.title, "style": settings.window.toolbarStyle.rawValue,
                                       "size": [settings.window.frame.width, settings.window.frame.height], "page": settings.webView.frame.height,
                                       "resizable": settings.window.styleMask.contains(.resizable),
                                       "selected": settings.window.toolbar?.selectedItemIdentifier?.rawValue ?? "", "url": settings.webView.url?.absoluteString.split(separator: "#").first.map(String.init) ?? "",
                                       "toolbar": toolbar(settings.window)]
        }
        return description
    }

    // The page is drawn first, from takeSnapshot, and the title bar, toolbar, and sidebar from cacheDisplay over it, because the
    // web view lies under them. cacheDisplay cannot draw real glass: backdrop layers and scroll-edge pockets blur what is behind
    // them, which an offscreen drawing does not have, so they are hidden while drawing. The toolbar then shows the page as if
    // through clear glass, and the sidebar draws as an opaque panel. The selected segment of a toolbar group draws without its
    // label, and the sidebar selection draws black while the focus is outside the sidebar.
    func snapshot(_ target: NSWindow, _ web: WKWebView, to file: URL, then next: @escaping () -> Void) {
        // The launch state covers the web view, which may hold no page yet.
        guard launch.superview == nil else { return compose(target, web, nil, to: file, then: next) }
        // A snapshot rect is measured from the top left of the area inside the obscured insets, so this rect takes the whole view.
        let configuration = WKSnapshotConfiguration()
        let insets = web.obscuredContentInsets
        configuration.rect = web.bounds.offsetBy(dx: -insets.left, dy: -insets.top)
        web.takeSnapshot(with: configuration) { image, error in
            guard let image else { self.automationFail("No web view snapshot: \(error.map { "\($0)" } ?? "unknown error").") }
            self.compose(target, web, image, to: file, then: next)
        }
    }

    func compose(_ target: NSWindow, _ web: WKWebView, _ image: NSImage?, to file: URL, then next: @escaping () -> Void) {
        let chrome = self.draw(target, over: image == nil ? nil : web)
        let frameView = target.contentView!.superview!
        var rect = web.convert(web.bounds, to: frameView)
        if frameView.isFlipped { rect.origin.y = frameView.bounds.height - rect.maxY }
        let content = target === self.window && self.toolbar.popover.isShown ? self.toolbar.popover.contentViewController?.view : nil
        var place: NSRect?
        if let content, let popover = content.window {
            place = popover.convertToScreen(content.convert(content.bounds, to: nil)).offsetBy(dx: -target.frame.minX, dy: -target.frame.minY)
        }
        // A popover can reach past the window's edge, so the canvas grows to hold it.
        let canvas = NSRect(origin: .zero, size: chrome.size).union(place ?? .zero)
        let bitmap = self.blank(canvas.size)
        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)
        NSGraphicsContext.current!.cgContext.translateBy(x: -canvas.minX, y: -canvas.minY)
        image?.draw(in: rect)
        chrome.draw(in: NSRect(origin: .zero, size: chrome.size), from: NSRect(origin: .zero, size: chrome.size), operation: .sourceOver, fraction: 1, respectFlipped: false, hints: nil)
        // The popover's glass frame draws as a coloured square offscreen, so only the part under its content is drawn,
        // on a plain background and without the arrow.
        if let content, let place, let popover = content.window {
            let local = content.convert(content.bounds, to: nil)
            let outline = NSBezierPath(roundedRect: place, xRadius: 14, yRadius: 14)
            let picture = NSImage(size: popover.frame.size)
            picture.addRepresentation(self.draw(popover))
            content.effectiveAppearance.performAsCurrentDrawingAppearance {
                NSColor.windowBackgroundColor.setFill(); outline.fill()
                NSGraphicsContext.saveGraphicsState()
                outline.addClip()
                picture.draw(in: place, from: local, operation: .sourceOver, fraction: 1)
                NSGraphicsContext.restoreGraphicsState()
                NSColor.separatorColor.setStroke(); outline.stroke()
            }
        }
        NSGraphicsContext.restoreGraphicsState()
        do { try bitmap.representation(using: .png, properties: [:])!.write(to: file) }
        catch { self.automationFail("Cannot write \(file.path): \(error.localizedDescription)") }
        self.automationLog("snapshot \(file.path)")
        next()
    }

    // With a web view, the chrome is drawn without it and without the window background, so the page drawn under it shows through.
    func draw(_ target: NSWindow, over web: WKWebView? = nil) -> NSBitmapImageRep {
        let background = target.backgroundColor, alpha = web?.alphaValue ?? 1
        if let web { web.alphaValue = 0; target.backgroundColor = .clear }
        defer { if let web { web.alphaValue = alpha; target.backgroundColor = background } }
        return draw(target.contentView!.superview!)
    }

    func blank(_ size: NSSize) -> NSBitmapImageRep {
        let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: Int(size.width) * 2, pixelsHigh: Int(size.height) * 2,
                                      bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                                      colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
        bitmap.size = size
        return bitmap
    }

    func draw(_ frameView: NSView) -> NSBitmapImageRep {
        let bitmap = blank(frameView.bounds.size)
        let backdrops = allViews(frameView).filter { view in
            !view.isHidden && (view.layer.map { "\(type(of: $0))" } == "CABackdropLayer" || "\(type(of: view))" == "NSScrollPocket")
        }
        backdrops.forEach { $0.isHidden = true }
        frameView.displayIfNeeded()
        frameView.cacheDisplay(in: frameView.bounds, to: bitmap)
        backdrops.forEach { $0.isHidden = false }
        return bitmap
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
