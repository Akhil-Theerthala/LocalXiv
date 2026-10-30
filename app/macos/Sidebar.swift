import Cocoa

// The source-list sidebar. Library mode: Home, LIBRARY, and RECENT. Reader mode: back, the Paper, and CONTENTS.
// A click or an arrow key selects its row at once and sends the row's command. The page posts its Chrome state after
// each command, also one that it drops or that changes nothing, and that state corrects the selection.
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
    // A click's command, with a callback once the page has run it.
    var sendClick: ([String: Any], @escaping () -> Void) -> Void = { $1() }
    let outline = NSOutlineView()
    let activity = ActivityButton()
    private var items: [Item] = []
    // The widest section number at each outline level, and the last width of the outline.
    private var widest: [Int: String] = [:], width: CGFloat = 0
    // A click holds its row from mouse-down until the page has run the row's command, so a state that the page posts
    // before then, such as the one for the focus that the click takes from a page field, does not select the old row.
    // `clicks` tells the callback of an older click from the current one.
    private var held: Int?, clicks = 0

    override func loadView() {
        outline.style = .sourceList
        outline.headerView = nil
        outline.floatsGroupRows = false
        // Ordinary rows take their height, font, and symbol size from the sidebar icon size in System Settings.
        outline.rowSizeStyle = .default
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
        // The Activity line is a bottom accessory of the sidebar item (Shell.swift), so the outline scrolls under it.
        activity.target = self; activity.action = #selector(showActivity)
        activity.isHidden = true
        view = scroll
    }

    // A new outline width, from the sidebar width or from a scroller that shows or hides, can change which outline
    // entries need a second line.
    override func viewDidLayout() {
        super.viewDidLayout()
        measureRows()
    }
    func outlineViewColumnDidResize(_ notification: Notification) { measureRows() }
    private func measureRows() {
        guard outline.bounds.width != width else { return }
        width = outline.bounds.width
        outline.noteHeightOfRows(withIndexesChanged: IndexSet(integersIn: 0..<outline.numberOfRows))
    }

    func apply(_ state: ChromeState) {
        loadViewIfNeeded()
        var rows: [Row] = [], selected: Int?
        widest = [:]
        if let reader = state.sidebar.reader {
            rows.append(Row(kind: .back, label: reader.back, symbol: "chevron.left", command: ["name": "leave"]))
            rows.append(Row(kind: .paper, label: reader.title, detail: reader.byline))
            // A view with no outline shows no Contents group.
            if !reader.outline.isEmpty { rows.append(Row(kind: .header, label: "Contents")) }
            for entry in reader.outline {
                // An entry with no id is a note, such as "A PDF has no sections.".
                if entry.id.isEmpty { rows.append(Row(kind: .note, label: entry.label)); continue }
                if entry.current { selected = rows.count }
                let level = min(max(entry.level, 1), 3)
                if !entry.number.isEmpty, numberWidth(entry.number, size: 13) > numberWidth(widest[level] ?? "", size: 13) { widest[level] = entry.number }
                rows.append(Row(kind: .item, label: entry.label, detail: entry.number, level: level, command: ["name": "outline", "id": entry.id]))
            }
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
        if let row = held ?? selected {
            if outline.selectedRow != row {
                outline.selectRowIndexes([row], byExtendingSelection: false)
                outline.scrollRowToVisible(row)
            }
        } else {
            outline.deselectAll(nil)
        }
        activity.show(state.activity)
        // As under an AppKit sheet, a modal web dialog keeps the sidebar's look and blocks only its input.
        outline.isEnabled = !state.modal
        activity.isEnabled = !state.modal
    }

    @objc func showActivity() { send(["name": "activity"]) }

    // A click on any row, also the selected one, sends that row's command.
    @objc func clicked() {
        let row = outline.clickedRow
        guard let item = outline.item(atRow: row) as? Item, !item.row.command.isEmpty else { held = nil; return }
        held = row; clicks += 1
        let click = clicks
        sendClick(item.row.command) { [weak self] in if self?.clicks == click { self?.held = nil } }
    }

    // This replaces shouldSelectItem and sees only the reader's changes. A click's command goes from clicked(), and a
    // drag does not move the selection. An arrow key moves the selection and sends its row's command: the outline
    // walks on to the next row when a key's proposal is refused, so a refused row without a command, such as a header,
    // is skipped.
    func outlineView(_ outlineView: NSOutlineView, selectionIndexesForProposedSelection proposed: IndexSet) -> IndexSet {
        let event = NSApp.currentEvent?.type
        guard event != .leftMouseDragged, let row = proposed.first,
              let item = outlineView.item(atRow: row) as? Item, !item.row.command.isEmpty else { return outlineView.selectedRowIndexes }
        switch event {
        case .leftMouseDown: held = row; clicks += 1
        case .leftMouseUp: break
        default: held = nil; if row != outlineView.selectedRow { send(item.row.command) }
        }
        return proposed
    }

    func outlineView(_ outlineView: NSOutlineView, rowViewForItem item: Any) -> NSTableRowView? { RowView() }
    func outlineView(_ outlineView: NSOutlineView, numberOfChildrenOfItem item: Any?) -> Int { item == nil ? items.count : 0 }
    func outlineView(_ outlineView: NSOutlineView, child index: Int, ofItem item: Any?) -> Any { items[index] }
    func outlineView(_ outlineView: NSOutlineView, isItemExpandable item: Any) -> Bool { false }
    func outlineView(_ outlineView: NSOutlineView, isGroupItem item: Any) -> Bool { (item as? Item)?.row.kind == .header }
    func outlineView(_ outlineView: NSOutlineView, heightOfRowByItem item: Any) -> CGFloat {
        guard let row = (item as? Item)?.row else { return outlineView.rowHeight }
        switch row.kind {
        case .paper: return 58
        case .note: return 44
        // An outline entry that does not fit on one line, such as a Blog question, gets a second line.
        // The 44 pt are the row and cell insets and the label padding (about 38 pt at 250 pt, j1-18-blog.png), plus a
        // margin. A width that is too large wraps a label in a one-line row and clips it.
        case .item where row.command["name"] == "outline" && outlineView.bounds.width > 0:
            let number = widest[row.level].map { numberWidth($0, size: labelSize) + 6 } ?? 0
            let width = outlineView.bounds.width - CGFloat(row.level - 1) * 14 - number - 44
            let height = (row.label as NSString).boundingRect(with: NSSize(width: width, height: .greatestFiniteMagnitude), options: .usesLineFragmentOrigin,
                                                             attributes: [.font: NSFont.systemFont(ofSize: labelSize)]).height
            return height > labelSize * 1.5 ? outlineView.rowHeight + ceil(labelSize * 1.25) : outlineView.rowHeight
        default: return outlineView.rowHeight
        }
    }

    func outlineView(_ outlineView: NSOutlineView, viewFor tableColumn: NSTableColumn?, item: Any) -> NSView? {
        guard let row = (item as? Item)?.row else { return nil }
        let cell = NSTableCellView()
        let label = NSTextField(labelWithString: row.label)
        label.lineBreakMode = .byTruncatingTail
        label.toolTip = row.label
        // The row size style sets the font of the cell's text field, so the header and the Paper keep theirs outside it.
        // It makes the label 11, 13, or 15 pt at Small, Medium, or Large. A section number takes the same size, and a
        // count 1 pt less.
        if ![.header, .paper].contains(row.kind) { cell.textField = label }
        let size = labelSize
        var views: [NSView] = []
        if let symbol = row.symbol, let image = NSImage(systemSymbolName: symbol, accessibilityDescription: nil) {
            let icon = NSImageView(image: image)
            icon.contentTintColor = outlineView.selectedRowIndexes.contains(outlineView.row(forItem: item)) ? nil : .secondaryLabelColor
            // Each symbol is centred in one fixed column, 18, 21, or 24 pt wide, so all labels start at one edge.
            icon.symbolConfiguration = NSImage.SymbolConfiguration(pointSize: size, weight: .regular)
            icon.imageAlignment = .alignCenter
            icon.widthAnchor.constraint(equalToConstant: (size * 1.6).rounded()).isActive = true
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
            // Each level has one number column, as wide as its widest number. The numbers align right, so "9" and "10"
            // give one label edge, and an entry with no number, such as the Abstract, keeps the column.
            if let widest = widest[row.level] {
                let number = secondary(row.detail, size: size)
                number.alignment = .right
                number.setContentHuggingPriority(.defaultLow, for: .horizontal)
                number.widthAnchor.constraint(equalToConstant: numberWidth(widest, size: size)).isActive = true
                views.append(number)
            }
            label.maximumNumberOfLines = 2
            label.cell?.wraps = true
            label.cell?.truncatesLastVisibleLine = true
            views.append(label)
        case .item, .back:
            views.append(label)
            if !row.detail.isEmpty { views.append(contentsOf: [NSView(), secondary(row.detail, size: size - 1)]) }
        }
        label.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        let stack = NSStackView(views: views)
        stack.spacing = 6
        // A section number sits on the first line of an entry that wraps.
        if row.command["name"] == "outline" { stack.alignment = .firstBaseline }
        stack.translatesAutoresizingMaskIntoConstraints = false
        cell.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: cell.leadingAnchor, constant: 4 + CGFloat(row.level - 1) * 14),
            stack.trailingAnchor.constraint(equalTo: cell.trailingAnchor, constant: -6),
            stack.centerYAnchor.constraint(equalTo: cell.centerYAnchor)])
        return cell
    }

    private var labelSize: CGFloat { [.small: 11, .large: 15][outline.effectiveRowSizeStyle] ?? 13 }
    private func numberWidth(_ text: String, size: CGFloat) -> CGFloat { secondary(text, size: size).intrinsicContentSize.width }

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
    private let warning = NSImageView()
    // Hidden, the accessory folds to no height.
    weak var accessory: NSSplitViewItemAccessoryViewController?

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
        // A failed job shows a red symbol, because red text at 12 pt is under 4.5:1.
        warning.image = NSImage(systemSymbolName: "exclamationmark.triangle.fill", accessibilityDescription: nil)
        warning.symbolConfiguration = NSImage.SymbolConfiguration(pointSize: 12, weight: .regular)
        warning.contentTintColor = .systemRed
        let line = NSStackView(views: [warning, label, count])
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
        if accessory?.isHidden != isHidden { accessory?.isHidden = isHidden }
        guard let activity else { progress.stopAnimation(nil); return }
        label.stringValue = activity.label
        warning.isHidden = !activity.failed
        progress.isHidden = activity.failed
        toolTip = activity.label
        // A control's cell is its accessibility element.
        cell?.setAccessibilityLabel(activity.label)
        count.stringValue = activity.count > 1 ? String(activity.count) : ""
        progress.isIndeterminate = activity.progress == nil
        if let value = activity.progress { progress.doubleValue = value; progress.stopAnimation(nil) } else { progress.startAnimation(nil) }
    }
}
