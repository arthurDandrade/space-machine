// Lê texto de imagens com o Vision (macOS). Uso: ocr <img1> [img2 ...]  → uma linha JSON por imagem.
import Foundation
import Vision
import AppKit

for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        print("{\"arquivo\": \"\(path)\", \"erro\": true}"); continue
    }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = false
    try? VNImageRequestHandler(cgImage: cg).perform([req])
    var linhas: [[String: Any]] = []
    for obs in req.results ?? [] {
        if let c = obs.topCandidates(1).first, c.confidence > 0.3 {
            let b = obs.boundingBox
            linhas.append(["t": c.string, "x": b.minX, "y": 1 - b.maxY, "w": b.width, "h": b.height])
        }
    }
    let d: [String: Any] = ["arquivo": path, "linhas": linhas]
    if let j = try? JSONSerialization.data(withJSONObject: d), let s = String(data: j, encoding: .utf8) { print(s) }
}
