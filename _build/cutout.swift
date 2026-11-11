// Team photo cutout: puts the person on pure white and frames a 4:5 portrait (640x800).
// Uses Apple's built-in subject detection (Vision, macOS 14+). Called by _build/team_photos.py.
//
//   cutout <input image> <output.png> [--level]
//
// --level straightens a tilted head (e.g. a selfie): the photo is rotated so the eyes are level before the
// cutout and framing. team_photos.py passes it for names listed in LEVEL.
import Foundation
import Vision
import CoreImage
import CoreImage.CIFilterBuiltins
import AppKit

let args = CommandLine.arguments
guard args.count >= 3, var input = CIImage(contentsOf: URL(fileURLWithPath: args[1]), options: [.applyOrientationProperty: true]) else {
    print("usage: cutout <input> <output.png> [--level]"); exit(2)
}
if args.contains("--level") {
    let lm = VNDetectFaceLandmarksRequest()
    try VNImageRequestHandler(ciImage: input).perform([lm])
    if let f = lm.results?.max(by: { $0.boundingBox.height < $1.boundingBox.height }),
       let l = f.landmarks?.leftPupil?.normalizedPoints.first, let r = f.landmarks?.rightPupil?.normalizedPoints.first {
        // pupil points are relative to the face box; convert to image pixels (CI origin bottom-left)
        let e = input.extent, b = f.boundingBox
        let p1 = CGPoint(x: (b.minX + l.x * b.width) * e.width, y: (b.minY + l.y * b.height) * e.height)
        let p2 = CGPoint(x: (b.minX + r.x * b.width) * e.width, y: (b.minY + r.y * b.height) * e.height)
        let (a, c) = p1.x < p2.x ? (p1, p2) : (p2, p1)
        let angle = atan2(c.y - a.y, c.x - a.x)              // tilt of the eye line
        let mid = CGPoint(x: e.midX, y: e.midY)
        let t = CGAffineTransform(translationX: mid.x, y: mid.y).rotated(by: -angle).translatedBy(x: -mid.x, y: -mid.y)
        let rotated = input.transformed(by: t)
        input = rotated.composited(over: CIImage(color: .white).cropped(to: rotated.extent))
            .transformed(by: CGAffineTransform(translationX: -rotated.extent.minX, y: -rotated.extent.minY))
        print(String(format: "levelled by %.1f degrees", angle * 180 / .pi))
    }
}
let handler = VNImageRequestHandler(ciImage: input)
let req = VNGenerateForegroundInstanceMaskRequest()
try handler.perform([req])
guard let obs = req.results?.first else { print("no person found in photo"); exit(1) }
let maskBuf = try obs.generateScaledMaskForImage(forInstances: obs.allInstances, from: handler)
let mask = CIImage(cvPixelBuffer: maskBuf)

// Subject on white
let ext = input.extent
let blend = CIFilter.blendWithMask()
blend.inputImage = input
blend.backgroundImage = CIImage(color: .white).cropped(to: ext)
blend.maskImage = mask
let onWhite = blend.outputImage!.cropped(to: ext)

// Horizontal centre of the subject (mask columns with any coverage)
let ctx = CIContext()
let mcg = ctx.createCGImage(mask, from: mask.extent)!
let mw = mcg.width, mh = mcg.height
var px = [UInt8](repeating: 0, count: mw * mh)
let gray = CGContext(data: &px, width: mw, height: mh, bitsPerComponent: 8, bytesPerRow: mw,
                     space: CGColorSpaceCreateDeviceGray(), bitmapInfo: 0)!
gray.draw(mcg, in: CGRect(x: 0, y: 0, width: mw, height: mh))
var minX = mw, maxX = 0, minRow = mh
for y in 0..<mh { for x in 0..<mw where px[y * mw + x] > 128 {
    minX = min(minX, x); maxX = max(maxX, x); minRow = min(minRow, y) } }
let cx = CGFloat(minX + maxX) / 2 / CGFloat(mw) * ext.width
let headTop = CGFloat(minRow) / CGFloat(mh) * ext.height          // from the top of the photo

// 4:5 crop with the same headroom for everyone: the top of the head sits 8% below the top edge
var cropH = min(ext.height, (ext.height - headTop) / 0.92)
var cropW = cropH * 0.8
if cropW > ext.width { cropW = ext.width; cropH = cropW / 0.8 }
var top = max(0, min(ext.height - cropH, headTop - cropH * 0.08))   // distance from the top of the photo
var centerX = cx

// Wide shots (waist-up): if the face would fill less than 27% of the frame height, zoom in so it fills ~32%
// with its top ~21% from the frame top, like the head-and-shoulders portraits. Tighter photos are untouched.
let faceReq = VNDetectFaceRectanglesRequest()
try handler.perform([faceReq])
if let face = faceReq.results?.max(by: { $0.boundingBox.height < $1.boundingBox.height })?.boundingBox {
    let faceH = face.height * ext.height, faceTop = (1 - face.maxY) * ext.height
    // Levelled selfies are always framed head-and-shoulders (a bit tighter), which also leaves out the arms.
    let level = args.contains("--level")
    if faceH / cropH < 0.27 || level {
        cropH = min(ext.height, faceH / (level ? 0.35 : 0.32)); cropW = cropH * 0.8
        if cropW > ext.width { cropW = ext.width; cropH = cropW / 0.8 }
        top = max(0, min(ext.height - cropH, faceTop - cropH * 0.21))
        centerX = face.midX * ext.width
    }
}
let x0 = max(0, min(ext.width - cropW, centerX - cropW / 2))
let rect = CGRect(x: ext.minX + x0, y: ext.minY + ext.height - top - cropH, width: cropW, height: cropH)   // CI origin is bottom-left
let framed = onWhite.cropped(to: rect).transformed(by: CGAffineTransform(translationX: -rect.minX, y: -rect.minY))
let scale = 640 / cropW
let out = framed.transformed(by: CGAffineTransform(scaleX: scale, y: scale))
var cg = ctx.createCGImage(out, from: CGRect(x: 0, y: 0, width: 640, height: 800))!

