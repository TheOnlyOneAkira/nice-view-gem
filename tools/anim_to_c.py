"""Convertit un GIF animé ou une série d'images en animation pour nice!view gem.

L'écran est en noir et blanc (1 bit). Chaque pixel plus sombre que le seuil
devient "allumé" (noir, ou blanc si l'écran est inversé dans la config).
Les zones transparentes sont considérées comme du fond.

Taille (écran vu à l'endroit) : 68 pixels de large au maximum, 92 de haut.
Une image plus grande est réduite automatiquement en gardant ses proportions.

Orientation : les images d'animation sont affichées sans passer par la
rotation du canevas ; elles sont donc tournées d'un quart de tour (sens
horaire par défaut, --rotate 270) avant conversion. Dessinez-les à l'endroit.

Le script écrit boards/shields/nice_view_gem/assets/anim_<nom>.c et ajoute
l'animation à la fin de assets/anim_registry.h (ordre = numéro ANIM_SEL).

Exemples :
  python tools/anim_to_c.py mon_chat.gif
  python tools/anim_to_c.py dossier_png/ --name vague --duration 1200
  python tools/anim_to_c.py a.png b.png c.png --name clignote --threshold 100
  python tools/anim_to_c.py --remove vague
  python tools/anim_to_c.py mon_chat.gif --preview   (aperçu PNG agrandi, sans rien écrire)

Nécessite Pillow : pip install pillow
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    from PIL import Image, ImageSequence
except ImportError:
    sys.exit("Pillow n'est pas installé : pip install pillow")

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "boards" / "shields" / "nice_view_gem" / "assets"
REGISTRY = ASSETS / "anim_registry.h"

MAX_W, MAX_H = 68, 92  # sens de lecture de l'écran
ROTATIONS = {0: None, 90: Image.Transpose.ROTATE_90, 180: Image.Transpose.ROTATE_180,
             270: Image.Transpose.ROTATE_270}  # angle PIL (sens antihoraire)
DEFAULT_ROTATE = 270  # = un quart de tour horaire
IMAGE_EXT = {".png", ".bmp", ".gif", ".jpg", ".jpeg", ".webp"}

REGISTRY_HEADER = """\
/*
 * Liste des animations de l'écran périphérique, dans l'ordre :
 * ANIM_SEL 0 = première ligne, ANIM_SEL 1 = deuxième, etc.
 * ANIM_NXT / ANIM_PRV parcourent cette liste en boucle.
 *
 * Mis à jour par tools/anim_to_c.py ; on peut réordonner les lignes à la main.
 * Chaque NVG_ANIM(nom) correspond à assets/anim_<nom>.c.
 */
