import Cocoa

// The Aa popover: Reading preferences. Each change sends `prefs` with one field; the Chrome state sets the controls.
final class ReadingPopover: NSViewController {
    // The values and colours are app/static/appearance.js's and app.css's.
    static let themes: [(value: String, label: String, colours: [(paper: NSColor, label: NSColor)])] = [
        ("light", "Light", [(.white, NSColor(hex: 0x1d1d1f))]),
        ("sepia", "Sepia", [(NSColor(hex: 0xf8f2e6), NSColor(hex: 0x3a2f22))]),
        ("dark", "Dark", [(NSColor(hex: 0x1e1e1e), NSColor(hex: 0xf2f2f4))]),
        ("system", "Match System", [(.white, NSColor(hex: 0x1d1d1f)), (NSColor(hex: 0x1e1e1e), NSColor(hex: 0xf2f2f4))])]
    static let fonts: [(value: String, label: String, font: NSFont?)] = [
        ("new-york", "New York", NSFont.systemFont(ofSize: 14).fontDescriptor.withDesign(.serif).flatMap { NSFont(descriptor: $0, size: 14) }),
        ("charter", "Charter", NSFont(name: "Charter-Roman", size: 14)),
        ("iowan", "Iowan Old Style", NSFont(name: "IowanOldStyle-Roman", size: 14)),
        ("palatino", "Palatino", NSFont(name: "Palatino-Roman", size: 14)),
        ("sf-pro", "SF Pro", NSFont.systemFont(ofSize: 14))]
    static let widths = ["short", "medium", "long"], spacings = ["compact", "normal", "relaxed"]

    var send: ([String: Any]) -> Void = { _ in }
    private var prefs = ChromeState.Prefs()
    private var swatches: [NSButton] = []
    private let font = NSPopUpButton()
    private let size = NSSlider(value: 18, minValue: 15, maxValue: 26, target: nil, action: nil)
    private let sizeValue = NSTextField(labelWithString: "")
    private let width = NSSegmentedControl(labels: ["Short", "Medium", "Long"], trackingMode: .selectOne, target: nil, action: nil)
    private let spacing = NSSegmentedControl(labels: ["Compact", "Normal", "Relaxed"], trackingMode: .selectOne, target: nil, action: nil)

