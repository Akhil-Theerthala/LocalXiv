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
        // ⌘+ is ⇧⌘= on most layouts, so a hidden twin takes ⌘=.
        let biggerTwin = command("Bigger", ["name": "text-size", "step": 1], "=")
        biggerTwin.isHidden = true
        biggerTwin.allowsKeyEquivalentWhenHidden = true
        let windowMenu = menu("Window", [item("Minimize", #selector(NSWindow.performMiniaturize(_:)), "m"), item("Zoom", #selector(NSWindow.performZoom(_:)))])
        let helpMenu = menu("Help", [item("LocalXiv Help", #selector(openHelp(_:)), target: self)])
        [menu("LocalXiv", app),
         menu("File", [command("Add Paper…", ["name": "add"], "n"),
                       menu("Export", [("EPUB", "export-epub"), ("PDF", "export-pdf"), ("PNG", "export-png"), ("Editable SVG", "export-svg")]
                            .map { command($0.0, ["name": "action", "id": $0.1]) }),
                       command("Send to Kindle…", ["name": "action", "id": "send-kindle"]), .separator(),
                       item("Close Window", #selector(NSWindow.performClose(_:)), "w")]),
         menu("Edit", [item("Undo", Selector(("undo:")), "z"), item("Redo", Selector(("redo:")), "z", [.shift, .command]), .separator(),
                       item("Cut", #selector(NSText.cut(_:)), "x"), item("Copy", #selector(NSText.copy(_:)), "c"),
                       item("Paste", #selector(NSText.paste(_:)), "v"), item("Select All", #selector(NSText.selectAll(_:)), "a"), .separator(),
                       item("Find…", #selector(find(_:)), "f", target: self)]),
         menu("View", [command("Overview", ["name": "view", "view": "overview"], "1"), command("Blog", ["name": "view", "view": "blog"], "2"),
                       command("Paper", ["name": "view", "view": "paper"], "3"), .separator(),
                       item("Show Sidebar", #selector(NSSplitViewController.toggleSidebar(_:)), "s", [.control, .command]), .separator(),
                       command("Bigger", ["name": "text-size", "step": 1], "+"), biggerTwin,
                       command("Smaller", ["name": "text-size", "step": -1], "-"), command("Actual Size", ["name": "text-size", "step": 0], "0"),
                       menu("Theme", ReadingPopover.themes.map { command($0.label, ["name": "prefs", "patch": ["theme": $0.value]]) }), .separator(),
                       item("Enter Full Screen", #selector(NSWindow.toggleFullScreen(_:)), "f", [.control, .command])]),
         menu("Go", [command("Back", ["name": "back"], "["), command("Forward", ["name": "forward"], "]"), .separator(),
                     command("Home", ["name": "go", "to": "home"], "h", [.shift, .command]), command("Library", ["name": "go", "to": "all"], "l", [.shift, .command])]),
         windowMenu, helpMenu].forEach { bar.addItem($0) }
        NSApp.windowsMenu = windowMenu.submenu
        NSApp.helpMenu = helpMenu.submenu
        return bar
    }

    @objc func runCommand(_ sender: NSMenuItem) {
        if let command = sender.representedObject as? [String: Any] { send(command) }
    }

    // In the reader, Find opens the find bar for the open view; elsewhere it goes to the toolbar search field.
    @objc func find(_ sender: Any?) {
        if chrome.mode == "reader" { findBar.open(); return }
        (window.toolbar?.items.first { $0.itemIdentifier == .search } as? NSSearchToolbarItem)?.beginSearchInteraction()
    }

    @objc func openHelp(_ sender: Any?) {
        NSWorkspace.shared.open(URL(string: "https://github.com/Akhil-Theerthala/LocalXiv#readme")!)
    }

    func validateMenuItem(_ item: NSMenuItem) -> Bool {
        // The find bar and the search field are in the main window, so Find does nothing while Settings is key.
        if item.action == #selector(find(_:)) { return NSApp.keyWindow === window }
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
        case "action": return state.allActions.contains { $0.id == command["id"] as? String && $0.enabled }
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
