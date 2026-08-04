from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "brand" / "techguy_huawei.ico"


def render(size: int = 256) -> Image.Image:
    scale = size / 256
    image = Image.new("RGBA", (size, size), (3, 7, 16, 255))
    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    body = [(58*scale, 213*scale), (44*scale, 178*scale), (55*scale, 117*scale), (77*scale, 55*scale), (128*scale, 27*scale), (183*scale, 59*scale), (204*scale, 119*scale), (207*scale, 210*scale)]
    g.polygon(body, fill=(8, 14, 30, 255), outline=(174, 65, 255, 255), width=max(2, int(5*scale)))
    g.line(body + [body[0]], fill=(47, 194, 255, 230), width=max(1, int(2*scale)))
    glow = glow.filter(ImageFilter.GaussianBlur(max(2, int(5*scale))))
    image.alpha_composite(glow)
    d = ImageDraw.Draw(image)
    d.polygon(body, fill=(5, 10, 23, 255), outline=(118, 82, 255, 255), width=max(2, int(3*scale)))
    d.rounded_rectangle((82*scale, 99*scale, 126*scale, 132*scale), radius=10*scale, outline=(226, 241, 255, 255), width=max(2, int(4*scale)))
    d.rounded_rectangle((135*scale, 99*scale, 179*scale, 132*scale), radius=10*scale, outline=(226, 241, 255, 255), width=max(2, int(4*scale)))
    d.line((126*scale, 113*scale, 135*scale, 113*scale), fill=(226, 241, 255, 255), width=max(2, int(4*scale)))
    return image


OUT.parent.mkdir(parents=True, exist_ok=True)
render().save(OUT, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(f"generated {OUT}")
