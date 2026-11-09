"""Génère les animations de départ (GIF noir et blanc) dans tools/animations/.

  rain   : nuage et pluie avec éclaboussures
  waves  : trois vagues qui défilent
  stars  : champ d'étoiles en vitesse lumière
  cube   : cube 3D en fil de fer qui tourne

Chaque animation boucle sans à-coup. Pour les convertir en code C :
  python tools/make_starter_animations.py
  python tools/anim_to_c.py tools/animations/rain.gif   (etc.)
ou tout d'un coup : python tools/make_starter_animations.py --convert
"""

from __future__ import annotations

import argparse
import math
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent / "animations"
W, H = 68, 68
INK, PAPER = 0, 255


def new() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    im = Image.new("L", (W, H), PAPER)
    return im, ImageDraw.Draw(im)


def rain(n: int = 20) -> list[Image.Image]:
    rnd = random.Random(7)
    top, ground = 17, 64
    span = ground - top
    columns = rnd.sample(range(9, 60, 4), 13)  # colonnes espacées : pas de gouttes collées
    drops = [(x, rnd.random(), rnd.randrange(3, 7), rnd.choice((1, 1, 2))) for x in columns]
    frames = []
    for t in range(n):
        im, d = new()
        # nuage
        for cx, cy, r in ((20, 11, 8), (32, 8, 10), (45, 10, 9), (54, 13, 6), (12, 14, 5)):
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=INK)
        d.rectangle((12, 12, 54, 18), fill=INK)
        # sol
        d.line((4, ground + 2, 63, ground + 2), fill=INK)
        for x, phase, length, speed in drops:
            u = (phase + speed * t / n) % 1.0
            y = top + u * (span + length)
            y1 = min(y, ground)
            y0 = max(top + 1, y - length)
            if y0 < y1:
                d.line((x, y0, x, y1), fill=INK)
            # éclaboussure juste après l'impact
            if y - length > ground - 1 or (y > ground and u * (span + length) - span < 3):
                k = (y - ground)
                if 0 <= k < 4:
                    d.point([(x - 2, ground), (x + 2, ground), (x - 1, ground - 1), (x + 1, ground - 1)], fill=INK)
        frames.append(im)
    return frames


def waves(n: int = 24) -> list[Image.Image]:
    layers = [  # (hauteur de base, amplitude, nb de périodes, vitesse, épaisseur)
        (22, 4, 1, 1, 2),
        (38, 5, 2, -1, 2),
        (54, 6, 1, 2, 3),
    ]
    frames = []
    for t in range(n):
        im, d = new()
        for base, amp, k, speed, width in layers:
            phase = 2 * math.pi * speed * t / n
            pts = [(x, base + amp * math.sin(2 * math.pi * k * x / W + phase)) for x in range(-2, W + 3)]
            d.line(pts, fill=INK, width=width, joint="curve")
        # écume sur la vague du bas
        base, amp, k, speed, _ = layers[2]
        phase = 2 * math.pi * speed * t / n
        for x in range(0, W, 6):
            y = base + amp * math.sin(2 * math.pi * k * x / W + phase)
            d.point([(x, y + 4), (x + 3, y + 6)], fill=INK)
        frames.append(im)
    return frames


def stars(n: int = 24) -> list[Image.Image]:
    rnd = random.Random(3)
    cx, cy = W / 2, H / 2
    pts = [(2 * math.pi * (i + rnd.uniform(-0.3, 0.3)) / 26, rnd.random()) for i in range(26)]
    frames = []
    for t in range(n):
        im, d = new()
        for ang, phase in pts:
            u = (phase + t / n) % 1.0
            r1 = 6 + 44 * u * u
            x1, y1 = cx + r1 * math.cos(ang), cy + r1 * math.sin(ang)
            if u < 0.3:  # étoile lointaine : un point
                d.point([(x1, y1)], fill=INK)
                continue
            r0 = r1 * (0.92 - 0.3 * u)
            x0, y0 = cx + r0 * math.cos(ang), cy + r0 * math.sin(ang)
            d.line((x0, y0, x1, y1), fill=INK, width=2 if u > 0.7 else 1)
        frames.append(im)
    return frames


def cube(n: int = 24) -> list[Image.Image]:
    verts = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    edges = [(a, b) for a in range(8) for b in range(a + 1, 8)
             if sum(verts[a][i] != verts[b][i] for i in range(3)) == 1]
    tilt = math.radians(28)
    frames = []
    for t in range(n):
        im, d = new()
        a = (math.pi / 2) * t / n  # un quart de tour : le cube retombe sur lui-même
        proj = []
        for x, y, z in verts:
            x, z = x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)
            y, z = y * math.cos(tilt) - z * math.sin(tilt), y * math.sin(tilt) + z * math.cos(tilt)
            f = 3.4 / (z + 4.6)
            proj.append((W / 2 + x * f * 21, H / 2 + y * f * 21))
        for i, j in edges:
            d.line((proj[i], proj[j]), fill=INK, width=2)
        frames.append(im)
    return frames


ANIMS = {  # nom : (générateur, durée d'une boucle en ms)
    "rain": (rain, 1000),
    "waves": (waves, 1500),
    "stars": (stars, 1200),
    "cube": (cube, 2000),
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--convert", action="store_true", help="convertir aussi en C (anim_to_c.py)")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    for name, (gen, total_ms) in ANIMS.items():
        frames = [f.point(lambda v: 0 if v < 128 else 255) for f in gen()]
        per = max(20, round(total_ms / len(frames)))
        path = OUT / f"{name}.gif"
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=per, loop=0, optimize=False)
        print(f"{path.name} : {len(frames)} images, {per * len(frames)} ms")
        if args.convert:
            subprocess.run([sys.executable, str(Path(__file__).parent / "anim_to_c.py"), str(path),
                            "--duration", str(total_ms)], check=True)


if __name__ == "__main__":
    main()
