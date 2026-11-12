"""
Turns the dark homepage of paolo.sh (the Iron Giant's night: stars, the
ridge, the pines, his eyes) into an animated SVG for the GitHub profile.

Every glyph sits on an explicit grid (one x per character), so the picture
holds together whatever monospace font the viewer's browser picks.
Animation is CSS + SMIL, which GitHub plays inside an <img>.

usage: python3 -I scripts/night.py <night-world.webp> <night-mattes.webp> <out.svg>
"""

import random
import sys

from PIL import Image

WORLD, MATTES, OUT = sys.argv[1:4]

PHOTO_H = 1100  # the resting part of the world: its bottom 1100 px
CROP_TOP = 120  # mostly empty sky above this
EYES = (1180, 712 - CROP_TOP)  # where his eyes open on a wide screen
EYE = "#7cb8ff"
STARS = 18  # how many of the painting's stars to keep, brightest first

COLS, CW, CH, FONT = 150, 6.0, 11.0, 10

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
EYE_COLS = (round(ex) - 2, round(ex) + 1)


def near_eyes(col, row):
    return EYE_COLS[0] - 4 <= col <= EYE_COLS[1] + 4 and abs(row - EYE_ROW) <= 1


# --- Stars: only the brightest few of the painting's ---------------------------

stars = {}
candidates = sorted(
    ((s, c, r) for (c, r), (_, _, _, s) in info.items() if solid(c, r) < 0.05 and s > 50),
    reverse=True,
)
for rank, (s, c, r) in enumerate(candidates[:STARS]):
    if any(abs(c - c2) <= 1 and abs(r - r2) <= 1 for c2, r2 in stars):
        continue
    g = "+" if rank < 5 else "*" if rank < 12 else "."
    tone = 2 if rank < 5 else 1 if rank < 12 else 0
    stars[c, r] = (g, f"s{tone} t{random.randint(1, 3)}")
# A handful of faint ones, as on the site.
for _ in range(4):
    c, r = random.randrange(COLS), random.randrange(ROWS)
    if solid(c, r) == 0 and solid(c, r + 1) == 0 and (c, r) not in stars:
        stars[c, r] = (".", f"s0 t{random.randint(1, 3)}")

# --- Land and pines --------------------------------------------------------------

glyphs = dict(stars)  # (col, row) -> (glyph, class): plain text cells

ASCII_RAMP = ":;=+*#%@"


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
BASE = CH * 0.74


def esc(ch):
    return {"<": "&lt;", ">": "&gt;", "&": "&amp;"}.get(ch, ch)


def text_rows(cells):
    groups = {}
    for (col, row), (g, cls) in cells.items():
        groups.setdefault((row, cls), []).append((col, g))
    out = []
    for (row, cls), items in sorted(groups.items()):
        items.sort()
        xs = " ".join(f"{c * CW + CW / 2:g}" for c, _ in items)
        out.append(f'<text class="{cls}" x="{xs}" y="{row * CH + BASE:g}">{"".join(esc(g) for _, g in items)}</text>')
    return "\n".join(out)


# The searchlight: the same glyphs, shown only inside a cone that swings from
# his eyes across the sky now and then.
ecx = (EYE_COLS[0] + EYE_COLS[1] + 1) / 2 * CW
ecy = (EYE_ROW + 0.5) * CH
beam = {}
for row in range(ROWS):
    for col in range(COLS):
        if row < EYE_ROW and (col, row) not in glyphs and solid(col, row) < 0.05:
            if random.random() < 0.5:
                beam[col, row] = (".:-=+"[min(4, int(random.random() ** 1.6 * 5))], "b")
L = VW * 1.3
cone = f"M{ecx:g} {ecy:g} L{ecx - L * 0.14:g} {ecy - L:g} L{ecx + L * 0.14:g} {ecy - L:g} Z"
spline = ";".join([".4 0 .6 1"] * 5)
rot = lambda a: f"{a} {ecx:g} {ecy:g}"

# The eyes: they look slowly from side to side (never up or down) and blink.
glance = ";".join(f"{v * CW:g} 0" for v in (0, 0, -1, -1, 0.8, 0.8, 0, 0))
glance_times = "0;.1;.18;.38;.48;.7;.8;1"
glance_splines = ";".join([".5 0 .5 1"] * 7)
open_times = "0;.5;.52;.56;.58"


def eye_cells(open_):
    g = "O" if open_ else "-"
    xs = " ".join(f"{c * CW + CW / 2:g}" for c in EYE_COLS)
    return f'<text class="eye" x="{xs}" y="{EYE_ROW * CH + BASE:g}">{g}{g}</text>'


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
{text_rows(glyphs)}
<g>
  <animateTransform attributeName="transform" type="translate" dur="18s" repeatCount="indefinite"
    calcMode="spline" values="{glance}" keyTimes="{glance_times}" keySplines="{glance_splines}"/>
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
print(f"{COLS}x{ROWS}, {len(stars)} stars, {len(glyphs)} glyphs, {len(svg) / 1024:.0f} KB")
