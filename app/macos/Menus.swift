import Cocoa
#if canImport(Sparkle)
import Sparkle
#endif

// The menu bar from the spec's table. A command item carries its command and is enabled from the Chrome state.
// Its key equivalent runs before the page acts on the key, and the page's own key map is off in the Native shell.
extension PapersApp: NSMenuItemValidation {
    func makeMainMenu() -> NSMenu {
        let bar = NSMenu()
        func menu(_ title: String, _ items: [NSMenuItem]) -> NSMenuItem {
            let item = NSMenuItem(title: title, action: nil, keyEquivalent: "")
            item.submenu = NSMenu(title: title)
            items.forEach { item.submenu!.addItem($0) }
            return item
        }
        func item(_ title: String, _ action: Selector?, _ key: String = "", _ modifiers: NSEvent.ModifierFlags = .command, target: AnyObject? = nil) -> NSMenuItem {
            let item = NSMenuItem(title: title, action: action, keyEquivalent: key)
            item.keyEquivalentModifierMask = modifiers
            item.target = target
            return item
        }
        func command(_ title: String, _ command: [String: Any], _ key: String = "", _ modifiers: NSEvent.ModifierFlags = .command) -> NSMenuItem {
            let item = item(title, #selector(runCommand(_:)), key, modifiers, target: self)
            item.representedObject = command
            return item
        }
        var app: [NSMenuItem] = [item("About LocalXiv", #selector(NSApplication.orderFrontStandardAboutPanel(_:))), .separator(),
                   item("Settings…", #selector(openSettings(_:)), ",", target: self)]
#if canImport(Sparkle)
        app.append(item("Check for Updates…", #selector(SPUStandardUpdaterController.checkForUpdates(_:)), target: updaterController))
#endif
        let services = menu("Services", [])
        NSApp.servicesMenu = services.submenu
        app += [.separator(), services, .separator(), item("Hide LocalXiv", #selector(NSApplication.hide(_:)), "h"),
                item("Hide Others", #selector(NSApplication.hideOtherApplications(_:)), "h", [.option, .command]),
                item("Show All", #selector(NSApplication.unhideAllApplications(_:))), .separator(),
                item("Quit LocalXiv", #selector(NSApplication.terminate(_:)), "q")]
        // Search (⌥⌘F) and its hidden twin, ⌘K, expand the toolbar search in every mode, also in the reader, where ⌘F opens the find bar.
        let searchKey = item("Search", #selector(search(_:)), "k", target: self)
        searchKey.isHidden = true
        searchKey.allowsKeyEquivalentWhenHidden = true
        // ⌘+ is ⇧⌘= on most layouts, so a hidden twin takes ⌘=.
        let biggerTwin = command("Bigger", ["name": "text-size", "step": 1], "=")
        biggerTwin.isHidden = true
        biggerTwin.allowsKeyEquivalentWhenHidden = true
        let windowMenu = menu("Window", [item("Minimize", #selector(NSWindow.performMiniaturize(_:)), "m"), item("Zoom", #selector(NSWindow.performZoom(_:))), .separator(),
                                         item("Bring All to Front", #selector(NSApplication.arrangeInFront(_:)))])
        let paperMenu = menu("Paper", [])
        let helpMenu = menu("Help", [item("LocalXiv Help", #selector(openHelp(_:)), target: self)])
        [menu("LocalXiv", app),
         menu("File", [command("Add Paper…", ["name": "add"], "n"),
                       menu("Export", [("EPUB", "export-epub"), ("EPUB with Notes", "export-epub-notes"), ("PDF", "export-pdf"), ("PNG", "export-png"), ("Editable SVG", "export-svg"),
                                       ("Highlights and Notes…", "export-records")]
                            .map { command($0.0, ["name": "action", "id": $0.1]) }),
                       command("Send to Kindle…", ["name": "action", "id": "send-kindle"]), .separator(),
                       item("Close Window", #selector(NSWindow.performClose(_:)), "w")]),
         menu("Edit", [item("Undo", #selector(undo(_:)), "z", target: self), item("Redo", Selector(("redo:")), "z", [.shift, .command]), .separator(),
                       item("Cut", #selector(NSText.cut(_:)), "x"), item("Copy", #selector(NSText.copy(_:)), "c"),
                       item("Paste", #selector(NSText.paste(_:)), "v"), item("Select All", #selector(NSText.selectAll(_:)), "a"), .separator(),
                       menu("Find", [item("Search", #selector(search(_:)), "f", [.option, .command], target: self),
                                     item("Find…", #selector(find(_:)), "f", target: self), item("Find Next", #selector(findNext(_:)), "g", target: self),
                                     item("Find Previous", #selector(findPrevious(_:)), "g", [.shift, .command], target: self),
                                     item("Use Selection for Find", #selector(useSelectionForFind(_:)), "e", target: self), searchKey])]),
         menu("View", [command("Overview", ["name": "view", "view": "overview"], "1"), command("Blog", ["name": "view", "view": "blog"], "2"),
                       command("Paper", ["name": "view", "view": "paper"], "3"), .separator(),
                       item("Show Sidebar", #selector(NSSplitViewController.toggleSidebar(_:)), "s", [.control, .command]),
                       item("Hide Toolbar", #selector(toggleToolbar(_:)), "t", [.option, .command], target: self), .separator(),
                       command("Bigger", ["name": "text-size", "step": 1], "+"), biggerTwin,
                       command("Smaller", ["name": "text-size", "step": -1], "-"), command("Actual Size", ["name": "text-size", "step": 0], "0"),
                       menu("Theme", ReadingPopover.themes.map { command($0.label, ["name": "prefs", "patch": ["theme": $0.value]]) }),
                       item("Show Reading Preferences…", #selector(openReadingPreferences(_:)), target: self), .separator(),
                       item("Enter Full Screen", #selector(NSWindow.toggleFullScreen(_:)), "f", [.control, .command])]),
         paperMenu,
         menu("Go", [command("Back", ["name": "back"], "["), command("Forward", ["name": "forward"], "]"), .separator(),
                     command("Home", ["name": "go", "to": "home"], "h", [.shift, .command]), command("Library", ["name": "go", "to": "all"], "l", [.shift, .command])]),
         windowMenu, helpMenu].forEach { bar.addItem($0) }
        NSApp.windowsMenu = windowMenu.submenu
        NSApp.helpMenu = helpMenu.submenu
        fill(paperMenu.submenu!, Self.firstPaperActions)
        return bar
    }

    // Until a Paper opens, the reader's actions under their first labels fill the Paper menu, disabled.
    static let firstPaperActions = [
        ChromeState.Action(id: "highlight", label: "Highlight"), .init(id: "add-note", label: "Add Note…"), .init(id: "ask", label: "Ask…"),
        .init(id: "explain", label: "Explain"), .init(id: "ask-paper", label: "Ask About the Paper…", separatorBefore: true), .init(id: "all-notes", label: "All Notes"), .init(id: "clear-chat", label: "Clear Chat"),
        .init(id: "copy-notes", label: "Copy Notes from an Older Version"),
        .init(id: "mark-read", label: "Mark as Read", separatorBefore: true), .init(id: "open-pdf", label: "Open PDF", separatorBefore: true),
        .init(id: "open-arxiv", label: "Open on arXiv"), .init(id: "copy-link", label: "Copy arXiv Link", separatorBefore: true),
        .init(id: "copy-bibtex", label: "Copy BibTeX"), .init(id: "copy-records", label: "Copy Highlights and Notes"), .init(id: "regenerate", label: "Regenerate", separatorBefore: true),
        .init(id: "remove", label: "Remove from Library…", separatorBefore: true)]

    // The Paper menu: the More actions, with the Share menu's two Copy actions before Regenerate.
    // Outside the reader the Chrome state has no actions, so the menu keeps its items and validation disables them.
    func updatePaperMenu(_ state: ChromeState) {
        guard let more = state.actions["more"], !more.isEmpty, state.actions != chrome.actions,
              let menu = NSApp.mainMenu?.item(withTitle: "Paper")?.submenu else { return }
        let copies = (state.actions["share"] ?? []).filter { $0.id.hasPrefix("copy-") }
        let split = more.firstIndex { $0.id == "regenerate" } ?? more.endIndex
        fill(menu, Array(more[..<split] + copies + more[split...]))
    }

    // The key equivalents of the Paper menu, by action.
    static let paperKeys: [String: (String, NSEvent.ModifierFlags)] = ["highlight": ("h", [.control, .command]), "add-note": ("n", [.control, .command]),
                                                                       "ask-paper": ("a", [.shift, .command]), "all-notes": ("n", [.shift, .command]),
                                                                       "remove": ("\u{8}", .command)]

    // The commands on the selection in the Paper. They come first in the Paper menu, and last in the context menu.
    static let selectionActions = ["highlight", "add-note", "ask", "explain"]
    // The Highlight colours of app/static/margin.js's COLOURS, in title case for the context menu.
    static let colours = [("key", "Key Point"), ("question", "Question"), ("use", "Use in My Work"), ("disagree", "Disagree")]

    private func fill(_ menu: NSMenu, _ actions: [ChromeState.Action]) {
        menu.removeAllItems()
        for action in actions {
            if action.separatorBefore && !menu.items.isEmpty { menu.addItem(.separator()) }
            let item = actionItem(action)
            (item.keyEquivalent, item.keyEquivalentModifierMask) = Self.paperKeys[action.id] ?? ("", .command)
            menu.addItem(item)
        }
    }

    private func actionItem(_ action: ChromeState.Action) -> NSMenuItem {
        let item = NSMenuItem(title: action.label, action: #selector(runCommand(_:)), keyEquivalent: "")
        item.target = self
        item.representedObject = ["name": "action", "id": action.id]
        return item
    }

    // The context menu in the Paper view of a converted Paper: a separator and the selection commands, with no keys, as
    // the Human Interface Guidelines say. Highlight is a submenu of the four colours. Each item gets its state now,
    // because WebKit's menu does not validate its items.
    func addSelectionItems(to menu: NSMenu) {
        guard chrome.mode == "reader", chrome.views?.current == "paper" else { return }
        let items = chrome.allActions.filter { Self.selectionActions.contains($0.id) && $0.enabled }.map(actionItem)
        guard !items.isEmpty else { return }
        if !menu.items.isEmpty { menu.addItem(.separator()) }
        for item in items {
            item.isEnabled = validateMenuItem(item)
            if (item.representedObject as? [String: Any])?["id"] as? String == "highlight" {
                let colours = NSMenu(title: item.title)
                colours.autoenablesItems = false
                for (id, label) in Self.colours {
                    let colour = colours.addItem(withTitle: label, action: #selector(runCommand(_:)), keyEquivalent: "")
                    colour.target = self
                    colour.representedObject = ["name": "action", "id": "highlight", "colour": id]
                    colour.isEnabled = item.isEnabled
                }
                item.submenu = colours
            }
            menu.addItem(item)
        }
    }

    // A context menu of the page, such as on a Library or Notes row, as an NSMenu at the pointer. The items are
    // Chrome state Actions, and the pick goes back as {name: 'menu-pick', id}. The menu opens after this message returns.
    func showMenu(_ items: [[String: Any]]) {
        let menu = NSMenu()
        menu.autoenablesItems = false
        for action in items {
            if action["separatorBefore"] as? Bool == true && !menu.items.isEmpty { menu.addItem(.separator()) }
            let item = menu.addItem(withTitle: action["label"] as? String ?? "", action: #selector(runCommand(_:)), keyEquivalent: "")
            item.target = self
            item.representedObject = ["name": "menu-pick", "id": action["id"] as? String ?? ""]
            item.isEnabled = action["enabled"] as? Bool == true
        }
        let point = webView.convert(window.mouseLocationOutsideOfEventStream, from: nil)
        DispatchQueue.main.async { menu.popUp(positioning: nil, at: point, in: self.webView) }
    }

    @objc func runCommand(_ sender: NSMenuItem) {
        if let command = sender.representedObject as? [String: Any] { send(command) }
    }

    // Edit › Undo restores the last removed Question card while no text field in the main window has the focus.
    // Otherwise it is the key window's own undo, which undoes typing in a field of the page, the toolbar, or Settings.
    var pageUndo: Bool { chrome.canUndo && !chrome.editing && NSApp.keyWindow === window && !(window.firstResponder is NSText) }

    @objc func undo(_ sender: Any?) {
        if pageUndo { send(["name": "undo"]) } else { NSApp.keyWindow?.tryToPerform(#selector(undo(_:)), with: sender) }
    }

    // In the reader, Find opens the find bar for the open view; elsewhere it goes to the toolbar search field.
    @objc func find(_ sender: Any?) {
        if chrome.mode == "reader" { findBar.open() } else { search(sender) }
    }

    // The search field is in the toolbar, so a hidden toolbar shows again first.
    @objc func search(_ sender: Any?) {
        window.toolbar?.isVisible = true
        (window.toolbar?.items.first { $0.itemIdentifier == .search } as? NSSearchToolbarItem)?.beginSearchInteraction()
    }

    // View › Hide Toolbar acts on the main window only, so the Settings window keeps its pane toolbar.
    @objc func toggleToolbar(_ sender: Any?) { window.toggleToolbarShown(sender) }

    @objc func findNext(_ sender: Any?) { findBar.find(backwards: false) }
    @objc func findPrevious(_ sender: Any?) { findBar.find(backwards: true) }

    // The page gives the selected text of the open view, and the find bar opens with it. Nothing selected does nothing.
    @objc func useSelectionForFind(_ sender: Any?) {
        webView.callAsyncJavaScript("return await window.localxiv.command({name: 'selection'})", in: nil, in: .page) { [weak self] result in
            guard let self, case .success(let value) = result, let text = value as? String, !text.isEmpty else { return }
            findBar.field.stringValue = text
            findBar.open()
        }
    }

    @objc func openHelp(_ sender: Any?) {
        NSWorkspace.shared.open(URL(string: "https://github.com/Akhil-Theerthala/LocalXiv#readme")!)
    }

    func validateMenuItem(_ item: NSMenuItem) -> Bool {
        // The find bar and the search field are in the main window, so Find does nothing while Settings is key.
        if [#selector(find(_:)), #selector(search(_:))].contains(item.action) { return NSApp.keyWindow === window }
        if item.action == #selector(useSelectionForFind(_:)) { return NSApp.keyWindow === window && chrome.mode == "reader" }
        if item.action == #selector(toggleToolbar(_:)) {
            item.title = window.toolbar?.isVisible == false ? "Show Toolbar" : "Hide Toolbar"
            return NSApp.keyWindow === window
        }
        if [#selector(findNext(_:)), #selector(findPrevious(_:))].contains(item.action) {
            return NSApp.keyWindow === window && chrome.mode == "reader" && !findBar.field.stringValue.isEmpty
        }
        if item.action == #selector(undo(_:)) {
            if pageUndo { item.title = chrome.undoName.isEmpty ? "Undo" : "Undo " + chrome.undoName; return true }
            return NSApp.keyWindow?.validateMenuItem(item) ?? false
        }
        // The Settings window loads from the background service, so it waits for the service's address and token.
        if [#selector(openSettings(_:)), #selector(openReadingPreferences(_:))].contains(item.action) { return origin != nil && token != nil }
        guard let command = item.representedObject as? [String: Any] else { return true }
        let state = chrome
        switch command["name"] as? String {
        case "view":
            let view = command["view"] as? String ?? ""
            item.state = state.views?.current == view ? .on : .off
            // An off view stays reachable: the view says how to connect a provider, or why the Paper cannot have one.
            return state.mode == "reader"
        case "back": return state.canBack
        case "forward": return state.canForward
        case "action":
            // In a text field, native or in the page, ⌘⌫ deletes to the start of the line, so Remove from Library… gives up the key there.
            if command["id"] as? String == "remove", NSApp.currentEvent?.type == .keyDown, NSApp.keyWindow?.firstResponder is NSText || state.editing { return false }
            // The selection commands act on the Paper, so a text field in the page keeps their keys.
            if Self.selectionActions.contains(command["id"] as? String ?? ""), state.editing { return false }
            return state.allActions.contains { $0.id == command["id"] as? String && $0.enabled }
        case "text-size":
            // The bounds and the default are app/static/appearance.js's SIZES and DEFAULTS.size.
            switch command["step"] as? Int {
            case 1: return state.prefs.size < 36
            case -1: return state.prefs.size > 15
            default: return state.prefs.size != 18
            }
        case "prefs":
            item.state = (command["patch"] as? [String: Any])?["theme"] as? String == state.prefs.theme ? .on : .off
            return true
        default: return true
        }
    }
}