"""


def load_frames(sources: list[Path]) -> tuple[list[Image.Image], int | None]:
    """Renvoie les images (RGBA) et la durée totale lue dans un GIF, si connue."""
    files: list[Path] = []
    for src in sources:
        if src.is_dir():
            files += sorted(p for p in src.iterdir() if p.suffix.lower() in IMAGE_EXT)
        elif src.is_file():
            files.append(src)
        else:
            sys.exit(f"Introuvable : {src}")
    if not files:
        sys.exit("Aucune image trouvée.")

    frames: list[Image.Image] = []
    total_ms = 0
    timed = True
    for f in files:
        with Image.open(f) as im:
            for fr in ImageSequence.Iterator(im):
                frames.append(fr.convert("RGBA"))
                d = fr.info.get("duration")
                if d:
                    total_ms += int(d)
                else:
                    timed = False
    return frames, (total_ms if timed and total_ms > 0 else None)


def to_1bit(frame: Image.Image, threshold: int, invert: bool) -> Image.Image:
    bg = Image.new("RGBA", frame.size, (255, 255, 255, 255))
    gray = Image.alpha_composite(bg, frame).convert("L")
    if invert:
        gray = gray.point(lambda v: 255 - v)
    # 1 = pixel allumé (sombre dans l'image source)
    return gray.point(lambda v: 1 if v < threshold else 0, mode="1")


def fit(frames: list[Image.Image]) -> list[Image.Image]:
    w = max(f.width for f in frames)
    h = max(f.height for f in frames)
    if w <= MAX_W and h <= MAX_H:
        return frames
    scale = min(MAX_W / w, MAX_H / h)
    size = (max(1, round(w * scale)), max(1, round(h * scale)))
    print(f"Images réduites de {w}x{h} à {size[0]}x{size[1]}")
    return [f.resize(size, Image.LANCZOS) for f in frames]


def pack(img: Image.Image) -> bytes:
    """Format LVGL I1 : lignes de ceil(w/8) octets, bit de poids fort à gauche."""
    w, h = img.size
    stride = (w + 7) // 8
    px = img.load()
    out = bytearray()
    for y in range(h):
        row = bytearray(stride)
        for x in range(w):
            if px[x, y]:
                row[x // 8] |= 0x80 >> (x % 8)
        out += row
    return bytes(out)


def c_bytes(data: bytes, indent: str = "    ") -> str:
    lines = []
    for i in range(0, len(data), 16):
        lines.append(indent + ", ".join(f"0x{b:02x}" for b in data[i:i + 16]) + ",")
    return "\n".join(lines)


def write_c(name: str, frames: list[Image.Image], duration: int, x: int, y: int, source: str) -> Path:
    w, h = frames[0].size
    stride = (w + 7) // 8
    data_size = 8 + stride * h
    parts = [
        f"/* Animation « {name} » : {len(frames)} images {w}x{h}, {duration} ms par boucle.",
        f" * Générée par tools/anim_to_c.py depuis {source} — ne pas modifier à la main. */",
        '#include "animations.h"',
        "",
        "#if CONFIG_NICE_VIEW_WIDGET_INVERTED",
        "#define NVG_PALETTE 0x00, 0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff",
        "#else",
        "#define NVG_PALETTE 0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 0x00, 0xff",
        "#endif",
        "",
    ]
    for i, fr in enumerate(frames, 1):
        parts += [
            f"static const uint8_t {name}_{i:02d}_map[] = {{",
            "    NVG_PALETTE,",
            c_bytes(pack(fr)),
            "};",
            "",
            f"static const lv_image_dsc_t {name}_{i:02d} = {{",
            "    .header.cf = LV_COLOR_FORMAT_I1,",
            f"    .header.w = {w},",
            f"    .header.h = {h},",
            f"    .data_size = {data_size},",
            f"    .data = {name}_{i:02d}_map,",
            "};",
            "",
        ]
    refs = ", ".join(f"&{name}_{i:02d}" for i in range(1, len(frames) + 1))
    parts += [
        f"static const lv_image_dsc_t *const {name}_frames[] = {{",
        f"    {refs},",
        "};",
        "",
        f"const struct nvg_animation nvg_anim_{name} = {{",
        f'    .name = "{name}",',
        f"    .frames = {name}_frames,",
        f"    .frame_count = {len(frames)},",
        f"    .duration_ms = {duration},",
        f"    .x = {x},",
        f"    .y = {y},",
        "};",
        "",
    ]
    out = ASSETS / f"anim_{name}.c"
    out.write_text("\n".join(parts), encoding="utf-8", newline="\n")
    return out


def read_registry() -> list[str]:
    if not REGISTRY.is_file():
        return []
    return re.findall(r"^\s*NVG_ANIM\((\w+)\)", REGISTRY.read_text(encoding="utf-8"), flags=re.M)


def write_registry(names: list[str]) -> None:
    body = "".join(f"NVG_ANIM({n})\n" for n in names)
    REGISTRY.write_text(REGISTRY_HEADER + body, encoding="utf-8", newline="\n")


def preview(name: str, frames: list[Image.Image], scale: int = 3) -> Path:
    """Planche de toutes les images, agrandie, pour vérifier le rendu."""
    w, h = frames[0].size
    cols = min(len(frames), 8)
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("L", (cols * (w + 2) * scale, rows * (h + 2) * scale), 160)
    for i, fr in enumerate(frames):
        im = fr.point(lambda v: 0 if v else 255, mode="L").resize((w * scale, h * scale), Image.NEAREST)
        sheet.paste(im, ((i % cols) * (w + 2) * scale + scale, (i // cols) * (h + 2) * scale + scale))
    out = Path.cwd() / f"preview_{name}.png"
    sheet.save(out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sources", nargs="*", type=Path, help="GIF, images, ou dossier d'images (ordre alphabétique)")
    ap.add_argument("--name", help="nom de l'animation (lettres, chiffres, _) ; par défaut le nom du fichier")
    ap.add_argument("--duration", type=int, help="durée d'une boucle en ms (défaut : celle du GIF, sinon 80 ms par image)")
    ap.add_argument("--threshold", type=int, default=128, help="seuil 0-255 : plus sombre = pixel allumé (défaut 128)")
    ap.add_argument("--invert", action="store_true", help="inverser l'image source (clair = allumé)")
    ap.add_argument("--rotate", type=int, choices=sorted(ROTATIONS), default=DEFAULT_ROTATE,
                    help=f"rotation PIL (antihoraire) appliquée avant conversion (défaut {DEFAULT_ROTATE} = quart de tour horaire)")
    ap.add_argument("--x", type=int, help="position horizontale (défaut : centré dans la zone libre)")
    ap.add_argument("--y", type=int, help="position verticale (défaut : centré)")
    ap.add_argument("--no-register", action="store_true", help="ne pas ajouter à anim_registry.h")
    ap.add_argument("--remove", metavar="NOM", help="retirer une animation (fichier + registre)")
    ap.add_argument("--preview", action="store_true", help="écrire seulement preview_<nom>.png")
    args = ap.parse_args()

    if args.remove:
        names = [n for n in read_registry() if n != args.remove]
        write_registry(names)
        f = ASSETS / f"anim_{args.remove}.c"
        if f.is_file() and args.remove != "crystal":
            f.unlink()
        print(f"Animation « {args.remove} » retirée. Ordre : {', '.join(names)}")
        return

    if not args.sources:
        ap.error("indiquez un GIF, des images ou un dossier")

    name = args.name or args.sources[0].stem
    name = re.sub(r"\W", "_", name).lower()
    if not re.match(r"^[a-z_]\w*$", name):
        sys.exit(f"Nom invalide : {name}")

    raw, gif_ms = load_frames(args.sources)
    frames = [to_1bit(f, args.threshold, args.invert) for f in fit(raw)]
    if len({f.size for f in frames}) > 1:
        sys.exit("Toutes les images doivent avoir la même taille.")
    if len(frames) > 255:
        sys.exit(f"{len(frames)} images : 255 au maximum.")

    if args.preview:
        print(f"Aperçu : {preview(name, frames)}")
        return

    if ROTATIONS[args.rotate] is not None:
        frames = [f.transpose(ROTATIONS[args.rotate]) for f in frames]

    w, h = frames[0].size
    duration = args.duration or gif_ms or 80 * len(frames)
    x = args.x if args.x is not None else (MAX_H - w) // 2
    y = args.y if args.y is not None else (MAX_W - h) // 2  # zone d'écran : MAX_H x MAX_W une fois tournée

    out = write_c(name, frames, duration, x, y, args.sources[0].name)
    size = len(frames) * (8 + ((w + 7) // 8) * h)
    print(f"Écrit {out.relative_to(ROOT)} : {len(frames)} images {w}x{h}, {duration} ms, ~{size / 1024:.1f} Ko de flash")

    if not args.no_register:
        names = read_registry() or ["crystal"]
        if name not in names:
            names.append(name)
        write_registry(names)
        print("Ordre des animations : " + ", ".join(f"{i}={n}" for i, n in enumerate(names)))


if __name__ == "__main__":
    main()
