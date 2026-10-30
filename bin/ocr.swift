// ocr — Vision OCR da riga di comando.
// Uso:   ocr <immagine> [lingua...]        (default: it-IT en-US)
// Esce:  JSON su stdout { "text": "...", "lines": [{text, conf, box}] }
// Nota:  usa VNRecognizeTextRequest .accurate, nessun modello da scaricare.

import AppKit
import Foundation
import Vision

let args = CommandLine.arguments
guard args.count >= 2 else {
    FileHandle.standardError.write("uso: ocr <immagine> [lingua...]\n".data(using: .utf8)!)
    exit(2)
}
let path = args[1]
let langs = args.count > 2 ? Array(args[2...]) : ["it-IT", "en-US"]

guard let image = NSImage(contentsOfFile: path),
      let tiff = image.tiffRepresentation,
      let bitmap = NSBitmapImageRep(data: tiff),
      let cg = bitmap.cgImage else {
    FileHandle.standardError.write("immagine non leggibile: \(path)\n".data(using: .utf8)!)
    exit(1)
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = langs
request.usesLanguageCorrection = true
// codice/tool/URL: niente filtri aggressivi
request.minimumTextHeight = 0.008

let handler = VNImageRequestHandler(cgImage: cg, options: [:])
do {
    try handler.perform([request])
} catch {
    FileHandle.standardError.write("OCR fallito: \(error)\n".data(using: .utf8)!)
    exit(1)
}

struct Line: Codable {
    let text: String
    let conf: Float
    let x: Double
    let y: Double
}
struct Out: Codable {
    let text: String
    let lines: [Line]
}

var lines: [Line] = []
for obs in (request.results ?? []) {
    guard let best = obs.topCandidates(1).first else { continue }
    let b = obs.boundingBox
    // coordinate Vision: origine in basso a sinistra -> y dall'alto
    lines.append(Line(text: best.string,
                      conf: best.confidence,
                      x: Double(b.minX),
                      y: Double(1.0 - b.maxY)))
}
// ordine di lettura: righe (tolleranza), poi sinistra->destra
lines.sort { a, b in
    if abs(a.y - b.y) > 0.012 { return a.y < b.y }
    return a.x < b.x
}
let text = lines.map { $0.text }.joined(separator: "\n")
let out = Out(text: text, lines: lines)
let enc = JSONEncoder()
enc.outputFormatting = [.sortedKeys]
if let data = try? enc.encode(out), let s = String(data: data, encoding: .utf8) {
    print(s)
} else {
    print("{\"text\":\"\",\"lines\":[]}")
}
