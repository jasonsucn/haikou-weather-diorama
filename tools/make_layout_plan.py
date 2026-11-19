"""Top-view layout sketch for the Q-style Haikou diorama (planning only)."""
from PIL import Image, ImageDraw, ImageFont
import math, os

W, H = 1200, 820
img = Image.new("RGB", (W, H), "#0e1a28")
d = ImageDraw.Draw(img)

CX, CY, R = 470, 430, 350
SCALE = R / 112.0
SEA = "#14546b"
LAND = "#79a95c"
SAND = "#d8c08b"
INK = "#eef3f7"
MUTED = "#9fb3c8"
PANEL = "#13212f"


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
    return (CX + x * SCALE, CY - y * SCALE)


def blob(cx, cy, r0, wobble, points=72, phase=0.0):
    out = []
    for i in range(points):
        a = 2 * math.pi * i / points
        r = r0 * (1 + wobble * math.sin(3 * a + phase) + 0.05 * math.sin(7 * a + phase * 2))
        out.append((cx + math.cos(a) * r, cy + math.sin(a) * r * 0.68))
    return out


# base tray
d.ellipse([CX - R, CY - R, CX + R, CY + R], fill="#6b563f")
d.ellipse([CX - R + 12, CY - R + 12, CX + R - 12, CY + R - 12], fill=SEA)
d.ellipse([CX - R + 26, CY - R + 26, CX + R - 26, CY + R - 26], outline="#2c7a92", width=3)

# main island
main = blob(6, -4, 76, 0.10)
d.polygon([P(x, y) for x, y in main], fill=SAND)
d.polygon([P(x, y) for x, y in blob(6, -4, 72, 0.10)], fill=LAND, outline="#5d8a46", width=2)

# Haidian island
d.polygon([P(x, y) for x, y in blob(-70, 48, 27, 0.12, phase=1.2)], fill=SAND)
d.polygon([P(x, y) for x, y in blob(-70, 48, 24, 0.12, phase=1.2)], fill=LAND)

# Wanlv park
park = [(-4, -26), (38, -28), (40, -48), (2, -50)]
d.polygon([P(x, y) for x, y in park], fill="#8fc06b", outline="#c9dfae", width=3)

# roads
for a, b in [((-28, 32), (-28, -30)), ((-18, -22), (62, -22)), ((20, 32), (20, -52))]:
    d.line([P(*a), P(*b)], fill="#e8e0cf", width=3)

# Century bridge
d.line([P(-28, 20), P(-52, 40)], fill="#ffffff", width=6)
for x, y in ((-28, 20), (-52, 40)):
    px, py = P(x, y)
    d.ellipse([px - 5, py - 5, px + 5, py + 5], fill="#f2b3a0")

LM = [
    ("1", "世纪大桥", "白桥双塔 · 车流", -50, 38, "#f7f7f2"),
    ("2", "骑楼老街", "连续拱廊 · 招牌", -28, 2, "#f7b05c"),
    ("3", "钟楼", "红砖白塔 · 钟面", -26, -34, "#e87869"),
    ("4", "云洞图书馆", "白色壳体 · 圆洞", -33, 14, "#ffffff"),
    ("5", "万绿园", "草坪湖面 · 椰林", 18, -38, "#78c878"),
    ("6", "火山口", "锥形山体 · 观景台", 58, -34, "#c8785a"),
    ("7", "海甸岛", "椰林渔村 · 灯塔", -72, 50, "#6ec8dc"),
]
for num, name, sub, x, y, col in LM:
    px, py = P(x, y)
    d.ellipse([px - 21, py - 21, px + 21, py + 21], fill=col, outline="#0e1a28", width=4)
    f = font(21, True)
    d.text((px - d.textlength(num, font=f) / 2, py - 12), num, font=f, fill="#14202e")

# camera
cam = P(-96, -116)
d.line([(cam[0] + 12, cam[1] - 4), (cam[0] + 64, cam[1] - 34)], fill=(255, 214, 130), width=3)
d.ellipse([cam[0] - 9, cam[1] - 9, cam[0] + 9, cam[1] + 9], fill=(255, 214, 130))
d.text((cam[0] + 72, cam[1] - 34), "主视角", font=font(17), fill=(255, 214, 130))

# north
ax, ay = 470, 96
d.line([(ax, ay + 42), (ax, ay - 42)], fill=MUTED, width=3)
d.polygon([(ax, ay - 54), (ax - 9, ay - 34), (ax + 9, ay - 34)], fill=MUTED)
d.text((ax - 7, ay + 50), "N", font=font(20, True), fill=MUTED)

# legend panel
x0, y0 = 880, 70
d.rounded_rectangle([x0 - 24, y0 - 36, W - 40, H - 44], radius=18, fill=PANEL, outline="#22384c", width=2)
d.text((x0, y0), "地标清单", font=font(30, True), fill=INK)
d.text((x0, y0 + 44), "圆形底座 Ø 224 · 海面环宽 ~14", font=font(17), fill=MUTED)
y = y0 + 100
for num, name, sub, *_ , col in LM:
    d.ellipse([x0, y - 2, x0 + 26, y + 24], fill=col)
    f = font(18, True)
    d.text((x0 + 7, y + 1), num, font=f, fill="#14202e")
    d.text((x0 + 40, y - 4), name, font=font(21, True), fill=INK)
    d.text((x0 + 40, y + 24), sub, font=font(16), fill=MUTED)
    y += 84

d.text((x0, H - 56), "动画：海浪 · 云 · 椰树 · 渔船 · 车流 · 飞鸟", font=font(15), fill="#8fd0a0")

d.text((70, 40), "海口 Q 版微缩景观 · 俯视布局方案 v1", font=font(34, True), fill=INK)
d.line([(70, 132), (70 + 50 * SCALE / 4, 132)], fill=MUTED, width=4)
d.text((70, 104), "约 1 km（示意）", font=font(16), fill=MUTED)

img.save("docs/layout-plan.png")
print("saved docs/layout-plan.png", img.size)
