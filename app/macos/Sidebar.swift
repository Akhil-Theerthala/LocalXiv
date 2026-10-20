import Cocoa

// The source-list sidebar. Library mode: Home, LIBRARY, and RECENT. Reader mode: back, the Paper, and CONTENTS.
// A click sends its row's command and leaves the selection to the Chrome state, because the page drops page commands
// while a dialog is open and then posts no state.
final class SidebarController: NSViewController, NSOutlineViewDataSource, NSOutlineViewDelegate {
    struct Row: Equatable {
        enum Kind { case header, item, back, paper, note }
        var kind: Kind, label: String, detail = "", symbol: String? = nil, level = 1, command: [String: String] = [:]
    }
    final class Item: NSObject {
        let row: Row
        init(_ row: Row) { self.row = row }
    }

    var send: ([String: Any]) -> Void = { _ in }
    let outline = NSOutlineView()
    private let activity = ActivityButton()
    private var items: [Item] = []

    override func loadView() {
        outline.style = .sourceList
        outline.headerView = nil
        outline.floatsGroupRows = false
        outline.identifier = NSUserInterfaceItemIdentifier("sidebar")
        let column = NSTableColumn(identifier: NSUserInterfaceItemIdentifier("row"))
        outline.addTableColumn(column)
        outline.outlineTableColumn = column
        outline.dataSource = self; outline.delegate = self
        outline.target = self; outline.action = #selector(clicked)
        let scroll = NSScrollView()
        scroll.documentView = outline
        scroll.drawsBackground = false
        scroll.hasVerticalScroller = true
        // With a mouse attached, a legacy scroller would keep a strip of the sidebar empty when the rows fit.
        scroll.autohidesScrollers = true
        scroll.setContentHuggingPriority(.defaultLow, for: .vertical)
        activity.target = self; activity.action = #selector(showActivity)
        activity.isHidden = true
        let stack = NSStackView(views: [scroll, activity])
        stack.orientation = .vertical
        stack.spacing = 0
        stack.distribution = .fill
        for view in [scroll, activity] { view.widthAnchor.constraint(equalTo: stack.widthAnchor).isActive = true }
        view = stack
    }

    func apply(_ state: ChromeState) {
        loadViewIfNeeded()
        var rows: [Row] = [], selected: Int?
        if let reader = state.sidebar.reader {
            rows.append(Row(kind: .back, label: reader.back, symbol: "chevron.left", command: ["name": "leave"]))
            rows.append(Row(kind: .paper, label: reader.title, detail: reader.byline))
            rows.append(Row(kind: .header, label: "Contents"))
            for entry in reader.outline {
                // An entry with no id is a note, such as "A PDF has no sections.".
                if entry.id.isEmpty { rows.append(Row(kind: .note, label: entry.label)); continue }
                if entry.current { selected = rows.count }
                rows.append(Row(kind: .item, label: entry.label, detail: entry.number, level: min(max(entry.level, 1), 3), command: ["name": "outline", "id": entry.id]))
            }
            if reader.outline.isEmpty { rows.append(Row(kind: .note, label: "This view has no sections.")) }
        } else {
            let library = [("all", "All Papers", "books.vertical"), ("new", "New", "smallcircle.filled.circle"),
                           ("reading", "Reading", "circle.lefthalf.filled"), ("read", "Read", "checkmark.circle"),
                           ("notes", "Notes", "note.text")]
            if state.sidebar.selected == "home" { selected = 0 }
            rows.append(Row(kind: .item, label: "Home", symbol: "house", command: ["name": "go", "to": "home"]))
            rows.append(Row(kind: .header, label: "Library"))
            for (to, label, symbol) in library {
                if state.sidebar.selected == to { selected = rows.count }
                rows.append(Row(kind: .item, label: label, detail: state.sidebar.counts[to].map(String.init) ?? "", symbol: symbol, command: ["name": "go", "to": to]))
            }
            if !state.sidebar.recent.isEmpty { rows.append(Row(kind: .header, label: "Recent")) }
            for paper in state.sidebar.recent.prefix(5) {
                rows.append(Row(kind: .item, label: paper.title, symbol: "doc.text", command: ["name": "open", "id": paper.id]))
            }
        }
        if rows != items.map(\.row) {
            items = rows.map(Item.init)
            outline.reloadData()
        }
        if let selected {
            if outline.selectedRow != selected {
                outline.selectRowIndexes([selected], byExtendingSelection: false)
                outline.scrollRowToVisible(selected)
            }
        } else {
            outline.deselectAll(nil)
        }
        activity.show(state.activity)
    }

