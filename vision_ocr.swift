// macOS 標準の文字認識（Vision フレームワーク）で画像の文字を読み取る。
//
//   vision_ocr <画像> [<画像> ...]
//
// 画像ごとに 1 行の JSON を標準出力へ書く:
//   {"file": "...", "lines": [{"text": "...", "conf": 0.98, "box": [x, y, w, h]}, ...]}
// box は画像に対する比率（左上原点）。行は上から下、同じ高さなら左から右の順に並べる。
// LLM と違い読み取れない字を作らないので、講義資料の文字起こしに使う（extract_pdf.py が呼ぶ）。
import Foundation
import Vision
import ImageIO

struct Line: Codable { let text: String; let conf: Float; let box: [Double] }
struct Page: Codable { let file: String; let lines: [Line]; let error: String? }

func recognize(_ path: String) -> Page {
    let url = URL(fileURLWithPath: path)
    guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
          let image = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
        return Page(file: path, lines: [], error: "画像を開けない")
    }
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["ja-JP", "en-US"]
    request.usesLanguageCorrection = true
    do {
        try VNImageRequestHandler(cgImage: image, options: [:]).perform([request])
    } catch {
        return Page(file: path, lines: [], error: "\(error)")
    }
    var lines: [Line] = []
    for obs in request.results ?? [] {
        guard let top = obs.topCandidates(1).first else { continue }
        let b = obs.boundingBox  // 左下原点の比率 → 左上原点へ直す
        lines.append(Line(text: top.string, conf: top.confidence,
                          box: [b.origin.x, 1 - b.origin.y - b.height, b.width, b.height]))
    }
    // 上から下へ。行の高さの半分より近い差は同じ行とみなし、左から右へ
    lines.sort { a, c in
        let tol = min(a.box[3], c.box[3]) / 2
        if abs(a.box[1] - c.box[1]) > tol { return a.box[1] < c.box[1] }
        return a.box[0] < c.box[0]
    }
    return Page(file: path, lines: lines, error: nil)
}

let args = Array(CommandLine.arguments.dropFirst())
if args.isEmpty {
    FileHandle.standardError.write("usage: vision_ocr <image> [<image> ...]\n".data(using: .utf8)!)
    exit(2)
}
let encoder = JSONEncoder()
for path in args {
    let data = try encoder.encode(recognize(path))
    FileHandle.standardOutput.write(data)
    FileHandle.standardOutput.write("\n".data(using: .utf8)!)
}
