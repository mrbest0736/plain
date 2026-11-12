"""Generate the Plain logo: assets/logo.svg (vector) and assets/icon.png (512x512).

The design is pure geometry so both files match exactly: a rounded square with
an indigo-to-violet gradient, a white speech bubble (Plain is written in
English words), and inside it two rounded bars and a period — an abstract
Plain sentence, ending the way every Plain statement must.

Run from the project root:  python3 tools/make_logo.py
"""

import os

from PIL import Image, ImageDraw

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

INDIGO = (79, 70, 229, 255)


def draw_png(path, size=512):
    scale = size / 512.0
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def box(x0, y0, x1, y1):
        return [v * scale for v in (x0, y0, x1, y1)]

    gradient = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    top = (79, 70, 229)
    bottom = (147, 51, 234)
    for y in range(size):
        t = y / max(1, size - 1)
        color = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,)
        for x in range(size):
            gradient.putpixel((x, y), color)
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(box(16, 16, 496, 496), radius=round(116 * scale), fill=255)
    image.paste(gradient, (0, 0), mask)

    draw.ellipse(box(60, 92, 452, 428), fill=(255, 255, 255, 255))
    draw.polygon([pt * scale for pt in (337, 400, 424, 452, 402, 352)], fill=(255, 255, 255, 255))

    draw.rounded_rectangle(box(112, 233, 242, 285), radius=26 * scale, fill=INDIGO)
    draw.rounded_rectangle(box(266, 233, 352, 285), radius=26 * scale, fill=INDIGO)
    draw.ellipse(box(363, 232, 417, 286), fill=INDIGO)

    image.save(path, "PNG")


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
