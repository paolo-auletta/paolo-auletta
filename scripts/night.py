"""
Turns the dark homepage of paolo.sh (the Iron Giant's night: stars, the
ridge, the pines, his eyes) into an animated SVG for the GitHub profile.

Two styles:
  ascii  the scene in plain glyphs
  tiles  the land, the pines and the eyes as colored tiles with a letter
         in each; the sky stays plain glyphs

Every glyph sits on an explicit grid (one x per character), so the picture
holds together whatever monospace font the viewer's browser picks.
Animation is CSS + SMIL, which GitHub plays inside an <img>.

usage: python3 -I scripts/night.py <ascii|tiles> <night-world.webp> <night-mattes.webp> <out.svg>
"""

import random
import sys

from PIL import Image

STYLE, WORLD, MATTES, OUT = sys.argv[1:5]
assert STYLE in ("ascii", "tiles")

PHOTO_H = 1100  # the resting part of the world: its bottom 1100 px
CROP_TOP = 120  # mostly empty sky above this
EYES = (1180, 712 - CROP_TOP)  # where his eyes open on a wide screen
EYE = "#7cb8ff"
STARS = 34  # how many of the painting's stars to keep, brightest first

if STYLE == "ascii":
    COLS, CW, CH, FONT = 150, 6.0, 11.0, 10
else:
    COLS, CW, CH, FONT = 80, 12.0, 12.0, 9

random.seed(7)

world = Image.open(WORLD).convert("RGB")
W, H = world.size
photo = world.crop((0, H - PHOTO_H + CROP_TOP, W, H))
mattes = (
    Image.open(MATTES).convert("RGB").resize((W, PHOTO_H), Image.BILINEAR).crop((0, CROP_TOP, W, PHOTO_H))
)
PW, PH = photo.size
ROWS = round(COLS * (PH / PW) * (CW / CH))
cell_w, cell_h = PW / COLS, PH / ROWS
px, mx = photo.load(), mattes.load()


def lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def sample(col, row):
    """Land and pine coverage per quadrant, the pines' colors, the brightest star."""
    x0, y0 = col * cell_w, row * cell_h
    n = 6
    land = [[0, 0], [0, 0]]
    pine = [[0, 0], [0, 0]]
    light = []
    for j in range(n):
        for i in range(n):
            x = min(PW - 1, int(x0 + (i + 0.5) * cell_w / n))
            y = min(PH - 1, int(y0 + (j + 0.5) * cell_h / n))
            r, g, _ = mx[x, y]
            qy, qx = j * 2 // n, i * 2 // n
            if g > 128:
                pine[qy][qx] += 1
                light.append(px[x, y])
            elif r > 128:
                land[qy][qx] += 1
    star = 0.0
    for y in range(int(y0), min(PH, int(y0 + cell_h))):
        for x in range(int(x0), min(PW, int(x0 + cell_w))):
            if mx[x, y][0] < 100:
                star = max(star, lum(px[x, y]))
    q = (n // 2) ** 2
    return [[v / q for v in r] for r in land], [[v / q for v in r] for r in pine], light, star


info = {(c, r): sample(c, r) for r in range(ROWS) for c in range(COLS)}


def cover(col, row):
    if (col, row) not in info:
        return 0, 0
    land, pine, _, _ = info[col, row]
    return sum(map(sum, land)) / 4, sum(map(sum, pine)) / 4


def solid(col, row):
    return sum(cover(col, row))


ex, ey = EYES[0] / cell_w, EYES[1] / cell_h
# The eyes on the grid: one cell each, two cells apart.
EYE_ROW = int(ey)
EYE_COLS = (round(ex) - 2, round(ex) + 1) if STYLE == "ascii" else (round(ex) - 1, round(ex) + 1)


def near_eyes(col, row):
    if STYLE == "ascii":
        return EYE_COLS[0] - 4 <= col <= EYE_COLS[1] + 4 and abs(row - EYE_ROW) <= 1
    return EYE_COLS[0] - 3 <= col <= EYE_COLS[1] + 3 and abs(row - EYE_ROW) <= 1


# --- Stars: only the brightest few of the painting's ---------------------------

stars = {}
candidates = sorted(
    ((s, c, r) for (c, r), (_, _, _, s) in info.items() if solid(c, r) < 0.05 and s > 50),
    reverse=True,
)
for rank, (s, c, r) in enumerate(candidates[:STARS]):
    if any(abs(c - c2) <= 1 and abs(r - r2) <= 1 for c2, r2 in stars):
        continue
    g = "+" if rank < 8 else "*" if rank < 20 else "."
    tone = 2 if rank < 8 else 1 if rank < 20 else 0
    stars[c, r] = (g, f"s{tone} t{random.randint(1, 3)}")
# A handful of faint ones, as on the site.
for _ in range(10):
    c, r = random.randrange(COLS), random.randrange(ROWS)
    if solid(c, r) == 0 and solid(c, r + 1) == 0 and (c, r) not in stars:
        stars[c, r] = (".", f"s0 t{random.randint(1, 3)}")

# --- Land and pines --------------------------------------------------------------

glyphs = dict(stars)  # (col, row) -> (glyph, class): plain text cells
tiles = {}  # (col, row) -> (fill, letter, letter fill)

ASCII_RAMP = ":;=+*#%@"
PINE_FILLS = ["#251f40", "#2c2a55", "#283c69", "#2b5288", "#356ba8", "#4c88c8", "#78ade6"]
TILE_LETTERS = [":.", "%:", "%S", "SX%", "X8S", "8X@", "@8"]


def mix(hex_a, hex_b, t):
    a = [int(hex_a[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(hex_b[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


for (col, row), (land, pine, light, _) in info.items():
    if near_eyes(col, row):
        continue
    lc = sum(map(sum, land)) / 4
    pc = sum(map(sum, pine)) / 4
    above = solid(col, row - 1)

    if pc > 0.3:
        L = sum(lum(c) for c in light) / max(1, len(light))
        k = min(1, max(0, (L - 16) / 34))
        top, bot = pine[0][0] + pine[0][1], pine[1][0] + pine[1][1]
        left, right = pine[0][0] + pine[1][0], pine[0][1] + pine[1][1]
        if STYLE == "tiles":
            level = min(6, int(k * 7))
            fill = PINE_FILLS[level]
            ink = mix(fill, "#ffffff", 0.38) if level < 4 else mix(fill, "#000000", 0.4)
            tip = cover(col, row - 1)[1] < 0.15 and top < bot * 0.7
            tiles[col, row] = (fill, "^" if tip else random.choice(TILE_LETTERS[level]), ink)
            continue
        if cover(col, row - 1)[1] < 0.15 and top < bot * 0.7:
            g, tone = ("^" if abs(left - right) < 0.6 else "/" if left < right else "\\"), 4
        elif left < right * 0.45:
            g, tone = "/", 2 + round(k * 2)
        elif right < left * 0.45:
            g, tone = "\\", 2 + round(k * 2)
        else:
            g = ASCII_RAMP[min(len(ASCII_RAMP) - 1, int(k * len(ASCII_RAMP)))]
            tone = 0 if k < 0.2 else min(5, int(k * 5.5))
        glyphs[col, row] = (g, f"p{tone}")
    elif lc + pc > 0.12:
        left = land[0][0] + land[1][0]
        right = land[0][1] + land[1][1]
        top = land[0][0] + land[0][1]
        bot = land[1][0] + land[1][1]
        skyline = above < 0.5
        if STYLE == "tiles":
            if lc + pc < 0.5:
                # Half a tile of hill: drawn as a loose glyph, like the edges of the fish.
                glyphs[col, row] = ("." if bot > top else "'", "r")
            elif skyline:
                tiles[col, row] = ("#1d2546", random.choice("^-~"), "#4a5890")
            else:
                depth = min(1, (row - EYE_ROW + 12) / 30)
                fill = mix("#141b36", "#0c1024", max(0, depth))
                tiles[col, row] = (fill, random.choice(".:") if random.random() < 0.5 else "", mix(fill, "#ffffff", 0.16))
            continue
        if skyline:
            if lc + pc < 0.45:
                g = "." if bot > top else "'"
                if left < 0.2 and right > 0.5:
                    g = ","
            elif left < right * 0.5:
                g = "/"
            elif right < left * 0.5:
                g = "\\"
            else:
                g = "^" if top < bot * 0.6 and random.random() < 0.25 else "~" if random.random() < 0.3 else "-"
            glyphs[col, row] = (g, "r")
        elif (col + row) % 2 == 0:
            glyphs[col, row] = ("." if random.random() < 0.8 else ":", "h")

# --- SVG -------------------------------------------------------------------------

VW, VH = COLS * CW, ROWS * CH
BASE = CH * 0.74 if STYLE == "ascii" else CH * 0.7


def esc(ch):
    return {"<": "&lt;", ">": "&gt;", "&": "&amp;"}.get(ch, ch)


def text_rows(cells, cls_of=lambda v: v[1], glyph_of=lambda v: v[0]):
    groups = {}
    for (col, row), v in cells.items():
        g = glyph_of(v)
        if g:
            groups.setdefault((row, cls_of(v)), []).append((col, g))
    out = []
    for (row, cls), items in sorted(groups.items()):
        items.sort()
        xs = " ".join(f"{c * CW + CW / 2:g}" for c, _ in items)
        attr = f'class="{cls}"' if not cls.startswith("#") else f'fill="{cls}"'
        out.append(f'<text {attr} x="{xs}" y="{row * CH + BASE:g}">{"".join(esc(g) for _, g in items)}</text>')
    return "\n".join(out)


def tile_paths():
    by_fill = {}
    for (col, row), (fill, _, _) in tiles.items():
        by_fill.setdefault(fill, []).append((col, row))
    g = 1.0  # the gap between tiles
    s = CW - g
    out = []
    for fill, cells in sorted(by_fill.items()):
        d = "".join(f"M{c * CW + g / 2:g} {r * CH + g / 2:g}h{s:g}v{s:g}h-{s:g}z" for c, r in sorted(cells))
        out.append(f'<path fill="{fill}" d="{d}"/>')
    return "\n".join(out)


# The searchlight: the same glyphs, shown only inside a cone that swings from
# his eyes across the sky now and then.
ecx = (EYE_COLS[0] + EYE_COLS[1] + 1) / 2 * CW
ecy = (EYE_ROW + 0.5) * CH
beam = {}
for row in range(ROWS):
    for col in range(COLS):
        if row < EYE_ROW and (col, row) not in glyphs and (col, row) not in tiles and solid(col, row) < 0.05:
            if random.random() < 0.5:
                beam[col, row] = (".:-=+"[min(4, int(random.random() ** 1.6 * 5))], "b")
L = VW * 1.3
cone = f"M{ecx:g} {ecy:g} L{ecx - L * 0.14:g} {ecy - L:g} L{ecx + L * 0.14:g} {ecy - L:g} Z"
spline = ";".join([".4 0 .6 1"] * 5)
rot = lambda a: f"{a} {ecx:g} {ecy:g}"

# The eyes: they glance from cell to cell (whole cells, no sliding) and blink.
glance = "0 0;-1 0;-1 0;1 0;1 0;0 0;-1 0;0 0;1 0;1 0;0 0".split(";")
glance = ";".join(f"{float(v.split()[0]) * CW:g} 0" for v in glance)
glance_times = "0;.12;.27;.31;.43;.47;.6;.66;.74;.9;.95"
open_times = "0;.5;.52;.56;.58"


def eye_cells(open_):
    if STYLE == "ascii":
        g = "O" if open_ else "-"
        xs = " ".join(f"{c * CW + CW / 2:g}" for c in EYE_COLS)
        return f'<text class="eye" x="{xs}" y="{EYE_ROW * CH + BASE:g}">{g}{g}</text>'
    out = []
    for c in EYE_COLS:
        fill, ink, g = (EYE, "#f2f8ff", "O") if open_ else ("#2a4a7a", "#7cb8ff", "-")
        out.append(f'<rect x="{c * CW + 0.5:g}" y="{EYE_ROW * CH + 0.5:g}" width="{CW - 1:g}" height="{CH - 1:g}" fill="{fill}"/>')
        out.append(f'<text fill="{ink}" x="{c * CW + CW / 2:g}" y="{EYE_ROW * CH + BASE:g}" font-weight="700">{g}</text>')
    return "".join(out)


svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VW:g} {VH:g}" width="{VW:g}" height="{VH:g}" role="img" aria-label="A night sky over a ridge of pines, drawn in ASCII. Two blue eyes look out from the dark hills.">
<title>The Giant's night</title>
<style>
text {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; font-size: {FONT}px; text-anchor: middle; }}
.s0 {{ fill: #46557f; }} .s1 {{ fill: #8fa6dc; }} .s2 {{ fill: #e4ecff; }}
.r {{ fill: #46558c; }} .h {{ fill: #161c36; }} .b {{ fill: #9cc8ff; }}
.p0 {{ fill: #3b2d5c; }} .p1 {{ fill: #26406f; }} .p2 {{ fill: #2f5d97; }} .p3 {{ fill: #3f7cbf; }} .p4 {{ fill: #5d9be0; }} .p5 {{ fill: #8cc0f5; }}
.eye {{ fill: #f2f8ff; font-weight: 700; }}
.t1 {{ animation: tw 4.1s ease-in-out infinite; }}
.t2 {{ animation: tw 5.3s ease-in-out -1.7s infinite; }}
.t3 {{ animation: tw 6.7s ease-in-out -3.1s infinite; }}
@keyframes tw {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: .3; }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
</style>
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#05070f"/><stop offset=".7" stop-color="#0a1024"/><stop offset="1" stop-color="#070a16"/>
  </linearGradient>
  <radialGradient id="halo">
    <stop offset="0" stop-color="{EYE}" stop-opacity=".45"/><stop offset="1" stop-color="{EYE}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="fade" cx="{ecx:g}" cy="{ecy:g}" r="{VW * 0.75:g}" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
  </radialGradient>
  <filter id="bloom" x="-100%" y="-100%" width="300%" height="300%">
    <feGaussianBlur stdDeviation="{CW * 0.45:g}" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <mask id="cone" maskUnits="userSpaceOnUse" x="0" y="0" width="{VW:g}" height="{VH:g}">
    <path d="{cone}" fill="url(#fade)">
      <animateTransform attributeName="transform" type="rotate" dur="18s" repeatCount="indefinite"
        values="{rot(-58)};{rot(-58)};{rot(-20)};{rot(30)};{rot(52)};{rot(52)}"
        keyTimes="0;.42;.6;.78;.92;1" calcMode="spline" keySplines="{spline}"/>
    </path>
  </mask>
</defs>
<rect width="100%" height="100%" fill="url(#sky)"/>
<g mask="url(#cone)" opacity="0">
  <animate attributeName="opacity" dur="18s" repeatCount="indefinite"
    values="0;0;.05;.9;.35;.9;.75;0;0" keyTimes="0;.43;.45;.47;.49;.52;.88;.93;1"/>
{text_rows(beam)}
</g>
{tile_paths()}
{text_rows({k: v for k, v in tiles.items() if v[1]}, cls_of=lambda v: v[2], glyph_of=lambda v: v[1])}
{text_rows(glyphs)}
<g>
  <animateTransform attributeName="transform" type="translate" dur="18s" repeatCount="indefinite"
    calcMode="discrete" values="{glance}" keyTimes="{glance_times}"/>
  <ellipse cx="{ecx:g}" cy="{ecy:g}" rx="{CW * 4.5:g}" ry="{CH * 2:g}" fill="url(#halo)"/>
  <g filter="url(#bloom)">
    <g>
      <animate attributeName="opacity" dur="9s" repeatCount="indefinite" calcMode="discrete" values="1;0;1;0;1" keyTimes="{open_times}"/>
      {eye_cells(True)}
    </g>
    <g opacity="0">
      <animate attributeName="opacity" dur="9s" repeatCount="indefinite" calcMode="discrete" values="0;1;0;1;0" keyTimes="{open_times}"/>
      {eye_cells(False)}
    </g>
  </g>
</g>
</svg>
'''

with open(OUT, "w") as f:
    f.write(svg)
print(f"{STYLE}: {COLS}x{ROWS}, {len(stars)} stars, {len(tiles)} tiles, {len(glyphs)} glyphs, {len(svg) / 1024:.0f} KB")