// --mirror-left: for selfies where one arm is raised, rebuild the person's left side (frame right) as a mirror
// of the natural shoulder on the frame's left, across the centre of the face. Only the area beside the hair,
// below the chin, is replaced, so the face and hair stay untouched.
if args.contains("--mirror-left"), let face = faceReq.results?.max(by: { $0.boundingBox.height < $1.boundingBox.height })?.boundingBox {
    let W = 640, H = 800
    let buf = UnsafeMutablePointer<UInt8>.allocate(capacity: W * H * 4); buf.initialize(repeating: 0, count: W * H * 4)
    let bctx = CGContext(data: buf, width: W, height: H, bitsPerComponent: 8, bytesPerRow: W * 4,
                         space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
    bctx.draw(cg, in: CGRect(x: 0, y: 0, width: W, height: H))      // row 0 of buf = top of the image
    let axis = (face.midX * ext.width - x0) * scale                  // face centre, frame pixels
    let chin = Int(((1 - face.minY) * ext.height - top) * scale)     // bottom of the face box, from the top
    let src = Array(UnsafeBufferPointer(start: buf, count: W * H * 4))
    let luma = { (i: Int) -> Int in (Int(src[i]) * 3 + Int(src[i + 1]) * 6 + Int(src[i + 2])) / 10 }
    let eyeY = ((1 - face.midY) * ext.height - top) * scale, chinY = ((1 - face.minY) * ext.height - top) * scale
    let y0 = max(0, Int((eyeY + chinY) / 2))          // from mid-face down (catches a raised sleeve), faded in over 24 rows
    // the right hair strand's outer edge per row: first dark pixel scanning in from the right edge
    var edges = [Int](repeating: Int(axis), count: H)
    for y in y0..<H {
        for x in stride(from: W - 1, to: Int(axis), by: -1) where luma((y * W + x) * 4) < 110 { edges[y] = x; break }
    }
    for y in y0..<H {
        // work from 30 px inside the hair outwards; the face and neck further in are never touched
        let inner = max(Int(axis), edges[max(y0, y - 8)...min(H - 1, y + 8)].min()! - 30)
        let fade = min(1.0, Double(y - y0) / 24)
        for x in (inner + 1)..<W {
            let mx = Int((2 * axis - CGFloat(x)).rounded())
            let i = (y * W + x) * 4
            let m = mx >= 0 && mx < W ? (y * W + mx) * 4 : -1
            // hair (dark) stays on top; light pixels (sleeve, background) come from the mirrored left side
            let hair = max(0.0, min(1.0, Double(165 - luma(i)) / 60))
            let ramp = min(1.0, Double(x - inner) / 10)
            let t = (1 - hair) * fade * ramp
            for k in 0..<3 {
                let mv = m >= 0 ? Double(src[m + k]) : 255
                buf[i + k] = UInt8((Double(src[i + k]) * (1 - t) + mv * t).rounded())
            }
            buf[i + 3] = 255
        }
    }
    cg = bctx.makeImage()!
    print("mirrored the left shoulder across x=\(Int(axis)) from y=\(y0)")
}
// --widen <factor>: widen the body below the chin (face untouched) so the shoulders reach the frame edges like a
// normal portrait. The stretch eases in over the neck, so there is no visible seam.
if let wi = args.firstIndex(of: "--widen"), wi + 1 < args.count, let S = Double(args[wi + 1]),
   let face = faceReq.results?.max(by: { $0.boundingBox.height < $1.boundingBox.height })?.boundingBox {
    let W = 640, H = 800
    let buf = UnsafeMutablePointer<UInt8>.allocate(capacity: W * H * 4); buf.initialize(repeating: 0, count: W * H * 4)
    let wctx = CGContext(data: buf, width: W, height: H, bitsPerComponent: 8, bytesPerRow: W * 4,
                         space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
    wctx.draw(cg, in: CGRect(x: 0, y: 0, width: W, height: H))
    let src = Array(UnsafeBufferPointer(start: buf, count: W * H * 4))
    let axis = Double((face.midX * ext.width - x0) * scale)
    let chin = Double(((1 - face.minY) * ext.height - top) * scale)
    let ramp = 110.0
    for y in max(0, Int(chin))..<H {
        let u = min(1, (Double(y) - chin) / ramp), e = u * u * (3 - 2 * u)      // smoothstep
        let f = 1 + (S - 1) * e
        for x in 0..<W {
            let sx = axis + (Double(x) - axis) / f
            let x1 = max(0, min(W - 1, Int(sx.rounded(.down)))), x2 = min(W - 1, x1 + 1), w = sx - Double(x1)
            let i = (y * W + x) * 4, a = (y * W + x1) * 4, b = (y * W + x2) * 4
            for k in 0..<3 { buf[i + k] = UInt8((Double(src[a + k]) * (1 - w) + Double(src[b + k]) * w).rounded()) }
            buf[i + 3] = 255
        }
    }
    cg = wctx.makeImage()!
    print("widened below y=\(Int(chin)) by \(S)")
}
try NSBitmapImageRep(cgImage: cg).representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: args[2]))
print("ok")
