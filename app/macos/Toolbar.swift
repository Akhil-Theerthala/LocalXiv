import Cocoa

extension NSToolbarItem.Identifier {
    static let history = Self("history"), views = Self("views"), reading = Self("reading"), more = Self("more"), search = Self("search")
}

// The main toolbar. The Chrome state sets which items show and what they hold; each control sends one command.
final class ToolbarController: NSObject, NSToolbarDelegate, NSSearchFieldDelegate {
    static let views = ["overview", "blog", "paper"]
    let toolbar = NSToolbar(identifier: "main")
    let popover = NSPopover()
    let reading = ReadingPopover()
    var send: ([String: Any]) -> Void = { _ in } {
        didSet { reading.send = send }
    }
    weak var page: NSView?
    private var actions: [String: [ChromeState.Action]]?
    private var currentView = -1
    // Set when the field sends a search, until the page shows search mode or the field ends editing.
    private var searchSent = false

    override init() {
        super.init()
        toolbar.delegate = self
        toolbar.displayMode = .iconOnly
        popover.behavior = .transient
        popover.contentViewController = reading
    }

    func toolbarDefaultItemIdentifiers(_ toolbar: NSToolbar) -> [NSToolbarItem.Identifier] {
        [.toggleSidebar, .sidebarTrackingSeparator, .history, .flexibleSpace, .views, .reading, .more, .search]
    }
    func toolbarAllowedItemIdentifiers(_ toolbar: NSToolbar) -> [NSToolbarItem.Identifier] { toolbarDefaultItemIdentifiers(toolbar) }