    override func loadView() {
        let swatchRow = NSStackView(views: Self.themes.map { theme in
            let button = NSButton(image: Self.swatch(theme.colours), target: self, action: #selector(chooseTheme(_:)))
            button.identifier = NSUserInterfaceItemIdentifier("theme-" + theme.value)
            button.isBordered = false
            button.setAccessibilityLabel(theme.label)
            button.wantsLayer = true
            button.layer?.cornerRadius = 9
            button.layer?.masksToBounds = true
            swatches.append(button)
            let caption = NSTextField(labelWithString: theme.label)
            caption.font = .systemFont(ofSize: 11)
            caption.allowsDefaultTighteningForTruncation = true
            caption.textColor = .secondaryLabelColor
            let column = NSStackView(views: [button, caption])
            column.orientation = .vertical; column.spacing = 4
            return column
        })
        swatchRow.distribution = .fillEqually
        for option in Self.fonts {
            font.addItem(withTitle: option.label)
            font.lastItem?.representedObject = option.value
            if let face = option.font { font.lastItem?.attributedTitle = NSAttributedString(string: option.label, attributes: [.font: face]) }
        }
        font.identifier = NSUserInterfaceItemIdentifier("font")
        font.target = self; font.action = #selector(chooseFont(_:))
        size.identifier = NSUserInterfaceItemIdentifier("size")
        size.numberOfTickMarks = 12
        size.allowsTickMarkValuesOnly = true
        size.target = self; size.action = #selector(chooseSize(_:))
        sizeValue.font = .monospacedDigitSystemFont(ofSize: 12, weight: .regular)
        sizeValue.textColor = .secondaryLabelColor
        let sizeRow = NSStackView(views: [size, sizeValue])
        for (control, name) in [(width, "width"), (spacing, "spacing")] {
            control.identifier = NSUserInterfaceItemIdentifier(name)
            control.segmentDistribution = .fillEqually
            control.target = self; control.action = #selector(chooseSegment(_:))
        }
        let stack = NSStackView(views: [heading("Theme"), swatchRow, heading("Font"), font, heading("Text size"), sizeRow,
                                        heading("Line length"), width, heading("Line spacing"), spacing])
        stack.orientation = .vertical
        stack.alignment = .leading
        stack.spacing = 8
        for view in [swatchRow, font, sizeRow, width] { stack.setCustomSpacing(16, after: view) }
        stack.edgeInsets = NSEdgeInsets(top: 16, left: 16, bottom: 16, right: 16)
        stack.widthAnchor.constraint(equalToConstant: 320).isActive = true
        for view in [swatchRow, font, sizeRow, width, spacing] { view.widthAnchor.constraint(equalTo: stack.widthAnchor, constant: -32).isActive = true }
        view = stack
        show()
    }

    func apply(_ prefs: ChromeState.Prefs) {
        self.prefs = prefs
        if isViewLoaded { show() }
    }

    private func show() {
        for (button, theme) in zip(swatches, Self.themes) {
            let chosen = theme.value == prefs.theme
            button.state = chosen ? .on : .off
            button.layer?.borderWidth = chosen ? 2.5 : 1
            button.layer?.borderColor = (chosen ? NSColor.controlAccentColor : NSColor.separatorColor).cgColor
        }
        font.selectItem(at: Self.fonts.firstIndex { $0.value == prefs.font } ?? 0)
        size.integerValue = prefs.size
        sizeValue.stringValue = "\(prefs.size) px"
        width.selectedSegment = Self.widths.firstIndex(of: prefs.width) ?? 1
        spacing.selectedSegment = Self.spacings.firstIndex(of: prefs.spacing) ?? 1
    }

    private func heading(_ text: String) -> NSTextField {
        let field = NSTextField(labelWithString: text)
        field.font = .systemFont(ofSize: 11, weight: .semibold)
        field.textColor = .secondaryLabelColor
        return field
    }

    // A swatch is "Aa" on the theme's paper; Match System is half Light, half Dark.
    private static func swatch(_ colours: [(paper: NSColor, label: NSColor)]) -> NSImage {
        NSImage(size: NSSize(width: 60, height: 40), flipped: false) { rect in
            let text = NSAttributedString(string: "Aa", attributes: [.font: NSFont(descriptor: NSFont.systemFont(ofSize: 17, weight: .semibold).fontDescriptor.withDesign(.serif)!, size: 17)!])
            let origin = NSPoint(x: rect.midX - text.size().width / 2, y: rect.midY - text.size().height / 2)
            for (index, colour) in colours.enumerated() {
                let part = NSRect(x: rect.width * CGFloat(index) / CGFloat(colours.count), y: 0, width: rect.width / CGFloat(colours.count), height: rect.height)
                NSGraphicsContext.saveGraphicsState()
                part.clip()
                colour.paper.setFill(); part.fill()
                NSAttributedString(string: "Aa", attributes: text.attributes(at: 0, effectiveRange: nil).merging([.foregroundColor: colour.label]) { $1 }).draw(at: origin)
                NSGraphicsContext.restoreGraphicsState()
            }
            return true
        }
    }

    @objc func chooseTheme(_ sender: NSButton) {
        guard let index = swatches.firstIndex(of: sender) else { return }
        send(["name": "prefs", "patch": ["theme": Self.themes[index].value]])
    }
    @objc func chooseFont(_ sender: NSPopUpButton) {
        guard let value = sender.selectedItem?.representedObject as? String else { return }
        send(["name": "prefs", "patch": ["font": value]])
    }
    @objc func chooseSize(_ sender: NSSlider) {
        sizeValue.stringValue = "\(sender.integerValue) px"
        send(["name": "prefs", "patch": ["size": sender.integerValue]])
    }
    @objc func chooseSegment(_ sender: NSSegmentedControl) {
        let (field, values) = sender === width ? ("width", Self.widths) : ("spacing", Self.spacings)
        guard values.indices.contains(sender.selectedSegment) else { return }
        send(["name": "prefs", "patch": [field: values[sender.selectedSegment]]])
    }
}

extension NSColor {
    convenience init(hex: Int) {
        self.init(srgbRed: CGFloat(hex >> 16 & 0xff) / 255, green: CGFloat(hex >> 8 & 0xff) / 255, blue: CGFloat(hex & 0xff) / 255, alpha: 1)
    }
}
