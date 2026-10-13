import Cocoa

extension NSToolbarItem.Identifier {
    static let history = Self("history"), addPaper = Self("addPaper"), views = Self("views"), reading = Self("reading")
    static let share = Self("share"), more = Self("more"), search = Self("search")
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
    private var actions: [String: [ChromeState.Action]]?

    override init() {
        super.init()
        toolbar.delegate = self
        toolbar.displayMode = .iconOnly
        popover.behavior = .transient
        popover.contentViewController = reading
    }

    func toolbarDefaultItemIdentifiers(_ toolbar: NSToolbar) -> [NSToolbarItem.Identifier] {
        [.toggleSidebar, .sidebarTrackingSeparator, .history, .flexibleSpace, .addPaper, .views, .reading, .share, .more, .search]
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
        case .addPaper:
            return button(identifier.rawValue, "plus", "Add Paper", #selector(addPaper))
        case .views:
            let group = NSToolbarItemGroup(itemIdentifier: identifier, titles: ["Overview", "Blog", "Paper"], selectionMode: .selectOne,
                                           labels: ["Overview", "Blog", "Paper"], target: self, action: #selector(showView(_:)))
            group.label = "View"
            group.subitems.forEach { $0.autovalidates = false }
            group.isHidden = true
            return group
        case .reading:
            let item = button(identifier.rawValue, "textformat.size", "Reading", #selector(toggleReading(_:)))
            item.isHidden = true
            return item
        case .share, .more:
            let item = NSMenuToolbarItem(itemIdentifier: identifier)
            item.label = identifier == .share ? "Share" : "More"
            item.image = NSImage(systemSymbolName: identifier == .share ? "square.and.arrow.up" : "ellipsis.circle", accessibilityDescription: item.label)
            item.showsIndicator = false
            item.autovalidates = false
            item.isHidden = true
            return item
        case .search:
            let item = NSSearchToolbarItem(itemIdentifier: identifier)
            let field = item.searchField
            field.identifier = NSUserInterfaceItemIdentifier("search")
            field.placeholderString = "Search or paste an arXiv link"
            field.sendsSearchStringImmediately = true
            field.delegate = self
            field.target = self; field.action = #selector(searchChanged(_:))
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
            case .addPaper:
                item.isHidden = reader
            case .views:
                item.isHidden = !reader
                guard let group = item as? NSToolbarItemGroup else { break }
                for (view, segment) in zip(Self.views, group.subitems) { segment.isEnabled = (state.views?[view] ?? "off") != "off" }
                group.selectedIndex = Self.views.firstIndex(of: state.views?.current ?? "") ?? -1
            case .reading:
                item.isHidden = !reader
            case .share, .more:
                item.isHidden = !reader
                if state.actions != actions, let menuItem = item as? NSMenuToolbarItem {
                    let list = state.actions[item.itemIdentifier.rawValue] ?? []
                    menuItem.menu = menu(list)
                    menuItem.isEnabled = !list.isEmpty
                }
            case .search:
                // While the reader types, the page's query lags behind the field, so it replaces the text only when
                // the field is not being edited or the page has left search.
                if let field = (item as? NSSearchToolbarItem)?.searchField, field.stringValue != state.search.query,
                   field.currentEditor() == nil || state.mode != "search" {
                    field.abortEditing()
                    field.stringValue = state.search.query
                }
            default:
                break
            }
        }
        actions = state.actions
        if !reader && popover.isShown { popover.close() }
        reading.apply(state.prefs)
    }

    private func menu(_ actions: [ChromeState.Action]) -> NSMenu {
        let menu = NSMenu()
        menu.autoenablesItems = false
        for action in actions {
            if action.separatorBefore && !menu.items.isEmpty { menu.addItem(.separator()) }
            let item = menu.addItem(withTitle: action.label, action: #selector(runAction(_:)), keyEquivalent: "")
            item.target = self
            item.representedObject = action.id
            item.isEnabled = action.enabled
            if action.role == "destructive" {
                item.attributedTitle = NSAttributedString(string: action.label, attributes: [.foregroundColor: NSColor.systemRed, .font: NSFont.menuFont(ofSize: 0)])
            }
        }
        return menu
    }

    @objc func history(_ sender: NSToolbarItemGroup) { send(["name": sender.selectedIndex == 1 ? "forward" : "back"]) }
    @objc func addPaper() { send(["name": "add"]) }
    @objc func runAction(_ sender: NSMenuItem) { if let id = sender.representedObject as? String { send(["name": "action", "id": id]) } }

    @objc func showView(_ sender: NSToolbarItemGroup) {
        guard Self.views.indices.contains(sender.selectedIndex) else { return }
        send(["name": "view", "view": Self.views[sender.selectedIndex]])
    }

    @objc func toggleReading(_ sender: NSToolbarItem) {
        if popover.isShown { popover.close() } else { popover.show(relativeTo: sender) }
    }

    @objc func searchChanged(_ sender: NSSearchField) { send(["name": "search", "query": sender.stringValue]) }

    func control(_ control: NSControl, textView: NSTextView, doCommandBy selector: Selector) -> Bool {
        guard selector == #selector(NSResponder.insertNewline(_:)), let field = control as? NSSearchField else { return false }
        send(["name": "search", "query": field.stringValue, "submit": true])
        return true
    }
}