    func toolbar(_ toolbar: NSToolbar, itemForItemIdentifier identifier: NSToolbarItem.Identifier, willBeInsertedIntoToolbar flag: Bool) -> NSToolbarItem? {
        switch identifier {
        case .history:
            let images = ["chevron.left", "chevron.right"].compactMap { NSImage(systemSymbolName: $0, accessibilityDescription: nil) }
            let group = NSToolbarItemGroup(itemIdentifier: identifier, images: images, selectionMode: .momentary,
                                           labels: ["Back", "Forward"], target: self, action: #selector(history(_:)))
            group.label = "Back/Forward"
            group.isNavigational = true
            group.subitems.forEach { $0.autovalidates = false }
            return group
        case .views:
            let group = NSToolbarItemGroup(itemIdentifier: identifier, titles: ["Overview", "Blog", "Paper"], selectionMode: .selectOne,
                                           labels: ["Overview", "Blog", "Paper"], target: self, action: #selector(showView(_:)))
            group.label = "View"
            group.subitems.forEach { $0.autovalidates = false }
            group.isHidden = true
            return group
        case .reading:
            let item = button(identifier.rawValue, "textformat.size", "Reading Preferences", #selector(toggleReading(_:)))
            item.isHidden = true
            return item
        case .more:
            let item = NSMenuToolbarItem(itemIdentifier: identifier)
            item.label = "More"
            item.image = NSImage(systemSymbolName: "ellipsis", accessibilityDescription: item.label)
            item.showsIndicator = false
            item.autovalidates = false
            item.isHidden = true
            return item
        case .search:
            let item = NSSearchToolbarItem(itemIdentifier: identifier)
            let field = item.searchField
            field.identifier = NSUserInterfaceItemIdentifier("search")
            field.placeholderString = "Search or paste a link"
            field.sendsSearchStringImmediately = true
            field.delegate = self
            field.target = self; field.action = #selector(searchChanged(_:))
            // A narrow resting width folds the item to its magnifier button, which expands to the preferred width when
            // clicked or on beginSearchInteraction. The item folds again when the field loses focus with no text.
            let resting = field.widthAnchor.constraint(equalToConstant: 28)
            resting.priority = .defaultLow
            resting.isActive = true
            item.preferredWidthForSearchField = 280
            return item
        default:
            return nil
        }
    }

    private func button(_ identifier: String, _ symbol: String, _ label: String, _ action: Selector) -> NSToolbarItem {
        let item = NSToolbarItem(itemIdentifier: NSToolbarItem.Identifier(identifier))
        item.image = NSImage(systemSymbolName: symbol, accessibilityDescription: label)
        item.label = label
        item.toolTip = label
        item.target = self; item.action = action
        item.autovalidates = false
        return item
    }

    func apply(_ state: ChromeState) {
        let reader = state.mode == "reader"
        for item in toolbar.items {
            switch item.itemIdentifier {
            case .history:
                let buttons = (item as? NSToolbarItemGroup)?.subitems ?? []
                buttons.first?.isEnabled = state.canBack
                buttons.last?.isEnabled = state.canForward
            case .views:
                item.isHidden = !reader
                guard let group = item as? NSToolbarItemGroup else { break }
                currentView = Self.views.firstIndex(of: state.views?.current ?? "") ?? -1
                group.selectedIndex = currentView
            case .reading:
                item.isHidden = !reader
            case .more:
                item.isHidden = !reader
                if state.actions != actions, let menuItem = item as? NSMenuToolbarItem {
                    let more = state.actions["more"] ?? [], share = state.actions["share"] ?? []
                    menuItem.menu = menu(more, share: share)
                    menuItem.isEnabled = !(more + share).isEmpty
                }
            case .search:
                // While the reader types, the page's query lags behind the field, so it replaces the text only when
                // the field is not being edited or the page has left search. A state from before the first search
                // command can still arrive after the first keystroke, so it does not count as leaving search.
                if state.mode == "search" { searchSent = false }
                // Ending the interaction, not only the editing, gives the item back its resting width.
                if let item = item as? NSSearchToolbarItem, item.searchField.stringValue != state.search.query,
                   item.searchField.currentEditor() == nil || state.mode != "search" && !searchSent {
                    if item.searchField.currentEditor() != nil { item.endSearchInteraction() }
                    item.searchField.stringValue = state.search.query
                    // An expanded item folds only when its field loses focus with no text, so a field that the page
                    // empties after the focus left takes the focus for a moment and gives it back.
                    if state.search.query.isEmpty, item.searchField.currentEditor() == nil, let window = item.searchField.window {
                        let focus = window.firstResponder
                        window.makeFirstResponder(item.searchField)
                        window.makeFirstResponder(focus)
                    }
                }
            default:
                break
            }
        }
        actions = state.actions
        if !reader && popover.isShown { popover.close() }
        reading.apply(state.prefs)
    }

    // The More menu: the Paper actions, then the Share actions in a submenu.
    private func menu(_ actions: [ChromeState.Action], share: [ChromeState.Action] = []) -> NSMenu {
        let menu = NSMenu()
        menu.autoenablesItems = false
        for action in actions {
            if action.separatorBefore && !menu.items.isEmpty { menu.addItem(.separator()) }
            let item = menu.addItem(withTitle: action.label, action: #selector(runAction(_:)), keyEquivalent: "")
            item.target = self
            item.representedObject = action.id
            item.isEnabled = action.enabled
        }
        if !share.isEmpty {
            if !menu.items.isEmpty { menu.addItem(.separator()) }
            menu.addItem(withTitle: "Share", action: nil, keyEquivalent: "").submenu = self.menu(share)
        }
        return menu
    }

    @objc func history(_ sender: NSToolbarItemGroup) { send(["name": sender.selectedIndex == 1 ? "forward" : "back"]) }
    @objc func runAction(_ sender: NSMenuItem) { if let id = sender.representedObject as? String { send(["name": "action", "id": id]) } }

    @objc func showView(_ sender: NSToolbarItemGroup) {
        guard Self.views.indices.contains(sender.selectedIndex) else { return }
        send(["name": "view", "view": Self.views[sender.selectedIndex]])
        // As in the sidebar, only the page's next state moves the selection.
        sender.selectedIndex = currentView
    }

    @objc func toggleReading(_ sender: NSToolbarItem) {
        if popover.isShown { popover.close() } else { popover.show(relativeTo: sender) }
    }

    @objc func searchChanged(_ sender: NSSearchField) { search(sender.stringValue, submit: false) }

    func control(_ control: NSControl, textView: NSTextView, doCommandBy selector: Selector) -> Bool {
        guard let field = control as? NSSearchField else { return false }
        switch selector {
        case #selector(NSResponder.insertNewline(_:)):
            search(field.stringValue, submit: true)
        // Escape clears the text first, as the search field does; Escape in the empty field folds it and gives the focus back to the page.
        case #selector(NSResponder.cancelOperation(_:)) where field.stringValue.isEmpty:
            field.window?.makeFirstResponder(page)
        default:
            return false
        }
        return true
    }

    func controlTextDidEndEditing(_ notification: Notification) { searchSent = false }

    private func search(_ query: String, submit: Bool) {
        searchSent = true
        send(submit ? ["name": "search", "query": query, "submit": true] : ["name": "search", "query": query])
    }
}
