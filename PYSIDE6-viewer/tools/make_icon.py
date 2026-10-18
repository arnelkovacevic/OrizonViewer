"""Genera assets/orizon.ico (16/32/48/64/128/256) partendo dal simbolo Orizon.

Uso:  python tools/make_icon.py [sfondo]     (default #FFFFFF: il simbolo e' viola e
su blu #1E3D58 ha poco contrasto; per lo sfondo blu del tema: python tools/make_icon.py "#1E3D58")
Sorgente: assets/icon-orizon.ico (solo il simbolo); se manca, assets/Orizon-com.jpg (logo intero).
"""
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIZES = [16, 32, 48, 64, 128, 256]


def load_source() -> Image.Image:
    for name in ("icon-orizon.ico", "Orizon-com.jpg"):
        path = os.path.join(ROOT, "assets", name)
        if os.path.isfile(path):
            img = Image.open(path)
            img.load()
            return img.convert("RGBA")
    raise SystemExit("Nessuna immagine sorgente in assets/")


def build(background: str = "#FFFFFF") -> str:
    src = load_source()
    # ritaglia i margini vuoti (trasparenti o bianchi) lasciando solo il simbolo
    mask = Image.new("L", src.size, 0)
    px, mp = src.load(), mask.load()
    for y in range(src.height):
        for x in range(src.width):
            r, g, b, a = px[x, y]
            if a > 16 and min(r, g, b) < 235:
                mp[x, y] = 255
    bbox = mask.getbbox()
    if bbox:
        src = src.crop(bbox)
    side = 1024
    canvas = Image.new("RGBA", (side, side), background)
    scale = (side * 0.80) / max(src.size)          # centrato, con margine
    mark = src.resize((round(src.width * scale), round(src.height * scale)), Image.LANCZOS)
    canvas.alpha_composite(mark, ((side - mark.width) // 2, (side - mark.height) // 2))
    out = os.path.join(ROOT, "assets", "orizon.ico")
    canvas.save(out, format="ICO", sizes=[(s, s) for s in SIZES])
    return out


if __name__ == "__main__":
    print(build(sys.argv[1] if len(sys.argv) > 1 else "#FFFFFF"))