    @objc func showActivity() { send(["name": "activity"]) }

    // A click on any row, also the selected one, sends that row's command.
    @objc func clicked() { command(at: outline.clickedRow) }

    private func command(at row: Int) {
        guard let item = outline.item(atRow: row) as? Item, !item.row.command.isEmpty else { return }
        send(item.row.command)
    }

    // This replaces shouldSelectItem and sees only the reader's changes. A mouse proposal waits for the click's action.
    // An arrow key moves the selection and sends its row's command: the outline walks on to the next row when a key's
    // proposal is refused, so a refused row without a command, such as a header, is skipped.
    func outlineView(_ outlineView: NSOutlineView, selectionIndexesForProposedSelection proposed: IndexSet) -> IndexSet {
        guard ![.leftMouseDown, .leftMouseDragged, .leftMouseUp].contains(NSApp.currentEvent?.type), let row = proposed.first,
              let item = outlineView.item(atRow: row) as? Item, !item.row.command.isEmpty else { return outlineView.selectedRowIndexes }
        if row != outlineView.selectedRow { send(item.row.command) }
        return proposed
    }

    func outlineView(_ outlineView: NSOutlineView, rowViewForItem item: Any) -> NSTableRowView? { RowView() }
    func outlineView(_ outlineView: NSOutlineView, numberOfChildrenOfItem item: Any?) -> Int { item == nil ? items.count : 0 }
    func outlineView(_ outlineView: NSOutlineView, child index: Int, ofItem item: Any?) -> Any { items[index] }
    func outlineView(_ outlineView: NSOutlineView, isItemExpandable item: Any) -> Bool { false }
    func outlineView(_ outlineView: NSOutlineView, isGroupItem item: Any) -> Bool { (item as? Item)?.row.kind == .header }
    func outlineView(_ outlineView: NSOutlineView, heightOfRowByItem item: Any) -> CGFloat {
        switch (item as? Item)?.row.kind {
        case .paper: 58
        case .note: 44
        default: 28
        }
    }

    func outlineView(_ outlineView: NSOutlineView, viewFor tableColumn: NSTableColumn?, item: Any) -> NSView? {
        guard let row = (item as? Item)?.row else { return nil }
        let cell = NSTableCellView()
        let label = NSTextField(labelWithString: row.label)
        label.lineBreakMode = .byTruncatingTail
        label.toolTip = row.label
        cell.textField = label
        var views: [NSView] = []
        if let symbol = row.symbol, let image = NSImage(systemSymbolName: symbol, accessibilityDescription: nil) {
            let icon = NSImageView(image: image)
            icon.contentTintColor = outlineView.selectedRowIndexes.contains(outlineView.row(forItem: item)) ? nil : .secondaryLabelColor
            cell.imageView = icon
            views.append(icon)
        }
        switch row.kind {
        case .header:
            label.font = .systemFont(ofSize: 11, weight: .semibold)
            label.textColor = .secondaryLabelColor
            views.append(label)
        case .paper:
            label.font = .systemFont(ofSize: 13, weight: .semibold)
            label.maximumNumberOfLines = 2
            label.cell?.wraps = true
            label.cell?.truncatesLastVisibleLine = true
            let byline = secondary(row.detail, size: 11)
            let stack = NSStackView(views: [label, byline])
            stack.orientation = .vertical; stack.alignment = .leading; stack.spacing = 2
            views.append(stack)
        case .note:
            label.textColor = .secondaryLabelColor
            label.maximumNumberOfLines = 2
            label.cell?.wraps = true
            views.append(label)
        case .item where row.command["name"] == "outline":
            views.append(contentsOf: row.detail.isEmpty ? [label] : [secondary(row.detail, size: 13), label])
        case .item, .back:
            views.append(label)
            if !row.detail.isEmpty { views.append(contentsOf: [NSView(), secondary(row.detail, size: 12)]) }
        }
        label.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        let stack = NSStackView(views: views)
        stack.spacing = 6
        stack.translatesAutoresizingMaskIntoConstraints = false
        cell.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: cell.leadingAnchor, constant: 4 + CGFloat(row.level - 1) * 14),
            stack.trailingAnchor.constraint(equalTo: cell.trailingAnchor, constant: -6),
            stack.centerYAnchor.constraint(equalTo: cell.centerYAnchor)])
        return cell
    }

    private func secondary(_ text: String, size: CGFloat) -> NSTextField {
        let field = NSTextField(labelWithString: text)
        field.font = .monospacedDigitSystemFont(ofSize: size, weight: .regular)
        field.textColor = .secondaryLabelColor
        field.lineBreakMode = .byTruncatingTail
        field.setContentHuggingPriority(.required, for: .horizontal)
        return field
    }
}

