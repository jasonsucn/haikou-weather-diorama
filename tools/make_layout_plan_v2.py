"""V2 compact layout for the Q-style Haikou diorama (planning only).

Targets: base Ø200, land ~60% of base, sea ring ~14 u, dense old-town fabric,
marina + breakwater foreground, adjacent landmark gaps <= 60 u.
"""
from PIL import Image, ImageDraw, ImageFont
import math
import os
import random

W, H = 1400, 900
random.seed(7)

BG = "#0c1826"
PANEL = "#12202f"
INK = "#eef4f8"
MUTED = "#9db1c5"
ACCENT = "#f2c879"
SEA = "#155a72"
SEA_LIGHT = "#1d6e88"
LAND = "#7bab5e"
LAND_DARK = "#67924e"
SAND = "#dcc493"
BLOCK = ["#e8c6a0", "#d9a49c", "#a9c9d8", "#c9d9a9", "#efe0b8", "#b9a7c9", "#e6b98f"]

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

CX, CY, R = 470, 468, 360
U = R / 100.0  # px per world unit (base radius = 100 u)


def font(size, bold=False):
    for p in (r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
              r"C:\Windows\Fonts\simhei.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def P(x, y):
    return (CX + x * U, CY - y * U)


def blob(cx, cy, r0, wobble, yscale, points=110, phase=0.0):
    out = []
    for i in range(points):
        a = 2 * math.pi * i / points
        r = r0 * (1 + wobble * math.sin(3 * a + phase) + 0.04 * math.sin(7 * a + phase * 2))
        out.append((cx + math.cos(a) * r, cy + math.sin(a) * r * yscale))
    return out


def rrect(box, radius, fill, outline=None, width=1):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


# ---------------------------------------------------------------- base + sea
d.ellipse([CX - R, CY - R, CX + R, CY + R], fill="#6f5a42")
d.ellipse([CX - R + 10, CY - R + 10, CX + R - 10, CY + R - 10], fill="#7d664b")
d.ellipse([CX - R + 20, CY - R + 20, CX + R - 20, CY + R - 20], fill=SEA)
for k in range(5):
    rr = R - 24 - k * 10
    d.ellipse([CX - rr, CY - rr, CX + rr, CY + rr], outline="#23738c", width=1)
for i in range(48):
    a = random.uniform(0, 2 * math.pi)
    rr = random.uniform(84, 98) * U
    x, y = CX + math.cos(a) * rr, CY + math.sin(a) * rr * 0.94
    d.arc([x - 8, y - 3, x + 8, y + 3], 200, 340, fill="#2f88a2", width=2)

# ---------------------------------------------------------------- island
main = blob(0, -2, 83, 0.075, 0.93, phase=0.4)
d.polygon([P(x, y) for x, y in main], fill=SAND)
inner = blob(0, -2, 79.5, 0.075, 0.93, phase=0.4)
d.polygon([P(x, y) for x, y in inner], fill=LAND, outline=LAND_DARK, width=2)

# river channel: cuts the NW headland (Haidian) off the main island
channel = [(-83, 22), (-72, 33), (-60, 42), (-50, 51), (-41, 60)]
pts = [P(x, y) for x, y in channel]
d.line(pts, fill=SAND, width=int(8.2 * U), joint="curve")
d.line(pts, fill=SEA_LIGHT, width=int(6.4 * U), joint="curve")
d.line(pts, fill=SEA, width=int(5.6 * U), joint="curve")

# ---------------------------------------------------------------- roads
roads = [
    ((-56, 30), (-56, -36)),   # waterfront avenue
    ((-44, -10), (36, -10)),   # cross street
    ((-28, 26), (-28, -42)),   # old town lane
    ((14, 26), (14, -44)),     # CBD / park avenue
    ((38, 12), (38, -38)),     # east lane
    ((-72, 12), (-56, 16)),    # coast link
]
for a, b in roads:
    d.line([P(*a), P(*b)], fill="#e9e0cc", width=6)
    d.line([P(*a), P(*b)], fill="#cfc4ab", width=2)

# ---------------------------------------------------------------- Wanlv Park
park = [(-14, -45), (26, -45), (28, -21), (2, -17), (-16, -23)]
d.polygon([P(x, y) for x, y in park], fill="#93c474", outline="#d5e9ba", width=3)
lx, ly = P(6, -31)
d.ellipse([lx - 7.4 * U, ly - 4.0 * U, lx + 7.4 * U, ly + 4.0 * U], fill="#2f88a2", outline="#bfe8ee", width=3)
d.ellipse([lx - 6.4 * U, ly - 3.2 * U, lx + 6.4 * U, ly + 3.2 * U], fill="#43a3bb")
d.arc([lx - 10 * U, ly - 7 * U, lx + 10 * U, ly + 7 * U], 200, 340, fill="#e9e0cc", width=4)
d.line([P(-10, -21), P(24, -43)], fill="#e9e0cc", width=3)
for i in range(9):
    tx = -10 + i * 4.5
    ty = -22 - (i % 3) * 5
    px, py = P(tx, ty)
    d.ellipse([px - 4, py - 4, px + 4, py + 4], fill="#4f7d3c")

# ---------------------------------------------------------------- volcano
vx, vy = P(46, -26)
for k, col in ((18, "#77945e"), (14, "#89a667"), (10, "#9db473"), (6.5, "#b3c07f")):
    d.ellipse([vx - k * U, vy - k * U * 0.78, vx + k * U, vy + k * U * 0.78], fill=col)
d.ellipse([vx - 3.6 * U, vy - 2.4 * U, vx + 3.6 * U, vy + 2.4 * U], fill="#6a5344")
d.ellipse([vx - 2.4 * U, vy - 1.5 * U, vx + 2.4 * U, vy + 1.5 * U], fill="#3d2c24")
d.ellipse([vx + 11 * U - 4, vy - 4, vx + 11 * U + 4, vy + 4], fill=ACCENT)

# ---------------------------------------------------------------- green hill
hx, hy = P(-6, 38)
for k, col in ((15, "#6f9a55"), (11, "#7faa61"), (6.5, "#8fb96d")):
    d.ellipse([hx - k * U, hy - k * U * 0.72, hx + k * U, hy + k * U * 0.72], fill=col)

# ---------------------------------------------------------------- old town fabric (grid, dense)
for ix in range(10):
    for iy in range(11):
        x = -52 + ix * 4.9 + random.uniform(-0.7, 0.7)
        y = -36 + iy * 5.4 + random.uniform(-0.7, 0.7)
        if x > -12 or y > 28:
            continue
        if abs(x + 56) < 2.2 or abs(x + 28) < 2.2 or abs(y + 10) < 1.6:
            continue
        w = random.uniform(3.0, 4.2)
        h = random.uniform(3.4, 4.8)
        px, py = P(x, y)
        rrect([px - w * U / 2, py - h * U / 2, px + w * U / 2, py + h * U / 2], 2,
              random.choice(BLOCK), outline="#6b5a45", width=1)
        if random.random() < 0.4:
            d.line([(px - w * U / 2 + 2, py), (px + w * U / 2 - 2, py)], fill="#7a6750", width=1)

# CBD cluster
cbd = [(-16, 14), (-7, 20), (3, 14), (12, 21), (22, 12), (-13, 3), (1, 2), (17, 1), (-4, 25)]
for i, (x, y) in enumerate(cbd):
    px, py = P(x, y)
    w = random.uniform(5.5, 7.5)
    h = random.uniform(5.5, 7.5)
    rrect([px - w * U / 2, py - h * U / 2, px + w * U / 2, py + h * U / 2], 4,
          "#b9d2e2" if i % 2 else "#d6e6ef", outline="#5d7484", width=1)
    d.line([(px - w * U / 2 + 3, py), (px + w * U / 2 - 3, py)], fill="#8fb0c4", width=1)

# east residential clusters
for i in range(16):
    x = 20 + random.uniform(0, 36)
    y = random.uniform(-18, 26)
    if (x - 46) ** 2 + (y + 26) ** 2 < 20 ** 2:
        continue
    if abs(x - 38) < 2.5 or abs(y + 10) < 2.0:
        continue
    px, py = P(x, y)
    w = random.uniform(3.6, 5.6)
    h = random.uniform(3.6, 5.2)
    rrect([px - w * U / 2, py - h * U / 2, px + w * U / 2, py + h * U / 2], 3,
          random.choice(BLOCK), outline="#6b5a45", width=1)

# ---------------------------------------------------------------- trees
def in_island(x, y, margin=0.0):
    return (x / 82.0) ** 2 + ((y + 2) / 76.0) ** 2 < (1.0 - margin)


for i in range(110):
    x = random.uniform(-76, 76)
    y = random.uniform(-48, 46)
    if not in_island(x, y, 0.02):
        continue
    if -84 < x < -38 and 20 < y < 62:
        continue
    if (x - 6) ** 2 / 7.8 ** 2 + (y + 31) ** 2 / 4.4 ** 2 < 1.15:
        continue
    if (x - 46) ** 2 / 7 ** 2 + (y + 26) ** 2 / 5.5 ** 2 < 1.2:
        continue
    px, py = P(x, y)
    r = random.uniform(2.2, 3.8)
    d.ellipse([px - r, py - r * 0.9, px + r, py + r * 0.9], fill="#4f7d3c")
    d.ellipse([px - r * 0.55, py - r * 0.7, px + r * 0.15, py + r * 0.15], fill="#6f9c53")

# ---------------------------------------------------------------- marina + breakwater
d.arc([CX - 92 * U, CY - 30 * U, CX - 30 * U, CY + 52 * U], 35, 145, fill="#b9a884", width=6)
for t in range(40, 145, 7):
    a = math.radians(t)
    bx = CX - 61 * U + 31 * U * math.cos(a)
    by = CY + 11 * U + 41 * U * math.sin(a)
    d.ellipse([bx - 2.4, by - 2.4, bx + 2.4, by + 2.4], fill="#8e7d60")
for yy, xx in ((-56, -80), (-62, -76), (-68, -72)):
    d.line([P(xx, yy), P(xx + 16, yy - 2)], fill="#c8b48c", width=5)
    for b in range(3):
        bx = xx + 3 + b * 5.6
        px, py = P(bx, yy - 1.4)
        d.ellipse([px - 4.0 * U, py - 1.4 * U, px + 4.0 * U, py + 1.4 * U],
                  fill="#f5f2e8", outline="#3f5360", width=1)
        d.line([(px, py - 1.2 * U), (px, py - 3.8 * U)], fill="#6b5a45", width=2)
        d.polygon([(px, py - 3.8 * U), (px + 2.6 * U, py - 3.0 * U), (px, py - 2.1 * U)],
                  fill="#ffffff")

# east coast village + lane
for i in range(9):
    x = 46 + (i % 3) * 6.5 + random.uniform(-1, 1)
    y = 12 - (i // 3) * 7 + random.uniform(-1, 1)
    if (x - 46) ** 2 + (y + 26) ** 2 < 18 ** 2:
        continue
    px, py = P(x, y)
    w, h = random.uniform(3.6, 5.2), random.uniform(3.6, 5.0)
    rrect([px - w * U / 2, py - h * U / 2, px + w * U / 2, py + h * U / 2], 3,
          random.choice(BLOCK), outline="#6b5a45", width=1)
d.line([P(58, 18), P(58, -14)], fill="#e9e0cc", width=4)

# distant sailboats in the sea ring
for sx, sy, ss in ((88, 20, 1.0), (62, 70, 0.85), (90, -34, 0.8)):
    px, py = P(sx, sy)
    d.ellipse([px - 9 * ss, py - 2.2 * ss, px + 9 * ss, py + 2.2 * ss], fill="#f5f2e8", outline="#3f5360", width=1)
    d.line([(px, py - 2 * ss), (px, py - 13 * ss)], fill="#6b5a45", width=2)
    d.polygon([(px, py - 13 * ss), (px + 6 * ss, py - 4 * ss), (px, py - 2 * ss)], fill="#ffffff")

# ---------------------------------------------------------------- bridge (crosses the channel)
d.line([P(-78, 46), P(-58, 28)], fill="#ffffff", width=11)
d.line([P(-78, 46), P(-58, 28)], fill="#f2c0aa", width=6)
for x, y in ((-73, 41.5), (-63, 32.5)):
    px, py = P(x, y)
    d.ellipse([px - 5, py - 5, px + 5, py + 5], fill="#ffffff")
    d.ellipse([px - 2, py - 2, px + 2, py + 2], fill="#e87869")

# ---------------------------------------------------------------- landmark pins
LM = [
    ("1", "世纪大桥", "白桥双塔 · 车流灯带", -68, 37, "#ffffff"),
    ("2", "骑楼老街", "连续拱廊 · 彩色立面", -58, -4, "#f7b05c"),
    ("3", "钟楼", "红砖基座 · 四面钟", -54, -26, "#e87869"),
    ("4", "云洞图书馆", "白色壳体 · 圆形洞口", -66, 8, "#ffffff"),
    ("5", "万绿园", "草坪湖面 · 椰林步道", 18, -36, "#78c878"),
    ("6", "火山口", "锥形山体 · 观景台", 46, -26, "#c8785a"),
    ("7", "海甸岛", "渔村灯塔 · 椰林海岸", -70, 52, "#6ec8dc"),
]
for num, name, sub, x, y, col in LM:
    px, py = P(x, y)
    d.ellipse([px - 19, py - 19, px + 19, py + 19], fill=col, outline="#0c1826", width=4)
    d.text((px, py), num, font=font(19, True), fill="#14202e", anchor="mm")

# small area label
d.text(P(-60, 60), "海甸岛", font=font(16, True), fill=INK, anchor="mm")

# ---------------------------------------------------------------- legend panel
x0 = 900
d.rounded_rectangle([x0 - 34, 44, W - 36, H - 40], radius=20, fill=PANEL, outline="#22384c", width=2)
d.text((x0, 78), "V2 · 紧凑布局", font=font(34, True), fill=INK)
d.text((x0, 124), "圆形底座 Ø200 · 主岛 166×154 · 海环 ≈18", font=font(17), fill=MUTED)

y = 176
for num, name, sub, *_ , col in LM:
    d.ellipse([x0, y - 2, x0 + 30, y + 28], fill=col)
    d.text((x0 + 8, y + 3), num, font=font(19, True), fill="#14202e")
    d.text((x0 + 44, y - 4), name, font=font(22, True), fill=INK)
    d.text((x0 + 44, y + 27), sub, font=font(15), fill=MUTED)
    y += 72

by = 724
d.rounded_rectangle([x0 - 6, by - 14, W - 56, by + 82], radius=12, fill="#0e1c2a", outline="#2b4a60", width=1)
d.text((x0 + 8, by), "紧凑度", font=font(20, True), fill=ACCENT)
metrics = [("陆地占底座", "≈64%"), ("海面环宽", "≈18 u"), ("岛内内容覆盖", "≈72%"), ("最大相邻间距", "≈60 u")]
mx = x0 + 8
for label, val in metrics:
    d.text((mx, by + 30), label, font=font(13), fill=MUTED)
    d.text((mx, by + 49), val, font=font(17, True), fill=INK)
    mx += 112

# ---------------------------------------------------------------- title + footer
d.text((66, 56), "海口 Q 版微缩景观 · V2 紧凑布局", font=font(36, True), fill=INK)
d.text((68, 104), "比 V1：底座 Ø224→Ø200，主岛放大，海环 30→18，岛心填满老城肌理 / 绿丘 / 码头", font=font(17), fill=MUTED)

# north (right side, away from title)
ax, ay = 792, 158
d.line([(ax, ay + 36), (ax, ay - 34)], fill=MUTED, width=3)
d.polygon([(ax, ay - 46), (ax - 9, ay - 26), (ax + 9, ay - 26)], fill=MUTED)
d.text((ax - 6, ay + 42), "N", font=font(18, True), fill=MUTED)

# camera
cam = P(-104, -84)
d.line([(cam[0] + 10, cam[1] - 4), (cam[0] + 52, cam[1] - 28)], fill=ACCENT, width=3)
d.ellipse([cam[0] - 8, cam[1] - 8, cam[0] + 8, cam[1] + 8], fill=ACCENT)
d.text((cam[0] + 60, cam[1] - 30), "主视角", font=font(16), fill=ACCENT)

d.text((66, H - 46), "M2 阶段先出灰度密度图与 3 角度预览，密度达标后再细节建模", font=font(15), fill=MUTED)

img.save("docs/layout-plan-v2.png")
print("saved docs/layout-plan-v2.png", img.size)
