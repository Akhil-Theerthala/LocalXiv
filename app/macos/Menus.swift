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
        // ⌘K expands the toolbar search in every mode, also in the reader, where ⌘F opens the find bar.
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
                       menu("Export", [("EPUB", "export-epub"), ("PDF", "export-pdf"), ("PNG", "export-png"), ("Editable SVG", "export-svg")]
                            .map { command($0.0, ["name": "action", "id": $0.1]) }),
                       command("Send to Kindle…", ["name": "action", "id": "send-kindle"]), .separator(),
                       item("Close Window", #selector(NSWindow.performClose(_:)), "w")]),
         menu("Edit", [item("Undo", #selector(undo(_:)), "z", target: self), item("Redo", Selector(("redo:")), "z", [.shift, .command]), .separator(),
                       item("Cut", #selector(NSText.cut(_:)), "x"), item("Copy", #selector(NSText.copy(_:)), "c"),
                       item("Paste", #selector(NSText.paste(_:)), "v"), item("Select All", #selector(NSText.selectAll(_:)), "a"), .separator(),
                       menu("Find", [item("Find…", #selector(find(_:)), "f", target: self), item("Find Next", #selector(findNext(_:)), "g", target: self),
                                     item("Find Previous", #selector(findPrevious(_:)), "g", [.shift, .command], target: self), searchKey])]),
         menu("View", [command("Overview", ["name": "view", "view": "overview"], "1"), command("Blog", ["name": "view", "view": "blog"], "2"),
                       command("Paper", ["name": "view", "view": "paper"], "3"), .separator(),
                       item("Show Sidebar", #selector(NSSplitViewController.toggleSidebar(_:)), "s", [.control, .command]), .separator(),
                       command("Bigger", ["name": "text-size", "step": 1], "+"), biggerTwin,
                       command("Smaller", ["name": "text-size", "step": -1], "-"), command("Actual Size", ["name": "text-size", "step": 0], "0"),
                       menu("Theme", ReadingPopover.themes.map { command($0.label, ["name": "prefs", "patch": ["theme": $0.value]]) }), .separator(),
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
        ChromeState.Action(id: "ask-paper", label: "Ask About the Paper…"), .init(id: "all-notes", label: "All Notes"),
        .init(id: "mark-read", label: "Mark as Read", separatorBefore: true), .init(id: "open-pdf", label: "Open PDF", separatorBefore: true),
        .init(id: "open-arxiv", label: "Open on arXiv"), .init(id: "copy-link", label: "Copy arXiv Link", separatorBefore: true),
        .init(id: "copy-bibtex", label: "Copy BibTeX"), .init(id: "regenerate", label: "Regenerate", separatorBefore: true),
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
    static let paperKeys: [String: (String, NSEvent.ModifierFlags)] = ["ask-paper": ("a", [.shift, .command]), "all-notes": ("n", [.option, .command]),
                                                                       "remove": ("\u{8}", .command)]

    private func fill(_ menu: NSMenu, _ actions: [ChromeState.Action]) {
        menu.removeAllItems()
        for action in actions {
            if action.separatorBefore && !menu.items.isEmpty { menu.addItem(.separator()) }
            let (key, modifiers) = Self.paperKeys[action.id] ?? ("", .command)
            let item = menu.addItem(withTitle: action.label, action: #selector(runCommand(_:)), keyEquivalent: key)
            item.keyEquivalentModifierMask = modifiers
            item.target = self
            item.representedObject = ["name": "action", "id": action.id]
        }
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

    @objc func search(_ sender: Any?) {
        (window.toolbar?.items.first { $0.itemIdentifier == .search } as? NSSearchToolbarItem)?.beginSearchInteraction()
    }

    @objc func findNext(_ sender: Any?) { findBar.find(backwards: false) }
    @objc func findPrevious(_ sender: Any?) { findBar.find(backwards: true) }

    @objc func openHelp(_ sender: Any?) {
        NSWorkspace.shared.open(URL(string: "https://github.com/Akhil-Theerthala/LocalXiv#readme")!)
    }

    func validateMenuItem(_ item: NSMenuItem) -> Bool {
        // The find bar and the search field are in the main window, so Find does nothing while Settings is key.
        if [#selector(find(_:)), #selector(search(_:))].contains(item.action) { return NSApp.keyWindow === window }
        if [#selector(findNext(_:)), #selector(findPrevious(_:))].contains(item.action) {
            return NSApp.keyWindow === window && chrome.mode == "reader" && !findBar.field.stringValue.isEmpty
        }
        if item.action == #selector(undo(_:)) {
            if pageUndo { item.title = "Undo"; return true }
            return NSApp.keyWindow?.validateMenuItem(item) ?? false
        }
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
            return state.allActions.contains { $0.id == command["id"] as? String && $0.enabled }
        case "text-size":
            // The bounds and the default are app/static/appearance.js's SIZES and DEFAULTS.size.
            switch command["step"] as? Int {
            case 1: return state.prefs.size < 26
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