// A source list tints every row's symbol with the accent. Only the selected row keeps it, so the accent marks the selection.
final class RowView: NSTableRowView {
    override var isSelected: Bool {
        // A new row view is selected before it holds its cell, and view(atColumn:) throws then; viewFor tints that cell.
        didSet { for case let cell as NSTableCellView in subviews { cell.imageView?.contentTintColor = isSelected ? nil : .secondaryLabelColor } }
    }
}

// The Activity line pinned under the outline: the first running job and a progress bar. An NSButton, for VoiceOver and the keyboard.
final class ActivityButton: NSButton {
    let label = NSTextField(labelWithString: "")
    let count = NSTextField(labelWithString: "")
    let progress = NSProgressIndicator()

    init() {
        super.init(frame: .zero)
        identifier = NSUserInterfaceItemIdentifier("activity")
        isBordered = false
        title = ""
        label.lineBreakMode = .byTruncatingTail
        label.font = .systemFont(ofSize: 12)
        label.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        count.font = .monospacedDigitSystemFont(ofSize: 12, weight: .regular)
        count.textColor = .secondaryLabelColor
        progress.style = .bar
        progress.controlSize = .small
        progress.minValue = 0; progress.maxValue = 1
        let line = NSStackView(views: [label, count])
        let stack = NSStackView(views: [line, progress])
        stack.orientation = .vertical; stack.alignment = .leading; stack.spacing = 4
        for view in [line, progress] { view.widthAnchor.constraint(equalTo: stack.widthAnchor, constant: -28).isActive = true }
        stack.edgeInsets = NSEdgeInsets(top: 10, left: 14, bottom: 12, right: 14)
        stack.translatesAutoresizingMaskIntoConstraints = false
        addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: leadingAnchor), stack.trailingAnchor.constraint(equalTo: trailingAnchor),
            stack.topAnchor.constraint(equalTo: topAnchor), stack.bottomAnchor.constraint(equalTo: bottomAnchor)])
    }
    required init?(coder: NSCoder) { nil }

    // The labels and the bar would take the click otherwise.
    override func hitTest(_ point: NSPoint) -> NSView? { super.hitTest(point) == nil ? nil : self }
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }

    func show(_ activity: ChromeState.Activity?) {
        isHidden = activity == nil
        guard let activity else { progress.stopAnimation(nil); return }
        label.stringValue = activity.label
        label.textColor = activity.failed ? .systemRed : .labelColor
        progress.isHidden = activity.failed
        toolTip = activity.label
        // A control's cell is its accessibility element.
        cell?.setAccessibilityLabel(activity.label)
        count.stringValue = activity.count > 1 ? String(activity.count) : ""
        progress.isIndeterminate = activity.progress == nil
        if let value = activity.progress { progress.doubleValue = value; progress.stopAnimation(nil) } else { progress.startAnimation(nil) }
    }
}
