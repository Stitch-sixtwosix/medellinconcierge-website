// Builds the 1200x630 link-preview images (WhatsApp, Facebook, LinkedIn, X):
//   swiftc _build/share_card.swift -o /tmp/sharecard -sdk <MacOSX14 SDK> && /tmp/sharecard   ->  assets/share-en.jpg, assets/share-es.jpg
// White card, the full logo, one line about the company, the domain, and a red base bar.
import AppKit

let W = 1200.0, H = 630.0
let logo = NSImage(contentsOfFile: "assets/logo.png")!
let red = NSColor(srgbRed: 0.871, green: 0, blue: 0.004, alpha: 1)
let ink = NSColor(srgbRed: 0.11, green: 0.11, blue: 0.11, alpha: 1)
let muted = NSColor(srgbRed: 0.36, green: 0.36, blue: 0.36, alpha: 1)

func card(_ line: String, _ out: String) {
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: Int(W), pixelsHigh: Int(H), bitsPerSample: 8,
                               samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB,
                               bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    NSColor.white.setFill(); NSRect(x: 0, y: 0, width: W, height: H).fill()
    red.setFill(); NSRect(x: 0, y: 0, width: W, height: 18).fill()
    let lw = 720.0, lh = lw * 189 / 640
    logo.draw(in: NSRect(x: (W - lw) / 2, y: 290, width: lw, height: lh))
    let para = NSMutableParagraphStyle(); para.alignment = .center
    func text(_ s: String, _ size: CGFloat, _ weight: NSFont.Weight, _ color: NSColor, _ y: Double) {
        let a: [NSAttributedString.Key: Any] = [.font: NSFont.systemFont(ofSize: size, weight: weight),
                                                .foregroundColor: color, .paragraphStyle: para]
        NSAttributedString(string: s, attributes: a).draw(in: NSRect(x: 60, y: y, width: W - 120, height: size * 1.4))
    }
    text(line, 40, .semibold, ink, 180)
    text("medellinconcierge.net", 28, .regular, muted, 110)
    NSGraphicsContext.restoreGraphicsState()
    let jpg = rep.representation(using: .jpeg, properties: [.compressionFactor: 0.88])!
    try! jpg.write(to: URL(fileURLWithPath: out))
}
card("Property management in Medellín", "assets/share-en.jpg")
card("Administración de propiedades en Medellín", "assets/share-es.jpg")
