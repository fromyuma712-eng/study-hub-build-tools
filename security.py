# -*- coding: utf-8 -*-
"""配信物に付ける保護ヘッダ（Cloudflare Pages の _headers）と robots.txt を書き出す。

Cloudflare Access（本人のメールだけ許可）が一次の防御で、ここは多層防御の二次。
- 検索エンジンに載せない（X-Robots-Tag・robots.txt。各頁の meta robots と二重）
- 外部の資源は、使っているもの（Google Fonts と MathJax の CDN）だけに限る（CSP）。入力欄からの外部送信（connect-src・form-action）と、頁の埋め込み（frame-ancestors）を禁じる
- リファラを出さない、MIME の推測をさせない、カメラ等の機能を使わせない
`unsafe-inline` は、講義まとめが単一HTMLで CSS・JS を頁内に持つ設計のため外せない。自前配信（フォント・MathJax）にできれば外部ホストの許可も外せる。
"""
import os

import atomicio

CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' data: https://fonts.gstatic.com https://cdn.jsdelivr.net",
    "img-src 'self' data: blob:",
    "connect-src 'self'",
    "worker-src 'self'",
    "manifest-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'none'",
    "frame-ancestors 'none'",
])

HEADERS = [
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "no-referrer"),
    ("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=(), serial=(), interest-cohort=()"),
    ("Cross-Origin-Opener-Policy", "same-origin"),
    ("Cross-Origin-Resource-Policy", "same-origin"),
    ("X-Robots-Tag", "noindex, nofollow, noarchive, nosnippet"),
    ("Content-Security-Policy", CSP),
]


def headers_text():
    return "/*\n" + "".join("  %s: %s\n" % h for h in HEADERS)


def write_security_files(public_dir):
    atomicio.write_text(os.path.join(public_dir, "_headers"), headers_text())
    atomicio.write_text(os.path.join(public_dir, "robots.txt"), "User-agent: *\nDisallow: /\n")
    print("security -> public/_headers, robots.txt")


if __name__ == "__main__":
    write_security_files(os.path.join(os.path.dirname(os.path.abspath(__file__)), "public"))
