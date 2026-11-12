#!/usr/bin/env python3
"""Draws the hero's Aburrá Valley (the svg.valley in index.html): steep mountains on both sides dipping into a V
where the sun rises, hillside neighbourhoods with lit windows, a Metrocable line and the downtown skyline led by
the Coltejer tower's needle top. Deterministic (fixed seed), so rerunning gives the same picture.

    python3 _build/valley.py    # rewrites the <svg class="valley"> block in index.html, then run build.py
"""
import os, random, re

W, H = 1440, 260
rnd = random.Random(626)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ridge outlines as (x, y) polylines; y grows downward
BACK = [(0, 26), (90, 20), (170, 36), (250, 30), (330, 62), (420, 92), (500, 128), (580, 160), (650, 176), (720, 182),
        (790, 176), (860, 160), (940, 130), (1020, 96), (1100, 70), (1180, 44), (1260, 22), (1340, 30), (1440, 20)]
MID = [(0, 92), (120, 98), (230, 120), (330, 146), (430, 176), (520, 198), (620, 212), (720, 216), (820, 212),
       (920, 198), (1010, 176), (1110, 148), (1210, 122), (1320, 102), (1440, 96)]


def at(line, x):
    for (x0, y0), (x1, y1) in zip(line, line[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return line[-1][1]


def smooth(line):
    """Catmull-Rom through the points as cubic Béziers, closed down to the bottom edge."""
    p = [line[0]] + line + [line[-1]]
    d = f'M{line[0][0]} {line[0][1]}'
    for i in range(1, len(p) - 2):
        (x0, y0), (x1, y1), (x2, y2), (x3, y3) = p[i - 1], p[i], p[i + 1], p[i + 2]
        d += (f' C{x1 + (x2 - x0) / 6:.0f} {y1 + (y2 - y0) / 6:.0f} {x2 - (x3 - x1) / 6:.0f} {y2 - (y3 - y1) / 6:.0f}'
              f' {x2} {y2}')
    return d + f' V{H} H0Z'


out = [f'<svg class="valley" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMax slice" aria-hidden="true">',
       f'    <path d="{smooth(BACK)}" fill="#3d3d3d"/>']

# hillside neighbourhoods on the back slopes, thinning out towards the ridge, a few windows lit
houses, lights = [], []
for _ in range(520):
    x = rnd.uniform(10, 1430)
    if 470 < x < 970:
        continue
    top, floor = at(BACK, x) + 8, at(MID, x)
    if floor - top < 10:
        continue
    y = floor - (floor - top) * (rnd.random() ** 1.6)   # denser lower down
    w, h = rnd.choice((5, 6, 7, 8)), rnd.choice((4, 5, 6))
    houses.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{w}" height="{h}"/>')
    if rnd.random() < .32:
        lights.append(f'<rect x="{x + 1:.0f}" y="{y + 1:.0f}" width="2" height="2"/>')
out.append(f'    <g fill="#4a4a4a">{"".join(houses)}</g>')

out.append(f'    <path d="{smooth(MID)}" fill="#2f2f2f"/>')

# Metrocable: from the valley floor up the western slope, with towers and cabins
cx0, cy0, cx1, cy1 = 470, at(MID, 470) - 30, 160, at(BACK, 160) + 22
cable = [f'<line x1="{cx0}" y1="{cy0:.0f}" x2="{cx1}" y2="{cy1:.0f}" stroke="#6a6a6a" stroke-width="1.2"/>']
for t in (.28, .62):
    tx, ty = cx0 + (cx1 - cx0) * t, cy0 + (cy1 - cy0) * t
    cable.append(f'<line x1="{tx:.0f}" y1="{ty:.0f}" x2="{tx:.0f}" y2="{min(at(MID, tx), at(BACK, tx) + 60):.0f}" '
                 f'stroke="#5a5a5a" stroke-width="2"/>')
for t in (.14, .45, .8):
    tx, ty = cx0 + (cx1 - cx0) * t, cy0 + (cy1 - cy0) * t
    cable.append(f'<line x1="{tx:.0f}" y1="{ty:.0f}" x2="{tx:.0f}" y2="{ty + 5:.0f}" stroke="#6a6a6a" stroke-width="1"/>'
                 f'<rect x="{tx - 5:.0f}" y="{ty + 5:.0f}" width="10" height="8" rx="2" fill="#de0001"/>')
out.append('    <g>' + ''.join(cable) + '</g>')

# downtown skyline on the valley floor; (x, width, top) plus the Coltejer needle
towers = [(430, 16, 204), (448, 22, 182), (472, 14, 196), (488, 26, 160), (516, 20, 142), (580, 18, 176),
          (600, 22, 204), (624, 16, 212), (642, 26, 200), (670, 18, 214), (690, 30, 198), (722, 20, 210), (744, 26, 202),
          (772, 18, 214), (792, 24, 200), (818, 18, 210), (838, 20, 196), (860, 26, 150), (888, 18, 128), (908, 28, 164),
          (938, 20, 184), (960, 24, 196), (986, 16, 206)]
bld, win = [], []
for x, w, top in towers:
    bld.append(f'<rect x="{x}" y="{top}" width="{w}" height="{H - top}"/>')
    for wy in range(top + 8, 232, 9):
        for wx in range(x + 4, x + w - 3, 6):
            if rnd.random() < .16:
                win.append(f'<rect x="{wx}" y="{wy}" width="2" height="3"/>')
# Edificio Coltejer: slim tower with the tapering needle top
bld.append('<path d="M544 260 V92 L558 28 L572 92 V260Z"/><rect x="540" y="108" width="36" height="152"/>')
for wy in range(116, 232, 9):
    for wx in range(545, 572, 6):
        if rnd.random() < .16:
            win.append(f'<rect x="{wx}" y="{wy}" width="2" height="3"/>')
out.append(f'    <g fill="#191919">{"".join(bld)}</g>')
out.append(f'    <g fill="#f2c46d" opacity=".75">{"".join(lights + win)}</g>')

out.append(f'    <path d="M0 238 C300 222 520 246 760 234 C1000 224 1200 242 1440 230 V{H} H0Z" fill="#fafafa"/>')
out.append('  </svg>')
svg = '\n'.join(out)

p = os.path.join(ROOT, 'index.html')
s = open(p, encoding='utf-8').read()
s, n = re.subn(r'<svg class="valley".*?</svg>', lambda m: svg, s, flags=re.S)
assert n == 1, n
open(p, 'w', encoding='utf-8').write(s)
print(f'valley: {len(houses)} houses, {len(win)} lit windows, {len(svg)} bytes')
