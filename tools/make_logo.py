"""Generate the Plain logo: assets/logo.svg (vector) and assets/icon.png (512x512).

The design is pure geometry so both files match exactly: a rounded square with
an indigo-to-violet gradient, a white speech bubble (Plain is written in
English words), and inside it two rounded bars and a period - an abstract
Plain sentence, ending the way every Plain statement must.

The PNG is rasterised and written with the standard library alone (zlib and
struct), so the whole project keeps zero dependencies.

Run from the project root:  python3 tools/make_logo.py
"""

import os
import struct
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#4F46E5"/>
      <stop offset="1" stop-color="#9333EA"/>
    </linearGradient>
  </defs>
  <rect x="16" y="16" width="480" height="480" rx="116" fill="url(#bg)"/>
  <path d="M256 92 C 146 92 60 166 60 260 C 60 354 146 428 256 428 C 285 428 312 423 337 413 L 424 452 L 402 364 C 441 335 452 299 452 260 C 452 166 366 92 256 92 Z" fill="#FFFFFF"/>
  <rect x="112" y="233" width="130" height="52" rx="26" fill="#4F46E5"/>
  <rect x="266" y="233" width="86" height="52" rx="26" fill="#4F46E5"/>
  <circle cx="390" cy="259" r="27" fill="#4F46E5"/>
</svg>
"""

TOP = (79, 70, 229)
BOTTOM = (147, 51, 234)
INDIGO = (79, 70, 229)
WHITE = (255, 255, 255)
SAMPLES = ((0.25, 0.25), (0.25, 0.75), (0.75, 0.25), (0.75, 0.75))


def _in_rounded_rect(x, y, x0, y0, x1, y1, r):
    cx = min(max(x, x0 + r), x1 - r)
    cy = min(max(y, y0 + r), y1 - r)
    dx = x - cx
    dy = y - cy
    return dx * dx + dy * dy <= r * r


def _in_ellipse(x, y, cx, cy, a, b):
    dx = (x - cx) / a
    dy = (y - cy) / b
    return dx * dx + dy * dy <= 1.0


def _in_circle(x, y, cx, cy, r):
    dx = x - cx
    dy = y - cy
    return dx * dx + dy * dy <= r * r


def _in_triangle(x, y, ax, ay, bx, by, cx, cy):
    d1 = (x - bx) * (ay - by) - (ax - bx) * (y - by)
    d2 = (x - cx) * (by - cy) - (bx - cx) * (y - cy)
    d3 = (x - ax) * (cy - ay) - (cx - ax) * (y - ay)
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))


def _sample(u, v):
    if _in_rounded_rect(u, v, 112.0, 233.0, 242.0, 285.0, 26.0) or \
       _in_rounded_rect(u, v, 266.0, 233.0, 352.0, 285.0, 26.0) or \
       _in_circle(u, v, 390.0, 259.0, 27.0):
        return INDIGO
    if _in_ellipse(u, v, 256.0, 260.0, 196.0, 168.0) or \
       _in_triangle(u, v, 337.0, 400.0, 424.0, 452.0, 402.0, 352.0):
        return WHITE
    t = v / 511.0
    return tuple(round(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3))


def draw_png(path, size=512):
    scale = size / 512.0
    rows = []
    for y in range(size):
        row = bytearray()
        for x in range(size):
            r = g = b = a = 0
            for ox, oy in SAMPLES:
                u = (x + ox) / scale
                v = (y + oy) / scale
                if not _in_rounded_rect(u, v, 16.0, 16.0, 496.0, 496.0, 116.0):
                    continue
                color = _sample(u, v)
                r += color[0]
                g += color[1]
                b += color[2]
                a += 255
            count = len(SAMPLES)
            if a:
                row += bytes((round(r / count), round(g / count), round(b / count), round(a / count)))
            else:
                row += b"\x00\x00\x00\x00"
        rows.append(bytes(row))
    _write_png(path, size, rows)


def _png_chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def _write_png(path, width, rows):
    header = struct.pack(">IIBBBBB", width, len(rows), 8, 6, 0, 0, 0)
    raw = b"".join(b"\x00" + row for row in rows)
    with open(path, "wb") as handle:
        handle.write(b"\x89PNG\r\n\x1a\n")
        handle.write(_png_chunk(b"IHDR", header))
        handle.write(_png_chunk(b"IDAT", zlib.compress(raw, 9)))
        handle.write(_png_chunk(b"IEND", b""))


def main():
    os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
    svg_path = os.path.join(ROOT, "assets", "logo.svg")
    png_path = os.path.join(ROOT, "assets", "icon.png")
    with open(svg_path, "w", encoding="utf-8") as handle:
        handle.write(SVG)
    draw_png(png_path)
    print("wrote", svg_path)
    print("wrote", png_path)


if __name__ == "__main__":
    main()
