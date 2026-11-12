"""
Turns the dark homepage of paolo.sh (the Iron Giant's night: stars, the
ridge, the pines) into an animated ASCII SVG for the GitHub profile README.

Every glyph is placed on an explicit grid (one x per character), so the
picture holds together whatever monospace font the viewer's browser picks.
Animation is plain CSS + SMIL, which GitHub serves fine inside an <img>.

usage: python3 -I scripts/night.py <night-world.webp> <night-mattes.webp> <out.svg> [preview.png]
"""

import math
import random
import sys

from PIL import Image, ImageDraw, ImageFont

WORLD, MATTES, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
PREVIEW = sys.argv[4] if len(sys.argv) > 4 else None

# The resting part of the world: its bottom 1100 px, as on the site.
PHOTO_H = 1100
CROP_TOP = 120  # mostly empty sky above this
COLS = 150
CW, CH = 6.0, 11.0  # cell size in SVG units
FONT = 10

random.seed(7)

world = Image.open(WORLD).convert("RGB")
W, H = world.size
photo = world.crop((0, H - PHOTO_H + CROP_TOP, W, H))
mattes = Image.open(MATTES).convert("RGB").resize((W, PHOTO_H), Image.BILINEAR).crop((0, CROP_TOP, W, PHOTO_H))
PW, PH = photo.size
ROWS = round(COLS * (PH / PW) * (CW / CH))
cell_w, cell_h = PW / COLS, PH / ROWS

px = photo.load()
mx = mattes.load()

# Where his eyes open on a wide screen (the landing), in photo pixels.
EYES = (1180, 712 - CROP_TOP)

SKY, LAND, PINE = 0, 1, 2


def lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def sample(col, row):
    """Coverage of land and pines in a cell, per quadrant, and the pines' light."""
    x0, y0 = col * cell_w, row * cell_h
    n = 6
    land = [[0] * 2 for _ in range(2)]
    pine = [[0] * 2 for _ in range(2)]
    light = []
    star = 0.0
    for j in range(n):
        for i in range(n):
            x = min(PW - 1, int(x0 + (i + 0.5) * cell_w / n))
            y = min(PH - 1, int(y0 + (j + 0.5) * cell_h / n))
            r, g, _ = mx[x, y]
            q = (j * 2 // n, i * 2 // n)
            c = px[x, y]
            if g > 128:
                pine[q[0]][q[1]] += 1
                light.append(c)
            elif r > 128:
                land[q[0]][q[1]] += 1
    # Stars are a pixel or two wide: look at every pixel of a sky cell.
    for y in range(int(y0), min(PH, int(y0 + cell_h))):
        for x in range(int(x0), min(PW, int(x0 + cell_w))):
            if mx[x, y][0] < 100:
                star = max(star, lum(px[x, y]))
    q = (n // 2) ** 2
    land = [[v / q for v in r] for r in land]
    pine = [[v / q for v in r] for r in pine]
    return land, pine, light, star


# --- Build the grid -----------------------------------------------------------

cells = {}  # (col, row) -> (glyph, class)
info = {}
for row in range(ROWS):
    for col in range(COLS):
        info[col, row] = sample(col, row)


def cover(col, row):
    if not (0 <= col < COLS and 0 <= row < ROWS):
        return 0, 0
    land, pine, _, _ = info[col, row]
    return sum(map(sum, land)) / 4, sum(map(sum, pine)) / 4


PINE_RAMP = ":;=+*#%@"
for (col, row), (land, pine, light, star) in info.items():
    lc = sum(map(sum, land)) / 4
    pc = sum(map(sum, pine)) / 4
    solid = lc + pc

    if pc > 0.3:
        # Pines: their glyph is their light, their edges are slopes.
        L = sum(lum(c) for c in light) / max(1, len(light))
        b = sum(c[2] for c in light) / max(1, len(light))
        top = pine[0][0] + pine[0][1]
        bot = pine[1][0] + pine[1][1]
        left = pine[0][0] + pine[1][0]
        right = pine[0][1] + pine[1][1]
        above = cover(col, row - 1)[1]
        k = min(1, max(0, (L - 16) / 34))
        if above < 0.15 and top < bot * 0.7:
            g = "^" if abs(left - right) < 0.6 else ("/" if left < right else "\\")
            tone = 4
        elif left < right * 0.45:
            g, tone = "/", 2 + round(k * 2)
        elif right < left * 0.45:
            g, tone = "\\", 2 + round(k * 2)
        else:
            g = PINE_RAMP[min(len(PINE_RAMP) - 1, int(k * len(PINE_RAMP)))]
            tone = min(5, int(k * 5.5))
            # The painted needles: shadow in the trees reads violet.
            if k < 0.2:
                tone = 0
        cells[col, row] = (g, f"p{tone}")
    elif solid > 0.12:
        # The ridge: its skyline drawn, its body a dim weave.
        above = sum(cover(col, row - 1))
        top = land[0][0] + land[0][1] + pine[0][0] + pine[0][1]
        bot = land[1][0] + land[1][1] + pine[1][0] + pine[1][1]
        if above < 0.5:
            left = land[0][0] + land[1][0]
            right = land[0][1] + land[1][1]
            if solid < 0.45:
                g = "." if bot > top else "'"
                if left < 0.2 and right > 0.5:
                    g = ","
                elif right < 0.2 and left > 0.5:
                    g = "."
            elif left < right * 0.5:
                g = "/"
            elif right < left * 0.5:
                g = "\\"
            else:
                g = "^" if top < bot * 0.6 and random.random() < 0.25 else "~" if random.random() < 0.3 else "-"
            cells[col, row] = (g, "r")
        else:
            # Deeper in, fainter: the hills fall into the dark.
            if (col + row) % 2 == 0:
                cells[col, row] = ("." if random.random() < 0.8 else ":", "h")
    elif star > 88:
        g = "+" if star > 150 else "*" if star > 100 else "."
        tw = random.choice(["t1", "t2", "t3", "t4"])
        cells[col, row] = (g, f"s{0 if star < 90 else 1 if star < 150 else 2} {tw}")

# A few faint extra stars in the empty sky, as on the site.
for _ in range(40):
    col, row = random.randrange(COLS), random.randrange(ROWS)
    if (col, row) in cells:
        continue
    lc, pc = cover(col, row)
    if lc + pc > 0 or any(sum(cover(col, r)) > 0 for r in range(row, min(ROWS, row + 2))):
        continue
    cells[col, row] = (random.choice("..`'"), f"s0 {random.choice(['t1', 't2', 't3', 't4'])}")

# The eyes: clear their cells so the lamps sit on the dark.
ex, ey = EYES[0] / cell_w, EYES[1] / cell_h
GAP = 1.5  # half the distance between the eyes, in columns
for dc in range(-4, 5):
    for dr in range(-1, 2):
        cells.pop((int(ex) + dc, int(ey) + dr), None)

# --- Write the SVG ------------------------------------------------------------

VW, VH = COLS * CW, ROWS * CH + 4
EYE = "#7cb8ff"
ex_svg, ey_svg = ex * CW, ey * CH

groups = {}
for (col, row), (g, cls) in cells.items():
    groups.setdefault((row, cls), []).append((col, g))


def esc(ch):
    return {"<": "&lt;", ">": "&gt;", "&": "&amp;"}.get(ch, ch)


rows_svg = []
for (row, cls), items in sorted(groups.items()):
    items.sort()
    xs = " ".join(f"{c * CW + CW / 2:g}" for c, _ in items)
    text = "".join(esc(g) for _, g in items)
    rows_svg.append(f'<text class="{cls}" x="{xs}" y="{row * CH + CH * 0.78:g}">{text}</text>')

# The beam: a searchlight from the eyes, made of the same glyphs, swinging
# slowly across the sky now and then. A mask shows it only inside the cone.
beam_cells = []
for row in range(ROWS):
    for col in range(COLS):
        if (col, row) in cells:
            continue
        if sum(cover(col, row)) > 0.05:
            continue
        if row > ey:
            continue
        r = random.random()
        if r < 0.55:
            beam_cells.append((col, row, ".:-=+"[min(4, int(random.random() ** 1.6 * 5))]))
beam_rows = {}
for col, row, g in beam_cells:
    beam_rows.setdefault(row, []).append((col, g))
beam_svg = []
for row, items in sorted(beam_rows.items()):
    xs = " ".join(f"{c * CW + CW / 2:g}" for c, _ in items)
    beam_svg.append(f'<text x="{xs}" y="{row * CH + CH * 0.78:g}">{"".join(g for _, g in items)}</text>')

beam_len = VW * 1.3
cone = f"M{ex_svg:g} {ey_svg:g} L{ex_svg - beam_len * 0.14:g} {ey_svg - beam_len:g} L{ex_svg + beam_len * 0.14:g} {ey_svg - beam_len:g} Z"

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VW:g} {VH:g}" width="{VW:g}" height="{VH:g}" role="img" aria-label="A night sky over a ridge of pines, drawn in ASCII. Two blue eyes look out from the dark hills.">
<title>The Giant's night, in ASCII</title>
<style>
text {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; font-size: {FONT}px; text-anchor: middle; }}
.s0 {{ fill: #4a5a8c; }} .s1 {{ fill: #8fa6dc; }} .s2 {{ fill: #dfe9ff; }}
.r {{ fill: #46558c; }} .h {{ fill: #161c36; }}
.p0 {{ fill: #3b2d5c; }} .p1 {{ fill: #26406f; }} .p2 {{ fill: #2f5d97; }} .p3 {{ fill: #3f7cbf; }} .p4 {{ fill: #5d9be0; }} .p5 {{ fill: #8cc0f5; }}
.t1 {{ animation: tw 4.1s ease-in-out infinite; }}
.t2 {{ animation: tw 5.3s ease-in-out -1.7s infinite; }}
.t3 {{ animation: tw 6.7s ease-in-out -3.1s infinite; }}
@keyframes tw {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: .25; }} }}
.beam text {{ fill: #9cc8ff; }}
.eye {{ fill: #eef6ff; }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
</style>
<defs>
  <radialGradient id="glow">
    <stop offset="0" stop-color="{EYE}" stop-opacity=".85"/>
    <stop offset=".35" stop-color="{EYE}" stop-opacity=".28"/>
    <stop offset="1" stop-color="{EYE}" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#05070f"/>
    <stop offset=".7" stop-color="#0a1024"/>
    <stop offset="1" stop-color="#070a16"/>
  </linearGradient>
  <radialGradient id="fade" cx="{ex_svg:g}" cy="{ey_svg:g}" r="{VW * 0.75:g}" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#fff"/>
    <stop offset="1" stop-color="#fff" stop-opacity="0"/>
  </radialGradient>
  <mask id="cone" maskUnits="userSpaceOnUse" x="0" y="0" width="{VW:g}" height="{VH:g}">
    <path d="{cone}" fill="url(#fade)">
      <animateTransform attributeName="transform" type="rotate" dur="18s" repeatCount="indefinite"
        values="-58 {ex_svg:g} {ey_svg:g};-58 {ex_svg:g} {ey_svg:g};-20 {ex_svg:g} {ey_svg:g};30 {ex_svg:g} {ey_svg:g};52 {ex_svg:g} {ey_svg:g};52 {ex_svg:g} {ey_svg:g}"
        keyTimes="0;.42;.6;.78;.92;1" calcMode="spline"
        keySplines=".4 0 .6 1;.4 0 .6 1;.4 0 .6 1;.4 0 .6 1;.4 0 .6 1"/>
    </path>
  </mask>
</defs>
<rect width="100%" height="100%" fill="url(#sky)"/>
<g class="beam" mask="url(#cone)" opacity="0">
  <animate attributeName="opacity" dur="18s" repeatCount="indefinite"
    values="0;0;.05;.9;.35;.9;.75;0;0" keyTimes="0;.43;.45;.47;.49;.52;.88;.93;1"/>
  {"".join(beam_svg)}
</g>
{"".join(rows_svg)}
<g>
  <animateTransform attributeName="transform" type="translate" dur="18s" repeatCount="indefinite"
    values="0 0;0 0;-5 -1;-5 -1;4 0;4 0;-3 -2;-3 -2;3 -2;6 -1;6 -1;0 0"
    keyTimes="0;.1;.14;.26;.3;.4;.46;.6;.75;.88;.94;1" calcMode="spline"
    keySplines=".5 0 .5 1;.5 0 .5 1;.5 0 .5 1;.5 0 .5 1;.5 0 .5 1;.5 0 .5 1;.5 0 .5 1;.5 0 .5 1;.5 0 .5 1;.5 0 .5 1;.5 0 .5 1"/>
  <g>
    <animate attributeName="opacity" dur="18s" repeatCount="indefinite"
      values=".75;1;.8;1;.85;1;.75" keyTimes="0;.2;.45;.5;.55;.8;1"/>
    <circle cx="{ex_svg - GAP * CW:g}" cy="{ey_svg:g}" r="{CW * 2.6:g}" fill="url(#glow)"/>
    <circle cx="{ex_svg + GAP * CW:g}" cy="{ey_svg:g}" r="{CW * 2.6:g}" fill="url(#glow)"/>
  </g>
  <g>
    <animateTransform attributeName="transform" type="scale" additive="sum" dur="9s" repeatCount="indefinite"
      values="1 1;1 1;1 .1;1 1;1 1;1 .1;1 1;1 1" keyTimes="0;.5;.515;.53;.56;.575;.59;1"/>
    <ellipse class="eye" cx="{ex_svg - GAP * CW:g}" cy="{ey_svg:g}" rx="{CW * 0.55:g}" ry="{CW * 0.55:g}"/>
    <ellipse class="eye" cx="{ex_svg + GAP * CW:g}" cy="{ey_svg:g}" rx="{CW * 0.55:g}" ry="{CW * 0.55:g}"/>
  </g>
</g>
</svg>
'''

with open(OUT, "w") as f:
    f.write(svg)
print(f"{COLS}x{ROWS} grid, {len(cells)} glyphs, {len(svg) / 1024:.0f} KB")

# --- Preview ------------------------------------------------------------------
if PREVIEW:
    S = 2
    colors = {
        "s0": "#4a5a8c", "s1": "#8fa6dc", "s2": "#dfe9ff", "r": "#46558c", "h": "#161c36",
        "p0": "#3b2d5c", "p1": "#26406f", "p2": "#2f5d97", "p3": "#3f7cbf", "p4": "#5d9be0", "p5": "#8cc0f5",
    }
    img = Image.new("RGB", (int(VW * S), int(VH * S)), "#070a16")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", int(FONT * S))
    except OSError:
        font = ImageFont.load_default()
    for (col, row), (g, cls) in cells.items():
        d.text(((col * CW + CW / 2) * S, (row * CH + CH * 0.78) * S), g, fill=colors[cls.split()[0]], font=font, anchor="ms")
    for sx in (-GAP, GAP):
        cx, cy = (ex_svg + sx * CW) * S, ey_svg * S
        rr = CW * 0.55 * S
        d.ellipse((cx - rr * 2.4, cy - rr * 2.4, cx + rr * 2.4, cy + rr * 2.4), fill="#16284a")
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill="#eef6ff")
    img.save(PREVIEW)
