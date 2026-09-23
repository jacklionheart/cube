"""Compose out/locks-collage.png: the Locks as one shareable image.

Grid of card images (grouped W/U/B/R/G/Multi/C, best drafters' WR
first within each color), each captioned with exposure x and WR, with
a title bar. Card images are fetched once into imgcache/.

Usage: python3 locks_collage.py
"""

import json
import pathlib
import subprocess

from PIL import Image, ImageDraw, ImageFont

import report as rpt
from lane_compare import is_land
from theme_report import load_all

HERE = pathlib.Path(__file__).parent
CACHE = HERE / "imgcache"
COLS = 7
CARD_W = 300
PAD = 10
CAP_H = 34
TITLE_H = 74


def font(size, bold=False):
    for name in ("Helvetica.ttc", "HelveticaNeue.ttc", "Arial.ttf"):
        try:
            return ImageFont.truetype(f"/System/Library/Fonts/{name}", size,
                                      index=1 if bold else 0)
        except OSError:
            continue
    return ImageFont.load_default()


def main():
    drafts, cube, availability, scry, card_decks, drafted, mained = load_all()
    images = json.loads((HERE / "images.json").read_text())

    def colorgrp(c):
        base = c.replace(" 2", "", 1) if c.endswith(" 2") else c
        cs = (scry.get(base) or scry.get(c) or {}).get("colors") or []
        return "Multi" if len(cs) > 1 else (cs[0] if cs else "C")

    def wr_of(c):
        w = l = 0
        for d in drafts:
            p = d.picks.get(c)
            if p:
                dw, dl = d.records.get(p.player, (0, 0))
                w, l = w + dw, l + dl
        return w / (w + l) if w + l else 0

    locks, _ = rpt.compute_locks(cube, availability, scry, drafts,
                                 drafted, mained,
                                 min_avail=rpt.MIN_DRAFTED)
    order = {g: i for i, g in enumerate(list("WUBRG") + ["Multi", "C"])}
    locks.sort(key=lambda c: (order[colorgrp(c)], -wr_of(c)))

    CACHE.mkdir(exist_ok=True)
    tiles = []
    for c in locks:
        path = CACHE / (c.replace("/", "_").replace(" ", "_") + ".jpg")
        if not path.exists():
            subprocess.run(["curl", "-sL", "--fail", images[c],
                            "-o", str(path)], check=True)
        img = Image.open(path).convert("RGB")
        img = img.resize((CARD_W, round(img.height * CARD_W / img.width)),
                         Image.LANCZOS)
        tiles.append((c, img))

    card_h = max(im.height for _, im in tiles)
    rows = -(-len(tiles) // COLS)
    W = COLS * CARD_W + (COLS + 1) * PAD
    H = TITLE_H + rows * (card_h + CAP_H + PAD) + PAD
    canvas = Image.new("RGB", (W, H), "#ffffff")
    draw = ImageDraw.Draw(canvas)
    draw.text((PAD + 4, 18), f"Samp Roto s4 — the {len(tiles)} Locks",
              fill="#1a1a1a", font=font(34, bold=True))
    draw.text((PAD + 6, 52),
              "maindecked by every deck that could cast them (off-color/undrafted misses forgiven, max 2) · "
              "caption: times drafted x drafters' win rate",
              fill="#6b6b6b", font=font(16))
    cap_font = font(17)
    for i, (c, im) in enumerate(tiles):
        r, col = divmod(i, COLS)
        x = PAD + col * (CARD_W + PAD)
        y = TITLE_H + r * (card_h + CAP_H + PAD)
        canvas.paste(im, (x, y))
        cap = f"{drafted[c]}× · {wr_of(c):.0%}"
        tw = draw.textlength(cap, font=cap_font)
        draw.text((x + (CARD_W - tw) / 2, y + im.height + 6), cap,
                  fill="#444444", font=cap_font)
    out = HERE / "out" / "locks-collage.png"
    canvas.save(out)
    print(out, f"{W}x{H}")


if __name__ == "__main__":
    main()
